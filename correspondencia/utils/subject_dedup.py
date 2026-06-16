"""Claves de asunto y deduplicación por contenido (reenvíos institucionales Fwd/Re)."""

from __future__ import annotations

import re
from datetime import timedelta

from django.utils import timezone

from correspondencia.utils.blocked_recipients import (
    emails_destinatarios_bloqueados,
    normalizar_email_destinatario,
)
from correspondencia.utils.message_id_utils import message_id_matches_stored

_SUBJECT_PREFIXES = ('fwd:', 'fw:', 're:', 'rv:', 'res:')


def normalize_subject_key(subject: str) -> str:
    """Asunto normalizado sin prefijos Fwd/Re y con espacios colapsados."""
    text = re.sub(r'\s+', ' ', (subject or '').strip().lower())
    changed = True
    while changed:
        changed = False
        for prefix in _SUBJECT_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                changed = True
    return text


def es_remitente_institucional(email_raw: str) -> bool:
    normalizado = normalizar_email_destinatario(email_raw)
    return bool(normalizado and normalizado in emails_destinatarios_bloqueados())


def es_asunto_reenvio(subject: str) -> bool:
    subject_lower = (subject or '').strip().lower()
    return any(subject_lower.startswith(prefix) for prefix in _SUBJECT_PREFIXES)


def _message_ids_desde_referencias(headers: dict) -> list[str]:
    from correspondencia.utils.message_id_utils import normalize_message_id_value

    ids: list[str] = []
    for header_name in ('references', 'in-reply-to'):
        values = headers.get(header_name) or headers.get(header_name.title()) or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            for token in re.findall(r'<[^>]+>', str(value)):
                canonical = normalize_message_id_value(token)
                if canonical and '@' in canonical:
                    ids.append(canonical)
    return ids


def buscar_correo_activo_mismo_contenido(
    subject_key: str,
    *,
    exclude_canonical_mid: str = '',
    ventana_dias: int = 60,
):
    from correspondencia.models import CorreoEntrante

    if not subject_key:
        return None

    desde = timezone.now() - timedelta(days=ventana_dias)
    qs = CorreoEntrante.objects.filter(en_papelera=False, fecha_lectura_imap__gte=desde)
    token = subject_key[:50].strip()
    if token:
        qs = qs.filter(asunto__icontains=token)

    for correo in qs.only('id', 'asunto', 'message_id', 'remitente').order_by('id')[:300]:
        if normalize_subject_key(correo.asunto) != subject_key:
            continue
        if exclude_canonical_mid and message_id_matches_stored(exclude_canonical_mid, correo.message_id):
            continue
        return correo
    return None


def debe_omitir_reenvio_institucional_redundante(
    *,
    remitente_raw: str,
    subject: str,
    headers: dict | None,
    canonical_message_id: str,
) -> tuple[bool, str]:
    """
    Omite reenvíos manuales del buzón institucional cuando el contenido ya está en bandeja
    o el Message-ID referenciado ya fue ingestado.
    """
    if not es_remitente_institucional(remitente_raw):
        return False, ''

    subject_key = normalize_subject_key(subject)
    if not subject_key:
        return True, 'Mensaje institucional sin asunto (omitido).'

    if not es_asunto_reenvio(subject):
        return False, ''

    for ref_mid in _message_ids_desde_referencias(headers or {}):
        from correspondencia.models import CorreoEntrante

        if CorreoEntrante.objects.filter(message_id=ref_mid).exists():
            return True, f'Reenvío redundante (Message-ID referenciado ya en BD: {ref_mid[:40]}).'
        if CorreoEntrante.objects.filter(message_id__contains=ref_mid[:40]).exists():
            return True, 'Reenvío redundante (Message-ID referenciado ya en BD).'

    existente = buscar_correo_activo_mismo_contenido(
        subject_key,
        exclude_canonical_mid=canonical_message_id,
    )
    if existente:
        return True, f'Reenvío institucional redundante (contenido ya en bandeja id={existente.id}).'

    return False, ''
