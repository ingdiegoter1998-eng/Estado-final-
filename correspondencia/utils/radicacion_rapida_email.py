"""Envío de notificaciones de radicación rápida entrante vía Gmail API."""

from __future__ import annotations

import os
from typing import Sequence

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string

from correspondencia.aprobacion_envio import (
    _ajustar_to_bcc_gmail_api,
    _direccion_remitente_visible,
)
from correspondencia.utils.blocked_recipients import (
    mensaje_destinatario_bloqueado,
    normalizar_email_destinatario,
    validar_emails_destinatario_permitidos,
)

HEADER_NOTIFICACION_CORRESPONDENCIA = 'X-Correspondencia-Notification'
VALOR_NOTIFICACION_RADICACION_RAPIDA = 'radicacion-rapida'


class DestinatarioNotificacionRapidaInvalido(ValueError):
    """El correo del funcionario no puede usarse como destinatario de la notificación."""


def get_radicacion_rapida_entrante_mail_connection():
    """
    Notificaciones de radicación rápida entrante → Gmail API (cuenta institucional).
  """
    backend = getattr(
        settings,
        'RADICACION_RAPIDA_ENTRANTE_EMAIL_BACKEND',
        'correspondencia.email_backends.GmailAPIEmailBackend',
    )
    return get_connection(backend=backend)


def preparar_destinatarios_notificacion_radicacion_rapida(email_funcionario: str) -> tuple[list[str], list[str]]:
    """
    Gmail API: un destinatario real en To, sin copiar al buzón institucional.
    Alineado con aprobacion_envio._ajustar_to_bcc_gmail_api.
    """
    email = (email_funcionario or '').strip()
    if not email:
        return [], []

    ok, error = validar_emails_destinatario_permitidos([email])
    if not ok:
        raise DestinatarioNotificacionRapidaInvalido(error or mensaje_destinatario_bloqueado(email))

    return _ajustar_to_bcc_gmail_api([], [email])


def _remitente_notificacion_radicacion_rapida() -> str:
    remitente = _direccion_remitente_visible()
    if not remitente:
        raise ValueError(
            'Configure OUTBOUND_EMAIL_ADDRESS (o DEFAULT_FROM_EMAIL) con el buzón Gmail API autorizado.'
        )
    return remitente


def enviar_notificacion_radicacion_rapida_entrante(
    *,
    email_funcionario: str,
    contexto_email: dict,
    asunto: str,
    adjuntos: Sequence[tuple[str, bytes, str]] | None = None,
    extra_headers: dict | None = None,
    connection=None,
) -> EmailMessage:
    """
    Envía la notificación HTML al funcionario responsable.
    No usa In-Reply-To: el envío sale del buzón institucional y el threading
    duplicaba el hilo original en esa bandeja.
    """
    to_recipients, bcc_recipients = preparar_destinatarios_notificacion_radicacion_rapida(
        email_funcionario
    )
    if not to_recipients:
        raise DestinatarioNotificacionRapidaInvalido('No hay destinatario válido para la notificación.')

    html_notificacion = render_to_string(
        'correspondencia/email/notificacion_asignacion_entrante.html',
        contexto_email,
    )

    mail_connection = connection or get_radicacion_rapida_entrante_mail_connection()
    owned_connection = connection is None
    if owned_connection:
        mail_connection.open()

    notification_headers = dict(extra_headers or {})
    notification_headers.setdefault(
        HEADER_NOTIFICACION_CORRESPONDENCIA,
        VALOR_NOTIFICACION_RADICACION_RAPIDA,
    )

    try:
        email_msg = EmailMessage(
            subject=asunto,
            body=html_notificacion,
            from_email=_remitente_notificacion_radicacion_rapida(),
            to=to_recipients,
            bcc=bcc_recipients,
            connection=mail_connection,
            headers=notification_headers,
        )
        email_msg.content_subtype = 'html'

        for nombre, contenido, tipo_mime in adjuntos or ():
            email_msg.attach(nombre, contenido, tipo_mime or 'application/octet-stream')

        email_msg.send(fail_silently=False)
        return email_msg
    finally:
        if owned_connection:
            try:
                mail_connection.close()
            except Exception:
                pass


def adjuntos_desde_queryset(adjuntos_qs):
    """Lee adjuntos de modelos con archivo, nombre_original y tipo_mime."""
    items = []
    for adj in adjuntos_qs:
        if not adj.archivo:
            continue
        try:
            adj.archivo.open('rb')
            items.append((
                adj.nombre_original or os.path.basename(adj.archivo.name),
                adj.archivo.read(),
                adj.tipo_mime or 'application/octet-stream',
            ))
        except Exception:
            continue
        finally:
            try:
                adj.archivo.close()
            except Exception:
                pass
    return items


def es_email_institucional_bloqueado(email: str) -> bool:
    """True si el correo coincide con el buzón institucional (no debe ser destinatario)."""
    normalizado = normalizar_email_destinatario(email)
    if not normalizado:
        return False
    ok, _ = validar_emails_destinatario_permitidos([email])
    return not ok
