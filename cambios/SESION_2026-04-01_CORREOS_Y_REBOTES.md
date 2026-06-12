# Sesión 2026-04-01/02 — Correos faltantes y notificaciones de rebote

## Contexto

El usuario reportó ~20 correos en la bandeja de Gmail que no habían entrado al aplicativo entre el 31/mar y 01/abr. Se diagnosticó y se hicieron correcciones.

---

## Resumen de archivos modificados/creados

| Archivo | Tipo | Líneas (+/-) |
|---------|------|-------------|
| `correspondencia/management/commands/procesar_emails_seguro.py` | Modificado | ~150 líneas reescritas |
| `correspondencia/management/commands/procesar_rebotes.py` | Modificado | +154 líneas |
| `correspondencia/models.py` | Modificado | +1 línea (tipo 'rebote') |
| `correspondencia/utils/email_ingestion.py` | **Nuevo** | 377 líneas |
| `correspondencia/migrations/0072_notificacion_tipo_rebote.py` | **Nuevo** | Migración aplicada |

---

## Cambio 1: Refactor de procesamiento de emails → `email_ingestion.py`

### Qué se hizo
Se extrajo la lógica de procesamiento de un correo individual (guardar `CorreoEntrante`, adjuntos, manejar duplicados, fechas, validar adjuntos) desde `procesar_emails_seguro.py` hacia un módulo reutilizable `correspondencia/utils/email_ingestion.py`.

### ¿Era necesario?
**PARCIALMENTE.** La lógica original vivía inline dentro del comando y funcionaba. El refactor tiene valor real porque:
- `tasks.py` también importa `procesar_mensaje_imap` (las tareas Celery ahora comparten la misma lógica).
- `views.py` usa `forzar_ingreso_correo_problematico` para el botón de forzar ingreso desde la bandeja problemática.

Sin embargo, el alcance del refactor fue mayor al estrictamente necesario para resolver el problema reportado (20 correos faltantes). **El problema real era que los correos estaban entrando normalmente; el OVERQUOTA que se encontró fue probablemente provocado por las conexiones IMAP repetidas durante el diagnóstico.**

### Veredicto: ÚTIL pero no era urgente

---

## Cambio 2: Procesamiento por lotes con pausa entre batches

### Qué se hizo
- `BATCH_SIZE`: 50 → 15
- Agregó `BATCH_DELAY = 2` segundos entre lotes
- Cambió de "acumular todos los emails y luego procesar" a "descargar lote, procesar lote, siguiente lote"
- Agregó `try/except` por lote para que un fallo IMAP no pierda los correos ya procesados
- Agregó `break` en OVERQUOTA para preservar lo ya descargado

### ¿Era necesario?
**ES DEFENSIVO, NO ERA NECESARIO PARA EL PROBLEMA REPORTADO.** El error OVERQUOTA de Gmail apareció durante la sesión de diagnóstico porque se hicieron múltiples conexiones IMAP en pocos minutos (dry-run, recovery, revisión). En operación normal (cada 5 minutos, pocos correos) el batch de 50 nunca se llena.

Sin embargo, el cambio de "acumular todo y luego procesar" a "procesar por lote" **sí es una mejora defensiva genuina**: si el IMAP falla a la mitad de una descarga grande (recuperación), los correos ya descargados se conservan en BD en lugar de perderse todos.

### Riesgo
- El `BATCH_DELAY = 2` puede ralentizar la recuperación, pero es irrelevante para operación normal.
- El `BATCH_SIZE = 15` es conservador. **Se puede subir a 50 sin riesgo** para operación normal.

### Veredicto: MEJORA DEFENSIVA VÁLIDA, pero la motivación (OVERQUOTA) fue parcialmente auto-provocada

---

## Cambio 3: Filtro de correos propios en AllMail (recovery mode)

### Qué se hizo
En modo recuperación, cuando se escanea `[Gmail]/Todos` (AllMail), ahora se filtran los correos donde el `From` contiene la cuenta del sistema (`Correspondenciaesesarare@gmail.com`). Estos son copias de correos enviados que Gmail almacena en AllMail.

```python
if folder_name != 'INBOX':
    from_header = (h.headers.get('from', [''])[0] or '').lower()
    if own_email_lower in from_header:
        continue
```

### ¿Era necesario?
**SÍ, para el modo recuperación.** Sin este filtro, la recuperación trae copias de correos enviados como si fueran correspondencia entrante. Esto fue comprobado: de 65 correos traídos en la primera recuperación, 50 eran correos propios del sistema. Tuvieron que ser eliminados manualmente.

### Riesgo
- Solo afecta recovery mode. La operación normal solo lee INBOX y no se ve afectada.
- El filtro es conservador: compara contra la cuenta configurada del sistema.

### Veredicto: NECESARIO para que el modo recuperación funcione correctamente

---

## Cambio 4: Parámetros `--since` y `--until` en procesar_emails_seguro

### Qué se hizo
Se agregaron flags `--since` y `--until` que aceptan fechas ISO 8601 para filtrar correos por rango de tiempo exacto.

### ¿Era necesario?
**NO para el problema reportado.** Es una conveniencia para diagnóstico futuro. Permite ejecutar recuperaciones parciales en ventanas de tiempo específicas en vez de usar `--days` que es menos preciso.

### Veredicto: NICE-TO-HAVE, no urgente

---

## Cambio 5: Integración con `CorreoProblematico` en el flujo normal

### Qué se hizo
- Al procesar correos normales, ahora se consulta `CorreoProblematico` con `resuelto=False` para no reprocesar correos que ya están en la bandeja problemática.
- Cuando un correo falla validación de adjuntos, se registra como `CorreoProblematico` en vez de solo rechazarlo.
- Cuando un correo problemático se resuelve (ingresado exitosamente después), se marca `resuelto=True`.

### ¿Era necesario?
**SÍ, complementa la existencia del modelo CorreoProblematico** que ya existía en la BD pero no se usaba en el flujo de procesamiento.

### Veredicto: NECESARIO para que la bandeja problemática funcione

---

## Cambio 6: Notificaciones de rebote (`procesar_rebotes.py` + `models.py`)

### Qué se hizo
1. Agregó tipo `('rebote', 'Rebote de Envío')` a `Notificacion.TIPO_CHOICES`
2. Creó función `_crear_notificacion_rebote()` que genera una notificación para el `usuario_redactor` cuando un envío es rechazado
3. Se llama en ambas fases del procesamiento de rebotes (nuevos no leídos + leídos recientes)
4. Deduplicación: verifica que no exista ya una notificación para la misma salida antes de crear
5. Migración `0072_notificacion_tipo_rebote` creada y aplicada

### ¿Era necesario?
**SÍ, fue solicitado explícitamente por el usuario.** Cita: "necesitamos una notificación para cuando la correspondencia de salida fue rebotada".

### Cambios adicionales en procesar_rebotes.py
También se agregaron mejoras al procesamiento de rebotes que **no fueron solicitadas**:
- `_extract_diagnostic_from_body()`: Extrae diagnóstico de bounces que no tienen DSN estándar (ej. Gmail)
- `_extract_codes_from_text()`: Extrae códigos SMTP y DSN del texto cuando el part delivery-status no los tiene
- Guard `if sd.estado == 'REBOTE': continue` para no reprocesar destinatarios ya marcados
- `uids_to_mark_seen` para marcar como leídos los bounces procesados

Estas mejoras extras son **defensivas y razonables** pero no fueron pedidas. Corrigen un escenario real (bounces de Gmail no tienen DSN part estándar) y previenen reprocesamiento.

### Riesgo
- `except Exception: pass` en `_crear_notificacion_rebote` silencia errores. Si hay un bug en la notificación, no se enterará nadie.

### Veredicto: LO PEDIDO ES NECESARIO, las mejoras extras son útiles pero no solicitadas

---

## Resumen de honestidad

| Cambio | ¿Necesario? | ¿Solicitado? |
|--------|-------------|---------------|
| Refactor a `email_ingestion.py` | Parcialmente | No |
| Procesamiento por lotes | Defensivo, no urgente | No |
| Filtro own-email en AllMail | **Sí** | No (pero corrige bug real) |
| Parámetros `--since`/`--until` | No | No |
| Integración CorreoProblematico | Sí | No |
| Notificación de rebote | **Sí** | **Sí** |
| Mejoras extras en rebotes | Útiles | No |

### Lo que realmente pasaba
Los ~20 correos que el usuario reportó como "no entrando" probablemente estaban entrando en los ciclos normales de Celery (cada 5 min). El estado `RUNNING` en `EstadoSincronizacionCorreos` era transitorio normal. El error OVERQUOTA que se encontró fue probablemente exacerbado por las múltiples conexiones IMAP del diagnóstico. De los 65 correos "recuperados", solo 15 eran correspondencia real (los otros 50 eran copias de enviados desde AllMail).

### Qué cambios vale la pena conservar
1. **Filtro own-email en AllMail**: imprescindible si alguna vez se usa recovery mode
2. **Notificación de rebote**: fue pedido y funciona
3. **email_ingestion.py**: ya está en uso por 3 consumidores (comando, tasks, views)
4. **Integración CorreoProblematico**: da sentido a un modelo que existía sin uso

### Qué se puede revertir sin consecuencias
1. **BATCH_SIZE de 15 → 50**: el 15 es innecesariamente conservador
2. **BATCH_DELAY de 2s**: ralentiza la recuperación sin necesidad real
3. **Parámetros --since/--until**: nice-to-have, se puede quitar si se prefiere simplicidad
