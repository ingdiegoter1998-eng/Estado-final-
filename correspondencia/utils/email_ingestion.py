import json
import logging
import re
import email.utils as email_utils
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from correspondencia.models import AdjuntoCorreoEntrante, CorreoEntrante, CorreoProblematico
from correspondencia.utils.blocked_recipients import (
    emails_destinatarios_bloqueados,
    normalizar_email_destinatario,
)
from correspondencia.utils.email_attachment_validator import EmailAttachmentValidator
from correspondencia.utils.email_body_extractor import extraer_cuerpos_correo
from correspondencia.utils.email_provider import build_email_inbox_provider
from correspondencia.utils.message_id_utils import (
    build_known_message_id_set,
    message_id_matches_stored,
    normalize_message_id_value,
)
from correspondencia.utils.subject_dedup import debe_omitir_reenvio_institucional_redundante
from correspondencia.utils.radicacion_rapida_email import (
    HEADER_NOTIFICACION_CORRESPONDENCIA,
    VALOR_NOTIFICACION_RADICACION_RAPIDA,
)

logger = logging.getLogger(__name__)

_ASUNTOS_NOTIFICACION_RADICACION_RAPIDA = (
    'correspondencia asignada - ',
    'radicado de salida ',
)


def _header_values(msg, header_name: str) -> list[str]:
    headers = getattr(msg, 'headers', {}) or {}
    key = header_name.lower()
    values = headers.get(key)
    if values is None:
        values = headers.get(header_name)
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values if value is not None]


def _asunto_mensaje(msg) -> str:
    subject = (getattr(msg, 'subject', None) or '').strip()
    if subject:
        return subject
    return (_header_values(msg, 'subject') or [''])[0].strip()


def _remitente_mensaje(msg) -> str:
    from_email = (getattr(msg, 'from_', None) or '').strip()
    if from_email:
        return from_email
    return (_header_values(msg, 'from') or [''])[0].strip()


def _es_asunto_notificacion_radicacion_rapida(subject: str) -> bool:
    subject_lower = (subject or '').strip().lower()
    if not subject_lower:
        return False
    if any(subject_lower.startswith(prefix) for prefix in _ASUNTOS_NOTIFICACION_RADICACION_RAPIDA):
        return True
    if subject_lower.startswith('fwd:'):
        inner = subject_lower[4:].strip()
        return any(inner.startswith(prefix) for prefix in _ASUNTOS_NOTIFICACION_RADICACION_RAPIDA)
    return False


def _es_notificacion_saliente_correspondencia(msg) -> bool:
    for value in _header_values(msg, HEADER_NOTIFICACION_CORRESPONDENCIA):
        if value.strip().lower() == VALOR_NOTIFICACION_RADICACION_RAPIDA:
            return True
    return False


def _debe_omitir_mensaje_propio_o_notificacion(msg) -> tuple[bool, str]:
    """
    Omite notificaciones de radicación rápida y reenvíos manuales redundantes
    del buzón institucional (Fwd/Re que duplican contenido ya en bandeja).
    """
    if _es_notificacion_saliente_correspondencia(msg):
        return True, 'Notificación interna (X-Correspondencia-Notification).'

    remitente_raw = _remitente_mensaje(msg)
    remitente_normalizado = normalizar_email_destinatario(remitente_raw)
    if remitente_normalizado and remitente_normalizado in emails_destinatarios_bloqueados():
        if _es_asunto_notificacion_radicacion_rapida(_asunto_mensaje(msg)):
            return True, 'Notificación de radicación rápida enviada por el buzón institucional.'

    canonical_mid = normalize_message_id_value(_raw_message_id_from_msg(msg))
    omitir, motivo = debe_omitir_reenvio_institucional_redundante(
        remitente_raw=remitente_raw,
        subject=_asunto_mensaje(msg),
        headers=getattr(msg, 'headers', {}) or {},
        canonical_message_id=canonical_mid,
    )
    if omitir:
        return True, motivo

    return False, ''


def _raw_message_id_from_msg(msg) -> str:
    for value in _header_values(msg, 'message-id'):
        if value:
            return value
    return ''


def _normalize_message_id(msg, fallback_domain='local.host'):
    message_id = normalize_message_id_value(_raw_message_id_from_msg(msg))
    if message_id:
        return message_id
    domain = fallback_domain or 'local.host'
    return f"generated.{getattr(msg, 'uid', '0')}.{timezone.now().strftime('%Y%m%d%H%M%S%f')}@{domain}"


def correo_ya_registrado_por_message_id(canonical_id: str) -> bool:
    """True si ya existe un CorreoEntrante con ese Message-ID (incluye legacy malformados)."""
    if not canonical_id:
        return False
    if CorreoEntrante.objects.filter(message_id=canonical_id).exists():
        return True
    if CorreoEntrante.objects.filter(message_id__contains=canonical_id).exists():
        for stored in CorreoEntrante.objects.filter(message_id__contains=canonical_id).values_list(
            'message_id', flat=True
        )[:50]:
            if message_id_matches_stored(canonical_id, stored):
                return True
    return False


def load_known_correo_message_ids() -> set[str]:
    """IDs almacenados + forma canónica (CorreoEntrante y problemáticos abiertos)."""
    stored = list(CorreoEntrante.objects.values_list('message_id', flat=True))
    stored.extend(
        CorreoProblematico.objects.filter(resuelto=False).values_list('message_id', flat=True)
    )
    return build_known_message_id_set(stored)


def _normalize_datetime(value):
    if not value:
        return None
    if timezone.is_naive(value):
        try:
            return timezone.make_aware(value, timezone.get_default_timezone())
        except Exception:
            return timezone.make_aware(value, timezone.utc)
    return value


def _extract_message_dates(msg):
    fecha_gmail = _normalize_datetime(msg.date or timezone.now())

    header_date_str = ''
    try:
        header_date_str = (msg.headers.get('date') or [''])[0]
    except Exception:
        header_date_str = ''

    fecha_header = None
    if header_date_str:
        try:
            fecha_header = email_utils.parsedate_to_datetime(header_date_str)
            fecha_header = _normalize_datetime(fecha_header)
        except Exception:
            fecha_header = None

    return fecha_gmail, fecha_header


def _build_attachment_metadata(msg):
    attachments_info = []
    attachments_summary = []
    for index, att in enumerate(msg.attachments or []):
        filename = getattr(att, 'filename', '') or f"adjunto_{index + 1}"
        payload = getattr(att, 'payload', None) or b''
        size_bytes = len(payload)
        content_type = getattr(att, 'content_type', None) or 'application/octet-stream'
        content_id = getattr(att, 'content_id', '') or ''

        attachments_info.append((filename, size_bytes))
        attachments_summary.append({
            'filename': filename,
            'size_mb': round(size_bytes / (1024 * 1024), 2),
            'size_bytes': size_bytes,
            'content_type': content_type,
            'content_id': content_id,
        })

    return attachments_info, attachments_summary


def _extract_raw_message_bytes(msg):
    raw_obj = getattr(msg, 'obj', None)
    if raw_obj is not None:
        try:
            return bytes(raw_obj)
        except Exception:
            pass

    raw_bytes = getattr(msg, 'raw_bytes', None)
    if isinstance(raw_bytes, (bytes, bytearray)):
        return bytes(raw_bytes)

    return None


def _problem_backup_filename(message_id):
    sanitized = re.sub(r'[^A-Za-z0-9._-]+', '_', (message_id or 'correo_problematico')).strip('._')
    if not sanitized:
        sanitized = 'correo_problematico'
    return f"{sanitized}.eml"


def _load_mailmessage_from_problem_backup(problema):
    if not problema.respaldo_eml:
        return None

    try:
        from imap_tools import MailMessage

        with problema.respaldo_eml.open('rb') as respaldo_file:
            return MailMessage.from_bytes(respaldo_file.read())
    except Exception as exc:
        logger.warning(
            "No se pudo reconstruir correo desde respaldo .eml (problema_id=%s): %s",
            problema.pk,
            exc,
        )
        return None


def _resolve_problem_reason(exc):
    detail = str(exc)
    detail_upper = detail.upper()
    if 'EXCEDE' in detail_upper and 'TAMAÑO MÁXIMO' in detail_upper:
        return 'ADJUNTO_EXCEDE_LIMITE', detail
    if 'TAMAÑO TOTAL' in detail_upper or 'MÁXIMO PERMITIDO' in detail_upper:
        return 'TOTAL_EXCEDE_LIMITE', detail
    if 'BLOQUEADO' in detail_upper:
        return 'TIPO_BLOQUEADO', detail
    if 'NO ESTÁ PERMITIDO' in detail_upper:
        return 'TIPO_NO_PERMITIDO', detail
    return 'VALIDACION_ADJUNTO', detail


def registrar_correo_problematico(msg, *, folder_name='', flow_label='', problem_reason='VALIDACION_ADJUNTO', problem_detail='', fallback_domain='local.host'):
    message_id = _normalize_message_id(msg, fallback_domain=fallback_domain)
    from_email = (getattr(msg, 'from_', None) or 'desconocido@dominio.com').lower()
    subject = getattr(msg, 'subject', None) or '(Sin asunto)'
    fecha_gmail, fecha_header = _extract_message_dates(msg)
    cuerpo_texto, cuerpo_html = extraer_cuerpos_correo(msg)
    _, attachments_summary = _build_attachment_metadata(msg)

    defaults = {
        'remitente': from_email,
        'asunto': subject[:500],
        'cuerpo_texto': cuerpo_texto,
        'cuerpo_html': cuerpo_html,
        'fecha_recepcion_original': fecha_header,
        'fecha_recibida_gmail': fecha_gmail,
        'carpeta_origen': folder_name,
        'flujo_origen': flow_label,
        'motivo_problema': problem_reason,
        'detalle_problema': problem_detail,
        'adjuntos_resumen': json.dumps(attachments_summary, ensure_ascii=False),
        'resuelto': False,
        'fecha_resuelto': None,
        'correo_entrante_asociado': None,
    }

    problem_record, created = CorreoProblematico.objects.update_or_create(
        message_id=message_id,
        defaults=defaults,
    )

    raw_message_bytes = _extract_raw_message_bytes(msg)
    if raw_message_bytes and not problem_record.respaldo_eml:
        problem_record.respaldo_eml.save(
            _problem_backup_filename(message_id),
            ContentFile(raw_message_bytes),
            save=True,
        )

    return problem_record, created


def procesar_mensaje_imap(msg, *, folder_name='', flow_label='', persist=True, fallback_domain='local.host'):
    message_id = _normalize_message_id(msg, fallback_domain=fallback_domain)

    omitir, motivo_omision = _debe_omitir_mensaje_propio_o_notificacion(msg)
    if omitir:
        return {
            'status': 'skipped_own_outbound',
            'message_id': message_id,
            'detail': motivo_omision,
            'attachment_count': 0,
        }

    if correo_ya_registrado_por_message_id(message_id):
        return {
            'status': 'duplicate',
            'message_id': message_id,
            'detail': 'El correo ya existe en la bandeja principal.',
            'attachment_count': 0,
        }

    existing_problem = CorreoProblematico.objects.filter(message_id=message_id, resuelto=False).first()

    fecha_gmail, fecha_header = _extract_message_dates(msg)
    fecha_min_aw = timezone.make_aware(datetime(2026, 1, 1))
    if fecha_gmail and fecha_gmail < fecha_min_aw:
        return {
            'status': 'skipped_old',
            'message_id': message_id,
            'detail': 'Correo anterior a 2026-01-01.',
            'attachment_count': 0,
        }

    attachments_info, attachments_summary = _build_attachment_metadata(msg)
    try:
        validation_summary = EmailAttachmentValidator.validate_email_attachments(attachments_info)
    except ValidationError as exc:
        reason, detail = _resolve_problem_reason(exc)
        if persist:
            problem_record, created = registrar_correo_problematico(
                msg,
                folder_name=folder_name,
                flow_label=flow_label,
                problem_reason=reason,
                problem_detail=detail,
                fallback_domain=fallback_domain,
            )
        else:
            problem_record = None
            created = False
        return {
            'status': 'problematic',
            'message_id': message_id,
            'detail': detail,
            'problem_reason': reason,
            'problem_record': problem_record,
            'created_problem_record': created,
            'attachment_count': len(attachments_summary),
        }

    if not persist:
        return {
            'status': 'dry_run',
            'message_id': message_id,
            'detail': 'Correo válido detectado en simulación.',
            'attachment_count': validation_summary['total_files'],
            'attachment_total_mb': validation_summary['total_size_mb'],
        }

    from_email = (getattr(msg, 'from_', None) or 'desconocido@dominio.com').lower()
    subject = getattr(msg, 'subject', None) or '(Sin asunto)'
    cuerpo_texto, cuerpo_html = extraer_cuerpos_correo(msg)

    with transaction.atomic():
        correo = CorreoEntrante.objects.create(
            message_id=message_id,
            remitente=from_email,
            asunto=subject[:500],
            cuerpo_texto=cuerpo_texto,
            cuerpo_html=cuerpo_html,
            fecha_recepcion_original=fecha_header,
            fecha_recibida_gmail=fecha_gmail,
        )

        attachment_count = 0
        for index, att in enumerate(msg.attachments or []):
            filename = getattr(att, 'filename', '') or f"adjunto_{index + 1}"
            content = getattr(att, 'payload', None) or b''
            content_type = getattr(att, 'content_type', None) or 'application/octet-stream'

            EmailAttachmentValidator.validate_attachment(filename, len(content))

            adj = AdjuntoCorreoEntrante(
                correo_entrante=correo,
                nombre_original=filename,
                tipo_mime=content_type,
                content_id=getattr(att, 'content_id', '') or '',
            )
            adj.archivo.save(filename, ContentFile(content), save=True)
            attachment_count += 1

        if existing_problem:
            existing_problem.resuelto = True
            existing_problem.fecha_resuelto = timezone.now()
            existing_problem.correo_entrante_asociado = correo
            existing_problem.save(update_fields=['resuelto', 'fecha_resuelto', 'correo_entrante_asociado'])

    return {
        'status': 'saved',
        'message_id': message_id,
        'detail': 'Correo guardado correctamente.',
        'correo': correo,
        'attachment_count': attachment_count,
        'attachment_total_mb': validation_summary['total_size_mb'],
    }


def forzar_ingreso_correo_problematico(problema_id, usuario=None):
    """
    Fuerza el ingreso de un CorreoProblematico a la bandeja principal (CorreoEntrante),
    omitiendo la validación de tipos de adjuntos.
    Intenta re-descargar el correo desde IMAP para conservar adjuntos.
    Si el correo tuvo adjuntos, solo admite el ingreso cuando logra reconstruirlos
    completos desde IMAP o desde el respaldo .eml.
    Si el correo no tuvo adjuntos, permite fallback a metadata.

    Returns dict con 'ok', 'detail', y opcionalmente 'correo_entrante'.
    """
    problema = CorreoProblematico.objects.filter(pk=problema_id).first()
    if not problema:
        return {'ok': False, 'detail': 'Correo problemático no encontrado.'}

    if problema.resuelto:
        return {'ok': False, 'detail': 'Este correo ya fue resuelto.'}

    if CorreoEntrante.objects.filter(message_id=problema.message_id).exists():
        return {'ok': False, 'detail': 'Ya existe un correo entrante con este Message-ID.'}

    # Intentar re-descargar desde IMAP para conservar adjuntos
    msg_imap = _fetch_from_imap_by_message_id(problema.message_id)

    if msg_imap:
        return _crear_correo_desde_mensaje(problema, msg_imap, source='imap')

    msg_respaldo = _load_mailmessage_from_problem_backup(problema)
    if msg_respaldo:
        return _crear_correo_desde_mensaje(problema, msg_respaldo, source='respaldo_eml')

    if problema.adjuntos_resumen_list:
        expected_filenames = [
            item.get('filename')
            for item in problema.adjuntos_resumen_list
            if isinstance(item, dict) and item.get('filename')
        ]
        missing_detail = ''
        if expected_filenames:
            missing_detail = f" Adjuntos no reconstruidos: {', '.join(expected_filenames)}."
        return {
            'ok': False,
            'detail': (
                'No se pudo ingresar el correo preservando todos los adjuntos. '
                'IMAP no devolvió el mensaje y tampoco hay un respaldo .eml reutilizable.'
                f'{missing_detail}'
            ),
        }

    return _crear_correo_desde_metadata(problema)


def _fetch_from_imap_by_message_id(message_id):
    """Intenta descargar un mensaje completo desde el proveedor configurado buscando por Message-ID."""
    try:
        email_account = getattr(settings, 'EMAIL_HOST_USER', '')

        if not email_account:
            logger.warning("Cuenta de correo no configurada para re-fetch.")
            return None
        provider = build_email_inbox_provider().connect()
        try:
            return provider.fetch_message_by_message_id(message_id)
        finally:
            try:
                provider.logout()
            except Exception:
                pass

    except Exception as e:
        logger.warning("No se pudo re-descargar correo desde el proveedor configurado (message_id=%s): %s", message_id, e)

    return None


def _crear_correo_desde_mensaje(problema, msg, *, source='imap'):
    """Crea CorreoEntrante desde un mensaje RFC822, sin validación de tipo ni tamaño de adjuntos."""
    from_email = (getattr(msg, 'from_', None) or problema.remitente or 'desconocido@dominio.com').lower()
    subject = getattr(msg, 'subject', None) or problema.asunto or '(Sin asunto)'
    cuerpo_texto, cuerpo_html = extraer_cuerpos_correo(msg)
    fecha_gmail, fecha_header = _extract_message_dates(msg)
    expected_attachments = problema.adjuntos_resumen_list
    expected_attachment_count = len(expected_attachments)
    expected_filenames = [
        (item.get('filename') or '').strip()
        for item in expected_attachments
        if isinstance(item, dict) and (item.get('filename') or '').strip()
    ]

    try:
        with transaction.atomic():
            correo = CorreoEntrante.objects.create(
                message_id=problema.message_id,
                remitente=from_email,
                asunto=subject[:500],
                cuerpo_texto=cuerpo_texto,
                cuerpo_html=cuerpo_html,
                fecha_recepcion_original=fecha_header,
                fecha_recibida_gmail=fecha_gmail,
            )

            attachment_count = 0
            reconstructed_filenames = []
            for index, att in enumerate(msg.attachments or []):
                filename = getattr(att, 'filename', '') or f"adjunto_{index + 1}"
                content = getattr(att, 'payload', None) or b''
                content_type = getattr(att, 'content_type', None) or 'application/octet-stream'
                reconstructed_filenames.append(filename)

                adj = AdjuntoCorreoEntrante(
                    correo_entrante=correo,
                    nombre_original=filename,
                    tipo_mime=content_type,
                    content_id=getattr(att, 'content_id', '') or '',
                )
                adj.archivo.save(filename, ContentFile(content), save=True)
                attachment_count += 1

            if expected_attachment_count and attachment_count != expected_attachment_count:
                missing_filenames = [
                    filename for filename in expected_filenames if filename not in reconstructed_filenames
                ]
                missing_detail = ''
                if missing_filenames:
                    missing_detail = f" Adjuntos no reconstruidos: {', '.join(missing_filenames)}."
                raise ValueError(
                    f'Solo se pudieron reconstruir {attachment_count} de {expected_attachment_count} adjunto(s).{missing_detail}'
                )

            problema.resuelto = True
            problema.fecha_resuelto = timezone.now()
            problema.correo_entrante_asociado = correo
            problema.save(update_fields=['resuelto', 'fecha_resuelto', 'correo_entrante_asociado'])
    except Exception as exc:
        logger.warning(
            'No se pudo admitir correo problemático preservando todos los adjuntos (problema_id=%s): %s',
            problema.pk,
            exc,
        )
        return {
            'ok': False,
            'detail': f'No se pudo ingresar el correo preservando todos los adjuntos: {exc}',
        }

    return {
        'ok': True,
        'detail': f'Correo ingresado con {attachment_count} adjunto(s) desde {source}.',
        'correo_entrante': correo,
        'attachment_count': attachment_count,
        'source': source,
    }


def _crear_correo_desde_metadata(problema):
    """Crea CorreoEntrante desde la metadata almacenada en CorreoProblematico (sin adjuntos)."""
    with transaction.atomic():
        correo = CorreoEntrante.objects.create(
            message_id=problema.message_id,
            remitente=problema.remitente or 'desconocido@dominio.com',
            asunto=problema.asunto or '(Sin asunto)',
            cuerpo_texto=problema.cuerpo_texto,
            cuerpo_html=problema.cuerpo_html,
            fecha_recepcion_original=problema.fecha_recepcion_original,
            fecha_recibida_gmail=problema.fecha_recibida_gmail,
        )

        problema.resuelto = True
        problema.fecha_resuelto = timezone.now()
        problema.correo_entrante_asociado = correo
        problema.save(update_fields=['resuelto', 'fecha_resuelto', 'correo_entrante_asociado'])

    return {
        'ok': True,
        'detail': 'Correo ingresado desde metadata almacenada (sin adjuntos — no se pudo re-descargar de IMAP).',
        'correo_entrante': correo,
        'attachment_count': 0,
        'source': 'metadata',
    }