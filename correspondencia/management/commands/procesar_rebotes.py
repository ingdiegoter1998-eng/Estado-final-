import imaplib
from email.message import Message
import re
from datetime import timedelta
from imap_tools import MailBox

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from correspondencia.models import SalidaDestinatario
from correspondencia.models import HistorialSalida
from correspondencia.models import Notificacion
from correspondencia.aprobacion_envio import sincronizar_estado_envio_respuesta
from correspondencia.utils.email_provider import build_email_inbox_provider


BOUNCE_SENDER_HINTS = (
    'mailer-daemon',
    'postmaster',
    'mail delivery subsystem',
    'mail delivery system',
)

BOUNCE_SUBJECT_HINTS = (
    'delivery status notification',
    'delivery failure',
    'delivery failed',
    'undeliverable',
    'returned mail',
    'failure notice',
    'mail delivery failed',
)

BOUNCE_BODY_HINTS = (
    'delivery status notification',
    'delivery failed',
    'mail delivery subsystem',
    'returned mail',
    'unable to deliver',
    'undeliverable',
    'address not found',
    'user unknown',
    'mailbox unavailable',
)


def _parse_dsn(msg: Message):
    """Extrae datos clave del DSN.

    Retorna (original_message_id, final_recipient, status, diagnostic, smtp_code).
    """
    original_message_id = None
    final_recipient = None
    status = None
    diagnostic = None
    smtp_code = None

    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == 'message/delivery-status':
            payload = part.get_payload()
            blocks = payload if isinstance(payload, list) else [payload]
            for block in blocks:
                try:
                    fr = block.get('Final-Recipient') or block.get('Original-Recipient')
                    if fr and ';' in fr:
                        final_recipient = fr.split(';', 1)[-1].strip()
                    status = block.get('Status') or status
                    diagnostic = block.get('Diagnostic-Code') or diagnostic
                    if diagnostic:
                        m = re.search(r"\b(\d{3})\b", diagnostic)
                        if m:
                            smtp_code = m.group(1)
                except Exception:
                    continue
        elif ctype == 'message/rfc822':
            inner = part.get_payload()
            if inner:
                try:
                    original_message_id = inner[0].get('Message-ID') or inner[0].get('References')
                except Exception:
                    pass

    # Fallback: intentar por cabeceras superiores
    if not original_message_id:
        original_message_id = msg.get('Original-Message-ID') or msg.get('References')

    return original_message_id, final_recipient, status, diagnostic, smtp_code


def _extract_emails_from_text(text: str) -> set[str]:
    """Extrae posibles correos electrónicos desde texto libre."""
    if not text:
        return set()
    # Regex simple para emails
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return set(re.findall(pattern, text))


def _extract_diagnostic_from_body(text: str) -> str | None:
    """
    Extrae fragmento diagnóstico relevante del cuerpo de un bounce no estándar.
    Busca líneas son patrones comunes de error SMTP/bounce.
    """
    if not text:
        return None
    patterns = [
        r"(?i)((?:550|551|552|553|554|450|451|452|421|422)\s.{5,120})",
        r"(?i)((?:mailbox|address|recipient|user|account)\s+(?:not found|does not exist|unavailable|full|disabled|rejected|unknown).{0,80})",
        r"(?i)((?:delivery|mail).{0,10}(?:failed|failure|rejected|refused|error).{0,80})",
        r"(?i)((?:unable to deliver|undeliverable|returned mail|mail delivery subsystem).{0,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()[:200]
    return None


def _extract_codes_from_text(text: str) -> tuple[str | None, str | None]:
    """
    Intenta extraer smtp_code (ej. '550') y dsn_status (ej. '5.7.1') del cuerpo
    de texto de un bounce que no tiene part delivery-status.

    Retorna (smtp_code, dsn_status).
    """
    if not text:
        return None, None

    smtp_code = None
    dsn_status = None

    # DSN extendido: 5.1.1, 5.7.1, 4.2.2, etc.
    dsn_match = re.search(r'\b([45]\.\d{1,3}\.\d{1,3})\b', text)
    if dsn_match:
        dsn_status = dsn_match.group(1)

    # Código SMTP 3 dígitos: 550, 451, 421, etc.
    smtp_match = re.search(r'\b([45]\d{2})\b', text)
    if smtp_match:
        smtp_code = smtp_match.group(1)

    # Clasificación por contenido si no hay código explícito
    if not smtp_code and not dsn_status:
        text_lower = text.lower()
        if any(p in text_lower for p in [
            'address not found', 'user unknown', 'does not exist',
            'no such user', 'mailbox not found', 'recipient rejected',
            'dirección de correo inexistente',
        ]):
            smtp_code = '550'
            dsn_status = '5.1.1'
        elif any(p in text_lower for p in [
            'mailbox full', 'over quota', 'quota exceeded',
        ]):
            smtp_code = '552'
            dsn_status = '5.2.2'
        elif any(p in text_lower for p in [
            'rejected', 'blocked', 'spam', 'policy',
            'transport.rules', 'not allowed',
        ]):
            smtp_code = '550'
            dsn_status = '5.7.1'

    return smtp_code, dsn_status


def _extract_message_id_candidates(raw_value: str | None) -> list[str]:
    """Extrae uno o varios Message-ID desde una cabecera References/Message-ID."""
    if not raw_value:
        return []

    candidates: list[str] = []
    for match in re.findall(r'<[^>]+>', raw_value):
        value = match.strip()
        if value and value not in candidates:
            candidates.append(value)

    if candidates:
        return candidates

    raw_clean = raw_value.strip()
    if raw_clean and raw_clean not in candidates:
        candidates.append(raw_clean)

    return candidates


def _looks_like_dsn(msg: Message, text_body: str) -> bool:
    """Filtra mensajes normales del INBOX y deja pasar solo candidatos plausibles a DSN."""
    try:
        content_types = {(part.get_content_type() or '').lower() for part in msg.walk()}
    except Exception:
        content_type = (msg.get_content_type() or '').lower() if hasattr(msg, 'get_content_type') else ''
        content_types = {content_type} if content_type else set()

    if 'message/delivery-status' in content_types or 'multipart/report' in content_types:
        return True

    if msg.get('X-Failed-Recipients') or msg.get('Final-Recipient') or msg.get('Original-Recipient'):
        return True

    from_header = (msg.get('From') or '').lower()
    subject = (msg.get('Subject') or '').lower()
    body_lower = (text_body or '').lower()

    sender_looks_like_bounce = any(token in from_header for token in BOUNCE_SENDER_HINTS)
    subject_looks_like_bounce = any(token in subject for token in BOUNCE_SUBJECT_HINTS)
    body_looks_like_bounce = any(token in body_lower for token in BOUNCE_BODY_HINTS)

    return sender_looks_like_bounce and (subject_looks_like_bounce or body_looks_like_bounce)


def _allow_email_only_fallback(msg: Message, recipients: set[str], status: str | None, diagnostic: str | None, smtp_code: str | None) -> bool:
    """Solo permite fallback por email si el mensaje trae evidencia mínima de rebote."""
    if not recipients:
        return False
    if smtp_code or status or diagnostic:
        return True
    return bool(
        msg.get('X-Failed-Recipients') or
        msg.get('Final-Recipient') or
        msg.get('Original-Recipient')
    )


def _resolve_bounce_queryset(base_qs, message_ids: list[str], recipients: set[str], allow_email_fallback: bool, fallback_window):
    """Resuelve destinatarios afectados priorizando Message-ID y dejando el fallback auditado."""
    qs = base_qs
    if message_ids:
        qs = qs.filter(id_mensaje_enviado__in=message_ids)
    if recipients:
        qs = qs.filter(email_snapshot__in=list(recipients))
    if qs.exists():
        return qs, 'primary'

    if allow_email_fallback and recipients:
        qs = base_qs.filter(
            email_snapshot__in=list(recipients),
            fecha_envio__gte=fallback_window,
        )
        if qs.exists():
            return qs, 'fallback_email'

    if message_ids:
        qs = base_qs.filter(id_mensaje_enviado__in=message_ids)
        if qs.exists():
            return qs, 'fallback_message_id'

    return base_qs.none(), None


def _extract_bounce_recipients_generic(msg: Message, text_fallback: str) -> set[str]:
    """
    Extrae destinatarios fallidos desde cabeceras y cuerpo de bounces no estándar (p.ej. Gmail).
    Busca en:
      - X-Failed-Recipients
      - Final-Recipient/Original-Recipient en cabecera superior
      - Cuerpo de texto plano
    """
    candidates: set[str] = set()

    # Cabecera X-Failed-Recipients (si existe)
    xfailed = msg.get('X-Failed-Recipients')
    if xfailed:
        candidates.update(_extract_emails_from_text(xfailed))

    # Final/Original Recipient en cabecera superior (fuera del part delivery-status)
    fr = msg.get('Final-Recipient') or msg.get('Original-Recipient')
    if fr and ';' in fr:
        candidates.add(fr.split(';', 1)[-1].strip())
    elif fr:
        candidates.update(_extract_emails_from_text(fr))

    # Cuerpo de texto (p. ej., "address not found" de Gmail)
    candidates.update(_extract_emails_from_text(text_fallback))

    return candidates


def _crear_notificacion_rebote(salida, recipients, smtp_code, dsn_status):
    """Crea notificación de rebote para el redactor de la correspondencia de salida."""
    try:
        usuario = salida.usuario_redactor
        if not usuario:
            return

        emails_rebotados = ', '.join(recipients) if recipients else 'destinatario desconocido'
        codigo_info = ''
        if smtp_code:
            codigo_info = f' (código {smtp_code})'
        elif dsn_status:
            codigo_info = f' (DSN {dsn_status})'

        # Deduplicación: no crear si ya existe notificación de rebote para esta salida
        if Notificacion.objects.filter(
            usuario=usuario,
            tipo='rebote',
            url__contains=f'/respuesta/{salida.pk}/detalle/',
        ).exists():
            return

        Notificacion.objects.create(
            usuario=usuario,
            tipo='rebote',
            titulo=f'Rebote en envío {salida.numero_radicado_salida}',
            mensaje=(
                f'El correo enviado a {emails_rebotados} fue rechazado por el servidor destino{codigo_info}. '
                f'Radicado de salida: {salida.numero_radicado_salida}. '
                f'Revise el detalle para verificar la dirección del destinatario.'
            ),
            correspondencia=salida.respuesta_a,
            url=f'/registros/correspondencia/respuesta/{salida.pk}/detalle/',
        )
    except Exception:
        pass


class Command(BaseCommand):
    help = 'Lee la fuente de rebotes configurada y actualiza estados REBOTE en destinatarios.'

    def _procesar_mensaje_dsn(self, msg):
        text_body = getattr(msg, 'text', '') or ''
        if not _looks_like_dsn(msg.obj, text_body):
            return 0, False

        orig_id, rcpt, status, diag, smtp_code = _parse_dsn(msg.obj)
        message_ids = _extract_message_id_candidates(orig_id)

        recipients = set()
        if rcpt:
            recipients.add(rcpt)
        recipients.update(_extract_bounce_recipients_generic(msg.obj, text_body))

        if not diag and not smtp_code:
            body_diag = _extract_diagnostic_from_body(text_body)
            if body_diag:
                diag = body_diag
        if not smtp_code or not status:
            body_smtp, body_dsn = _extract_codes_from_text(text_body)
            if not smtp_code and body_smtp:
                smtp_code = body_smtp
            if not status and body_dsn:
                status = body_dsn
        if not diag and text_body:
            diag = _extract_diagnostic_from_body(text_body) or text_body.strip()[:200]

        if not (message_ids or recipients):
            return 0, True

        now = timezone.now()
        fallback_window = now - timedelta(days=7)
        base_qs = SalidaDestinatario.objects.filter(estado='ENVIADO')
        allow_email_fallback = _allow_email_only_fallback(msg.obj, recipients, status, diag, smtp_code)
        qs, match_type = _resolve_bounce_queryset(
            base_qs=base_qs,
            message_ids=message_ids,
            recipients=recipients,
            allow_email_fallback=allow_email_fallback,
            fallback_window=fallback_window,
        )

        if not qs.exists():
            return 0, True

        if match_type == 'fallback_email':
            self.stdout.write(
                self.style.WARNING(
                    f"Rebote matcheado por fallback email uid={msg.uid} recipients={sorted(recipients)}"
                )
            )

        salidas_afectadas = set()
        procesados = 0
        for sd in qs:
            if sd.estado == 'REBOTE':
                continue
            sd.estado = 'REBOTE'
            sd.dsn_status = status or sd.dsn_status
            sd.ultimo_evento_at = now
            if smtp_code:
                sd.smtp_code = smtp_code
            if diag:
                bloque_dsn = f"DSN: {diag}"
                detalle_actual = sd.detalle_error or ''
                if bloque_dsn not in detalle_actual:
                    sd.detalle_error = f"{detalle_actual}\n{bloque_dsn}".strip()
            sd.save(update_fields=['estado', 'dsn_status', 'ultimo_evento_at', 'smtp_code', 'detalle_error'])
            salidas_afectadas.add(sd.correspondencia_salida)
            procesados += 1

        for salida in salidas_afectadas:
            enviados, total = sincronizar_estado_envio_respuesta(salida, marcar_entrada_respondida=False)
            HistorialSalida.objects.create(
                correspondencia_salida=salida,
                tipo_evento='ENVIO_FALLIDO',
                descripcion=(
                    f"Se detectó rebote posterior al envío. "
                    f"Estado agregado actual: {enviados}/{total} destinatarios OK."
                )
            )
            _crear_notificacion_rebote(salida, recipients, smtp_code, status)

        return procesados, True

    def handle(self, *args, **options):
        email_account = getattr(settings, 'EMAIL_HOST_USER', None)
        bounces_folder = getattr(settings, 'IMAP_FOLDER_BOUNCES', 'Bounces')

        if not email_account:
            self.stderr.write(self.style.ERROR('Falta EMAIL_HOST_USER para procesar rebotes.'))
            return

        mailbox = None
        procesados = 0
        try:
            mailbox = build_email_inbox_provider(
                mailbox_factory=MailBox,
                imap_factory=imaplib.IMAP4_SSL,
            ).connect()

            # Carpeta(s) a revisar: preferida + INBOX como respaldo
            folders_to_try = []
            if bounces_folder:
                folders_to_try.append(bounces_folder)
            if 'INBOX' not in folders_to_try:
                folders_to_try.append('INBOX')

            seen_time_window_days = 3
            processed_uids: set[str] = set()

            for folder in folders_to_try:
                # 1) No leídos primero (evita reprocesar)
                uids_to_mark_seen: list[str] = []
                for msg in mailbox.fetch_unread_messages(folder):
                    try:
                        procesados_msg, processed = self._procesar_mensaje_dsn(msg)
                        procesados += procesados_msg
                        if processed:
                            processed_uids.add(msg.uid)
                            uids_to_mark_seen.append(msg.uid)
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"Error procesando DSN: {e}"))

                # Marcar como leídos los rebotes ya procesados para no reprocesarlos
                if uids_to_mark_seen:
                    try:
                        mailbox.mark_seen_many(uids_to_mark_seen)
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"No se pudieron marcar como vistos: {e}"))

                # 2) Leídos recientes como respaldo (p. ej. Gmail ya marcó visto)
                date_from = (timezone.now() - timedelta(days=seen_time_window_days)).date()
                for msg in mailbox.fetch_messages_since(folder, date_gte=date_from):
                    if msg.uid in processed_uids:
                        continue
                    try:
                        procesados_msg, processed = self._procesar_mensaje_dsn(msg)
                        procesados += procesados_msg
                        if processed:
                            processed_uids.add(msg.uid)
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"Error procesando DSN (visto): {e}"))

            self.stdout.write(self.style.SUCCESS(f"Rebotes procesados/actualizados: {procesados}"))

        finally:
            try:
                if mailbox:
                    mailbox.logout()
            except Exception:
                pass

