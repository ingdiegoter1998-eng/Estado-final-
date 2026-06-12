import os
import time
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import logging
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django import db

from .utils.email_provider import build_email_inbox_provider, get_email_ingestion_sync_source
from .utils.email_ingestion import procesar_mensaje_imap

logger = logging.getLogger(__name__)
User = get_user_model()

# Lock simple en Redis para evitar procesamiento simultáneo de emails
_EMAIL_LOCK_KEY = 'correspondencia:email_processing_lock'
_WATCHDOG_LOCK_KEY = 'correspondencia:watchdog_lock'
_APROBAR_RESPUESTAS_LOCK_KEY = 'correspondencia:aprobar_respuestas_lock'


def _acquire_named_lock(lock_key, timeout=180):
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('default')
        return redis_conn.set(lock_key, time.time(), nx=True, ex=timeout)
    except Exception:
        from django.core.cache import cache
        return bool(cache.add(lock_key, time.time(), timeout))


def _release_named_lock(lock_key):
    try:
        from django_redis import get_redis_connection
        get_redis_connection('default').delete(lock_key)
    except Exception:
        from django.core.cache import cache
        cache.delete(lock_key)

def _acquire_email_lock(timeout=180):
    """Intenta adquirir lock Redis para procesamiento de emails. Retorna True si lo obtiene."""
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('default')
        return redis_conn.set(_EMAIL_LOCK_KEY, time.time(), nx=True, ex=timeout)
    except Exception:
        # Sin django-redis: usar el cache compartido de Django. cache.add es atómico
        # (sólo escribe si la clave no existe), por lo que evita la condición de carrera
        # de get()+set() entre procesos worker.
        from django.core.cache import cache
        return bool(cache.add(_EMAIL_LOCK_KEY, time.time(), timeout))


def _release_email_lock():
    """Libera el lock Redis de procesamiento de emails."""
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('default')
        redis_conn.delete(_EMAIL_LOCK_KEY)
    except Exception:
        from django.core.cache import cache
        cache.delete(_EMAIL_LOCK_KEY)


@shared_task(name='correspondencia.tasks.procesar_emails_periodico', soft_time_limit=180, time_limit=210, acks_late=True)
def procesar_emails_periodico():
    """Tarea periódica para ejecutar el comando seguro manage.py procesar_emails_seguro."""
    from django.utils import timezone
    from .models import EstadoSincronizacionCorreos

    db.close_old_connections()

    if not _acquire_email_lock(timeout=240):
        logger.info("procesar_emails_periodico: otra tarea de emails ya está en ejecución, omitiendo.")
        return

    sync, _ = EstadoSincronizacionCorreos.objects.get_or_create(fuente=get_email_ingestion_sync_source())
    sync.ultimo_inicio = timezone.now()
    sync.estado = 'RUNNING'
    sync.ultimo_error = ''
    sync.save(update_fields=['ultimo_inicio', 'estado', 'ultimo_error', 'actualizado_en'])

    try:
        logger.info("Iniciando tarea periódica: procesar_emails_seguro")
        call_command('procesar_emails_seguro')
        logger.info("Tarea periódica procesar_emails_seguro finalizada exitosamente.")
        sync.ultimo_fin = timezone.now()
        sync.estado = 'SUCCESS'
        sync.save(update_fields=['ultimo_fin', 'estado', 'actualizado_en'])
    except SoftTimeLimitExceeded:
        logger.error("procesar_emails_periodico: TIMEOUT - tarea excedió el límite de tiempo")
        sync.ultimo_fin = timezone.now()
        sync.estado = 'FAIL'
        sync.ultimo_error = 'Timeout: la tarea excedió el límite de 180s'
        sync.save(update_fields=['ultimo_fin', 'estado', 'ultimo_error', 'actualizado_en'])
    except Exception as e:
        logger.error(f"Error ejecutando la tarea periódica procesar_emails_seguro: {e}", exc_info=True)
        sync.ultimo_fin = timezone.now()
        sync.estado = 'FAIL'
        sync.ultimo_error = str(e)[:500]
        sync.save(update_fields=['ultimo_fin', 'estado', 'ultimo_error', 'actualizado_en'])
    finally:
        _release_email_lock()
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.procesar_emails_imap_manual', soft_time_limit=900, time_limit=960)
def procesar_emails_imap_manual():
    """Sincronización puntual por IMAP, disparada manualmente desde Ventanilla."""
    from django.test.utils import override_settings
    from django.utils import timezone

    from .models import EstadoSincronizacionCorreos

    db.close_old_connections()

    if not _acquire_email_lock(timeout=960):
        logger.info("procesar_emails_imap_manual: otra tarea de emails ya está en ejecución, omitiendo.")
        return

    account = getattr(settings, 'IMAP_MANUAL_EMAIL_USER', '') or getattr(settings, 'EMAIL_HOST_USER', '')
    password = getattr(settings, 'IMAP_MANUAL_EMAIL_PASSWORD', '') or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    server = getattr(settings, 'IMAP_MANUAL_SERVER', '') or getattr(settings, 'IMAP_SERVER', 'imap.gmail.com')
    port = getattr(settings, 'IMAP_MANUAL_PORT', None) or getattr(settings, 'IMAP_PORT', 993)

    sync, _ = EstadoSincronizacionCorreos.objects.get_or_create(fuente='GMAIL_IMAP')
    sync.ultimo_inicio = timezone.now()
    sync.estado = 'RUNNING'
    sync.ultimo_error = ''
    sync.save(update_fields=['ultimo_inicio', 'estado', 'ultimo_error', 'actualizado_en'])

    try:
        if not account or not password:
            raise RuntimeError('Faltan IMAP_MANUAL_EMAIL_USER/IMAP_MANUAL_EMAIL_PASSWORD para procesar por IMAP.')

        inicio_hoy = timezone.localtime(timezone.now()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        logger.info("Iniciando sincronización manual IMAP desde %s", inicio_hoy.isoformat())

        with override_settings(
            EMAIL_INGESTION_PROVIDER='imap',
            EMAIL_HOST_USER=account,
            EMAIL_HOST_PASSWORD=password,
            IMAP_SERVER=server,
            IMAP_PORT=int(port),
        ):
            call_command(
                'procesar_emails_seguro',
                recovery=True,
                since=inicio_hoy.isoformat(),
            )

        sync.ultimo_fin = timezone.now()
        sync.estado = 'SUCCESS'
        sync.save(update_fields=['ultimo_fin', 'estado', 'actualizado_en'])
        logger.info("Sincronización manual IMAP finalizada exitosamente.")
    except SoftTimeLimitExceeded:
        logger.error("procesar_emails_imap_manual: TIMEOUT - tarea excedió el límite de tiempo")
        sync.ultimo_fin = timezone.now()
        sync.estado = 'FAIL'
        sync.ultimo_error = 'Timeout: la tarea excedió el límite de 900s'
        sync.save(update_fields=['ultimo_fin', 'estado', 'ultimo_error', 'actualizado_en'])
    except Exception as e:
        logger.error("Error ejecutando sincronización manual IMAP: %s", e, exc_info=True)
        sync.ultimo_fin = timezone.now()
        sync.estado = 'FAIL'
        sync.ultimo_error = str(e)[:500]
        sync.save(update_fields=['ultimo_fin', 'estado', 'ultimo_error', 'actualizado_en'])
    finally:
        _release_email_lock()
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.precalentar_cache_sla_periodico')
def precalentar_cache_sla_periodico():
    """Mantiene caliente el cache de IDs SLA para no bloquear workers Gunicorn."""
    from correspondencia.utils.sla_queries import refresh_ids_entrantes_con_respuesta_cache

    db.close_old_connections()
    return refresh_ids_entrantes_con_respuesta_cache()


@shared_task(name='correspondencia.tasks.sincronizar_entregas_postmark_periodico')
def sincronizar_entregas_postmark_periodico():
    """Backfill de eventos Delivery/Bounce desde API Postmark (no bloquea peticiones HTTP)."""
    from datetime import timedelta

    from correspondencia.models import SalidaDestinatario
    from correspondencia.utils.postmark_message_details import (
        message_ids_pendientes_sync,
        sincronizar_lote_desde_api,
    )

    db.close_old_connections()
    if getattr(settings, 'EMAIL_PROVIDER', '') != 'postmark':
        return
    if not getattr(settings, 'POSTMARK_SERVER_TOKEN', '').strip():
        return

    try:
        cutoff = timezone.now() - timedelta(days=30)
        destinatarios = list(
            SalidaDestinatario.objects.filter(
                estado='ENVIADO',
                postmark_message_id__gt='',
                fecha_envio__gte=cutoff,
            ).order_by('-fecha_envio')[:200]
        )
        pendientes = message_ids_pendientes_sync(destinatarios)
        if not pendientes:
            return
        consultados = sincronizar_lote_desde_api(pendientes, max_fetch=10)
        logger.info(
            'sincronizar_entregas_postmark_periodico: %s MessageIDs consultados en API.',
            consultados,
        )
    except Exception as e:
        logger.error('Error sincronizando entregas Postmark: %s', e, exc_info=True)
    finally:
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.procesar_rebotes_periodico')
def procesar_rebotes_periodico():
    """Tarea periódica para ejecutar el comando manage.py procesar_rebotes."""
    db.close_old_connections()
    if (
        getattr(settings, 'EMAIL_PROVIDER', '') == 'postmark'
        and getattr(settings, 'POSTMARK_BOUNCES_VIA_WEBHOOK', False)
        and getattr(settings, 'POSTMARK_WEBHOOK_ENABLED', False)
    ):
        logger.info(
            'procesar_rebotes_periodico: omitido (rebotes vía webhook Postmark activos).'
        )
        return
    try:
        logger.info("Iniciando tarea periódica: procesar_rebotes")
        call_command('procesar_rebotes')
        logger.info("Tarea periódica procesar_rebotes finalizada exitosamente.")
    except Exception as e:
        logger.error(f"Error ejecutando la tarea periódica procesar_rebotes: {e}", exc_info=True)
    finally:
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.actualizar_urgencias_pendientes')
def actualizar_urgencias_pendientes():
    """
    Actualiza horas transcurridas y marca como vencidas las urgencias pendientes.
    Se ejecuta cada 30 minutos.
    """
    from .models import CorrespondenciaUrgencia
    from django.utils import timezone
    
    db.close_old_connections()
    try:
        logger.info("Iniciando actualización de urgencias pendientes")
        
        # Obtener urgencias activas (no respondidas)
        urgencias = CorrespondenciaUrgencia.objects.filter(
            estado__in=['PENDIENTE', 'EN_PROCESO']
        )
        
        actualizadas = 0
        vencidas = 0
        
        for urgencia in urgencias:
            # Actualizar horas transcurridas
            urgencia.actualizar_horas_transcurridas()
            actualizadas += 1
            
            # Verificar si debe marcarse como vencida
            if urgencia.marcar_vencida():
                vencidas += 1
                logger.warning(f"Urgencia {urgencia.radicado} marcada como VENCIDA")
        
        logger.info(f"Urgencias actualizadas: {actualizadas}, vencidas: {vencidas}")
        
    except Exception as e:
        logger.error(f"Error actualizando urgencias pendientes: {e}", exc_info=True)


@shared_task(name='correspondencia.tasks.escalar_urgencias_criticas')
def escalar_urgencias_criticas():
    """
    Envía notificaciones de escalamiento para urgencias críticas vencidas.
    Se ejecuta cada hora.
    """
    from .models import CorrespondenciaUrgencia, Notificacion
    from django.contrib.auth.models import User
    from django.utils import timezone
    
    try:
        logger.info("Iniciando escalamiento de urgencias críticas")
        
        # Obtener urgencias críticas vencidas sin responder
        urgencias_criticas = CorrespondenciaUrgencia.objects.filter(
            prioridad='CRITICA',
            estado='VENCIDA'
        ).select_related('oficina_destino', 'usuario_radica')
        
        if not urgencias_criticas.exists():
            logger.info("No hay urgencias críticas vencidas para escalar")
            return
        
        # Obtener líderes de oficina y superusuarios
        lideres = User.objects.filter(
            groups__name='Lider de Oficina',
            is_active=True
        ).distinct()
        
        superusuarios = User.objects.filter(
            is_superuser=True,
            is_active=True
        )
        
        destinatarios = set(lideres) | set(superusuarios)
        
        notificaciones = []
        for urgencia in urgencias_criticas:
            for usuario in destinatarios:
                notificaciones.append(Notificacion(
                    usuario=usuario,
                    tipo='urgencia',
                    titulo=f'⚠️ URGENCIA CRÍTICA VENCIDA: {urgencia.radicado}',
                    mensaje=f'Oficina: {urgencia.oficina_destino.nombre} - {urgencia.correo_entrante.asunto[:80]}',
                    url=f'/correspondencia/urgencias/{urgencia.pk}/'
                ))
        
        if notificaciones:
            Notificacion.objects.bulk_create(notificaciones, ignore_conflicts=True)
            logger.info(f"Enviadas {len(notificaciones)} notificaciones de escalamiento")
        
    except Exception as e:
        logger.error(f"Error escalando urgencias críticas: {e}", exc_info=True)


def _get_usuario_aprobacion_automatica():
    """
    Usuario usado como aprobador en la tarea Celery de aprobación automática.
    Variable de entorno CELERY_APROBACION_USER (ej. sistema_correspondencia).
    Si no existe el usuario se crea con is_active=True (aprobación automática).
    """
    username = os.getenv('CELERY_APROBACION_USER') or getattr(settings, 'CELERY_APROBACION_USER', None)
    if not username:
        return None
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={'is_active': True, 'email': f'{username}@sistema.local'}
    )
    return user


@shared_task(name='correspondencia.tasks.aprobar_y_enviar_respuestas_pendientes_periodico')
def aprobar_y_enviar_respuestas_pendientes_periodico():
    """
    Aprueba y envía automáticamente todas las respuestas en PENDIENTE_APROBACION o ERROR_ENVIO.
    Se ejecuta cada minuto por Celery Beat (intervalo configurable).
    """
    from .models import CorrespondenciaSalida
    from .aprobacion_envio import aprobar_y_enviar_una_respuesta

    db.close_old_connections()
    if not _acquire_named_lock(_APROBAR_RESPUESTAS_LOCK_KEY, timeout=600):
        logger.info('Aprobación automática omitida: otra instancia en curso')
        return

    try:
        usuario = _get_usuario_aprobacion_automatica()
        respuestas = CorrespondenciaSalida.objects.filter(
            estado__in=['PENDIENTE_APROBACION', 'ERROR_ENVIO']
        ).prefetch_related('destinatarios', 'adjuntos')

        total_ok = 0
        total_errores = 0

        for respuesta in respuestas:
            try:
                enviados, total = aprobar_y_enviar_una_respuesta(respuesta, usuario)
                if total > 0 and enviados == total:
                    total_ok += 1
                else:
                    total_errores += 1
            except Exception as e:
                total_errores += 1
                logger.warning(
                    "Aprobación automática falló para %s: %s",
                    respuesta.numero_radicado_salida,
                    e,
                    exc_info=True
                )

        if total_ok or total_errores:
            logger.info(
                "Aprobación automática respuestas: %s OK, %s errores",
                total_ok,
                total_errores
            )
    finally:
        _release_named_lock(_APROBAR_RESPUESTAS_LOCK_KEY)


@shared_task(name='correspondencia.tasks.watchdog_inbox', soft_time_limit=90, time_limit=120)
def watchdog_inbox():
    """
    Tarea watchdog que vigila INBOX cada minuto.
    Descarga headers de TODOS los correos de hoy (leídos y no leídos),
    compara con la BD y procesa correos faltantes.
    NO depende del flag UNSEEN — así captura correos que el usuario
    leyó en Gmail web antes de que el sistema los importara.
    Usa lock para no colisionar con procesar_emails_periodico.
    """
    from datetime import datetime
    import imaplib

    from imap_tools import MailBox, AND
    from .models import CorreoEntrante, CorreoProblematico

    EMAIL_ACCOUNT = settings.EMAIL_HOST_USER

    db.close_old_connections()

    # Lock propio del watchdog: no compite con procesar_emails_periodico
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('default')
        if redis_conn.get(_EMAIL_LOCK_KEY):
            acquired = False
        else:
            acquired = redis_conn.set(_WATCHDOG_LOCK_KEY, time.time(), nx=True, ex=120)
    except Exception:
        from django.core.cache import cache
        if cache.get(_EMAIL_LOCK_KEY):
            acquired = False
        else:
            # cache.add es atómico: sólo adquiere el lock del watchdog si no existe ya.
            acquired = bool(cache.add(_WATCHDOG_LOCK_KEY, time.time(), 120))

    if not acquired:
        logger.debug("watchdog_inbox: otra instancia de watchdog ya está corriendo.")
        return

    mailbox = None
    try:
        mailbox = build_email_inbox_provider(
            mailbox_factory=MailBox,
            imap_factory=imaplib.IMAP4_SSL,
        ).connect()

        # Correos de ayer y hoy para capturar emails de la noche anterior no procesados
        from datetime import timedelta
        ayer = (datetime.now() - timedelta(days=1)).date()
        headers = list(mailbox.fetch_headers('INBOX', date_gte=ayer))

        if not headers:
            logger.debug("watchdog_inbox: sin correos hoy en INBOX.")
            return

        # Comparar con BD
        existing_ids = set(
            CorreoEntrante.objects.values_list('message_id', flat=True)
        )
        existing_ids.update(
            CorreoProblematico.objects.filter(resuelto=False).values_list('message_id', flat=True)
        )

        missing_uids = []
        for h in headers:
            mid = (h.headers.get('message-id', [''])[0].strip("<>").strip())
            if mid and mid not in existing_ids:
                missing_uids.append(h.uid)

        if not missing_uids:
            logger.debug("watchdog_inbox: todos los correos de hoy en INBOX ya están en BD.")
            return

        logger.info(f"watchdog_inbox: {len(missing_uids)} correo(s) faltante(s) detectado(s). Procesando...")

        # Descargar solo los faltantes (en un solo lote, máximo ~20)
        emails = list(mailbox.fetch_messages_by_uids('INBOX', missing_uids[:20]))

        correos_guardados = 0
        correos_problematicos = 0
        for msg in emails:
            try:
                result = procesar_mensaje_imap(
                    msg,
                    folder_name='INBOX',
                    flow_label='watchdog',
                    persist=True,
                    fallback_domain='gmail.com',
                )

                mailbox.mark_seen(msg.uid)

                if result['status'] == 'saved':
                    correos_guardados += 1
                    logger.info(
                        "watchdog_inbox: guardado message_id=%s adjuntos=%s",
                        result['message_id'],
                        result.get('attachment_count', 0),
                    )
                elif result['status'] == 'problematic':
                    correos_problematicos += 1
                    logger.warning(
                        "watchdog_inbox: correo derivado a bandeja problemática message_id=%s motivo=%s",
                        result['message_id'],
                        result.get('problem_reason', 'VALIDACION_ADJUNTO'),
                    )

            except Exception as e:
                logger.error(f"watchdog_inbox: error procesando UID={msg.uid}: {e}", exc_info=True)

        if correos_guardados:
            logger.info(f"watchdog_inbox: {correos_guardados} correo(s) rescatado(s) exitosamente.")
        if correos_problematicos:
            logger.warning(f"watchdog_inbox: {correos_problematicos} correo(s) enviado(s) a bandeja problemática.")

    except imaplib.IMAP4.error as e:
        logger.error(f"watchdog_inbox: error IMAP: {e}")
    except Exception as e:
        logger.error(f"watchdog_inbox: error general: {e}", exc_info=True)
    finally:
        if mailbox:
            try:
                mailbox.logout()
            except Exception:
                pass
        # Liberar lock propio del watchdog
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection('default')
            redis_conn.delete(_WATCHDOG_LOCK_KEY)
        except Exception:
            from django.core.cache import cache
            cache.delete(_WATCHDOG_LOCK_KEY)
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.gmail_pubsub_pull_periodico', soft_time_limit=120, time_limit=150)
def gmail_pubsub_pull_periodico():
    """Consume notificaciones Pub/Sub de Gmail watch y dispara history sync."""
    from .utils.email_provider import get_email_ingestion_provider_name

    if get_email_ingestion_provider_name() != 'gmail_api':
        logger.debug('gmail_pubsub_pull_periodico: omitido (ingestion != gmail_api)')
        return

    db.close_old_connections()
    try:
        from .utils.gmail_pipeline import run_pubsub_pull

        result = run_pubsub_pull()
        logger.info('gmail_pubsub_pull_periodico: %s', result.summary)
        if result.status == 'FAIL':
            raise RuntimeError(result.output)
        if result.summary.get('rate_limited'):
            logger.warning('gmail_pubsub_pull_periodico: omitido por rate limit Gmail API')
            return
    except Exception as exc:
        logger.error('gmail_pubsub_pull_periodico: %s', exc, exc_info=True)
        raise
    finally:
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.gmail_watch_renew_periodico', soft_time_limit=120, time_limit=150)
def gmail_watch_renew_periodico():
    """Renueva users.watch si está por expirar o no existe."""
    from .utils.email_provider import get_email_ingestion_provider_name

    if get_email_ingestion_provider_name() != 'gmail_api':
        logger.debug('gmail_watch_renew_periodico: omitido (ingestion != gmail_api)')
        return

    db.close_old_connections()
    try:
        from .utils.gmail_pipeline import renew_watch_if_needed

        result = renew_watch_if_needed()
        logger.info('gmail_watch_renew_periodico: %s', result.summary)
        if result.status == 'FAIL':
            raise RuntimeError(result.output)
    except Exception as exc:
        logger.error('gmail_watch_renew_periodico: %s', exc, exc_info=True)
        raise
    finally:
        db.close_old_connections()


@shared_task(name='correspondencia.tasks.ejecutar_operacion_control_correos', soft_time_limit=900, time_limit=960)
def ejecutar_operacion_control_correos(ejecucion_id):
    """Ejecuta una operación del panel de control de correos y guarda su salida."""
    from django.utils import timezone

    from .email_sync_control import dumps_payload, execute_control_operation, loads_payload
    from .models import EjecucionControlCorreos

    db.close_old_connections()
    ejecucion = EjecucionControlCorreos.objects.get(pk=ejecucion_id)
    ejecucion.estado = 'RUNNING'
    ejecucion.iniciado_en = timezone.now()
    ejecucion.error = ''
    ejecucion.save(update_fields=['estado', 'iniciado_en', 'error'])

    try:
        parametros = loads_payload(ejecucion.parametros)
        resultado = execute_control_operation(ejecucion.tipo_operacion, parametros)

        metricas = resultado.get('metrics', {})
        ejecucion.estado = resultado.get('status', 'SUCCESS')
        ejecucion.resumen = dumps_payload(resultado.get('summary', {}))
        ejecucion.salida = resultado.get('output', '')
        ejecucion.total_encontrados = metricas.get('total_encontrados')
        ejecucion.total_nuevos = metricas.get('total_nuevos')
        ejecucion.total_guardados = metricas.get('total_guardados')
        ejecucion.total_rechazados = metricas.get('total_rechazados')
        ejecucion.total_adjuntos = metricas.get('total_adjuntos')
        ejecucion.total_duplicados = metricas.get('total_duplicados')
        ejecucion.total_sospechosos = metricas.get('total_sospechosos')
        ejecucion.total_errores = metricas.get('total_errores')
        ejecucion.finalizado_en = timezone.now()
        ejecucion.save(
            update_fields=[
                'estado',
                'resumen',
                'salida',
                'total_encontrados',
                'total_nuevos',
                'total_guardados',
                'total_rechazados',
                'total_adjuntos',
                'total_duplicados',
                'total_sospechosos',
                'total_errores',
                'finalizado_en',
            ]
        )
        return resultado.get('summary', {})
    except SoftTimeLimitExceeded:
        ejecucion.estado = 'FAIL'
        ejecucion.error = 'Timeout: la operación excedió el límite de tiempo configurado.'
        ejecucion.finalizado_en = timezone.now()
        ejecucion.save(update_fields=['estado', 'error', 'finalizado_en'])
        raise
    except Exception as exc:
        logger.error('Error ejecutando operación de control de correos %s: %s', ejecucion_id, exc, exc_info=True)
        ejecucion.estado = 'FAIL'
        ejecucion.error = str(exc)
        ejecucion.finalizado_en = timezone.now()
        ejecucion.save(update_fields=['estado', 'error', 'finalizado_en'])
        raise