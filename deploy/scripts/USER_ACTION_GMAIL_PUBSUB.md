# Gmail Pub/Sub — acciones IT + verificación dev

Infra confirmada en GCP (**proyecto `correspondencia-django`**):

| Recurso | Nombre completo |
|---------|-----------------|
| Tema Pub/Sub | `projects/correspondencia-django/topics/gmail-correspondencia` |
| Suscripción | `projects/correspondencia-django/subscriptions/gmail-correspondencia-sub` |
| Gmail API | Habilitada en el proyecto |

Variables ya alineadas en `.env` (repo principal; el worktree enlaza al mismo archivo).

---

## Pendiente IT (para que lleguen correos por push)

### 1. Permiso Gmail → Pub/Sub

En el tema `gmail-correspondencia`, agregar **Publisher** a:

```
gmail-api-push@system.gserviceaccount.com
```

Sin esto, `gmail_watch_start` falla al registrar `users.watch`.

### 2. Service account para pull (Django/Celery)

1. Crear SA en `correspondencia-django` (ej. `correspondencia-pubsub-pull`).
2. Rol: **Pub/Sub Subscriber** sobre la suscripción `gmail-correspondencia-sub`.
3. Descargar JSON y guardarlo en:

   ```
   deploy/secrets/gcp-pubsub-subscriber.json
   ```

4. En `.env` (ya preparado):

   ```env
   GMAIL_API_PUBSUB_CREDENTIALS_FILE=deploy/secrets/gcp-pubsub-subscriber.json
   ```

   Alternativa: `export GOOGLE_APPLICATION_CREDENTIALS=...`

### 3. OAuth del buzón (lectura/modify)

El refresh token en `.env` debe ser de la **cuenta que recibe** la correspondencia.  
Cuando IT migre al buzón institucional, regenerar token con scopes:

- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.send` (si también envían por Gmail API)

Comandos OAuth existentes: `gmail_oauth_desktop_start`, `gmail_oauth_exchange`.

---

## Verificación dev (después del JSON de SA)

```bash
cd /home/devdiego/Correspondencia-diciembre-1.0
source venv/bin/activate

# Estado general
python manage.py gmail_operational_status

# Registrar watch Gmail → Pub/Sub (una vez o al renovar)
python manage.py gmail_watch_start

# Probar pull manual (debe decir "Sin mensajes" o procesar history)
python manage.py gmail_pubsub_pull --max-messages=5

# Tick completo (watch + pull + history)
python manage.py gmail_pipeline_tick
```

Reiniciar Celery para cargar `.env` y Beat condicional:

```bash
sudo systemctl restart correspondencia-celery-beat correspondencia-celery-worker
```

Con `EMAIL_INGESTION_PROVIDER=gmail_api`, Beat debe programar:

- `gmail_pubsub_pull_periodico` (~60 s)
- `gmail_watch_renew_periodico` (~6 h)
- `procesar_emails_periodico` como **backup poll** (~15 min)
- **No** `watchdog_inbox` (IMAP legacy)

---

## Métricas en consola GCP

Si Pub/Sub muestra **0 mensajes** es normal hasta que:

1. `gmail_watch_start` esté OK, y
2. Llegue un correo nuevo al buzón watch (INBOX).

Enviar un correo de prueba al buzón y revisar de nuevo la suscripción `gmail-correspondencia-sub`.

---

## Salida de correo (Postmark)

Sin cambios: `EMAIL_PROVIDER=postmark`. Ver `deploy/scripts/USER_ACTION_POSTMARK.md`.

Ingesta Gmail y salida Postmark son independientes.

## Salida puntual por Gmail API (Postmark caído)

Mientras Postmark rechace el From, un radicado en cola puede enviarse solo por Gmail sin cambiar EMAIL_PROVIDER:

    DJANGO_SETTINGS_MODULE=hospital_document_management.settings \
      venv/bin/python manage.py enviar_salida_por_gmail --radicado SALIENTE-2026-XXXX

Opciones: --salida-id, --dry-run. Requiere GMAIL_API_* y OUTBOUND_EMAIL_ADDRESS en .env.
