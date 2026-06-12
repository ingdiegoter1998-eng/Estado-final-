import base64
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from correspondencia.utils.postmark_webhooks import procesar_evento_postmark

logger = logging.getLogger(__name__)


def _webhook_auth_ok(request) -> bool:
    expected_user = getattr(settings, 'POSTMARK_WEBHOOK_USER', '').strip()
    expected_password = getattr(settings, 'POSTMARK_WEBHOOK_PASSWORD', '').strip()
    if not expected_user and not expected_password:
        return True

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Basic '):
        return False

    try:
        decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
    except (UnicodeDecodeError, ValueError):
        return False

    if ':' not in decoded:
        return False

    user, password = decoded.split(':', 1)
    return user == expected_user and password == expected_password


@csrf_exempt
@require_POST
def postmark_webhook(request):
    """Recibe eventos de Postmark (Bounce, Delivery, etc.) y responde 200 de inmediato."""
    if not getattr(settings, 'POSTMARK_WEBHOOK_ENABLED', True):
        return HttpResponse(status=503)

    if not _webhook_auth_ok(request):
        logger.warning('Webhook Postmark rechazado: credenciales inválidas')
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning('Webhook Postmark con JSON inválido')
        return HttpResponse(status=400)

    try:
        resultado = procesar_evento_postmark(payload)
    except Exception:
        logger.exception('Error procesando webhook Postmark')
        # Postmark reintenta si no recibe 200; preferimos ack y registrar en logs.
        return JsonResponse({'status': 'error'}, status=200)

    return JsonResponse(resultado, status=200)
