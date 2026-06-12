"""
Lógica compartida para aprobar y enviar una respuesta de correspondencia (salida).
Usada por la vista masiva "Aprobar Todas" y por la tarea Celery de aprobación automática.
"""
import logging
import os
from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import CorrespondenciaSalida, HistorialSalida, CorreoEntrante
from .utils.outbound_gmail_api import (
    get_outbound_gmail_api_mail_connection,
    gmail_api_outbound_disponible,
)
from .utils.postmark_outbound import (
    envio_usara_postmark,
    postmark_attachments_limit_bytes,
    validar_adjuntos_para_envio,
)


logger = logging.getLogger(__name__)


POSTMARK_BOUNCE_TEST_DOMAIN = 'bounce-testing.postmarkapp.com'


def _es_destino_prueba_rebote_postmark(email: str) -> bool:
    return POSTMARK_BOUNCE_TEST_DOMAIN in (email or '').strip().lower()


def _ajustar_to_bcc_postmark(to_recipients, bcc_emails, remitente_visible):
    """
    Postmark solo dispara rebotes de prueba si el destino @bounce-testing va en To, no solo en Bcc
    mientras To entrega al remitente institucional.
    """
    if not bcc_emails:
        return to_recipients, bcc_emails
    if not all(_es_destino_prueba_rebote_postmark(e) for e in bcc_emails):
        if not to_recipients:
            return [remitente_visible], bcc_emails
        return to_recipients, bcc_emails
    if len(bcc_emails) == 1:
        return [bcc_emails[0]], []
    # Varios destinatarios de prueba: primer rebote en To, resto en Bcc.
    return [bcc_emails[0]], bcc_emails[1:]


def _ajustar_to_bcc_gmail_api(to_recipients, bcc_emails):
    """
    Gmail API exige un To con dirección real (rechaza vacío y undisclosed-recipients:;).
    Sin copiar al buzón institucional: primer destinatario en To, el resto en Bcc.
    """
    if not bcc_emails:
        return to_recipients, bcc_emails
    if to_recipients:
        return to_recipients, bcc_emails
    if len(bcc_emails) == 1:
        return [bcc_emails[0]], []
    return [bcc_emails[0]], bcc_emails[1:]


def _direccion_remitente_visible():
    """
    Dirección con formato RFC válido para From/To cosméticos.
    Gmail API rechaza headers To vacíos o con dirección <>.
    """
    addr = (getattr(settings, 'OUTBOUND_EMAIL_ADDRESS', '') or '').strip()
    if addr and '@' in addr:
        name = (getattr(settings, 'OUTBOUND_EMAIL_NAME', '') or '').strip()
        return f'"{name}" <{addr}>' if name else addr
    from_email = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    if from_email and '@' in from_email and '<>' not in from_email:
        return from_email
    return None


def sincronizar_estado_envio_respuesta(respuesta, marcar_entrada_respondida=True):
    """
    Recalcula el estado agregado de una respuesta saliente con base en sus destinatarios.

    Regla actual:
    - `ENVIADA` solo si TODOS los destinatarios quedaron `ENVIADO`.
    - `ERROR_ENVIO` si existe al menos un destinatario pendiente/fallido/rebotado.

    Returns:
        tuple[int, int]: (enviados_ok, total_destinatarios)
    """
    resumen = respuesta.destinatarios.values('estado').order_by().annotate(total=models.Count('id'))
    conteos = {item['estado']: item['total'] for item in resumen}

    total_destinatarios = sum(conteos.values())
    enviados = conteos.get('ENVIADO', 0)
    pendientes = conteos.get('PENDIENTE', 0)
    fallidos = conteos.get('FALLO', 0)
    rebotes = conteos.get('REBOTE', 0)

    nuevo_estado = respuesta.estado
    if total_destinatarios:
        if enviados == total_destinatarios:
            nuevo_estado = 'ENVIADA'
        elif pendientes or fallidos:
            # Solo PENDIENTE y FALLO disparan ERROR_ENVIO (reintentable).
            # REBOTE es terminal: no se reintenta automáticamente.
            nuevo_estado = 'ERROR_ENVIO'
        elif rebotes and enviados + rebotes == total_destinatarios:
            # Todos los que no rebotaron fueron enviados: envío parcial exitoso.
            nuevo_estado = 'ENVIADA'

    update_fields = []
    if respuesta.estado != nuevo_estado:
        respuesta.estado = nuevo_estado
        update_fields.append('estado')

    if enviados and not respuesta.fecha_envio:
        respuesta.fecha_envio = timezone.now()
        update_fields.append('fecha_envio')

    if update_fields:
        respuesta.save(update_fields=update_fields)

    if marcar_entrada_respondida and respuesta.respuesta_a and nuevo_estado == 'ENVIADA' and respuesta.respuesta_a.estado != 'RESPONDIDA':
        respuesta.respuesta_a.estado = 'RESPONDIDA'
        respuesta.respuesta_a.save(update_fields=['estado'])

    return enviados, total_destinatarios


def _extraer_id_proveedor_envio(email):
    postmark_response = getattr(email, 'postmark_response', None)
    if isinstance(postmark_response, dict):
        postmark_message_id = (postmark_response.get('MessageID') or '').strip() or None
        if postmark_message_id:
            return postmark_message_id
    gmail_response = getattr(email, 'gmail_api_response', None)
    if isinstance(gmail_response, dict):
        return (gmail_response.get('id') or '').strip() or None
    return None


def aprobar_y_enviar_una_respuesta(respuesta, usuario_aprobador, *, mail_connection=None, proveedor_envio=None):
    """
    Aprueba una respuesta de salida y envía el correo por BCC a sus destinatarios.
    Actualiza estado, historial y correspondencia entrante asociada.

    Args:
        respuesta: instancia de CorrespondenciaSalida (estado PENDIENTE_APROBACION o ERROR_ENVIO).
        usuario_aprobador: User o None (aprobación automática Celery).
        mail_connection: conexión Django mail opcional (p. ej. Gmail API one-off).
        proveedor_envio: etiqueta para historial ('gmail_api', 'postmark', etc.).

    Returns:
        Tupla (enviados_ok: int, total_destinatarios: int).

    Raises:
        ValueError: si no hay destinatarios o hay más de 50.
    """
    with transaction.atomic():
        usuario_redactor = respuesta.usuario_redactor
        perfil = getattr(usuario_redactor, 'perfil', None) if usuario_redactor else None
        nombre_entidad = None
        if respuesta.respuesta_a and respuesta.respuesta_a.remitente:
            rem = respuesta.respuesta_a.remitente
            if hasattr(rem, 'entidad_externa') and rem.entidad_externa:
                nombre_entidad = rem.entidad_externa.nombre

        contexto = {
            'nombre_oficina': perfil.oficina.nombre if perfil and perfil.oficina else 'Oficina no especificada',
            'nombre_funcionario': usuario_redactor.get_full_name() or usuario_redactor.username if usuario_redactor else 'N/A',
            'cargo_funcionario': perfil.cargo if perfil and perfil.cargo else 'Cargo no especificado',
            'nombre_entidad': nombre_entidad,
            'numero_radicado_salida': respuesta.numero_radicado_salida,
            'numero_radicado_entrada': respuesta.respuesta_a.numero_radicado if respuesta.respuesta_a else None,
            'cuerpo_respuesta': respuesta.cuerpo,
        }

        html_message = render_to_string('correspondencia/email/respuesta_salida_base.html', contexto)
        plain_message = strip_tags(html_message)

        destinatarios = list(respuesta.destinatarios.select_related('contacto'))
        if not destinatarios:
            raise ValueError("No hay destinatarios para enviar esta respuesta.")
        if len(destinatarios) > 50:
            raise ValueError("No se permiten más de 50 destinatarios.")

        destinatarios_pendientes = [
            sd for sd in destinatarios
            if sd.estado in {'PENDIENTE', 'FALLO'}
        ]

        if not destinatarios_pendientes:
            return sincronizar_estado_envio_respuesta(respuesta)

        adjuntos_email = []
        for adj in respuesta.adjuntos.all():
            if adj.archivo:
                try:
                    adj.archivo.open('rb')
                    adjuntos_email.append((
                        adj.nombre_original or os.path.basename(adj.archivo.name),
                        adj.archivo.read(),
                        adj.tipo_mime or 'application/octet-stream'
                    ))
                finally:
                    adj.archivo.close()

        total_adjuntos_bytes = sum(len(contenido) for _, contenido, _ in adjuntos_email)
        if (
            mail_connection is None
            and proveedor_envio is None
            and envio_usara_postmark(proveedor_envio=proveedor_envio)
            and total_adjuntos_bytes > postmark_attachments_limit_bytes()
            and gmail_api_outbound_disponible()
        ):
            mail_connection = get_outbound_gmail_api_mail_connection()
            proveedor_envio = 'gmail_api'
            logger.info(
                'Salida %s: adjuntos %.2f MB superan límite Postmark; envío por Gmail API.',
                respuesta.numero_radicado_salida,
                total_adjuntos_bytes / (1024 * 1024),
            )

        validar_adjuntos_para_envio(adjuntos_email, proveedor_envio=proveedor_envio)

        update_fields = []
        if respuesta.estado != 'APROBADA':
            respuesta.estado = 'APROBADA'
            update_fields.append('estado')
        if usuario_aprobador and respuesta.usuario_aprobador_id != getattr(usuario_aprobador, 'id', None):
            respuesta.usuario_aprobador = usuario_aprobador
            update_fields.append('usuario_aprobador')
        if not respuesta.fecha_aprobacion:
            respuesta.fecha_aprobacion = timezone.now()
            update_fields.append('fecha_aprobacion')

        if update_fields:
            respuesta.save(update_fields=update_fields)

        if 'fecha_aprobacion' in update_fields or 'estado' in update_fields:
            HistorialSalida.objects.create(
                correspondencia_salida=respuesta,
                tipo_evento='APROBACION',
                usuario=usuario_aprobador
            )

        original_message_id = None
        if respuesta.respuesta_a_id:
            try:
                correo_origen = CorreoEntrante.objects.filter(
                    radicado_asociado_id=respuesta.respuesta_a_id
                ).order_by('fecha_lectura_imap').first()
                if correo_origen and getattr(correo_origen, 'message_id', None):
                    original_message_id = correo_origen.message_id
            except Exception:
                pass

        extra_headers = {}
        if original_message_id:
            extra_headers['In-Reply-To'] = original_message_id
            extra_headers['References'] = original_message_id

        bcc_emails = [sd.email_snapshot for sd in destinatarios_pendientes]
        enviados_intento = 0
        message_id_generado = make_msgid(domain=getattr(settings, 'EMAIL_MESSAGE_ID_DOMAIN', None) or None)

        try:
            proveedor_label = (proveedor_envio or getattr(settings, 'EMAIL_PROVIDER', '') or 'default').strip()
            HistorialSalida.objects.create(
                correspondencia_salida=respuesta,
                tipo_evento='INTENTO_ENVIO',
                usuario=usuario_aprobador,
                descripcion=(
                    f"Intentando envío BCC ({proveedor_label}) a {len(bcc_emails)} destinatarios pendientes "
                    f"de {len(destinatarios)} total(es)."
                )
            )

            connection = mail_connection or get_connection()
            connection.open()
            gmail_thread_id = None

            to_recipients = [settings.TO_DEFAULT] if getattr(settings, 'TO_DEFAULT', '').strip() else []
            reply_to_recipients = [settings.REPLY_TO_DEFAULT] if getattr(settings, 'REPLY_TO_DEFAULT', '').strip() else []
            remitente_visible = _direccion_remitente_visible()
            if not remitente_visible:
                raise ValueError(
                    'Configure OUTBOUND_EMAIL_ADDRESS (o EMAIL_HOST_USER) con el buzón Gmail API autorizado.'
                )

            # Postmark: To al remitente institucional (API). Gmail API: To al primer destinatario real.
            merged_headers = {**extra_headers, 'Message-ID': message_id_generado}
            if envio_usara_postmark(proveedor_envio=proveedor_envio):
                to_recipients, bcc_emails = _ajustar_to_bcc_postmark(
                    to_recipients, bcc_emails, remitente_visible
                )
            else:
                to_recipients, bcc_emails = _ajustar_to_bcc_gmail_api(to_recipients, bcc_emails)

            try:
                email = EmailMessage(
                    subject=respuesta.asunto,
                    body=plain_message,
                    from_email=remitente_visible,
                    to=to_recipients,
                    bcc=bcc_emails,
                    reply_to=reply_to_recipients,
                    connection=connection,
                    headers=merged_headers
                )
                email.content_subtype = "html"
                email.body = html_message
                for nombre, contenido, tipo_mime in adjuntos_email:
                    email.attach(nombre, contenido, tipo_mime)
                email.postmark_metadata = {'salida_id': str(respuesta.pk)}
                email.send(fail_silently=False)

                provider_message_id = _extraer_id_proveedor_envio(email)
                gmail_response = getattr(email, 'gmail_api_response', {}) or {}
                gmail_thread_id = (gmail_response.get('threadId') or '').strip() or None

                fecha_envio = timezone.now()
                respuesta.id_mensaje_enviado = message_id_generado
                respuesta.postmark_message_id = provider_message_id
                respuesta.fecha_envio = fecha_envio
                respuesta.save(update_fields=['id_mensaje_enviado', 'postmark_message_id', 'fecha_envio'])

                for sd in destinatarios_pendientes:
                    sd.estado = 'ENVIADO'
                    sd.fecha_envio = fecha_envio
                    sd.id_mensaje_enviado = message_id_generado
                    sd.postmark_message_id = provider_message_id
                    sd.detalle_error = None
                    sd.smtp_code = None
                    sd.dsn_status = None
                    sd.ultimo_evento_at = fecha_envio
                    sd.save(update_fields=[
                        'estado', 'fecha_envio', 'id_mensaje_enviado', 'postmark_message_id',
                        'detalle_error', 'smtp_code', 'dsn_status', 'ultimo_evento_at',
                    ])
                enviados_intento = len(destinatarios_pendientes)

            except Exception as e_send:
                fallo_at = timezone.now()
                for sd in destinatarios_pendientes:
                    sd.estado = 'FALLO'
                    sd.detalle_error = str(e_send)
                    sd.ultimo_evento_at = fallo_at
                    sd.save(update_fields=['estado', 'detalle_error', 'ultimo_evento_at'])
                HistorialSalida.objects.create(
                    correspondencia_salida=respuesta,
                    tipo_evento='ENVIO_FALLIDO',
                    usuario=usuario_aprobador,
                    descripcion=f"Fallo en envío BCC: {e_send}"
                )
                enviados_intento = 0
            finally:
                try:
                    connection.close()
                except Exception:
                    pass

            enviados_totales, total_destinatarios = sincronizar_estado_envio_respuesta(respuesta)

            if enviados_intento > 0:
                extra_gmail = ''
                if gmail_thread_id:
                    extra_gmail = f' Gmail threadId={gmail_thread_id}.'
                HistorialSalida.objects.create(
                    correspondencia_salida=respuesta,
                    tipo_evento='ENVIO_EXITOSO',
                    usuario=usuario_aprobador,
                    descripcion=(
                        f"Envíos OK ({proveedor_label}) en este intento: {enviados_intento}. "
                        f"Acumulado correcto: {enviados_totales} / {total_destinatarios}."
                        f"{extra_gmail}"
                    )
                )

            if enviados_totales < total_destinatarios:
                logger.warning(
                    "Salida %s con entrega incompleta: %s/%s destinatarios OK",
                    respuesta.numero_radicado_salida,
                    enviados_totales,
                    total_destinatarios,
                )

            return (enviados_totales, total_destinatarios)

        except Exception as e_outer:
            respuesta.estado = 'ERROR_ENVIO'
            respuesta.save(update_fields=['estado'])
            HistorialSalida.objects.create(
                correspondencia_salida=respuesta,
                tipo_evento='ENVIO_FALLIDO',
                usuario=usuario_aprobador,
                descripcion=f"Error en envío: {e_outer}"
            )
            raise

    return sincronizar_estado_envio_respuesta(respuesta)
