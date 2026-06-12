"""Conexión Gmail API para envíos salientes puntuales sin cambiar EMAIL_PROVIDER global."""

from django.conf import settings
from django.core.mail import get_connection


def gmail_api_outbound_disponible() -> bool:
    """True si hay credenciales OAuth para envío saliente por Gmail API."""
    return all(
        getattr(settings, key, '').strip()
        for key in (
            'GMAIL_API_CLIENT_ID',
            'GMAIL_API_CLIENT_SECRET',
            'GMAIL_API_REFRESH_TOKEN',
        )
    )


def get_outbound_gmail_api_mail_connection():
    """
    Envío saliente por Gmail API (OAuth). Producción puede seguir en Postmark
    (EMAIL_BACKEND global); usar solo en comandos/operaciones one-off.
    """
    backend = getattr(
        settings,
        'OUTBOUND_GMAIL_API_EMAIL_BACKEND',
        'correspondencia.email_backends.GmailAPIEmailBackend',
    )
    return get_connection(backend=backend)
