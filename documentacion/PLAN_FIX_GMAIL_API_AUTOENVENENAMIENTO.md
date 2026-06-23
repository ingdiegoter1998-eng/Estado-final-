# Plan de implementación: detener el auto-envenenamiento de Gmail API (429)

> **Para el agente que implementa:** Este documento es autocontenido. NO necesitas
> el historial del chat. Lee la sección "Reglas de oro" antes de tocar nada y sigue
> las fases en orden. Cada tarea indica archivo, ubicación, cambio y criterio de
> aceptación. Si una tarea no se puede completar tal cual, **detente y reporta**; no
> improvises soluciones alternativas.

---

## 0. Contexto (por qué hacemos esto)

El aplicativo usa **un solo buzón institucional** (`correspondencia@esehospitaldelsarare.gov.co`)
vía **Gmail API + Pub/Sub + Celery + Redis**. Con tráfico real casi nulo (~1 correo
cada 30 h) el sistema entra en **HTTP 429 `User-rate limit exceeded`** durante horas.

Diagnóstico confirmado con código y logs de producción (23-jun-2026):

1. **Descarga `format='raw'` en escaneos masivos.** `fetch_unread_messages` lista hasta
   `GMAIL_API_MAX_SCAN_MESSAGES=300` no-leídos y baja **cada uno completo (con adjuntos)**.
2. **Re-escaneo sin acotar fecha.** `is:unread` re-descarga los mismos correos en cada
   ciclo del backup poll (30 min) y de rebotes (10 min). Esto dispara un límite de
   **ancho de banda / diario** de Google → `Retry-After` de **~5 horas** (firma de límite
   diario, no de tasa por minuto).
3. **Bucle de re-entrega Pub/Sub.** Si hay 429 no se hace `ack`; Pub/Sub re-entrega las
   mismas notificaciones, que vuelven a disparar `history.list`. El sistema se golpea solo.
4. **Cooldown global único.** Un 429 de *lectura* activa el mismo cooldown que bloquea
   `aprobar_y_enviar_respuestas_pendientes` → **las salidas no se envían** aunque
   `messages.send` tenga cuota. Es la causa de "el aplicativo falla".

**Objetivo:** eliminar el consumo improductivo de cuota y desacoplar lectura de envío,
**sin cambiar la arquitectura** (sigue siendo un buzón único + Gmail API + Pub/Sub).

---

## Reglas de oro (NO violar)

- ❌ **NO** introducir múltiples cuentas Gmail, Domain-Wide Delegation, ni Service Account
  para impersonar usuarios. El diseño es **un buzón institucional único**.
- ❌ **NO** reactivar Postmark ni SMTP como proveedor principal. `EMAIL_PROVIDER=gmail_api`
  y `EMAIL_INGESTION_PROVIDER=gmail_api` se mantienen.
- ❌ **NO** eliminar la cola persistente `gmail_history_queue.py`; se sigue usando.
- ✅ Mantener compatibilidad con IMAP manual bajo demanda (no tocar `IMAPMailboxProvider`).
- ✅ Cada cambio debe dejar los tests existentes en verde.
- ✅ Trabajar en la rama `main`. Un commit por fase (A, B, C, D, E).

---

## Archivos involucrados (mapa rápido)

| Archivo | Rol en este plan |
|---------|------------------|
| `correspondencia/utils/email_provider.py` | `GmailAPIInboxProvider`: `fetch_*`, `_list_message_ids` (Fase A) |
| `hospital_document_management/settings.py` | Intervalos Beat y `GMAIL_API_MAX_SCAN_MESSAGES` (Fase B) |
| `correspondencia/management/commands/gmail_history_sync.py` | Drenaje por history (Fase B) |
| `correspondencia/management/commands/gmail_pubsub_pull.py` | `ack` de Pub/Sub (Fase C) |
| `correspondencia/utils/gmail_history_queue.py` | Cola persistente (Fase C, solo lectura/uso) |
| `correspondencia/utils/gmail_rate_limit.py` | Cooldown por scope (Fase D, E) |
| `correspondencia/tasks.py` | Tareas periódicas: scope de cooldown (Fase D) |
| `correspondencia/tests/test_gmail_history_sync.py` | Tests existentes a mantener verdes |

---

## FASE A — Eliminar descargas `format='raw'` para detección

**Problema:** `GmailAPIInboxProvider.fetch_messages_by_uids` usa `format='raw'`
(`email_provider.py` ~línea 330) y se invoca sobre listas de hasta 300 mensajes en
`fetch_unread_messages`. `raw` descarga el cuerpo completo + adjuntos = consumo enorme
de ancho de banda.

### Tarea A.1 — Separar "detección" (metadata) de "descarga real" (raw)

**Archivo:** `correspondencia/utils/email_provider.py`, clase `GmailAPIInboxProvider`.

1. Crear un método nuevo `fetch_metadata_by_uids(self, folder_name, uids)` que use
   `format='metadata'` con `metadataHeaders=['Message-ID', 'Date', 'From', 'Subject', 'To']`.
   Debe devolver objetos normalizados suficientes para **decidir si un correo ya está
   radicado / es duplicado**, SIN descargar el cuerpo.
   - Reutiliza el patrón de `fetch_headers` (que ya usa `format='metadata'`, ~línea 306-322).
2. **No** cambiar `fetch_messages_by_uids` (sigue en `raw`): se usará **solo** para los
   IDs que realmente se van a radicar.

**Criterio de aceptación:** existe `fetch_metadata_by_uids`; `fetch_headers` sigue igual;
ningún test rompe.

### Tarea A.2 — `fetch_unread_messages` deja de bajar todo en raw

**Archivo:** `correspondencia/utils/email_provider.py`, método `fetch_unread_messages`
(~línea 373-375).

Cambiar el flujo a dos pasos:
1. Listar IDs con `_list_message_ids(folder_name, query_parts=['is:unread'])` (igual que hoy).
2. Obtener **metadata** de esos IDs (`fetch_metadata_by_uids`), NO raw.
3. Devolver la metadata. El consumidor (`procesar_emails_seguro` / ingestión) decidirá con
   metadata qué IDs son nuevos y solo entonces llamará `fetch_messages_by_uids` (raw) para
   esos pocos.

> Si el consumidor actual espera el cuerpo completo en `fetch_unread_messages`, NO cambiar
> la firma de golpe. En su lugar, dejar `fetch_unread_messages` devolviendo metadata y
> ajustar el llamador en `correspondencia/utils/email_ingestion.py` /
> `procesar_emails_seguro.py` para que descargue raw solo de los IDs no radicados.
> **Si esto implica cambios de más de ~40 líneas en el llamador, detente y reporta** para
> revisión humana antes de continuar.

**Criterio de aceptación:** un escaneo de 300 no-leídos genera 300 `messages.get`
**metadata** (1 unidad c/u) + N `messages.get` **raw** solo de los nuevos (N≈0 en estado
estable), en lugar de 300 raw. Verificable revisando el código y, si es posible, contando
llamadas en un test con mock.

### Tarea A.3 — Reducir el tope de escaneo

**Archivo:** `hospital_document_management/settings.py`.

Añadir/confirmar el setting y bajar el default de escaneo (hoy 300):

```python
GMAIL_API_MAX_SCAN_MESSAGES = int(os.getenv('GMAIL_API_MAX_SCAN_MESSAGES', '50'))
```

**Criterio de aceptación:** `settings.GMAIL_API_MAX_SCAN_MESSAGES == 50` por defecto;
configurable por entorno.

---

## FASE B — Pub/Sub como vía principal; backup poll mínimo

**Problema:** el backup poll (`procesar_emails_periodico`) y rebotes re-escanean la
bandeja completa aunque Pub/Sub ya entrega los nuevos.

### Tarea B.1 — Acotar el backup poll por fecha reciente

**Archivo:** `correspondencia/utils/email_provider.py` (método `fetch_messages_since`) y/o
el llamador en `procesar_emails_seguro`.

- Asegurar que el backup poll consulta solo correos **del día actual** (ya existe
  `fetch_messages_since` con `after:YYYY/MM/DD`). Confirmar que el backup poll usa
  `fetch_messages_since(date_gte=hoy)` y **metadata primero** (igual que Fase A.2), no raw
  de toda la bandeja.

**Criterio de aceptación:** el backup poll nunca descarga más de
`GMAIL_API_MAX_SCAN_MESSAGES` mensajes y filtra por fecha del día.

### Tarea B.2 — Espaciar/confirmar intervalos en `.env` y settings

**Archivo:** `.env` (producción) y `hospital_document_management/settings.py` (defaults).

Confirmar estos valores (ya están así en `.env`, validar que sigan):

```env
CELERY_GMAIL_PUBSUB_PULL_INTERVAL=180
CELERY_GMAIL_BACKUP_POLL_INTERVAL=1800
CELERY_APROBAR_RESPUESTAS_INTERVAL=900
GMAIL_API_HISTORY_FETCH_BATCH_SIZE=4
GMAIL_API_HISTORY_FETCH_DELAY_MS=500
GMAIL_API_PUBSUB_PULL_MAX_MESSAGES=3
GMAIL_API_MAX_SCAN_MESSAGES=50
```

**Criterio de aceptación:** valores presentes; ningún intervalo de lectura por debajo de
los indicados.

### Tarea B.3 — `history_sync` no re-lista innecesariamente

**Archivo:** `correspondencia/management/commands/gmail_history_sync.py`,
método `_refresh_pending_queue` (~línea 188-230).

Hoy `_refresh_pending_queue` llama `history.list` desde `start_history_id` **en cada
ejecución**, aunque ya haya cola pendiente. Cambiar para que:
- Si `pending_count() > 0` al inicio, **drene primero la cola** y **omita** la llamada
  `history.list` de ese ciclo (no re-descubrir).
- Solo cuando la cola esté vacía, consultar `history.list` para descubrir nuevos.

**Criterio de aceptación:** con cola no vacía, un ciclo de `gmail_history_sync` hace
**0** llamadas a `history.list`. Cubrir con test (mock de `list_history` con `assert_not_called`).

---

## FASE C — Romper el bucle de re-entrega de Pub/Sub

**Problema:** `gmail_pubsub_pull.py` solo hace `ack` si el history sync completó. Con 429,
no hay ack → Pub/Sub re-entrega → más llamadas.

### Tarea C.1 — `ack` tras registrar el `historyId` en la cola persistente

**Archivo:** `correspondencia/management/commands/gmail_pubsub_pull.py`, método `handle`
(~línea 42-99).

Reordenar la lógica:
1. Tras `pull`, extraer `history_ids` de los mensajes (ya se hace, líneas 51-59).
2. **Registrar** esos `historyId` / disparar el merge en la cola persistente
   (`gmail_history_queue.merge_pending_ids` o el mecanismo equivalente que use
   `gmail_history_sync`) **antes** de decidir el ack.
3. Hacer `ack` de las notificaciones Pub/Sub **siempre que el historyId quede persistido**,
   aunque el drenaje real (descarga de mensajes) se difiera por cooldown.
4. El drenaje posterior se hace desde la **cola interna**, no re-pidiendo a Pub/Sub.

> El objetivo: una notificación Pub/Sub se procesa **una sola vez**. El backlog de mensajes
> a descargar vive en Redis (cola persistente), no en Pub/Sub.

**Criterio de aceptación:** ante cooldown activo, las notificaciones Pub/Sub se **ackean**
(no se re-entregan) y su `historyId` queda en la cola persistente para drenar luego.
Añadir/ajustar test que verifique el `ack` aun con rate limit.

> ⚠️ Si el rediseño del ack resulta ambiguo respecto a la semántica actual de
> "reentregar para no perder correos", **detente y reporta** con tu propuesta antes de
> implementar. Perder un correo entrante es inaceptable; preferimos ackear + cola interno.

---

## FASE D — Separar cooldown de LECTURA del de ENVÍO

**Problema:** un único cooldown (`gmail_rate_limit.py`) bloquea lectura y envío por igual.

### Tarea D.1 — Cooldown con `scope`

**Archivo:** `correspondencia/utils/gmail_rate_limit.py`.

Introducir un parámetro `scope` con valores `'read'` y `'send'` (default `'read'` para
no romper llamadas existentes). Claves de cache separadas:

```python
GMAIL_API_RATE_LIMIT_CACHE_KEY_READ = 'correspondencia:gmail_api_rate_limit_until:read'
GMAIL_API_RATE_LIMIT_CACHE_KEY_SEND = 'correspondencia:gmail_api_rate_limit_until:send'
```

Funciones a actualizar (mantener firmas retrocompatibles vía `scope='read'` por defecto):
- `remember_gmail_rate_limit(exc_or_text, *, fallback_seconds=900, scope='read')`
- `get_gmail_rate_limit_until(scope='read')`
- `gmail_rate_limit_message(prefix=..., scope='read')`
- `should_skip_gmail_api_celery_task(task_name, *, logger=None, scope='read')`

**Criterio de aceptación:** un 429 con `scope='read'` NO afecta a `get_gmail_rate_limit_until('send')`
y viceversa. Cubrir con test unitario.

### Tarea D.2 — Asignar scope a cada operación

**Archivo:** `correspondencia/tasks.py`.

| Tarea / operación | scope |
|-------------------|-------|
| `gmail_pubsub_pull_periodico` | `read` |
| `procesar_emails_periodico` (backup poll) | `read` |
| `procesar_rebotes_periodico` | `read` |
| `gmail_history_sync` / `list_history` / `fetch_*` | `read` |
| `aprobar_y_enviar_respuestas_pendientes_periodico` | `send` |
| Envío saliente (`messages.send`, `outbound_gmail_api`) | `send` |

- En `gmail_client.py`, cuando un 429 venga de `send_message`, registrar con `scope='send'`;
  cuando venga de `list_history` / lectura, `scope='read'`.
- En `aprobar_y_enviar_respuestas_pendientes_periodico` (~línea 374-388), el
  `should_skip_gmail_api_celery_task(...)` debe usar `scope='send'`.

**Criterio de aceptación:** con un 429 de lectura activo, la tarea de aprobación/envío
**NO** se omite por cooldown de lectura (solo se omitiría por un 429 propio de `send`).
Verificar con test: simular cooldown read activo y comprobar que la aprobación procede.

> ⚠️ El flag manual `CELERY_PAUSE_GMAIL_API_TASKS=true` debe seguir pausando **todo**
> (read y send), porque es el interruptor de emergencia del operador. No lo dividas.

---

## FASE E — Respetar el `Retry-After` real de Google

**Problema:** si el cooldown local expira antes que el bloqueo real de Google, al reanudar
se vuelve a golpear y se **renueva** el 429.

### Tarea E.1 — Verificar el cálculo del cooldown

**Archivo:** `correspondencia/utils/gmail_rate_limit.py`, `remember_gmail_rate_limit`.

- Confirmar que cuando el error trae `Retry after <timestamp>`, el cooldown dura
  **hasta ese timestamp + buffer** y el `timeout` del cache cubre toda la ventana
  (hoy: `timeout = retry_after - now`, correcto).
- `GMAIL_API_RATE_LIMIT_COOLDOWN_BUFFER_SECONDS=300` se mantiene.
- Asegurar que **ninguna** ruta de código borra el cooldown antes de tiempo
  (`get_gmail_rate_limit_until` solo lo borra si ya expiró — correcto, no tocar).

**Criterio de aceptación:** dado un error con `Retry after` a +5 h, `get_gmail_rate_limit_until`
devuelve esa marca (+buffer) y no expira antes. Test con `Retry after` futuro.

---

## Orden de ejecución y commits

Implementar en este orden (mayor impacto primero):

1. **Fase D** (desacople read/send) → restablece envío de salidas de inmediato.
2. **Fase A** (sin raw masivo) → corta el consumo de ancho de banda que causa el castigo.
3. **Fase B** (Pub/Sub principal + history sin re-list) → reduce llamadas redundantes.
4. **Fase C** (ack Pub/Sub) → rompe el bucle de re-entrega.
5. **Fase E** (verificación cooldown) → cierre y robustez.

Un commit por fase, mensaje en español, prefijo `fix(gmail-api):`. Ejemplo:

```
fix(gmail-api): separa cooldown de lectura y envío (no bloquear salidas por 429 de ingesta)
```

---

## Pruebas obligatorias tras cada fase

```bash
cd /home/devdiego/Correspondencia-diciembre-1.0

# Tests de la tubería Gmail (deben quedar verdes)
./venv/bin/python -m pytest correspondencia/tests/test_gmail_history_sync.py -q
./venv/bin/python -m pytest correspondencia/tests/test_depurar_duplicados_correo_entrante.py -q

# Suite de correo completa si existe
./venv/bin/python -m pytest correspondencia/tests/ -k "gmail or rate_limit or pubsub or rebote" -q

# Sanity de Django
./venv/bin/python manage.py check
```

Tras Fases A–C, añadir tests nuevos:
- A.2: escaneo usa metadata, no raw masivo (mock contando llamadas).
- B.3: con cola no vacía, `history.list` no se llama.
- C.1: con cooldown, las notificaciones Pub/Sub se ackean y el historyId queda en cola.
- D.1/D.2: cooldown read no bloquea send.

---

## Verificación en producción (sin empeorar la cuota)

```bash
# Estado del cooldown SIN llamar a Gmail (solo cache)
./venv/bin/python manage.py shell -c "
from correspondencia.utils.gmail_rate_limit import get_gmail_rate_limit_until
print('read:', get_gmail_rate_limit_until('read'))
print('send:', get_gmail_rate_limit_until('send'))
"

# Conteo de 429 y tareas omitidas del día
journalctl -u correspondencia-celery-worker --since today --no-pager | grep -c "429"
journalctl -u correspondencia-celery-worker --since today --no-pager | grep -c "omitido"
```

Tras desplegar: reiniciar Celery para cargar cambios.

```bash
sudo systemctl restart correspondencia-celery-worker correspondencia-celery-beat
```

**Meta de éxito:** en 24 h, los 429 caen a ~0 con tráfico normal, y las salidas en
`PENDIENTE_APROBACION` se envían sin quedar bloqueadas por incidentes de ingesta.

---

## Qué hacer si algo se complica

- Si un cambio rompe tests que no entiendes, **revierte esa fase** (`git revert`) y reporta.
- Si el rediseño del ack (Fase C) o del llamador de `fetch_unread_messages` (Fase A.2)
  excede el alcance descrito, **detente y reporta** con un resumen de lo encontrado.
- Nunca dejes el árbol en estado a medias: cada fase debe compilar, pasar `manage.py check`
  y los tests antes de commitear.
