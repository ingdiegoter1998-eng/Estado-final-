#!/usr/bin/env bash
# Despliegue seguro sin tumbar producción.
# - Respaldo previo en deploy/backups/
# - Recarga Gunicorn con HUP (conserva variables de entorno del master)
# - Reinicia pool Celery (conserva entorno del worker master)
# - NO hace restart completo de servicios salvo que USE_FULL_RESTART=1
set -euo pipefail

PROJECT_DIR="/home/devdiego/Correspondencia-diciembre-1.0"
cd "$PROJECT_DIR"
VENV="$PROJECT_DIR/venv/bin"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$PROJECT_DIR/deploy/backups/pre-deploy-$STAMP"

log() { echo "[safe_deploy] $*"; }

log "1/7 Respaldo en $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -a .env "$BACKUP_DIR/.env" 2>/dev/null || true
cp -a deploy/nginx/correspondencia.conf "$BACKUP_DIR/" 2>/dev/null || true
cp -a deploy/systemd/*.service "$BACKUP_DIR/" 2>/dev/null || true
git status --short > "$BACKUP_DIR/git-status.txt" 2>/dev/null || true
git rev-parse HEAD > "$BACKUP_DIR/git-head.txt" 2>/dev/null || true

log "2/7 Validación Django (check)"
"$VENV/python" manage.py check || {
  log "WARN: manage.py check falló; revisar antes de continuar."
}

log "3/7 Migraciones (si hay credenciales DB en entorno)"
if [[ -n "${DB_USER:-}" && -n "${DB_PASSWORD:-}" ]] || grep -qE '^DB_USER=.+' .env 2>/dev/null; then
  "$VENV/python" manage.py migrate --noinput
else
  log "SKIP migrate: .env no tiene DB_USER/DB_PASSWORD."
  log "      Si hay migraciones nuevas (0074_postmark, 0075_gmail), pedir al inge credenciales SQL"
  log "      o ejecutar migrate manualmente antes del próximo restart completo."
fi

log "4/7 collectstatic"
"$VENV/python" manage.py collectstatic --noinput

log "5/7 Nginx (solo si cambió la config del repo)"
if ! cmp -s deploy/nginx/correspondencia.conf /etc/nginx/sites-available/correspondencia 2>/dev/null; then
  sudo cp deploy/nginx/correspondencia.conf /etc/nginx/sites-available/correspondencia
  sudo nginx -t
  sudo systemctl reload nginx
  log "Nginx recargado."
else
  log "Nginx sin cambios."
fi

log "6/7 Recarga Gunicorn (HUP — sin perder env del master)"
if [[ "${USE_FULL_RESTART:-0}" == "1" ]]; then
  log "FULL RESTART solicitado — requiere DB_* en .env"
  sudo systemctl restart correspondencia
else
  MAINPID="$(systemctl show correspondencia -p MainPID --value)"
  if [[ -n "$MAINPID" && "$MAINPID" != "0" ]]; then
    kill -HUP "$MAINPID" 2>/dev/null || sudo kill -HUP "$MAINPID"
    log "HUP enviado a gunicorn master PID=$MAINPID"
  else
    log "WARN: gunicorn no activo"
  fi
fi

log "7/7 Recarga workers Celery (pool_restart)"
if [[ "${USE_FULL_RESTART:-0}" == "1" ]]; then
  sudo systemctl restart correspondencia-celery-worker correspondencia-celery-beat
else
  "$VENV/celery" -A hospital_document_management control pool_restart 2>/dev/null || {
    log "WARN: pool_restart falló; Celery sigue con código anterior hasta restart manual."
  }
fi

log "Post-despliegue: probar http://127.0.0.1/registros/login/"
log "Webhook Postmark producción: http://192.168.3.230/registros/correspondencia/api/webhooks/postmark/"
log "Rollback: ver $BACKUP_DIR/ROLLBACK.md (copiar ROLLBACK.md al crear backup manual si falta)"
cat > "$BACKUP_DIR/ROLLBACK.md" <<EOF
# Rollback $STAMP
cp -a $BACKUP_DIR/.env $PROJECT_DIR/.env
MAINPID=\$(systemctl show correspondencia -p MainPID --value)
sudo kill -HUP "\$MAINPID"
EOF
log "Listo."
