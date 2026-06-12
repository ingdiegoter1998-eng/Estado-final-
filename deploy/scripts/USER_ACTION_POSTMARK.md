# Postmark — configuración operativa (modelo híbrido)

Salida por **Postmark** + entrada por **Gmail** (IMAP hoy; Pub/Sub en migración).

## Variables `.env` (salida)

```env
EMAIL_PROVIDER=postmark
POSTMARK_SERVER_TOKEN=<server-token>
POSTMARK_MESSAGE_STREAM=outbound
OUTBOUND_EMAIL_ADDRESS=correspondencia@hospitaldelsarare.gov.co
OUTBOUND_EMAIL_NAME="Pruebas Correspondencia Django"

POSTMARK_WEBHOOK_USER=correspondencia-webhook
POSTMARK_WEBHOOK_PASSWORD=<secreto-webhook>
POSTMARK_WEBHOOK_ENABLED=true
POSTMARK_BOUNCES_VIA_WEBHOOK=true
```

Con `POSTMARK_BOUNCES_VIA_WEBHOOK=true`, Celery **no** ejecuta `procesar_rebotes` por IMAP (los rebotes llegan por webhook).

## Webhook en Postmark

**Importante:** los envíos usan el stream **`outbound`** (`POSTMARK_MESSAGE_STREAM`). El webhook debe estar en ese mismo stream, no en `broadcast`. Si el test del panel da 200 pero los envíos reales no disparan eventos, revisa el stream en Postmark → Webhooks.

1. Server → Message Stream **outbound** → **Webhooks** → Add webhook.
2. URL producción:
   ```
   https://<dominio-hospital>/registros/correspondencia/api/webhooks/postmark/
   ```
3. Eventos: **Delivery** y **Bounce** (opcional: Spam Complaint).
4. **Custom headers and basic auth**: mismo usuario/contraseña que `.env`.
5. **Save** → **Send test** → debe responder **200**.

### Pruebas locales con ngrok

```bash
# Terminal 1
cd /home/devdiego/Correspondencia-diciembre-1.0
source venv/bin/activate
python manage.py runserver 127.0.0.1:8000

# Terminal 2
ngrok http 8000
```

Copiar la URL `https://xxxx.ngrok-free.app` y registrar:

```
https://xxxx.ngrok-free.app/registros/correspondencia/api/webhooks/postmark/
```

Inspector: http://127.0.0.1:4040

## Verificar salida (From + token)

```bash
python manage.py postmark_outbound_status
python manage.py postmark_outbound_status --probe-api
python manage.py gmail_operational_status   # incluye bloque postmark_outbound_*
```

Envío de prueba (sin rebote):

```bash
python manage.py postmark_send_test
python manage.py postmark_send_test --to operador@ejemplo.gov.co
```

**From incorrecto:** si `OUTBOUND_EMAIL_ADDRESS` apunta a `esehospitaldelsarare.gov.co` u otro dominio sin Sender Signature, Postmark responde HTTP 400. Debe coincidir con la firma verificada (`correspondencia@hospitaldelsarare.gov.co` salvo que IT registre otra en Postmark y actualice `POSTMARK_VERIFIED_SENDER`).

Tras cambiar `.env` en producción:

```bash
sudo systemctl restart correspondencia correspondencia-celery-worker correspondencia-celery-beat
```

## Ver estado de webhooks recibidos

```bash
python manage.py postmark_webhook_status
```

## Pruebas de rebote (dominio agujero negro Postmark)

Postmark simula rebotes sin dañar reputación del dominio real:

| Tipo | Dirección |
|------|-----------|
| Soft bounce | `SoftBounce@bounce-testing.postmarkapp.com` |
| Hard bounce | `HardBounce@bounce-testing.postmarkapp.com` |
| Transitorio | `Transient@bounce-testing.postmarkapp.com` |

Documentación: [How to test bounces](https://postmarkapp.com/support/article/1239-how-to-test-bounces).

**Hard bounce:** la dirección queda en la **suppression list** del stream; hay que reactivarla en Postmark antes de reutilizarla. Si Postmark responde `ErrorCode 406` (inactive), use `transient` en el comando o reactive la dirección en el panel.

**Importante (BCC):** los destinos `@bounce-testing.postmarkapp.com` deben ir en el campo **To** de Postmark (no solo en Bcc con el remitente en To), o el rebote no se dispara. La app ya hace ese ajuste automáticamente en `aprobacion_envio.py`.

### Comando automatizado (recomendado)

Requisitos: `runserver` + webhook (ngrok o producción) en stream **outbound**.

```bash
# Soft bounce E2E (clona salida 1595, envía, espera webhook)
python manage.py postmark_bounce_test soft

# Hard bounce (usar salida distinta; no repetir el mismo email suprimido)
python manage.py postmark_bounce_test hard --from-salida-id 1595

# Solo crear salida pendiente para probar por UI
python manage.py postmark_bounce_test soft --no-send
```

Tras cada prueba:

```bash
python manage.py postmark_webhook_status --hours 1
```

Validar en BD: destinatario `REBOTE`, historial `ENVIO_FALLIDO`, evento webhook `processed`.

### Prueba manual por UI

1. Ejecutar `python manage.py postmark_bounce_test soft --no-send` y anotar el `id` de salida.
2. Abrir `/registros/correspondencia/ventanilla/respuesta/<id>/revisar/`.
3. **Aprobar y Enviar Respuesta** (pausar Celery beat si compite con la prueba).

## DKIM (pendiente IT)

En Postmark → **Domains** → agregar `hospitaldelsarare.gov.co` y publicar registros DNS que indique el panel. Sin DKIM los correos pueden ir a Spam, pero la API y webhooks funcionan igual.

## Próximo paso: entrada Gmail Pub/Sub

Variables ya en `.env`:

- `EMAIL_INGESTION_PROVIDER=gmail_api`
- `GMAIL_API_PUBSUB_TOPIC`
- `GMAIL_API_PUBSUB_SUBSCRIPTION`

La implementación completa (`gmail_pubsub_pull`, `gmail_history_sync`, `email_provider`) está en la rama/worktree `Correspondencia-diciembre-1.0-gmail-api-migration` para integrar cuando IT confirme la cuenta institucional.
