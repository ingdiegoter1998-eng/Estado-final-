#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/devdiego/Correspondencia-diciembre-1.0"
SERVICE_SRC="$PROJECT_DIR/deploy/systemd/correspondencia.service"
NGINX_SRC="$PROJECT_DIR/deploy/nginx/correspondencia.conf"
LOGROTATE_SRC="$PROJECT_DIR/deploy/logrotate/correspondencia"

echo "[+] Recogiendo archivos estáticos"
cd "$PROJECT_DIR"
source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null || true
python manage.py collectstatic --noinput

echo "[+] Preparando directorios de logs"
sudo mkdir -p /var/log/correspondencia
sudo chown devdiego:www-data /var/log/correspondencia

echo "[+] Instalando servicio systemd"
sudo cp "$SERVICE_SRC" /etc/systemd/system/correspondencia.service
sudo systemctl daemon-reload
sudo systemctl enable --now correspondencia

echo "[+] Verificando Nginx"
if ! command -v nginx >/dev/null 2>&1; then
  echo "[+] Nginx no encontrado. Instalando..."
  sudo apt update
  sudo apt install -y nginx
fi

echo "[+] Habilitando y creando rutas de Nginx"
sudo systemctl enable --now nginx
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

echo "[+] Instalando sitio Nginx"
sudo cp "$NGINX_SRC" /etc/nginx/sites-available/correspondencia
sudo ln -sf /etc/nginx/sites-available/correspondencia /etc/nginx/sites-enabled/correspondencia
sudo nginx -t
sudo systemctl reload nginx

echo "[+] Configurando logrotate para Gunicorn"
sudo cp "$LOGROTATE_SRC" /etc/logrotate.d/correspondencia

echo "[+] Reglas UFW (opcional: solo intranet)"
if sudo ufw status | grep -q "Status: active"; then
  sudo ufw delete allow 80 || true
  sudo ufw allow from 192.168.0.0/16 to any port 80
  sudo ufw status
else
  echo "UFW no activo. Saltando reglas."
fi

echo "[+] Verificación rápida"
curl -I http://192.168.3.230/ || true
echo "Listo."
