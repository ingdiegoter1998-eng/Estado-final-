"""Destinatarios institucionales que no deben usarse en salidas (To/Cc/Bcc manual)."""
from __future__ import annotations

import re
from functools import lru_cache

from django.conf import settings

_EMAIL_IN_ANGLE = re.compile(r'<([^>]+)>')

MENSAJE_DESTINATARIO_INSTITUCIONAL = (
    'No puede agregar {email} como destinatario: corresponde a la cuenta del '
    'sistema de correspondencia del hospital. Utilice únicamente el correo del '
    'contacto o entidad destinatario. No aporta al envío y complica el seguimiento '
    'del radicado.'
)

AVISO_UI_DESTINATARIOS = (
    'No incluya la cuenta institucional de correspondencia entre los destinatarios. '
    'Es el buzón del propio sistema; agregarla no entrega la respuesta al destinatario '
    'externo y solo genera registros duplicados en la bandeja institucional.'
)


def normalizar_email_destinatario(raw: str) -> str:
    """Normaliza un correo para comparación en la blocklist."""
    value = (raw or '').strip()
    if not value:
        return ''
    match = _EMAIL_IN_ANGLE.search(value)
    if match:
        value = match.group(1)
    return value.strip().lower()


def _agregar_email_si_valido(destino: set[str], raw: str) -> None:
    email = normalizar_email_destinatario(raw)
    if email and '@' in email:
        destino.add(email)


@lru_cache(maxsize=1)
def emails_destinatarios_bloqueados() -> frozenset[str]:
    """Conjunto de correos institucionales bloqueados como destinatarios."""
    bloqueados: set[str] = set()

    for valor in getattr(settings, 'CORRESPONDENCIA_INSTITUTIONAL_INBOX_DEFAULTS', ()) or ():
        _agregar_email_si_valido(bloqueados, valor)

    for attr in (
        'OUTBOUND_EMAIL_ADDRESS',
        'EMAIL_HOST_USER',
        'IMAP_MANUAL_EMAIL_USER',
        'DEFAULT_FROM_EMAIL',
    ):
        _agregar_email_si_valido(bloqueados, getattr(settings, attr, '') or '')

    for valor in getattr(settings, 'POSTMARK_VERIFIED_SENDERS', ()) or ():
        _agregar_email_si_valido(bloqueados, valor)

    for valor in getattr(settings, 'CORRESPONDENCIA_BLOCKED_RECIPIENT_EMAILS', ()) or ():
        _agregar_email_si_valido(bloqueados, valor)

    return frozenset(bloqueados)


def destinatarios_bloqueados_en_lista(emails) -> list[str]:
    """Devuelve los correos bloqueados presentes en la lista (orden estable)."""
    bloqueados = emails_destinatarios_bloqueados()
    encontrados: list[str] = []
    vistos: set[str] = set()
    for raw in emails or []:
        email = normalizar_email_destinatario(raw)
        if email and email in bloqueados and email not in vistos:
            vistos.add(email)
            encontrados.append(email)
    return encontrados


def mensaje_destinatario_bloqueado(email: str | None = None) -> str:
    etiqueta = (email or 'esta dirección').strip() or 'esta dirección'
    return MENSAJE_DESTINATARIO_INSTITUCIONAL.format(email=etiqueta)


def validar_emails_destinatario_permitidos(emails) -> tuple[bool, str | None]:
    """Valida que ningún destinatario esté en la blocklist institucional."""
    bloqueados = destinatarios_bloqueados_en_lista(emails)
    if not bloqueados:
        return True, None
    return False, mensaje_destinatario_bloqueado(bloqueados[0])
