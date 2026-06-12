# Rollback — pre-deploy 2026-06-01 17:33

## Restaurar configuración

```bash
BACKUP=/home/devdiego/Correspondencia-diciembre-1.0/deploy/backups/pre-deploy-20260601-173309
cd /home/devdiego/Correspondencia-diciembre-1.0
cp -a "$BACKUP/.env" .env
sudo cp "$BACKUP/nginx-correspondencia.conf" /etc/nginx/sites-available/correspondencia
sudo cp "$BACKUP/correspondencia.service" /etc/systemd/system/correspondencia.service
sudo cp "$BACKUP/correspondencia-celery-worker.service" /etc/systemd/system/
sudo cp "$BACKUP/correspondencia-celery-beat.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart correspondencia correspondencia-celery-worker correspondencia-celery-beat
sudo nginx -t && sudo systemctl reload nginx
```

## Git (opcional)

Ver `git-head.txt` y `git-status.txt` en esta carpeta para el estado previo.
