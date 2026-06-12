"""Comprobaciones operativas de salida Postmark (From, token, proveedor)."""

from __future__ import annotations

import json
from urllib import error, request

from django.conf import settings

POSTMARK_ATTACHMENTS_MAX_BYTES_DEFAULT = 10 * 1024 * 1024
OUTBOUND_ATTACHMENTS_MAX_BYTES_DEFAULT = 25 * 1024 * 1024


def correspondencia_max_outbound_attachments_bytes() -> int:
    """Límite de negocio para carga de adjuntos en salidas (UI/radicación)."""
    return int(
        getattr(
            settings,
            'CORRESPONDENCIA_MAX_OUTBOUND_ATTACHMENTS_BYTES',
            OUTBOUND_ATTACHMENTS_MAX_BYTES_DEFAULT,
        )
    )


def postmark_attachments_limit_bytes() -> int:
    """Límite real de la API Postmark (ErrorCode 300 si se supera)."""
    return int(
        getattr(
            settings,
            'POSTMARK_MAX_ATTACHMENTS_BYTES',
            getattr(
                settings,
                'POSTMARK_ATTACHMENTS_MAX_BYTES',
                POSTMARK_ATTACHMENTS_MAX_BYTES_DEFAULT,
            ),
        )
    )


def salida_adjuntos_upload_limit_bytes() -> int:
    """Límite al subir adjuntos en formularios de salida."""
    return correspondencia_max_outbound_attachments_bytes()


def salida_adjuntos_envio_limit_bytes(*, proveedor_envio: str | None = None) -> int:
    """Límite efectivo al enviar: min(carga, Postmark) si el proveedor es Postmark."""
    upload = salida_adjuntos_upload_limit_bytes()
    if envio_usara_postmark(proveedor_envio=proveedor_envio):
        return min(upload, postmark_attachments_limit_bytes())
    return upload


def salida_adjuntos_limit_bytes() -> int:
    """Alias de límite de carga (compatibilidad con vistas/JS)."""
    return salida_adjuntos_upload_limit_bytes()


def envio_usara_postmark(*, proveedor_envio: str | None = None) -> bool:
    explicit = (proveedor_envio or '').strip().lower()
    if explicit == 'gmail_api':
        return False
    if explicit == 'postmark':
        return True
    return (getattr(settings, 'EMAIL_PROVIDER', '') or '').strip().lower() == 'postmark'


def _format_mb(bytes_val: int) -> str:
    return f'{bytes_val / (1024 * 1024):.2f} MB'


def mensaje_error_carga_adjuntos(total_bytes: int) -> str:
    limite = salida_adjuntos_upload_limit_bytes()
    return (
        f'El tamaño total de adjuntos ({_format_mb(total_bytes)}) supera el límite de carga '
        f'(máx. {limite / (1024 * 1024):.0f} MB). '
        'Use un enlace de Drive en el cuerpo del mensaje para archivos más pesados.'
    )


def validar_adjuntos_para_envio(
    adjuntos: list[tuple[str, bytes, str]],
    *,
    proveedor_envio: str | None = None,
) -> None:
    """
    Valida tamaño total de adjuntos antes de enviar.

    Raises:
        ValueError: si Postmark rechazaría el envío (ErrorCode 300, límite 10 MB).
    """
    if not envio_usara_postmark(proveedor_envio=proveedor_envio):
        upload_limite = salida_adjuntos_upload_limit_bytes()
        total = sum(len(contenido) for _, contenido, _ in adjuntos)
        if total <= upload_limite:
            return
        raise ValueError(mensaje_error_carga_adjuntos(total))

    limite = postmark_attachments_limit_bytes()
    total = sum(len(contenido) for _, contenido, _ in adjuntos)
    if total <= limite:
        return

    archivos = [
        f'{nombre} ({len(contenido) / (1024 * 1024):.2f} MB)'
        for nombre, contenido, _ in adjuntos
    ]
    raise ValueError(
        f'Los adjuntos suman {_format_mb(total)} y superan el límite de Postmark '
        f'(máx. {limite / (1024 * 1024):.0f} MB). Postmark no permite más de 10 MB en adjuntos; '
        f'no es posible enviar {correspondencia_max_outbound_attachments_bytes() / (1024 * 1024):.0f} MB '
        'por este canal. Reduzca o comprima archivos, incluya un enlace Drive en el cuerpo, '
        'o solicite envío alternativo por Gmail API. '
        f'Archivos: {", ".join(archivos)}.'
    )


def _verified_sender_candidates() -> list[str]:
    raw = (
        getattr(settings, 'POSTMARK_VERIFIED_SENDERS', None)
        or getattr(settings, 'POSTMARK_VERIFIED_SENDER', '')
        or 'correspondencia@esehospitaldelsarare.gov.co'
    )
    if isinstance(raw, (list, tuple)):
        return [str(item).strip().lower() for item in raw if str(item).strip()]
    return [part.strip().lower() for part in str(raw).split(',') if part.strip()]


def build_postmark_outbound_status(*, probe_api: bool = False) -> dict:
    """
    Estado de configuración saliente Postmark para monitoreo y arranque.

    probe_api: si True y hay token, consulta GET /senders (no envía correo).
    """
    provider = (getattr(settings, 'EMAIL_PROVIDER', '') or '').strip().lower()
    outbound = (getattr(settings, 'OUTBOUND_EMAIL_ADDRESS', '') or '').strip()
    token = (getattr(settings, 'POSTMARK_SERVER_TOKEN', '') or '').strip()
    stream = (getattr(settings, 'POSTMARK_MESSAGE_STREAM', '') or 'outbound').strip() or 'outbound'
    verified = _verified_sender_candidates()
    outbound_lower = outbound.lower()

    issues: list[str] = []
    if provider != 'postmark':
        issues.append(f'EMAIL_PROVIDER={provider or "(vacío)"}; se esperaba postmark.')
    if not token:
        issues.append('POSTMARK_SERVER_TOKEN no configurado.')
    if not outbound or '@' not in outbound:
        issues.append('OUTBOUND_EMAIL_ADDRESS vacío o inválido.')
    elif verified and outbound_lower not in verified:
        issues.append(
            f'OUTBOUND_EMAIL_ADDRESS ({outbound}) no coincide con remitentes verificados en Postmark: '
            f'{", ".join(verified)}.'
        )

    api_ok = None
    api_detail = ''
    if probe_api and token and provider == 'postmark':
        api_ok, api_detail = _probe_postmark_senders(token)

    return {
        'email_provider': provider,
        'outbound_email_address': outbound,
        'postmark_message_stream': stream,
        'postmark_token_configured': bool(token),
        'postmark_verified_senders': verified,
        'outbound_matches_verified_sender': (
            bool(outbound_lower and verified and outbound_lower in verified)
        ),
        'postmark_outbound_ready': (
            provider == 'postmark'
            and bool(token)
            and bool(outbound)
            and (not verified or outbound_lower in verified)
        ),
        'postmark_outbound_issues': issues,
        'postmark_api_reachable': api_ok,
        'postmark_api_detail': api_detail,
        'postmark_attachments_max_bytes': postmark_attachments_limit_bytes(),
        'outbound_attachments_upload_max_bytes': salida_adjuntos_upload_limit_bytes(),
    }


def _probe_postmark_senders(server_token: str) -> tuple[bool | None, str]:
    """Comprueba token de servidor contra GET /message-streams (no envía correo)."""
    req = request.Request(
        'https://api.postmarkapp.com/message-streams',
        headers={
            'Accept': 'application/json',
            'X-Postmark-Server-Token': server_token,
        },
        method='GET',
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode('utf-8')
        parsed = json.loads(body or '{}')
        streams = parsed.get('MessageStreams') if isinstance(parsed, dict) else parsed
        names = []
        for item in streams or []:
            if isinstance(item, dict):
                name = (item.get('ID') or item.get('Name') or '').strip()
                if name:
                    names.append(name)
        return True, f'token válido; streams: {", ".join(names) or "(sin listar)"}'
    except error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace') if hasattr(exc, 'read') else str(exc)
        return False, f'HTTP {exc.code}: {body[:200]}'
    except error.URLError as exc:
        return False, f'Sin conexión: {exc.reason}'
    except Exception as exc:
        return False, str(exc)
