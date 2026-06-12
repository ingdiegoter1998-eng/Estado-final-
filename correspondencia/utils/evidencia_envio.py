"""Utilidades para trazabilidad de envío y evidencia de entrega."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from correspondencia.models import HistorialSalida, PostmarkWebhookEvento, SalidaDestinatario


def _outbound_provider_label() -> str:
    provider = (getattr(settings, 'EMAIL_PROVIDER', '') or 'smtp').strip().lower()
    if provider == 'gmail_api':
        return 'Gmail API'
    if provider == 'postmark':
        return 'Postmark'
    return 'SMTP'


NIVEL_EVIDENCIA_COMPLETA = 'COMPLETA'
NIVEL_EVIDENCIA_ENVIADO = 'ENVIADO_SIN_CONFIRMACION'
NIVEL_EVIDENCIA_REBOTE = 'REBOTE'
NIVEL_EVIDENCIA_FALLO = 'FALLO'
NIVEL_EVIDENCIA_PENDIENTE = 'PENDIENTE'

NIVEL_LABELS = {
    NIVEL_EVIDENCIA_COMPLETA: 'Entrega confirmada (tercero)',
    NIVEL_EVIDENCIA_ENVIADO: 'Enviado — sin confirmación de entrega',
    NIVEL_EVIDENCIA_REBOTE: 'Rebote registrado',
    NIVEL_EVIDENCIA_FALLO: 'Fallo de envío',
    NIVEL_EVIDENCIA_PENDIENTE: 'Pendiente',
}


@dataclass
class FilaSeguimiento:
    destinatario_id: int
    salida_id: int
    numero_radicado: str
    asunto: str
    oficina: str
    email: str
    nombre: str
    estado: str
    nivel_evidencia: str
    nivel_label: str
    fecha_envio: datetime | None
    postmark_message_id: str | None
    ultimo_evento_at: datetime | None
    tiene_entrega_confirmada: bool
    detalle_resumen: str


def linea_es_confirmacion_entrega(linea: str) -> bool:
    """True si la línea de detalle_error registra aceptación SMTP (p. ej. Postmark Delivery)."""
    texto = (linea or '').strip()
    if not texto:
        return True
    lower = texto.lower()
    if lower.startswith('dsn:') or lower.startswith('postmark:'):
        return False
    if not lower.startswith('entrega:'):
        return False
    cuerpo = lower.split(':', 1)[-1]
    if 'entrega confirmada' in cuerpo:
        return True
    if '250' in cuerpo and 'ok' in cuerpo:
        return True
    if '250 2.0.0' in cuerpo or '250 2.1.0' in cuerpo:
        return True
    return 'smtp;250' in cuerpo.replace(' ', '')


def detalle_error_es_solo_confirmacion_entrega(detalle_error: str | None) -> bool:
    """True cuando detalle_error solo contiene bitácora de entrega exitosa (no errores/rebotes)."""
    detalle = (detalle_error or '').strip()
    if not detalle:
        return False
    for linea in detalle.splitlines():
        if linea.strip() and not linea_es_confirmacion_entrega(linea):
            return False
    return True


def destinatario_tiene_problema_entrega(destinatario: SalidaDestinatario) -> bool:
    """True solo para fallos/rebotes reales, no para confirmaciones SMTP 250 en detalle_error."""
    if destinatario.estado in ('FALLO', 'REBOTE'):
        return True
    detalle = (destinatario.detalle_error or '').strip()
    if detalle and not detalle_error_es_solo_confirmacion_entrega(detalle):
        return True
    smtp_code = destinatario.smtp_code
    if smtp_code and str(smtp_code).startswith(('4', '5')):
        return True
    dsn_status = destinatario.dsn_status
    if dsn_status and str(dsn_status).startswith(('4.', '5.')):
        return True
    return False


def destinatario_entrega_confirmada_servidor(destinatario: SalidaDestinatario) -> bool:
    """True cuando hay evidencia de que el servidor del destinatario aceptó el mensaje."""
    if destinatario.estado != 'ENVIADO':
        return False
    if _tiene_entrega_confirmada(destinatario):
        return True
    return detalle_error_es_solo_confirmacion_entrega(destinatario.detalle_error)


def _tiene_entrega_confirmada(destinatario: SalidaDestinatario) -> bool:
    salida_id = destinatario.correspondencia_salida_id
    email = (destinatario.email_snapshot or '').strip().lower()
    if HistorialSalida.objects.filter(
        correspondencia_salida_id=salida_id,
        tipo_evento='ENTREGA_CONFIRMADA',
        descripcion__icontains=email,
    ).exists():
        return True
    pm_id = (destinatario.postmark_message_id or '').strip()
    if pm_id:
        return PostmarkWebhookEvento.objects.filter(
            record_type='Delivery',
            postmark_message_id=pm_id,
            recipient__iexact=email,
            procesado=True,
            resultado='processed',
        ).exists()
    return False


def clasificar_nivel_evidencia(destinatario: SalidaDestinatario) -> str:
    estado = destinatario.estado
    if estado == 'REBOTE':
        return NIVEL_EVIDENCIA_REBOTE
    if estado == 'FALLO':
        return NIVEL_EVIDENCIA_FALLO
    if estado == 'PENDIENTE':
        return NIVEL_EVIDENCIA_PENDIENTE
    if estado == 'ENVIADO' and _tiene_entrega_confirmada(destinatario):
        return NIVEL_EVIDENCIA_COMPLETA
    if estado == 'ENVIADO':
        return NIVEL_EVIDENCIA_ENVIADO
    return NIVEL_EVIDENCIA_PENDIENTE


def _resumen_detalle(destinatario: SalidaDestinatario, nivel: str) -> str:
    if nivel == NIVEL_EVIDENCIA_REBOTE:
        return (destinatario.dsn_status or 'Rebote') + (
            f': {(destinatario.detalle_error or "")[:120]}' if destinatario.detalle_error else ''
        )
    if nivel == NIVEL_EVIDENCIA_FALLO:
        return (destinatario.detalle_error or 'Error de envío')[:160]
    if nivel == NIVEL_EVIDENCIA_COMPLETA:
        bloque = destinatario.detalle_error or ''
        for linea in bloque.splitlines():
            if linea.strip().lower().startswith('entrega:'):
                return linea.replace('Entrega:', '').strip()[:160]
        return 'Confirmación de entrega (webhook del proveedor)'
    if destinatario.postmark_message_id:
        return f'ID de mensaje ({_outbound_provider_label()}): {destinatario.postmark_message_id}'
    return ''


def resumir_confirmacion_entrega_destinatario(destinatario: SalidaDestinatario) -> SalidaDestinatario:
    """Enriquece un destinatario ENVIADO con resumen legible de confirmación SMTP."""
    nivel = clasificar_nivel_evidencia(destinatario)
    destinatario.entrega_resumen = _resumen_detalle(destinatario, nivel) or (
        'El servidor del destinatario aceptó el mensaje (confirmación SMTP 250).'
    )
    detalle = (destinatario.detalle_error or '').strip()
    destinatario.entrega_detalle_tecnico = detalle or destinatario.entrega_resumen
    return destinatario


def fila_seguimiento_desde_destinatario(destinatario: SalidaDestinatario) -> FilaSeguimiento:
    salida = destinatario.correspondencia_salida
    nivel = clasificar_nivel_evidencia(destinatario)
    oficina = ''
    if salida.oficina_emisora_nombre:
        oficina = salida.oficina_emisora_nombre
    elif salida.oficina_emisora_id:
        oficina = getattr(salida.oficina_emisora, 'nombre', '') or ''

    return FilaSeguimiento(
        destinatario_id=destinatario.id,
        salida_id=salida.id,
        numero_radicado=salida.numero_radicado_salida,
        asunto=salida.asunto or '',
        oficina=oficina,
        email=destinatario.email_snapshot,
        nombre=destinatario.nombre_snapshot or '',
        estado=destinatario.estado,
        nivel_evidencia=nivel,
        nivel_label=NIVEL_LABELS[nivel],
        fecha_envio=destinatario.fecha_envio,
        postmark_message_id=destinatario.postmark_message_id,
        ultimo_evento_at=destinatario.ultimo_evento_at,
        tiene_entrega_confirmada=nivel == NIVEL_EVIDENCIA_COMPLETA,
        detalle_resumen=_resumen_detalle(destinatario, nivel),
    )


def eventos_webhook_para_destinatario(destinatario: SalidaDestinatario):
    pm_id = (destinatario.postmark_message_id or '').strip()
    if not pm_id:
        return PostmarkWebhookEvento.objects.none()
    email = (destinatario.email_snapshot or '').strip()
    qs = PostmarkWebhookEvento.objects.filter(postmark_message_id=pm_id)
    if email:
        qs = qs.filter(recipient__iexact=email)
    return qs.order_by('recibido_at')


def linea_tiempo_salida(salida_id: int) -> list[dict]:
    """Unifica historial de salida y webhooks vinculados por MessageID."""
    eventos: list[dict] = []

    for h in HistorialSalida.objects.filter(correspondencia_salida_id=salida_id).select_related('usuario'):
        eventos.append({
            'fecha': h.fecha_hora,
            'tipo': h.get_tipo_evento_display(),
            'origen': 'Sistema',
            'usuario': h.usuario.get_full_name() if h.usuario else None,
            'detalle': h.descripcion or '',
            'codigo': h.tipo_evento,
        })

    message_ids = set(
        SalidaDestinatario.objects.filter(correspondencia_salida_id=salida_id)
        .exclude(postmark_message_id__isnull=True)
        .exclude(postmark_message_id='')
        .values_list('postmark_message_id', flat=True)
    )
    for pm_id in message_ids:
        for wh in PostmarkWebhookEvento.objects.filter(postmark_message_id=pm_id).order_by('recibido_at'):
            detalle = wh.payload.get('Details') or wh.payload.get('Description') or wh.resultado
            eventos.append({
                'fecha': wh.recibido_at,
                'tipo': f'Postmark {wh.record_type}',
                'origen': 'Postmark (tercero)',
                'usuario': None,
                'detalle': f'{wh.recipient}: {detalle}',
                'codigo': wh.record_type,
            })

    eventos.sort(key=lambda e: e['fecha'] or timezone.now())
    return eventos
