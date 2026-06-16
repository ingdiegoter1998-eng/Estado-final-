---
name: gmail-api-rate-limit
description: 'Diagnostica y contiene incidentes de Gmail API 429 (User-rate limit exceeded): pausa Celery, verifica cache de cooldown, alternativas SMTP/IMAP, y reactivacion segura. Usar cuando sync o envios fallen con HttpError 429, rateLimitExceeded, Retry after, cuota arrastrada, o gmail_operational_status en FAIL por rate limit.'
argument-hint: 'Describe el 429: hora del error, tarea que fallo, si Celery sigue activo'
user-invocable: true
disable-model-invocation: false
---

# Gmail API Rate Limit (429)

## Sintoma

- `HttpError 429` / `User-rate limit exceeded` / `rateLimitExceeded`
- `Retry after 2026-...Z` en envios, sync, perfil OAuth o history
- `sync_estado: FAIL` con ultimo error de rate limit
- La ventana **se alarga** aunque Celery parezca quieto

## Causa habitual en este proyecto

Todas estas operaciones comparten **la misma cuota por usuario** (`correspondencia@esehospitaldelsarare.gov.co`):

| Consumidor | Intervalo | API |
|---|---|---|
| `gmail_pubsub_pull_periodico` | ~60 s | history + messages.get |
| `procesar_emails_periodico` | ~5 min | messages.list |
| `procesar_rebotes_periodico` | 10 min | labels + bandeja |
| `aprobar_y_enviar_respuestas_pendientes` | 3 min | messages.send |
| Aprobacion manual UI | bajo demanda | messages.send |
| `gmail_operational_status` | manual | users.getProfile |

El bloqueo es **deslizante**: cualquier llamada durante el castigo renueva `Retry after`.

**Trampa conocida:** el cache interno (`gmail_rate_limit_until`) puede expirar **antes** de que Google levante el bloqueo. Entonces Celery reanuda y **renueva** el 429 (visto en logs: `procesar_rebotes` y `procesar_emails` a las 11:51).

## Diagnostico (sin empeorar cuota)

```bash
cd ~/Correspondencia-diciembre-1.0

# Solo cache — NO llama Gmail API
./venv/bin/python manage.py shell -c "
from correspondencia.utils.gmail_rate_limit import get_gmail_rate_limit_until, celery_gmail_api_tasks_paused
from django.utils import timezone
r = get_gmail_rate_limit_until()
print('pausa_celery:', celery_gmail_api_tasks_paused())
print('rate_limit_hasta:', r or 'LIBRE')
if r: print('min_restantes:', round((r-timezone.now()).total_seconds()/60, 1))
"

# Quien golpeo la API en los ultimos 30 min
journalctl -u correspondencia-celery-worker --since '30 min ago' --no-pager \
  | grep -iE 'omitido|429|HttpError|pubsub|rebotes|procesar_emails|aprobar'
```

**No** ejecutar `gmail_operational_status` en bucle: consulta perfil OAuth y puede renovar 429 si el cache expiro.

## Contencion inmediata

1. En `.env`:
   ```env
   CELERY_PAUSE_GMAIL_API_TASKS=true
   ```
2. Reiniciar workers (carga `.env`):
   ```bash
   sudo systemctl restart correspondencia-celery-worker correspondencia-celery-beat
   ```
3. **No** aprobar salidas ni radicar con notificacion por correo en la UI.
4. Operacion manual mientras dura el 429:
   - **Entrantes:** IMAP (`procesar_emails_seguro` con `EMAIL_INGESTION_PROVIDER=imap` override)
   - **Salidas:** `python manage.py enviar_salida_por_smtp --radicado SALIENTE-...`

## Reactivacion segura

Solo cuando `rate_limit_hasta: LIBRE` **y** han pasado **≥5 min** sin 429 en logs:

1. `.env` → `CELERY_PAUSE_GMAIL_API_TASKS=false`
2. `sudo systemctl restart correspondencia-celery-worker correspondencia-celery-beat`
3. Esperar 2–3 ciclos de pubsub (~3 min) y revisar logs: deben decir `omitido` o sync OK, **no** 429.
4. Una prueba de envio API; si 429, volver a pausar.

## Archivos clave

- `correspondencia/utils/gmail_rate_limit.py` — cache cooldown + `CELERY_PAUSE_GMAIL_API_TASKS`
- `correspondencia/tasks.py` — guard en tareas periodicas
- `hospital_document_management/settings.py` — Beat schedule
- `.env` — `CELERY_PAUSE_GMAIL_API_TASKS`, `CELERY_GMAIL_PUBSUB_PULL_INTERVAL`

## Relacionado

- `.github/skills/correos-tareas-operativas/SKILL.md` — sync IMAP, recovery, panel control
