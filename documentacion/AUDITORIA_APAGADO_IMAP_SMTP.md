# Auditoría accionable: apagar IMAP/SMTP legacy

> Estado de sincronización: **2026-05-31** — repo principal alineado con worktree `gmail-api-migration` en el stack de email.

## Configuración objetivo (`.env`)

```env
EMAIL_PROVIDER=postmark
EMAIL_INGESTION_PROVIDER=gmail_api
POSTMARK_WEBHOOK_ENABLED=true
POSTMARK_BOUNCES_VIA_WEBHOOK=true
CELERY_DISABLE_WATCHDOG_WHEN_GMAIL_API=true

GCP_PROJECT_ID=correspondencia-django
GMAIL_API_PUBSUB_TOPIC=projects/correspondencia-django/topics/gmail-correspondencia
GMAIL_API_PUBSUB_SUBSCRIPTION=projects/correspondencia-django/subscriptions/gmail-correspondencia-sub
GMAIL_API_PUBSUB_CREDENTIALS_FILE=deploy/secrets/gcp-pubsub-subscriber.json
```

Guía operativa IT: `deploy/scripts/USER_ACTION_GMAIL_PUBSUB.md`

Con esto:

- **Salida** → Postmark API (`PostmarkEmailBackend`)
- **Entrada** → Gmail API + Pub/Sub (`build_email_inbox_provider`)
- **Rebotes** → webhook Postmark (Celery `procesar_rebotes_periodico` se omite)
- **Watchdog IMAP** → eliminado del Beat cuando `gmail_api` está activo

---

## Fase 1 — Ya aplicado (sincronización código)

| Archivo | Rol |
|---------|-----|
| `hospital_document_management/settings.py` | Providers, Beat condicional Gmail API, flags Postmark |
| `correspondencia/tasks.py` | Provider-aware sync, Gmail Pub/Sub, skip rebotes Postmark |
| `correspondencia/management/commands/procesar_emails_seguro.py` | Usa `build_email_inbox_provider()` |
| `correspondencia/management/commands/procesar_rebotes.py` | Provider + carpeta bounces |
| `correspondencia/utils/email_ingestion.py` | Pipeline compartido ingesta |
| `correspondencia/utils/email_provider.py` | `IMAPMailboxProvider` + `GmailAPIClient` |
| `correspondencia/utils/email_sync_helpers.py` | `is_gmail_api_ingestion()` |
| `correspondencia/email_backends.py` | Postmark + Gmail API send |
| `correspondencia/email_sync_control.py` | Panel control sync |
| `correspondencia/api_monitoreo.py` | API monitoreo email-sync |

---

## Fase 2 — Apagar rutas legacy en runtime (sin borrar código aún)

### 2.1 Celery Beat

**Archivo:** `hospital_document_management/settings.py`

| Tarea Beat | Acción con stack nuevo |
|------------|------------------------|
| `procesar_emails_periodico` | Mantener como **backup poll** (intervalo `CELERY_GMAIL_BACKUP_POLL_INTERVAL`, default 15 min) |
| `watchdog_inbox` | **Quitada del Beat** si `EMAIL_INGESTION_PROVIDER=gmail_api` y `CELERY_DISABLE_WATCHDOG_WHEN_GMAIL_API=true` |
| `procesar_rebotes_periodico` | **No corre** si Postmark webhook activo (`tasks.py` early return) |
| `gmail_pubsub_pull_periodico` | **Activa** solo con `gmail_api` |
| `gmail_watch_renew_periodico` | **Activa** solo con `gmail_api` |

**Verificación:**

```bash
# Reiniciar beat/worker tras cambiar .env
celery -A hospital_document_management inspect scheduled
```

### 2.2 Defaults peligrosos

**Archivo:** `hospital_document_management/settings.py`

- [ ] Confirmar que **no** hay passwords SMTP en defaults (solo vacíos o desde env)
- [ ] Fallar al arrancar si `EMAIL_PROVIDER=postmark` y falta `POSTMARK_SERVER_TOKEN` (opcional, endurecimiento)

### 2.3 Comandos manuales legacy

| Comando | Estado | Acción recomendada |
|---------|--------|-------------------|
| `procesar_emails_seguro` | Activo vía provider | OK — respeta `EMAIL_INGESTION_PROVIDER` |
| `procesar_rebotes` | IMAP/provider | Desactivar uso manual si Postmark webhook OK |
| `procesar_emails.py` | **100% IMAP hardcodeado** | Marcar deprecated; no usar en prod |
| `check_faltantes.py` (raíz) | Script ad hoc + credenciales | Mover a `scripts/maintenance/` con env o eliminar |

---

## Fase 3 — Código a retirar o aislar (después de 2 semanas estables)

### Entrada IMAP (eliminar cuando Gmail API + Pub/Sub esté probado)

| Archivo | Qué tocar |
|---------|-----------|
| `correspondencia/utils/email_provider.py` | Clase `IMAPMailboxProvider` y rama `imap` en `build_email_inbox_provider` |
| `correspondencia/tasks.py` | `watchdog_inbox` completo |
| `correspondencia/email_sync_control.py` | `run_imap_smoke_test()`, acción `IMAP_TEST` |
| `correspondencia/api_monitoreo.py` | `IMAP_ONLY_ACTIONS`, `_build_imap_control_payload`, alias `/api/monitoreo/imap/` |
| `correspondencia/management/commands/procesar_emails.py` | **Eliminar** |
| `check_faltantes.py` | **Eliminar** o reescribir con provider |
| `imap/*.md` | Archivar o actualizar |

### Salida SMTP (eliminar cuando Postmark esté probado)

| Archivo | Qué tocar |
|---------|-----------|
| `hospital_document_management/settings.py` | Rama `EMAIL_BACKEND = smtp.EmailBackend` |
| `correspondencia/aprobacion_envio.py` | Ramas específicas SMTP (mantener `get_connection()` genérico) |
| `correspondencia/views.py` | Envíos directos `EmailMessage` — ya usan backend Django |

**No tocar (no es protocolo legacy de la app):**

- `validar_email_smtp_ajax` — validación MX puerto 25 de contactos
- Campos `smtp_code` en modelos — metadata Postmark/DSN, no envío SMTP

### UI / nombres legacy

| Archivo | Cambio |
|---------|--------|
| `monitoreo-nextjs/hooks/use-monitoreo.ts` | Renombrar `useIMAP` → `useEmailSync` (alias temporal OK) |
| Vistas ventanilla (`views.py`) | Textos "estado IMAP" → "estado sincronización email" |
| `correspondencia/models.py` | `fecha_lectura_imap`, `GMAIL_IMAP` — rename en migración futura |
| `README.md`, `documentacion/RESUMEN_*` | Actualizar diagramas |

---

## Fase 4 — Tests y regresión

| Suite | Comando |
|-------|---------|
| Unit/integration | `python3 -m pytest correspondencia/tests/ -q` |
| Email Gmail API | `pytest correspondencia/tests/test_gmail_api_inbox.py -q` |
| Postmark | `pytest correspondencia/tests/test_postmark_*.py -q` |
| E2E UI | `E2E_BASE_URL=http://127.0.0.1:8001 E2E_VENTANILLA_USER=... npm run test:e2e` |

Archivos E2E: `correspondencia/tests/e2e/`

---

## Fase 5 — Checklist go-live

- [ ] `.env` prod con `postmark` + `gmail_api`
- [ ] Celery Beat muestra `gmail-pubsub-pull`, no `watchdog-inbox`
- [ ] Webhook Postmark recibe bounces de prueba
- [ ] `gmail_operational_status` / panel monitoreo en verde
- [ ] No hay logs `imap.gmail.com` en worker (salvo fallback explícito)
- [ ] Credenciales IMAP/SMTP removidas de repo y scripts sueltos

---

## Mapa rápido: ¿qué protocolo usa cada flujo hoy?

| Flujo | Provider activo | Legacy si falla env |
|-------|-----------------|---------------------|
| Recibir correos | Gmail API (+ backup poll) | IMAP si `EMAIL_INGESTION_PROVIDER=imap` |
| Enviar respuestas | Postmark | SMTP Gmail si `EMAIL_PROVIDER=smtp` |
| Rebotes | Postmark webhook | IMAP carpeta bounces |
| Validar email contacto | MX/SMTP handshake puerto 25 | N/A (no es envío app) |
