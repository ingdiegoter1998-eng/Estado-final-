"""Consulta y sincronización de eventos de entrega desde la API Messages de Postmark."""

from __future__ import annotations

import json
import logging
from urllib import error, request

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from correspondencia.models import PostmarkWebhookEvento
from correspondencia.utils.postmark_webhooks import procesar_evento_postmark

logger = logging.getLogger(__name__)

_API_TYPE_TO_RECORD = {
    'Delivered': 'Delivery',
    'Bounced': 'Bounce',
    'Transient': 'Bounce',
}


def _normalizar_email(value: str | None) -> str:
    return (value or '').strip().lower()


def fetch_outbound_message_details(message_id: str, *, timeout: int = 15) -> dict | None:
    """GET /messages/outbound/{messageid}/details. Devuelve None si no hay token o el mensaje no existe."""
    message_id = (message_id or '').strip()
    token = (getattr(settings, 'POSTMARK_SERVER_TOKEN', '') or '').strip()
    if not message_id or not token:
        return None

    url = f'https://api.postmarkapp.com/messages/outbound/{message_id}/details'
    req = request.Request(
        url,
        headers={
            'Accept': 'application/json',
            'X-Postmark-Server-Token': token,
        },
        method='GET',
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8') or '{}')
    except error.HTTPError as exc:
        if exc.code == 404:
            return None
        body = exc.read().decode('utf-8', errors='replace') if hasattr(exc, 'read') else str(exc)
        logger.warning('Postmark details HTTP %s para %s: %s', exc.code, message_id, body[:200])
        return None
    except error.URLError as exc:
        logger.warning('Postmark details sin conexión para %s: %s', message_id, exc.reason)
        return None
    except Exception:
        logger.exception('Error consultando detalles Postmark para %s', message_id)
        return None


def _detalle_desde_api_event(api_event: dict) -> str:
    details = api_event.get('Details') or {}
    if isinstance(details, dict):
        for key in ('DeliveryMessage', 'Summary', 'Description', 'Details'):
            value = (details.get(key) or '').strip()
            if value:
                return value
        return json.dumps(details, ensure_ascii=False)[:500]
    return str(details).strip()[:500]


def api_event_a_payload_webhook(message_id: str, api_event: dict) -> dict | None:
    """Adapta un MessageEvent de la API al formato de webhook interno."""
    record_type = _API_TYPE_TO_RECORD.get((api_event.get('Type') or '').strip())
    recipient = (api_event.get('Recipient') or '').strip()
    if not record_type or not recipient:
        return None

    payload = {
        'RecordType': record_type,
        'MessageID': message_id,
        'Recipient': recipient,
        'Details': _detalle_desde_api_event(api_event),
        '_source': 'postmark_api',
    }
    received_at = api_event.get('ReceivedAt')
    if record_type == 'Delivery' and received_at:
        payload['DeliveredAt'] = received_at
    if record_type == 'Bounce':
        payload['Type'] = (api_event.get('Type') or '').strip() or 'Bounce'
        payload['Description'] = payload['Details']
    return payload


def _tiene_evento_local(message_id: str, recipient: str, record_type: str) -> bool:
    return PostmarkWebhookEvento.objects.filter(
        postmark_message_id=message_id,
        recipient__iexact=recipient,
        record_type=record_type,
    ).exists()


def sincronizar_eventos_desde_api(message_id: str, *, procesar: bool = True) -> dict:
    """
    Persiste MessageEvents de Postmark en PostmarkWebhookEvento y opcionalmente
    actualiza destinatarios (entrega/rebote) con la misma lógica que el webhook.
    """
    message_id = (message_id or '').strip()
    details = fetch_outbound_message_details(message_id)
    if not details:
        return {'status': 'not_found', 'message_id': message_id, 'synced': 0}

    synced = 0
    for api_event in details.get('MessageEvents') or []:
        payload = api_event_a_payload_webhook(message_id, api_event)
        if not payload:
            continue

        recipient = payload['Recipient']
        record_type = payload['RecordType']
        if _tiene_evento_local(message_id, recipient, record_type):
            continue

        if procesar:
            procesar_evento_postmark(payload)
        else:
            received_at = api_event.get('ReceivedAt')
            recibido_at = timezone.now()
            if received_at:
                parsed = parse_datetime(received_at)
                if parsed:
                    recibido_at = timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
            PostmarkWebhookEvento.objects.create(
                record_type=record_type,
                postmark_message_id=message_id,
                recipient=recipient,
                payload=payload,
                procesado=True,
                resultado='api_sync',
            )
        synced += 1

    return {'status': 'ok', 'message_id': message_id, 'synced': synced}


def message_ids_pendientes_sync(
    destinatarios,
    *,
    record_types: tuple[str, ...] = ('Delivery', 'Bounce'),
) -> list[str]:
    """MessageIDs de destinatarios ENVIADO sin evento local para su correo."""
    pares_por_id: dict[str, set[str]] = {}
    for destinatario in destinatarios:
        if destinatario.estado != 'ENVIADO':
            continue
        message_id = (destinatario.postmark_message_id or '').strip()
        email = _normalizar_email(destinatario.email_snapshot)
        if not message_id or not email:
            continue
        pares_por_id.setdefault(message_id, set()).add(email)

    if not pares_por_id:
        return []

    eventos_locales = PostmarkWebhookEvento.objects.filter(
        postmark_message_id__in=list(pares_por_id.keys()),
        record_type__in=record_types,
    ).values_list('postmark_message_id', 'recipient')

    cubiertos: dict[str, set[str]] = {}
    for message_id, recipient in eventos_locales:
        pm_id = (message_id or '').strip()
        email = _normalizar_email(recipient)
        if pm_id and email:
            cubiertos.setdefault(pm_id, set()).add(email)

    pendientes: list[str] = []
    for message_id, emails in pares_por_id.items():
        cubiertos_id = cubiertos.get(message_id, set())
        if not emails.issubset(cubiertos_id):
            pendientes.append(message_id)
    return pendientes


def sincronizar_lote_desde_api(message_ids: list[str], *, max_fetch: int = 15) -> int:
    """Sincroniza hasta max_fetch MessageIDs. Devuelve cuántos IDs se consultaron."""
    consultados = 0
    for message_id in message_ids[:max_fetch]:
        sincronizar_eventos_desde_api(message_id)
        consultados += 1
    return consultados


def evento_api_para_destinatario(details: dict | None, email: str) -> dict | None:
    """Devuelve el MessageEvent más relevante para un destinatario (sin persistir)."""
    if not details:
        return None

    email = _normalizar_email(email)
    candidatos = []
    for api_event in details.get('MessageEvents') or []:
        if _normalizar_email(api_event.get('Recipient')) != email:
            continue
        candidatos.append(api_event)

    if not candidatos:
        return None

    prioridad = {'Bounced': 0, 'Transient': 1, 'Delivered': 2}
    candidatos.sort(key=lambda ev: prioridad.get((ev.get('Type') or '').strip(), 99))
    return candidatos[0]
