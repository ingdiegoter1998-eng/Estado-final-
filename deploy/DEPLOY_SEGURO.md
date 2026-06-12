# Despliegue seguro (sin tumbar producción)

## Cuándo usar

Después de cambios en código Django/Celery/estáticos, en la **misma carpeta de producción** (`/home/devdiego/Correspondencia-diciembre-1.0`).

## Comando

```bash
cd /home/devdiego/Correspondencia-diciembre-1.0
./deploy/scripts/safe_deploy.sh
```

## Qué hace (sin restart completo)

1. Respaldo en `deploy/backups/pre-deploy-YYYYMMDD-HHMMSS/`
2. `manage.py check`
3. `migrate` **solo si** `.env` tiene `DB_USER` y `DB_PASSWORD`
4. `collectstatic`
5. **HUP a Gunicorn** (recarga código; conserva credenciales SQL del master)
6. `celery control pool_restart` (si el worker tiene `--pool-restarts`)

## Importante: credenciales SQL

Gunicorn/Celery en producción llevan meses activos con credenciales SQL **en memoria**. El `.env` actual puede no tener `DB_USER`/`DB_PASSWORD`.

- **No hacer** `systemctl restart correspondencia` hasta restaurar credenciales en `.env` (ver `deploy/env/db.env.example`).
- Migraciones pendientes (`0074_postmark_webhooks`, `0075_gmail_watch`): pedir al inge credenciales SQL o aplicar migrate manualmente.

## Restart completo (solo con credenciales SQL en .env)

```bash
USE_FULL_RESTART=1 ./deploy/scripts/safe_deploy.sh
```

## Rollback

Ver `deploy/backups/pre-deploy-*/ROLLBACK.md`.

## Post-despliegue

| Prueba | URL / comando |
|--------|----------------|
| Login | `http://192.168.3.230/registros/login/` → 200 |
| Seguimiento entrega | `/registros/correspondencia/ventanilla/seguimiento-entrega/` → 302 si no logueado |
| Webhook Postmark | POST `/registros/correspondencia/api/webhooks/postmark/` → 200 |
| Estado webhooks | `python manage.py postmark_webhook_status` |

### Webhook Postmark en producción

URL para configurar en Postmark (stream **outbound**):

```
http://192.168.3.230/registros/correspondencia/api/webhooks/postmark/
```

Basic auth: mismos valores que `POSTMARK_WEBHOOK_USER` / `POSTMARK_WEBHOOK_PASSWORD` en `.env`.

Postmark en la nube **no alcanza** IP privada `192.168.x` salvo túnel (ngrok/Tailscale Funnel) o proxy público. Sin URL pública, la evidencia “Entrega confirmada” no se actualiza aunque Postmark entregue el correo.

## Pub/Sub JSON

Opcional para avisos instantáneos. Sin `deploy/secrets/gcp-pubsub-subscriber.json`, sigue activo el polling Gmail cada ~15 min.

## Monitoreo (Next.js `/monitoreo`)

Tras cambios en `monitoreo-nextjs`, compilar **siempre** con `NEXT_BASE_PATH=/monitoreo` (el servicio systemd ya lo define en runtime, pero el artefacto `.next` se genera en build):

```bash
./deploy/scripts/build_monitoreo.sh
sudo systemctl restart correspondencia-monitoreo
```

Si `npm run build` se ejecutó sin `NEXT_BASE_PATH`, `/monitoreo` redirige a `/` y Nginx/Django puede mostrar el 404 «PÁGINA NO ENCONTRADA».
