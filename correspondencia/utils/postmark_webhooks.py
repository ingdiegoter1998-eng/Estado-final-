"""Procesamiento de eventos webhook de Postmark (Bounce, Delivery, etc.)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from correspondencia.aprobacion_envio import sincronizar_estado_envio_respuesta
from correspondencia.management.commands.procesar_rebotes import _crear_notificacion_rebote
from correspondencia.models import HistorialSalida, PostmarkWebhookEvento, SalidaDestinatario

logger = logging.getLogger(__name__)


def _normalizar_email(value: str | None) -> str:
    return (value or '').strip().lower()


def _extraer_destinatario(payload: dict) -> str:
    for key in ('Recipient', 'Email', 'To'):
        email = _normalizar_email(payload.get(key))
        if email and '@' in email:
            return email
    return ''


def _extraer_salida_id(payload: dict) -> int | None:
    metadata = payload.get('Metadata') or {}
    raw = metadata.get('salida_id')
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _buscar_destinatarios_enviados(
    *,
    postmark_message_id: str,
    recipient: str,
    salida_id: int | None = None,
):
    base_qs = SalidaDestinatario.objects.select_related('correspondencia_salida').filter(estado='ENVIADO')

    if postmark_message_id:
        qs = base_qs.filter(postmark_message_id=postmark_message_id)
        if recipient:
            qs = qs.filter(email_snapshot__iexact=recipient)
        if qs.exists():
            return qs

    if salida_id and recipient:
        qs = base_qs.filter(correspondencia_salida_id=salida_id, email_snapshot__iexact=recipient)
        if qs.exists():
            return qs

    if recipient:
        ventana = timezone.now() - timedelta(days=7)
        qs = base_qs.filter(email_snapshot__iexact=recipient, fecha_envio__gte=ventana)
        if qs.count() == 1:
            return qs

    return SalidaDestinatario.objects.none()


def _registrar_recepcion(payload: dict) -> tuple[PostmarkWebhookEvento | None, bool]:
    record_type = (payload.get('RecordType') or '').strip()
    postmark_message_id = (payload.get('MessageID') or '').strip()
    recipient = _extraer_destinatario(payload)

    if not record_type or not postmark_message_id:
        return None, False

    evento, created = PostmarkWebhookEvento.objects.get_or_create(
        record_type=record_type,
        postmark_message_id=postmark_message_id,
        recipient=recipient,
        defaults={'payload': payload},
    )
    return evento, created


def procesar_evento_postmark(payload: dict) -> dict:
    """Procesa un payload JSON de Postmark. Idempotente por RecordType+MessageID+Recipient."""
    record_type = (payload.get('RecordType') or '').strip()

    evento, created = _registrar_recepcion(payload)
    if evento and not created and evento.procesado:
        return {
            'status': 'duplicate',
            'record_type': record_type,
            'message_id': payload.get('MessageID'),
        }

    if record_type == 'Bounce':
        resultado = procesar_rebote_postmark(payload)
    elif record_type == 'Delivery':
        resultado = procesar_entrega_postmark(payload)
    else:
        resultado = {
            'status': 'ignored',
            'record_type': record_type or 'unknown',
        }

    if evento:
        evento.procesado = True
        evento.resultado = resultado.get('status', '')
        evento.save(update_fields=['procesado', 'resultado'])

    return resultado


@transaction.atomic
def procesar_rebote_postmark(payload: dict) -> dict:
    postmark_message_id = (payload.get('MessageID') or '').strip()
    recipient = _extraer_destinatario(payload)
    salida_id = _extraer_salida_id(payload)

    qs = _buscar_destinatarios_enviados(
        postmark_message_id=postmark_message_id,
        recipient=recipient,
        salida_id=salida_id,
    )
    if not qs.exists():
        logger.warning(
            'Rebote Postmark sin match message_id=%s recipient=%s salida_id=%s',
            postmark_message_id,
            recipient,
            salida_id,
        )
        return {
            'status': 'no_match',
            'record_type': 'Bounce',
            'message_id': postmark_message_id,
            'recipient': recipient,
        }

    descripcion = (payload.get('Description') or payload.get('Details') or payload.get('Name') or '').strip()
    tipo_rebote = (payload.get('Type') or '').strip()
    type_code = payload.get('TypeCode')
    smtp_code = str(type_code) if type_code is not None else None
    dsn_status = tipo_rebote or None
    now = timezone.now()

    salidas_afectadas = set()
    procesados = 0
    for sd in qs:
        if sd.estado == 'REBOTE':
            continue
        sd.estado = 'REBOTE'
        sd.dsn_status = dsn_status or sd.dsn_status
        sd.ultimo_evento_at = now
        if smtp_code:
            sd.smtp_code = smtp_code
        if descripcion:
            bloque = f'Postmark: {descripcion}'
            detalle_actual = sd.detalle_error or ''
            if bloque not in detalle_actual:
                sd.detalle_error = f'{detalle_actual}\n{bloque}'.strip()
        sd.save(update_fields=['estado', 'dsn_status', 'ultimo_evento_at', 'smtp_code', 'detalle_error'])
        salidas_afectadas.add(sd.correspondencia_salida)
        procesados += 1

    recipients = {recipient} if recipient else set()
    for salida in salidas_afectadas:
        enviados, total = sincronizar_estado_envio_respuesta(salida, marcar_entrada_respondida=False)
        HistorialSalida.objects.create(
            correspondencia_salida=salida,
            tipo_evento='ENVIO_FALLIDO',
            descripcion=(
                f'Rebote reportado por Postmark ({tipo_rebote or "bounce"}). '
                f'Estado agregado: {enviados}/{total} destinatarios OK.'
            ),
        )
        _crear_notificacion_rebote(salida, recipients, smtp_code, dsn_status)

    return {
        'status': 'processed',
        'record_type': 'Bounce',
        'message_id': postmark_message_id,
        'recipient': recipient,
        'updated': procesados,
    }


@transaction.atomic
def procesar_entrega_postmark(payload: dict) -> dict:
    postmark_message_id = (payload.get('MessageID') or '').strip()
    recipient = _extraer_destinatario(payload)
    salida_id = _extraer_salida_id(payload)

    qs = _buscar_destinatarios_enviados(
        postmark_message_id=postmark_message_id,
        recipient=recipient,
        salida_id=salida_id,
    )
    if not qs.exists():
        logger.info(
            'Entrega Postmark sin match message_id=%s recipient=%s salida_id=%s',
            postmark_message_id,
            recipient,
            salida_id,
        )
        return {
            'status': 'no_match',
            'record_type': 'Delivery',
            'message_id': postmark_message_id,
            'recipient': recipient,
        }

    delivered_at_raw = payload.get('DeliveredAt')
    delivered_at = parse_datetime(delivered_at_raw) if delivered_at_raw else None
    if delivered_at and timezone.is_naive(delivered_at):
        delivered_at = timezone.make_aware(delivered_at)
    evento_at = delivered_at or timezone.now()
    detalle_entrega = (payload.get('Details') or 'Entrega confirmada por Postmark.').strip()

    salidas_afectadas = set()
    procesados = 0
    for sd in qs:
        sd.ultimo_evento_at = evento_at
        bloque = f'Entrega: {detalle_entrega}'
        detalle_actual = sd.detalle_error or ''
        if bloque not in detalle_actual:
            # Reutilizamos detalle_error como bitácora técnica sin cambiar el estado ENVIADO.
            sd.detalle_error = f'{detalle_actual}\n{bloque}'.strip() if detalle_actual else bloque
        sd.save(update_fields=['ultimo_evento_at', 'detalle_error'])
        salidas_afectadas.add(sd.correspondencia_salida)
        procesados += 1

    for salida in salidas_afectadas:
        HistorialSalida.objects.create(
            correspondencia_salida=salida,
            tipo_evento='ENTREGA_CONFIRMADA',
            descripcion=(
                f'Postmark confirmó entrega a {recipient or "destinatario"}. '
                f'{detalle_entrega}'
            ),
        )

    return {
        'status': 'processed',
        'record_type': 'Delivery',
        'message_id': postmark_message_id,
        'recipient': recipient,
        'updated': procesados,
    }
