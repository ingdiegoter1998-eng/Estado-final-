#!/bin/bash
# =============================================================================
# deploy/setup_produccion.sh
# Script de deploy para integrar Next.js con Django vía Nginx
#
# Ejecutar como:  bash deploy/setup_produccion.sh
# Requiere sudo para: nginx, pm2 startup
# =============================================================================

set -e  # Salir si cualquier comando falla

PROJECT_DIR="/home/devdiego/Correspondencia-diciembre-1.0"
NEXTJS_DIR="$PROJECT_DIR/calendario-informes-nextjs"
DEPLOY_DIR="$PROJECT_DIR/deploy"

echo "============================================="
echo " Deploy: Calendario Next.js + Nginx"
echo "============================================="

# --- Paso 1: Instalar pm2 si no está ---
if ! command -v pm2 &>/dev/null; then
    echo "[1/6] Instalando pm2 globalmente..."
    sudo npm install -g pm2
else
    echo "[1/6] pm2 ya está instalado: $(pm2 --version)"
fi

# --- Paso 2: Build de Next.js ---
echo "[2/6] Construyendo Next.js para producción..."
cd "$NEXTJS_DIR"
npm install
NODE_ENV=production npm run build
echo "      Build completado."

# --- Paso 3: Crear directorio de logs ---
echo "[3/6] Creando directorio de logs..."
mkdir -p "$DEPLOY_DIR/logs"

# --- Paso 4: Iniciar/Reiniciar Next.js con pm2 ---
echo "[4/6] Iniciando Next.js con pm2..."
cd "$PROJECT_DIR"

if pm2 describe calendario-next &>/dev/null; then
    echo "      Proceso existente, reiniciando..."
    pm2 reload deploy/ecosystem.config.cjs --update-env
else
    echo "      Iniciando nuevo proceso..."
    pm2 start deploy/ecosystem.config.cjs
fi

pm2 save
echo "      Next.js corriendo en 127.0.0.1:3000"

# --- Paso 5: Copiar y activar config Nginx ---
echo "[5/6] Actualizando configuración Nginx..."
sudo cp "$DEPLOY_DIR/nginx_correspondencia.conf" /etc/nginx/sites-available/correspondencia
sudo nginx -t
sudo systemctl reload nginx
echo "      Nginx recargado correctamente."

# --- Paso 6: Configurar autostart (solo la primera vez) ---
echo "[6/6] Configurando autostart de pm2..."
echo "      IMPORTANTE: Si es la primera vez, ejecuta el comando que muestre pm2 startup:"
pm2 startup systemd -u devdiego --hp /home/devdiego 2>/dev/null || true

echo ""
echo "============================================="
echo " ✓ Deploy completado"
echo "============================================="
echo ""
echo " Django:  http://192.168.3.230/"
echo " Next.js: http://192.168.3.230/calendario"
echo ""
echo " Para ver logs de Next.js:"
echo "   pm2 logs calendario-next"
echo ""
echo " Para verificar estado:"
echo "   pm2 status"
echo "   sudo systemctl status nginx"
echo ""
