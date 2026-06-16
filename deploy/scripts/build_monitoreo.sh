#!/usr/bin/env bash
# Build Next.js monitoreo con basePath de producción (mismo que correspondencia-monitoreo.service).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/monitoreo-nextjs"
export NEXT_BASE_PATH=/monitoreo
export NEXT_BACKEND_ORIGIN="${NEXT_BACKEND_ORIGIN:-http://127.0.0.1}"
npm run build:prod

restart_monitoreo() {
  if command -v systemctl >/dev/null 2>&1; then
    if systemctl restart correspondencia-monitoreo 2>/dev/null; then
      echo "Servicio correspondencia-monitoreo reiniciado (systemctl)."
      return 0
    fi
    if sudo -n systemctl restart correspondencia-monitoreo 2>/dev/null; then
      echo "Servicio correspondencia-monitoreo reiniciado (sudo -n)."
      return 0
    fi
  fi
  local pid
  pid="$(systemctl show -p MainPID --value correspondencia-monitoreo 2>/dev/null || true)"
  if [[ -n "${pid}" && "${pid}" != "0" ]] && kill -TERM "${pid}" 2>/dev/null; then
    echo "Señal TERM enviada a correspondencia-monitoreo (PID ${pid}); systemd lo levantará de nuevo."
    return 0
  fi
  return 1
}

if restart_monitoreo; then
  echo "Next.js recargado con el build nuevo (CSS/JS alineados)."
else
  echo "AVISO: el build terminó pero NO se pudo reiniciar correspondencia-monitoreo."
  echo "Sin reinicio, la página queda SIN ESTILOS (HTML viejo + assets nuevos)."
  echo "Ejecute: sudo systemctl restart correspondencia-monitoreo"
fi

echo "Si cambió api_monitoreo.py o urls.py, recargue también Gunicorn:"
echo "  MAINPID=\$(systemctl show -p MainPID --value correspondencia); kill -HUP \"\$MAINPID\""
