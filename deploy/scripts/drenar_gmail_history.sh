#!/usr/bin/env bash
# Drena la cola de history sync por lotes sin saturar Gmail API.
set -euo pipefail
cd "$(dirname "$0")/../.."
export DJANGO_SETTINGS_MODULE=hospital_document_management.settings
PY=venv/bin/python
MAX_CICLOS="${1:-50}"
PAUSA="${2:-100}"

echo "=== Drenaje Gmail history sync (max $MAX_CICLOS ciclos, pausa ${PAUSA}s) ==="

for i in $(seq 1 "$MAX_CICLOS"); do
  echo ""
  echo "--- Ciclo $i/$(date -u '+%H:%M:%S UTC') ---"
  COOLDOWN=$($PY -c "
from correspondencia.utils.gmail_rate_limit import get_gmail_rate_limit_until
r = get_gmail_rate_limit_until()
print(r.isoformat() if r else '')
" 2>/dev/null || true)
  if [ -n "$COOLDOWN" ]; then
    echo "Cooldown activo hasta $COOLDOWN — esperando 60s"
    sleep 60
    continue
  fi
  if ! $PY manage.py gmail_history_sync 2>&1; then
    echo "Sync falló (posible 429) — pausa 90s"
    sleep 90
    continue
  fi
  PEND=$($PY -c "from correspondencia.utils.gmail_history_queue import pending_count; print(pending_count())")
  HID=$($PY manage.py shell -c "
from correspondencia.models import EstadoSincronizacionCorreos
from correspondencia.utils.email_provider import get_email_ingestion_sync_source
s=EstadoSincronizacionCorreos.objects.get(fuente=get_email_ingestion_sync_source())
print(s.ultimo_history_id)
" 2>/dev/null | tail -1)
  echo "pendientes_cola=$PEND ultimo_history_id=$HID"
  if [ "$PEND" = "0" ]; then
    TARGET=$($PY -c "from correspondencia.utils.gmail_history_queue import get_target_history_id; print(get_target_history_id() or '')")
    if [ -n "$TARGET" ] && [ "$HID" = "$TARGET" ] || [ "$PEND" = "0" ]; then
      echo "Cola vacía — drenaje completado."
      exit 0
    fi
  fi
  sleep "$PAUSA"
done

echo "Alcanzado máximo de ciclos sin vaciar cola."
exit 1
