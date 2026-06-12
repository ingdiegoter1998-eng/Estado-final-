#!/usr/bin/env bash
# Detiene servidores de desarrollo que compiten con Gunicorn/systemd en la VM de producción.
set -euo pipefail

echo "Deteniendo runserver dev que compite con Gunicorn/SQL Server..."
pkill -f 'manage.py runserver 0.0.0.0:8001' 2>/dev/null || true
pkill -f 'manage.py runserver 127.0.0.1:3002' 2>/dev/null || true
pkill -f 'manage.py runserver 8007' 2>/dev/null || true
pkill -f 'manage.py runserver' 2>/dev/null || true

echo "Deteniendo workers Celery huérfanos (invocación manual antigua)..."
pkill -f 'venv/bin/python3 venv/bin/celery' 2>/dev/null || true
pkill -f 'celery -A hospital_document_management worker --concurrency=2' 2>/dev/null || true
pkill -f 'celery -A hospital_document_management worker -l info -c 2' 2>/dev/null || true

echo "Procesos restantes (debe quedar gunicorn + celery systemd):"
ps aux | grep -E 'runserver|gunicorn|celery' | grep -v grep || true

echo "Listo. Producción: http://<host>/ y http://<host>/monitoreo (puertos 80 y 3001)."
