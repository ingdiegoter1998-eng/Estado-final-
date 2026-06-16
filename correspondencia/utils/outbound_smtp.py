"""Conexión SMTP para envíos salientes puntuales sin Gmail API."""

from django.conf import settings
from django.core.mail import get_connection


def smtp_outbound_disponible() -> bool:
    """True si hay usuario y contraseña para envío SMTP institucional."""
    user = (
        getattr(settings, 'EMAIL_HOST_USER', '')
        or getattr(settings, 'IMAP_MANUAL_EMAIL_USER', '')
    ).strip()
    password = (
        getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        or getattr(settings, 'IMAP_MANUAL_EMAIL_PASSWORD', '')
    ).strip()
    return bool(user and password and '@' in user)


def get_outbound_smtp_mail_connection():
    """
    Envío saliente por SMTP (smtp.gmail.com / Workspace).
    No consume cuota de Gmail API; útil durante rate limit 429.
    """
    if not smtp_outbound_disponible():
        raise ValueError(
            'Configure EMAIL_HOST_USER + EMAIL_HOST_PASSWORD '
            '(o IMAP_MANUAL_EMAIL_USER / IMAP_MANUAL_EMAIL_PASSWORD).'
        )
    user = (
        getattr(settings, 'EMAIL_HOST_USER', '')
        or getattr(settings, 'IMAP_MANUAL_EMAIL_USER', '')
    ).strip()
    password = (
        getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        or getattr(settings, 'IMAP_MANUAL_EMAIL_PASSWORD', '')
    ).strip()
    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com'),
        port=int(getattr(settings, 'EMAIL_PORT', 587)),
        username=user,
        password=password,
        use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
    )
