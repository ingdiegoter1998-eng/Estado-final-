#!/usr/bin/env bash
# Build Next.js monitoreo con basePath de producción (mismo que correspondencia-monitoreo.service).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/monitoreo-nextjs"
export NEXT_BASE_PATH=/monitoreo
export NEXT_BACKEND_ORIGIN="${NEXT_BACKEND_ORIGIN:-http://127.0.0.1}"
npm run build:prod
echo "Listo. Reinicie: sudo systemctl restart correspondencia-monitoreo"
echo "Si cambió api_monitoreo.py o urls.py, recargue también Gunicorn:"
echo "  MAINPID=\$(systemctl show -p MainPID --value correspondencia); kill -HUP \"\$MAINPID\""
