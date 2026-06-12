"""
API REST para el Tablero de Monitoreo Operativo.
Solo accesible por superusuarios.
Soporta filtro temporal: ?rango=hoy|ayer|semana|mes|7d|30d|90d
                       o ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD
"""
import json
from datetime import timedelta, datetime as dt_datetime
from django.conf import settings
from django.db.models import (
    Count, Q, Avg, F, Case, When, IntegerField, CharField, Value,
    Subquery, OuterRef, Exists, Max,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from celery import current_app
from django.db.models.functions import TruncDate, TruncHour, Coalesce, NullIf
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response

from .email_sync_control import dumps_payload, loads_payload
from .models import (
    Correspondencia, CorrespondenciaSalida, SalidaDestinatario,
    CorreoEntrante, AdjuntoCorreoEntrante,
    DistribucionInternaUsuario, ComunicacionInterna,
    CorrespondenciaUrgencia, HistorialCorrespondencia, HistorialSalida,
    Notificacion, EstadoSincronizacionCorreos,
    ComunicacionInternaDistribucion, EjecucionControlCorreos, CorreoProblematico,
    PostmarkWebhookEvento,
)
from .tasks import ejecutar_operacion_control_correos
from .utils.email_provider import get_email_ingestion_sync_source, get_email_ingestion_provider_name
from .utils.evidencia_envio import _tiene_entrega_confirmada
from .utils.sla_queries import excluir_entrantes_con_respuesta, ids_entrantes_con_respuesta


class IsSuperUser(BasePermission):
    """Solo superusuarios pueden acceder al monitoreo."""
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


STALE_PENDING_MINUTES = 20
STALE_RUNNING_MINUTES = 20

SHARED_EMAIL_SYNC_ACTIONS = {
    'VERIFY': 'Verificación de cobertura encolada.',
    'RECOVER': 'Recuperación de faltantes encolada.',
    'DUPLICATES': 'Verificación de duplicados encolada.',
    'DIAGNOSE': 'Diagnóstico operativo encolado.',
}

IMAP_ONLY_ACTIONS = {
    'IMAP_TEST': 'Prueba IMAP encolada.',
    'SYNC_NOW': 'Sincronización inmediata encolada.',
}

GMAIL_API_ONLY_ACTIONS = {
    'GMAIL_STATUS': 'Consulta de estado operativo Gmail API encolada.',
    'GMAIL_WATCH_RENEW': 'Renovación de watch Gmail encolada.',
    'GMAIL_PUBSUB_PULL': 'Consumo de Pub/Sub Gmail encolado.',
    'GMAIL_HISTORY_SYNC': 'Sincronización por history Gmail encolada.',
    'GMAIL_PIPELINE_TICK': 'Ciclo Gmail (watch + Pub/Sub) encolado.',
}

HEAVY_IMAP_OPERATIONS = {'VERIFY', 'RECOVER', 'IMAP_TEST', 'SYNC_NOW'}
HEAVY_GMAIL_OPERATIONS = {
    'VERIFY', 'RECOVER', 'GMAIL_WATCH_RENEW', 'GMAIL_PUBSUB_PULL',
    'GMAIL_HISTORY_SYNC', 'GMAIL_PIPELINE_TICK', 'SYNC_NOW',
}

ALLOWED_IMAP_ACTIONS = {**SHARED_EMAIL_SYNC_ACTIONS, **IMAP_ONLY_ACTIONS}


def _is_gmail_api_ingestion():
    return get_email_ingestion_provider_name() == 'gmail_api'


def _allowed_email_sync_actions():
    actions = dict(SHARED_EMAIL_SYNC_ACTIONS)
    if _is_gmail_api_ingestion():
        actions.update(GMAIL_API_ONLY_ACTIONS)
    else:
        actions.update(IMAP_ONLY_ACTIONS)
    return actions


def _heavy_email_sync_operations():
    return HEAVY_GMAIL_OPERATIONS if _is_gmail_api_ingestion() else HEAVY_IMAP_OPERATIONS


def _provider_specific_no_param_actions():
    if _is_gmail_api_ingestion():
        return {
            'DIAGNOSE', 'GMAIL_STATUS', 'GMAIL_WATCH_RENEW', 'GMAIL_PUBSUB_PULL',
            'GMAIL_HISTORY_SYNC', 'GMAIL_PIPELINE_TICK',
        }
    return {'DIAGNOSE', 'IMAP_TEST', 'SYNC_NOW'}


# Alias internos (api_monitoreo ya importa helpers cacheados en sla_queries).
_ids_entrantes_con_respuesta = ids_entrantes_con_respuesta
_excluir_entrantes_con_respuesta = excluir_entrantes_con_respuesta


# ─── UTILIDAD: PARSEO DE RANGO TEMPORAL ──────────────────────────────────────

def _parse_rango(request):
    """
    Extrae ?rango= o ?desde=&hasta= y devuelve (desde_dt, hasta_dt) aware.
    Retorna (None, None) si no hay filtro (modo tiempo real).
    """
    preset = request.GET.get('rango', '')
    ahora = timezone.now()

    mapa = {
        'hoy': (
            ahora.replace(hour=0, minute=0, second=0, microsecond=0),
            ahora,
        ),
        'ayer': (
            (ahora - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
            (ahora - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999),
        ),
        'semana': (
            (ahora - timedelta(days=ahora.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
            ahora,
        ),
        'mes': (
            ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            ahora,
        ),
        '7d': (
            (ahora - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0),
            ahora,
        ),
        '30d': (
            (ahora - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0),
            ahora,
        ),
        '90d': (
            (ahora - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0),
            ahora,
        ),
    }

    if preset in mapa:
        return mapa[preset]

    # Fechas personalizadas
    desde_str = request.GET.get('desde', '')
    hasta_str = request.GET.get('hasta', '')
    if desde_str:
        d = parse_date(desde_str)
        desde = timezone.make_aware(
            dt_datetime.combine(d, dt_datetime.min.time())
        ) if d else None
    else:
        desde = None

    if hasta_str:
        d = parse_date(hasta_str)
        hasta = timezone.make_aware(
            dt_datetime.combine(d, dt_datetime.min.time().replace(hour=23, minute=59, second=59))
        ) if d else ahora
    else:
        hasta = ahora if desde else None

    return (desde, hasta) if desde else (None, None)


def _default_hoy(request):
    """Devuelve (desde, hasta) con fallback a hoy."""
    ahora = timezone.now()
    desde, hasta = _parse_rango(request)
    if not desde:
        desde = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        hasta = ahora
    return desde, hasta


def _map_sync_health(estado_raw):
    if estado_raw == 'SUCCESS':
        return 'ok'
    if estado_raw == 'RUNNING':
        return 'syncing'
    if estado_raw == 'FAIL':
        return 'error'
    return 'warning'


def _safe_json_loads(payload):
    try:
        return json.loads(payload) if payload else {}
    except Exception:
        return {}


def _serialize_sync_state(sync):
    if not sync:
        return None
    return {
        'fuente': sync.fuente,
        'estado': sync.estado,
        'ultimo_inicio': sync.ultimo_inicio.isoformat() if sync.ultimo_inicio else None,
        'ultimo_fin': sync.ultimo_fin.isoformat() if sync.ultimo_fin else None,
        'ultimo_error': sync.ultimo_error,
        'ultimo_history_id': getattr(sync, 'ultimo_history_id', '') or '',
        'watch_topic': getattr(sync, 'watch_topic', '') or '',
        'watch_expira_en': sync.watch_expira_en.isoformat() if getattr(sync, 'watch_expira_en', None) else None,
        'ultima_renovacion_watch': sync.ultima_renovacion_watch.isoformat() if getattr(sync, 'ultima_renovacion_watch', None) else None,
        'actualizado_en': sync.actualizado_en.isoformat() if sync.actualizado_en else None,
    }


def _cancel_control_run(run):
    if run.task_id:
        try:
            current_app.control.revoke(run.task_id, terminate=True)
        except Exception:
            pass

    run.estado = 'FAIL'
    run.error = 'Cancelada manualmente desde el panel de control.'
    run.finalizado_en = timezone.now()
    run.save(update_fields=['estado', 'error', 'finalizado_en'])


def _serialize_control_run(run, include_full_output=False):
    resumen_data = loads_payload(run.resumen, {})
    parametros_data = loads_payload(run.parametros, {})
    payload = {
        'id': run.id,
        'tipo_operacion': run.tipo_operacion,
        'tipo_operacion_label': run.get_tipo_operacion_display(),
        'estado': run.estado,
        'estado_label': run.get_estado_display(),
        'creado_en': run.creado_en.isoformat() if run.creado_en else None,
        'iniciado_en': run.iniciado_en.isoformat() if run.iniciado_en else None,
        'finalizado_en': run.finalizado_en.isoformat() if run.finalizado_en else None,
        'task_id': run.task_id,
        'ejecutado_por': (
            run.ejecutado_por.get_full_name()
            or run.ejecutado_por.username
            if run.ejecutado_por else 'Sistema'
        ),
        'parametros': parametros_data,
        'resumen': resumen_data,
        'error': run.error,
        'salida_preview': (run.salida or '')[:800],
        'metrics': {
            'total_encontrados': run.total_encontrados,
            'total_nuevos': run.total_nuevos,
            'total_guardados': run.total_guardados,
            'total_rechazados': run.total_rechazados,
            'total_adjuntos': run.total_adjuntos,
            'total_duplicados': run.total_duplicados,
            'total_sospechosos': run.total_sospechosos,
            'total_errores': run.total_errores,
        },
    }
    if include_full_output:
        payload['salida'] = run.salida or ''
    return payload


def _sanear_ejecuciones_atascadas():
    ahora = timezone.now()
    stale_pending_before = ahora - timezone.timedelta(minutes=STALE_PENDING_MINUTES)
    stale_running_before = ahora - timezone.timedelta(minutes=STALE_RUNNING_MINUTES)

    pendientes = EjecucionControlCorreos.objects.filter(
        estado='PENDING',
        creado_en__lt=stale_pending_before,
    )
    for ejecucion in pendientes:
        ejecucion.estado = 'FAIL'
        ejecucion.error = 'Marcada como fallida automáticamente por permanecer en PENDING demasiado tiempo.'
        ejecucion.finalizado_en = ahora
        ejecucion.save(update_fields=['estado', 'error', 'finalizado_en'])

    corriendo = EjecucionControlCorreos.objects.filter(
        estado='RUNNING',
        iniciado_en__lt=stale_running_before,
    )
    for ejecucion in corriendo:
        ejecucion.estado = 'FAIL'
        ejecucion.error = 'Marcada como fallida automáticamente por permanecer en RUNNING más allá del tiempo esperado.'
        ejecucion.finalizado_en = ahora
        ejecucion.save(update_fields=['estado', 'error', 'finalizado_en'])


def _build_imap_control_payload(desde, hasta):
    provider = get_email_ingestion_provider_name()
    sync_source = get_email_ingestion_sync_source()
    sync = EstadoSincronizacionCorreos.objects.filter(fuente=sync_source).first()
    estado_raw = sync.estado if sync else 'UNKNOWN'
    recientes_qs = EjecucionControlCorreos.objects.select_related('ejecutado_por')[:15]
    recientes = [_serialize_control_run(run) for run in recientes_qs]
    ultima_verificacion = EjecucionControlCorreos.objects.filter(tipo_operacion='VERIFY').first()
    ultimo_diagnostico = EjecucionControlCorreos.objects.filter(tipo_operacion='DIAGNOSE').first()
    activas_qs = EjecucionControlCorreos.objects.filter(estado__in=['PENDING', 'RUNNING'])
    heavy_ops = _heavy_email_sync_operations()
    ultimo_fetch = CorreoEntrante.objects.aggregate(ultima=Max('fecha_lectura_imap'))['ultima']
    ultimo_correo_bd_obj = CorreoEntrante.objects.order_by('-fecha_lectura_imap').first()
    ultimo_correo_bd = None
    if ultimo_correo_bd_obj:
        ultimo_correo_bd = {
            'id': ultimo_correo_bd_obj.id,
            'remitente': ultimo_correo_bd_obj.remitente,
            'fecha_lectura_imap': (
                ultimo_correo_bd_obj.fecha_lectura_imap.isoformat()
                if ultimo_correo_bd_obj.fecha_lectura_imap else None
            ),
        }

    correos_procesados = CorreoEntrante.objects.filter(
        procesado=True,
        fecha_recibida_gmail__gte=desde,
        fecha_recibida_gmail__lte=hasta,
    ).count()
    errores_sync = CorreoEntrante.objects.filter(
        en_papelera=True,
        fecha_recibida_gmail__gte=desde,
        fecha_recibida_gmail__lte=hasta,
    ).count()
    problematicos_pendientes = CorreoProblematico.objects.filter(resuelto=False).count()

    ejecuciones = EjecucionControlCorreos.objects.filter(
        creado_en__gte=desde,
        creado_en__lte=hasta,
    )

    gmail_status = None
    if _is_gmail_api_ingestion():
        try:
            from .utils.gmail_pipeline import build_operational_status
            gmail_status = build_operational_status()
        except Exception as exc:
            gmail_status = {'error': str(exc)}

    return {
        'ingestion_provider': provider,
        'sync_fuente': sync_source,
        'available_actions': list(_allowed_email_sync_actions().keys()),
        'gmail_status': gmail_status,
        'estado_conexion': _map_sync_health(estado_raw),
        'ultima_sincronizacion': sync.ultimo_fin.isoformat() if sync and sync.ultimo_fin else None,
        'ultimo_fetch': ultimo_fetch.isoformat() if ultimo_fetch else None,
        'ultimo_correo_bd': ultimo_correo_bd,
        'sync_state': _serialize_sync_state(sync),
        'correos_procesados_hoy': correos_procesados,
        'errores_sync': errores_sync,
        'problematicos_pendientes': problematicos_pendientes,
        'ejecuciones_hoy': ejecuciones.count(),
        'tareas_celery': {
            'activas': ejecuciones.filter(estado__in=['PENDING', 'RUNNING']).count(),
            'exitosas': ejecuciones.filter(estado='SUCCESS').count(),
            'advertencias': ejecuciones.filter(estado='WARN').count(),
            'fallidas': ejecuciones.filter(estado='FAIL').count(),
        },
        'control_panel': {
            'active_runs_count': activas_qs.count(),
            'heavy_operation_in_progress': activas_qs.filter(tipo_operacion__in=heavy_ops).exists(),
            'active_run_types': list(activas_qs.values_list('tipo_operacion', flat=True)),
            'latest_verify': _serialize_control_run(ultima_verificacion) if ultima_verificacion else None,
            'latest_diagnose': _serialize_control_run(ultimo_diagnostico) if ultimo_diagnostico else None,
            'recent_runs': recientes,
        },
    }


def _create_imap_control_run(request):
    action = (request.data.get('action') or '').strip().upper()
    allowed_actions = _allowed_email_sync_actions()
    if action not in allowed_actions:
        return Response({'detail': 'La acción solicitada no es válida.'}, status=400)

    try:
        days = max(1, int(request.data.get('days') or 1))
    except (TypeError, ValueError):
        days = 1

    since = (request.data.get('since') or '').strip()
    until = (request.data.get('until') or '').strip()

    ejecucion_activa = EjecucionControlCorreos.objects.filter(
        tipo_operacion=action,
        estado__in=['PENDING', 'RUNNING'],
    ).order_by('-creado_en').first()
    if ejecucion_activa:
        return Response(
            {
                'detail': f'Ya existe una ejecución activa para {action}.',
                'run': _serialize_control_run(ejecucion_activa),
            },
            status=409,
        )

    if action in _heavy_email_sync_operations():
        otra_operacion_imap = EjecucionControlCorreos.objects.filter(
            tipo_operacion__in=_heavy_email_sync_operations(),
            estado__in=['PENDING', 'RUNNING'],
        ).order_by('-creado_en').first()
        if otra_operacion_imap:
            return Response(
                {
                    'detail': 'Ya hay una operación intensiva de correo en curso. Espera a que termine antes de lanzar otra.',
                    'run': _serialize_control_run(otra_operacion_imap),
                },
                status=409,
            )

    parametros = {'days': days}
    if since:
        parametros['since'] = since
    if until:
        parametros['until'] = until
    if action in _provider_specific_no_param_actions():
        parametros = {}

    ejecucion = EjecucionControlCorreos.objects.create(
        tipo_operacion=action,
        ejecutado_por=request.user,
        parametros=dumps_payload(parametros),
    )

    try:
        async_result = ejecutar_operacion_control_correos.delay(ejecucion.pk)
        ejecucion.task_id = async_result.id
        ejecucion.save(update_fields=['task_id'])
    except Exception as exc:
        ejecucion.estado = 'FAIL'
        ejecucion.error = str(exc)
        ejecucion.save(update_fields=['estado', 'error'])
        return Response({'detail': f'No fue posible encolar la operación: {exc}'}, status=500)

    return Response(
        {
            'detail': allowed_actions[action],
            'run': _serialize_control_run(ejecucion),
        },
        status=202,
    )


def _mensaje_rechazo_postmark_sin_aceptacion(detalle_error):
    """Explica fallos en los que Postmark respondió pero no aceptó el mensaje (sin MessageID)."""
    detalle = (detalle_error or '').strip().lower()
    if 'sender signature' in detalle or 'not a sender signature' in detalle:
        return (
            'Postmark rechazó el remitente (From): la dirección no está autorizada como '
            'Sender Signature. Revise OUTBOUND_EMAIL_ADDRESS y el panel de Postmark.'
        )
    if 'postmark rechazó' in detalle or 'postmark devolvió error' in detalle:
        return (
            'Postmark rechazó el envío en la API antes de aceptar el mensaje; '
            'no se generó MessageID ni aparece en el historial de envíos.'
        )
    if 'no fue posible conectar con postmark' in detalle:
        return 'No hubo conexión con la API de Postmark (red, DNS o firewall).'
    if 'postmark_server_token' in detalle:
        return 'Falta o es inválido POSTMARK_SERVER_TOKEN en la configuración del servidor.'
    return None


def _resumir_motivo_rebote(detalle_error, smtp_code, dsn_status, estado):
    """Genera una explicación segura y corta del estado de entrega."""
    from correspondencia.utils.evidencia_envio import detalle_error_es_solo_confirmacion_entrega

    if estado == 'ENVIADO' and detalle_error_es_solo_confirmacion_entrega(detalle_error):
        return 'El servidor del destinatario aceptó el mensaje (confirmación SMTP 250).'

    detalle = (detalle_error or '').strip()
    texto_base = ' '.join(detalle.split())
    texto_base_lower = texto_base.lower()

    mensaje_postmark = _mensaje_rechazo_postmark_sin_aceptacion(detalle_error)
    if mensaje_postmark:
        return mensaje_postmark

    if dsn_status == '5.1.1' or 'does not exist' in texto_base_lower or 'nosuchuser' in texto_base_lower:
        return 'La cuenta de correo no existe o la dirección parece incorrecta.'
    if dsn_status == '5.2.2' or 'mailbox full' in texto_base_lower:
        return 'El buzón del destinatario está lleno.'
    if dsn_status and str(dsn_status).startswith('4.'):
        return 'El servidor reportó un problema temporal de entrega.'
    if smtp_code and str(smtp_code).startswith('5'):
        return 'El servidor del destinatario rechazó el correo de forma permanente.'
    if detalle:
        return 'El servidor reportó un problema de entrega; hay detalle técnico registrado.'
    if estado == 'REBOTE':
        return 'Se detectó un rebote, pero el servidor no dejó diagnóstico técnico persistido.'
    return 'No se confirmó la entrega por un error durante el proceso de envío.'


def _verificacion_envio_destinatario(estado, fecha_envio, id_mensaje_enviado, detalle_error=None):
    """Diferencia intento de envío, aceptación local y entrega final."""
    envio_registrado = bool(fecha_envio or id_mensaje_enviado)

    if estado == 'REBOTE':
        if envio_registrado:
            return {
                'envio_registrado': True,
                'entrega_exitosa': False,
                'estado_final': 'no_entregado',
                'resumen': 'El sistema registró el envío y después recibió un rebote. No debe considerarse entregado.',
            }
        return {
            'envio_registrado': False,
            'entrega_exitosa': False,
            'estado_final': 'no_entregado',
            'resumen': 'Hay rebote registrado, pero no quedó evidencia suficiente del intento de envío.',
        }

    if estado == 'FALLO':
        if envio_registrado:
            return {
                'envio_registrado': True,
                'entrega_exitosa': False,
                'estado_final': 'error_envio',
                'resumen': 'Hubo intento de envío, pero el proceso terminó con error y no se confirmó la entrega.',
            }
        mensaje_postmark = _mensaje_rechazo_postmark_sin_aceptacion(detalle_error)
        return {
            'envio_registrado': False,
            'entrega_exitosa': False,
            'estado_final': 'error_envio',
            'resumen': mensaje_postmark or (
                'No se confirmó la aceptación del mensaje por el servidor saliente '
                '(sin fecha de envío ni MessageID en el sistema).'
            ),
        }

    return {
        'envio_registrado': envio_registrado,
        'entrega_exitosa': False,
        'estado_final': 'desconocido',
        'resumen': 'No hay una verificación concluyente de entrega final.',
    }


# ─── PULSO ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_pulso(request):
    """
    GET /api/monitoreo/pulso/?rango=semana
    Métricas principales del sistema.
    """
    ahora = timezone.now()
    desde, hasta = _default_hoy(request)

    entrantes = CorreoEntrante.objects.filter(
        fecha_recibida_gmail__gte=desde, fecha_recibida_gmail__lte=hasta,
    ).count()

    radicados = Correspondencia.objects.filter(
        fecha_radicacion__gte=desde, fecha_radicacion__lte=hasta,
    ).count()

    salientes = CorrespondenciaSalida.objects.filter(
        estado='ENVIADA', fecha_envio__gte=desde, fecha_envio__lte=hasta,
    ).count()

    internos = ComunicacionInterna.objects.filter(
        fecha_creacion__gte=desde, fecha_creacion__lte=hasta,
    ).count()

    # Interoficina: correspondencias del periodo que fueron distribuidas
    interoficina = Correspondencia.objects.filter(
        fecha_radicacion__gte=desde, fecha_radicacion__lte=hasta,
    ).annotate(
        n_dist=Count('distribuciones_internas')
    ).filter(n_dist__gt=0).count()

    # Sin responder en el periodo
    qs_periodo = Correspondencia.objects.filter(
        requiere_respuesta=True,
        fecha_radicacion__gte=desde,
        fecha_radicacion__lte=hasta,
    )
    sin_responder = _excluir_entrantes_con_respuesta(qs_periodo).count()

    plazo_vencido = _excluir_entrantes_con_respuesta(
        qs_periodo.filter(
            fecha_limite_respuesta_persist__isnull=False,
            fecha_limite_respuesta_persist__lt=ahora,
        )
    ).count()

    return Response({
        'radicados_hoy': radicados,
        'entrantes_hoy': entrantes,
        'salientes_hoy': salientes,
        'internos_hoy': internos,
        'interoficina_hoy': interoficina,
        'sin_responder': sin_responder,
        'plazo_vencido': plazo_vencido,
        'timestamp': ahora.isoformat(),
    })


# ─── SEMÁFORO SLA ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_sla(request):
    """
    GET /api/monitoreo/sla/?rango=mes
    Desglose de estados SLA con semáforo por oficina.
    """
    ahora = timezone.now()
    desde, hasta = _parse_rango(request)

    base = Correspondencia.objects.filter(requiere_respuesta=True)
    if desde:
        base = base.filter(fecha_radicacion__gte=desde, fecha_radicacion__lte=hasta)

    sin_respuesta = _excluir_entrantes_con_respuesta(base)
    ids_con_respuesta = _ids_entrantes_con_respuesta()

    vencidos = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__lt=ahora,
    ).count()

    por_vencer = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__gte=ahora,
        fecha_limite_respuesta_persist__lte=ahora + timedelta(days=4),
    ).count()

    a_tiempo_pending = sin_respuesta.filter(
        Q(fecha_limite_respuesta_persist__isnull=True)
        | Q(fecha_limite_respuesta_persist__gt=ahora + timedelta(days=4))
    ).count()

    # Respondidas a tiempo (ciclo N+1 pero sobre un set acotado)
    con_respuesta = base.filter(pk__in=ids_con_respuesta)
    respondidas_ok = 0
    for c in con_respuesta.filter(fecha_limite_respuesta_persist__isnull=False):
        resp = (
            CorrespondenciaSalida.objects
            .filter(respuesta_a=c, estado__in=['APROBADA', 'ENVIADA'])
            .order_by('-fecha_envio', '-fecha_aprobacion')
            .values_list('fecha_envio', 'fecha_aprobacion', 'fecha_creacion')
            .first()
        )
        if resp:
            fecha_resp = resp[0] or resp[1] or resp[2]
            if fecha_resp and c.fecha_limite_respuesta_persist and fecha_resp <= c.fecha_limite_respuesta_persist:
                respondidas_ok += 1

    total = base.count()
    a_tiempo_total = respondidas_ok + a_tiempo_pending
    pct = round(a_tiempo_total / total * 100, 1) if total else 100

    # Por oficina (solo pendientes sin respuesta)
    sla_by_office = (
        sin_respuesta
        .filter(oficina_destino__isnull=False)
        .values('oficina_destino__nombre')
        .annotate(
            total=Count('id'),
            _vencidos=Count('id', filter=Q(
                fecha_limite_respuesta_persist__isnull=False,
                fecha_limite_respuesta_persist__lt=ahora)),
            _por_vencer=Count('id', filter=Q(
                fecha_limite_respuesta_persist__isnull=False,
                fecha_limite_respuesta_persist__gte=ahora,
                fecha_limite_respuesta_persist__lte=ahora + timedelta(days=4))),
        )
        .order_by()
        .filter(total__gt=0)
    )
    por_oficina = []
    for row in sla_by_office:
        t = row['total']
        v = row['_vencidos']
        pv = row['_por_vencer']
        at = max(t - v - pv, 0)
        por_oficina.append({
            'oficina': row['oficina_destino__nombre'] or 'Sin asignar',
            'total': t,
            'a_tiempo': at,
            'por_vencer': pv,
            'vencidos': v,
            'pct_cumplimiento': round((t - v) / t * 100, 1) if t > 0 else 100,
        })
    por_oficina.sort(key=lambda x: x['pct_cumplimiento'])

    return Response({
        'global': {
            'pct_cumplimiento': pct,
            'a_tiempo': a_tiempo_total,
            'por_vencer': por_vencer,
            'vencidos': vencidos,
        },
        'por_oficina': por_oficina,
    })


# ─── PIPELINE DE ENVÍO ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_envio(request):
    """
    GET /api/monitoreo/envio/?rango=semana
    Pipeline de correspondencia saliente.
    """
    desde, hasta = _default_hoy(request)

    pendientes_envio = SalidaDestinatario.objects.filter(estado='PENDIENTE').count()

    en_cola = CorrespondenciaSalida.objects.filter(
        estado__in=['PENDIENTE_APROBACION', 'APROBADA']
    ).count()

    enviados = SalidaDestinatario.objects.filter(
        estado='ENVIADO', fecha_envio__gte=desde, fecha_envio__lte=hasta,
    ).count()

    errores = SalidaDestinatario.objects.filter(
        estado__in=['FALLO', 'REBOTE'],
        ultimo_evento_at__gte=desde, ultimo_evento_at__lte=hasta,
    ).count()

    rebotes_raw = list(
        SalidaDestinatario.objects.filter(
            estado__in=['FALLO', 'REBOTE'],
            ultimo_evento_at__gte=desde, ultimo_evento_at__lte=hasta,
        ).order_by('-ultimo_evento_at')[:10]
        .values(
            'email_snapshot', 'nombre_snapshot', 'estado',
            'detalle_error', 'smtp_code', 'dsn_status',
            'fecha_envio', 'id_mensaje_enviado', 'ultimo_evento_at',
            'correspondencia_salida__numero_radicado_salida',
            'correspondencia_salida_id',
        )
    )

    return Response({
        'pendientes_envio': pendientes_envio,
        'en_cola': en_cola,
        'enviados_hoy': enviados,
        'errores_hoy': errores,
        'rebotes_recientes': [
            {
                'email': r['email_snapshot'],
                'nombre': r['nombre_snapshot'] or '',
                'tipo': r['estado'],
                'error': r['detalle_error'] or '',
                'motivo_resumen': _resumir_motivo_rebote(
                    r.get('detalle_error'),
                    r.get('smtp_code'),
                    r.get('dsn_status'),
                    r.get('estado'),
                ),
                'smtp_code': r['smtp_code'] or '',
                'dsn_status': r['dsn_status'] or '',
                'fecha_envio': r['fecha_envio'].isoformat() if r.get('fecha_envio') else '',
                'tiene_message_id': bool(r.get('id_mensaje_enviado')),
                'message_id': r.get('id_mensaje_enviado') or '',
                'fecha': r['ultimo_evento_at'].isoformat() if r.get('ultimo_evento_at') else '',
                'radicado': r['correspondencia_salida__numero_radicado_salida'] or '',
                'salida_id': r.get('correspondencia_salida_id'),
                'verificacion_envio': _verificacion_envio_destinatario(
                    r.get('estado'),
                    r.get('fecha_envio'),
                    r.get('id_mensaje_enviado'),
                    r.get('detalle_error'),
                ),
            }
            for r in rebotes_raw
        ],
    })


def _postmark_message_url(message_id):
    template = (getattr(settings, 'POSTMARK_MESSAGE_URL_TEMPLATE', '') or '').strip()
    if not template or not message_id:
        return ''
    try:
        return template.format(message_id=message_id)
    except Exception:
        return ''


def _outbound_provider_label():
    """Etiqueta legible del proveedor de envío saliente configurado."""
    provider = (getattr(settings, 'EMAIL_PROVIDER', '') or 'smtp').strip().lower()
    if provider == 'gmail_api':
        return 'Gmail API'
    if provider == 'postmark':
        return 'Postmark'
    return 'SMTP'


def _outbound_usa_postmark():
    return (getattr(settings, 'EMAIL_PROVIDER', '') or '').strip().lower() == 'postmark'


def _evento_principal_para_destinatario(eventos, email):
    """Elige el evento Postmark más relevante para un destinatario."""
    email_norm = (email or '').strip().lower()
    candidatos = []
    for evento in eventos or []:
        recipient = (evento.recipient or '').strip().lower()
        if recipient and recipient != email_norm:
            continue
        candidatos.append(evento)
    if not candidatos:
        return None

    prioridad = {'Delivery': 0, 'Bounce': 1}
    candidatos.sort(
        key=lambda ev: (
            prioridad.get((ev.record_type or '').strip(), 99),
            -(ev.recibido_at.timestamp() if ev.recibido_at else 0),
        )
    )
    return candidatos[0]


def _postmark_estado_para_destinatario(destinatario, evento):
    """Estado de entrega para monitoreo (campo JSON legacy: postmark_estado)."""
    provider_id = (destinatario.postmark_message_id or '').strip()
    provider_label = _outbound_provider_label()

    if evento:
        record_type = (evento.record_type or '').strip()
        fuente = ''
        payload = evento.payload or {}
        if payload.get('_source') == 'postmark_api' or evento.resultado == 'api_sync':
            fuente = ' (sincronizado desde Postmark)'
        if record_type == 'Delivery':
            return f'Entregado por Postmark{fuente}'
        if record_type == 'Bounce':
            return f'Rebote en Postmark{fuente}'
        return f'Evento Postmark: {record_type or "registrado"}{fuente}'

    if destinatario.estado == 'ENVIADO' and _tiene_entrega_confirmada(destinatario):
        if _outbound_usa_postmark():
            return f'Entregado por {provider_label}'
        return 'Entrega confirmada por el servidor destino'

    if provider_id:
        if destinatario.estado == 'ENVIADO':
            return f'Enviado por {provider_label}; confirmación de entrega pendiente'
        return f'Enviado por {provider_label}; estado final en aplicativo'

    if destinatario.estado == 'FALLO':
        if _outbound_usa_postmark():
            return f'No aceptado por {provider_label} o sin MessageID persistido'
        return 'No aceptado por el proveedor de envío o sin ID persistido'
    return 'Sin referencia de entrega del proveedor persistida'


def _postmark_detalle_evento(evento):
    if not evento:
        return ''
    payload = evento.payload or {}
    for key in ('Description', 'Details', 'Name', 'Summary'):
        value = (payload.get(key) or '').strip()
        if value:
            return value
    return evento.resultado or ''


def _user_display(user):
    if not user:
        return ''
    return (user.get_full_name() or user.username or '').strip()


_SALIDA_OFICINA_SELECT_RELATED = (
    'correspondencia_salida__oficina_emisora',
    'correspondencia_salida__usuario_redactor__perfil__oficina',
    'correspondencia_salida__usuario_aprobador__perfil__oficina',
    'correspondencia_salida__respuesta_a__oficina_destino',
)


def _oficina_resuelta_expr(prefix='correspondencia_salida'):
    """Expresión ORM para nombre de oficina con fallbacks (filtros/agregaciones)."""
    p = prefix
    return Coalesce(
        NullIf(F(f'{p}__oficina_emisora_nombre'), Value('')),
        F(f'{p}__usuario_redactor__perfil__oficina__nombre'),
        F(f'{p}__usuario_aprobador__perfil__oficina__nombre'),
        F(f'{p}__oficina_emisora__nombre'),
        F(f'{p}__respuesta_a__oficina_destino__nombre'),
        Value(''),
        output_field=CharField(),
    )


def _filtro_rango_destinatario(desde, hasta):
    """Filtro por fecha indexable (ultimo_evento_at / fecha_envio)."""
    return (
        Q(ultimo_evento_at__gte=desde, ultimo_evento_at__lte=hasta)
        | Q(
            ultimo_evento_at__isnull=True,
            fecha_envio__gte=desde,
            fecha_envio__lte=hasta,
        )
    )


def _es_deadlock_sql(exc: Exception) -> bool:
    texto = str(exc).lower()
    return '1205' in texto or 'interbloqueo' in texto or 'deadlock' in texto


def _count_con_reintentos(qs, intentos: int = 3):
    import time as time_module
    from django.db import transaction

    ultimo_error = None
    for intento in range(intentos):
        try:
            with transaction.atomic():
                return qs.count()
        except Exception as exc:
            if not _es_deadlock_sql(exc):
                raise
            ultimo_error = exc
            time_module.sleep(0.25 * (intento + 1))
    if ultimo_error:
        raise ultimo_error
    return 0


def _listar_con_reintentos(qs, intentos: int = 3):
    import time as time_module

    ultimo_error = None
    for intento in range(intentos):
        try:
            return list(qs)
        except Exception as exc:
            if not _es_deadlock_sql(exc):
                raise
            ultimo_error = exc
            time_module.sleep(0.25 * (intento + 1))
    if ultimo_error:
        raise ultimo_error
    return []


def _filtro_oficina_destinatario(oficina_filter: str):
    if not oficina_filter:
        return Q()
    return (
        Q(correspondencia_salida__oficina_emisora_nombre__icontains=oficina_filter)
        | Q(correspondencia_salida__oficina_emisora__nombre__icontains=oficina_filter)
        | Q(correspondencia_salida__usuario_redactor__perfil__oficina__nombre__icontains=oficina_filter)
        | Q(correspondencia_salida__usuario_aprobador__perfil__oficina__nombre__icontains=oficina_filter)
        | Q(correspondencia_salida__respuesta_a__oficina_destino__nombre__icontains=oficina_filter)
    )


def _oficina_nombre_salida(salida):
    """Nombre de oficina para monitoreo: snapshot → redactor → aprobador → emisora → entrante."""
    nombre = (salida.oficina_emisora_nombre or '').strip()
    if nombre:
        return nombre

    redactor = salida.usuario_redactor
    if redactor:
        perfil = getattr(redactor, 'perfil', None)
        if perfil and perfil.oficina_id:
            nombre = (getattr(perfil.oficina, 'nombre', '') or '').strip()
            if nombre:
                return nombre

    aprobador = salida.usuario_aprobador
    if aprobador:
        perfil = getattr(aprobador, 'perfil', None)
        if perfil and perfil.oficina_id:
            nombre = (getattr(perfil.oficina, 'nombre', '') or '').strip()
            if nombre:
                return nombre

    if salida.oficina_emisora_id:
        nombre = (getattr(salida.oficina_emisora, 'nombre', '') or '').strip()
        if nombre:
            return nombre

    original = getattr(salida, 'respuesta_a', None)
    if original and original.oficina_destino_id:
        nombre = (getattr(original.oficina_destino, 'nombre', '') or '').strip()
        if nombre:
            return nombre

    return ''


def _archivo_payload(adjunto):
    url = ''
    archivo = getattr(adjunto, 'archivo', None)
    if archivo:
        try:
            url = archivo.url
        except Exception:
            url = ''
    return {
        'id': adjunto.id,
        'nombre': adjunto.nombre_original or str(adjunto),
        'tipo_mime': adjunto.tipo_mime or '',
        'fecha_carga': adjunto.fecha_carga.isoformat() if adjunto.fecha_carga else '',
        'url': url,
    }


def _evidencia_salida_payload(salida):
    evidencia = getattr(salida, 'evidencia_respuesta', None)
    if not evidencia:
        return None
    try:
        url = evidencia.url
    except Exception:
        url = ''
    return {
        'id': salida.id,
        'nombre': evidencia.name.split('/')[-1] if getattr(evidencia, 'name', '') else 'Evidencia de respuesta',
        'tipo_mime': '',
        'fecha_carga': salida.fecha_envio.isoformat() if salida.fecha_envio else '',
        'url': url,
    }


def _postmark_event_payload(evento):
    payload = evento.payload or {}
    return {
        'id': evento.id,
        'record_type': evento.record_type or '',
        'recipient': evento.recipient or '',
        'postmark_message_id': evento.postmark_message_id or '',
        'recibido_at': evento.recibido_at.isoformat() if evento.recibido_at else '',
        'procesado': evento.procesado,
        'resultado': evento.resultado or '',
        'detalle': _postmark_detalle_evento(evento),
        'bounce_type': payload.get('Type') or payload.get('BounceType') or '',
        'inactive': bool(payload.get('Inactive')) if 'Inactive' in payload else False,
    }


def _eventos_postmark_por_message_id(postmark_ids):
    eventos_por_id = {}
    if not postmark_ids:
        return eventos_por_id

    eventos = (
        PostmarkWebhookEvento.objects
        .filter(postmark_message_id__in=postmark_ids)
        .order_by('postmark_message_id', '-recibido_at')
    )
    for evento in eventos:
        eventos_por_id.setdefault((evento.postmark_message_id or '').strip(), []).append(evento)
    return eventos_por_id


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_salidas_correo(request):
    """
    GET /api/monitoreo/salidas-correo/?page=1&page_size=50&q=texto&estado=ENVIADO
    Flujo reciente de salidas de correo del aplicativo, una fila por destinatario.
    """
    desde, hasta = _parse_rango(request)
    if not desde:
        ahora = timezone.now()
        desde = (ahora - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        hasta = ahora

    qs = (
        SalidaDestinatario.objects
        .select_related(*_SALIDA_OFICINA_SELECT_RELATED)
        .filter(_filtro_rango_destinatario(desde, hasta))
        .exclude(estado='PENDIENTE')
    )

    estado = (request.GET.get('estado') or '').strip().upper()
    estados_validos = {'ENVIADO', 'FALLO', 'REBOTE'}
    if estado in estados_validos:
        qs = qs.filter(estado=estado)

    oficina_filter = (request.GET.get('oficina') or '').strip()
    if oficina_filter:
        qs = qs.filter(_filtro_oficina_destinatario(oficina_filter))

    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(email_snapshot__icontains=q)
            | Q(nombre_snapshot__icontains=q)
            | Q(id_mensaje_enviado__icontains=q)
            | Q(postmark_message_id__icontains=q)
            | Q(correspondencia_salida__numero_radicado_salida__icontains=q)
            | Q(correspondencia_salida__redactor_nombre__icontains=q)
            | _filtro_oficina_destinatario(q)
        )

    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(max(int(request.GET.get('page_size', 50)), 1), 50)
    offset = (page - 1) * page_size

    destinatarios = _listar_con_reintentos(
        qs.order_by('-ultimo_evento_at', '-fecha_envio', '-id')[offset:offset + page_size]
    )

    try:
        total = _count_con_reintentos(qs)
        resumen_estados = list(
            qs.values('estado').annotate(total=Count('id')).order_by('-total')
        )
        resumen_oficinas = list(
            qs.exclude(correspondencia_salida__oficina_emisora_nombre='')
              .values('correspondencia_salida__oficina_emisora_nombre')
              .annotate(total=Count('id'))
              .order_by('-total')[:20]
        )
    except Exception as exc:
        if not _es_deadlock_sql(exc):
            raise
        total = offset + len(destinatarios)
        resumen_estados = []
        resumen_oficinas = []

    postmark_ids = [
        (d.postmark_message_id or '').strip()
        for d in destinatarios
        if (d.postmark_message_id or '').strip()
    ]
    eventos_por_id = _eventos_postmark_por_message_id(postmark_ids)

    registros = []
    for d in destinatarios:
        salida = d.correspondencia_salida
        postmark_id = (d.postmark_message_id or '').strip()
        email = (d.email_snapshot or '').strip()
        evento = _evento_principal_para_destinatario(eventos_por_id.get(postmark_id, []), email)

        usuario = (
            (salida.redactor_nombre or '').strip()
            or (salida.usuario_redactor.get_full_name() if salida.usuario_redactor else '')
            or (salida.usuario_redactor.username if salida.usuario_redactor else '')
        )
        hora = d.ultimo_evento_at or d.fecha_envio or salida.fecha_envio or salida.fecha_aprobacion

        registros.append({
            'id': d.id,
            'salida_id': salida.id,
            'radicado': salida.numero_radicado_salida or '',
            'oficina_nombre': _oficina_nombre_salida(salida),
            'usuario_nombre': usuario or 'Sistema',
            'hora': hora.isoformat() if hora else '',
            'estado': d.estado,
            'estado_label': d.get_estado_display(),
            'destinatario_email': email,
            'destinatario_nombre': d.nombre_snapshot or '',
            'message_id': d.id_mensaje_enviado or '',
            'postmark_message_id': postmark_id,
            'postmark_estado': _postmark_estado_para_destinatario(d, evento),
            'postmark_record_type': evento.record_type if evento else '',
            'postmark_recibido_at': evento.recibido_at.isoformat() if evento else '',
            'postmark_detalle': _postmark_detalle_evento(evento),
            'postmark_url': _postmark_message_url(postmark_id),
            'detalle_error': d.detalle_error or '',
            'smtp_code': d.smtp_code or '',
            'dsn_status': d.dsn_status or '',
        })

    import math
    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': math.ceil(total / page_size) if total else 0,
        'desde': desde.isoformat(),
        'hasta': hasta.isoformat(),
        'resumen_estados': [
            {'estado': item['estado'], 'total': item['total']}
            for item in resumen_estados
        ],
        'resumen_oficinas': [
            {
                'oficina': item['correspondencia_salida__oficina_emisora_nombre'],
                'total': item['total'],
            }
            for item in resumen_oficinas
        ],
        'registros': registros,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_salidas_correo_detalle(request, salida_id):
    """
    GET /api/monitoreo/salidas-correo/<salida_id>/detalle/
    Detalle operativo de una salida de correspondencia para el modal React de monitoreo.
    """
    salida = get_object_or_404(
        CorrespondenciaSalida.objects
        .select_related(
            'respuesta_a',
            'respuesta_a__remitente',
            'respuesta_a__oficina_destino',
            'usuario_redactor__perfil__oficina',
            'usuario_aprobador__perfil__oficina',
            'destinatario_contacto',
            'oficina_emisora',
            'envio_grupo',
        )
        .prefetch_related(
            'adjuntos',
            'historial__usuario',
            'destinatarios__contacto',
        ),
        pk=salida_id,
    )

    destinatarios = list(salida.destinatarios.all().order_by('id'))

    postmark_ids = [
        (destinatario.postmark_message_id or '').strip()
        for destinatario in destinatarios
        if (destinatario.postmark_message_id or '').strip()
    ]
    eventos_por_id = _eventos_postmark_por_message_id(postmark_ids)

    destinatarios_payload = []
    eventos_postmark_payload = []
    for destinatario in destinatarios:
        postmark_id = (destinatario.postmark_message_id or '').strip()
        email = (destinatario.email_snapshot or '').strip()
        eventos_destinatario = []
        for evento in eventos_por_id.get(postmark_id, []):
            recipient = (evento.recipient or '').strip().lower()
            if not recipient or recipient == email.lower():
                evento_payload = _postmark_event_payload(evento)
                eventos_destinatario.append(evento_payload)
                eventos_postmark_payload.append(evento_payload)
        evento_principal = _evento_principal_para_destinatario(
            eventos_por_id.get(postmark_id, []),
            email,
        )

        destinatarios_payload.append({
            'id': destinatario.id,
            'nombre': destinatario.nombre_snapshot or '',
            'email': email,
            'estado': destinatario.estado,
            'estado_label': destinatario.get_estado_display(),
            'fecha_envio': destinatario.fecha_envio.isoformat() if destinatario.fecha_envio else '',
            'message_id': destinatario.id_mensaje_enviado or '',
            'postmark_message_id': postmark_id,
            'postmark_estado': _postmark_estado_para_destinatario(destinatario, evento_principal),
            'postmark_url': _postmark_message_url(postmark_id),
            'detalle_error': destinatario.detalle_error or '',
            'motivo_resumen': _resumir_motivo_rebote(
                destinatario.detalle_error,
                destinatario.smtp_code,
                destinatario.dsn_status,
                destinatario.estado,
            ) if destinatario.estado in {'FALLO', 'REBOTE'} or destinatario.detalle_error else '',
            'smtp_code': destinatario.smtp_code or '',
            'dsn_status': destinatario.dsn_status or '',
            'ultimo_evento_at': destinatario.ultimo_evento_at.isoformat() if destinatario.ultimo_evento_at else '',
            'eventos_postmark': eventos_destinatario,
        })

    correspondencia_original = None
    if salida.respuesta_a:
        original = salida.respuesta_a
        correspondencia_original = {
            'id': original.id,
            'radicado': original.numero_radicado or '',
            'asunto': original.asunto or '',
            'remitente': getattr(original.remitente, 'nombre_completo', '') or '',
            'oficina_destino': getattr(original.oficina_destino, 'nombre', '') or '',
            'url': reverse('correspondencia:detalle_correspondencia', args=[original.id]),
        }

    total_destinatarios = len(destinatarios_payload)
    total_enviados = sum(1 for item in destinatarios_payload if item['estado'] == 'ENVIADO')
    total_fallos = sum(1 for item in destinatarios_payload if item['estado'] == 'FALLO')
    total_rebotes = sum(1 for item in destinatarios_payload if item['estado'] == 'REBOTE')

    return Response({
        'id': salida.id,
        'radicado': salida.numero_radicado_salida or '',
        'estado': salida.estado,
        'estado_label': salida.get_estado_display(),
        'asunto': salida.asunto or '',
        'cuerpo': salida.cuerpo or '',
        'tipo_respuesta': salida.tipo_respuesta,
        'tipo_respuesta_label': salida.get_tipo_respuesta_display(),
        'motivo_respuesta_discrecional': salida.motivo_respuesta_discrecional or '',
        'motivo_rechazo': salida.motivo_rechazo or '',
        'fecha_creacion': salida.fecha_creacion.isoformat() if salida.fecha_creacion else '',
        'fecha_ultima_modificacion': salida.fecha_ultima_modificacion.isoformat() if salida.fecha_ultima_modificacion else '',
        'fecha_aprobacion': salida.fecha_aprobacion.isoformat() if salida.fecha_aprobacion else '',
        'fecha_envio': salida.fecha_envio.isoformat() if salida.fecha_envio else '',
        'message_id': salida.id_mensaje_enviado or '',
        'postmark_message_id': salida.postmark_message_id or '',
        'postmark_url': _postmark_message_url((salida.postmark_message_id or '').strip()),
        'oficina': {
            'id': salida.oficina_emisora_id,
            'nombre': _oficina_nombre_salida(salida),
        },
        'redactor': {
            'id': salida.usuario_redactor_id,
            'nombre': salida.redactor_nombre or _user_display(salida.usuario_redactor) or 'Sistema',
            'cargo': salida.redactor_cargo or '',
        },
        'aprobador': {
            'id': salida.usuario_aprobador_id,
            'nombre': _user_display(salida.usuario_aprobador),
        },
        'funcionario_envia': salida.funcionario_envia or '',
        'destinatario_principal': {
            'nombre': getattr(salida.destinatario_contacto, 'nombre_completo', '') or '',
            'email': salida.destinatario_email or getattr(salida.destinatario_contacto, 'correo_electronico', '') or '',
        },
        'envio': {
            'tipo': salida.envio_tipo or '',
            'grupo': getattr(salida.envio_grupo, 'nombre', '') or '',
            'total_destinatarios_snapshot': salida.envio_total_destinatarios,
            'detalle_snapshot': salida.envio_detalle_snapshot or '',
        },
        'resumen_entrega': {
            'total_destinatarios': total_destinatarios,
            'enviados': total_enviados,
            'fallos': total_fallos,
            'rebotes': total_rebotes,
        },
        'destinatarios': destinatarios_payload,
        'eventos_postmark': eventos_postmark_payload,
        'adjuntos': [_archivo_payload(adjunto) for adjunto in salida.adjuntos.all()],
        'evidencia_respuesta': _evidencia_salida_payload(salida),
        'historial': [
            {
                'id': evento.id,
                'tipo': evento.tipo_evento,
                'tipo_label': evento.get_tipo_evento_display(),
                'descripcion': evento.descripcion or '',
                'fecha_hora': evento.fecha_hora.isoformat() if evento.fecha_hora else '',
                'usuario': _user_display(evento.usuario) or 'Sistema',
            }
            for evento in salida.historial.all()
        ],
        'correspondencia_original': correspondencia_original,
        'django_detail_url': reverse('correspondencia:detalle_respuesta_salida', args=[salida.id]),
    })


# ─── SINCRONIZACIÓN IMAP ────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_imap(request):
    """
    GET /api/monitoreo/imap/?rango=semana
    POST /api/monitoreo/imap/
    Estado de sincronización IMAP, historial operativo y acciones de control.
    """
    _sanear_ejecuciones_atascadas()

    if request.method == 'POST':
        return _create_imap_control_run(request)

    desde, hasta = _default_hoy(request)
    return Response(_build_imap_control_payload(desde, hasta))


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_email_sync_run(request, run_id):
    """Detalle, cancelación o eliminación de una ejecución del panel de control."""
    _sanear_ejecuciones_atascadas()
    run = get_object_or_404(
        EjecucionControlCorreos.objects.select_related('ejecutado_por'),
        pk=run_id,
    )

    if request.method == 'GET':
        return Response(_serialize_control_run(run, include_full_output=True))

    if request.method == 'POST':
        admin_action = (request.data.get('admin_action') or '').strip()
        if admin_action != 'cancel_run':
            return Response({'detail': 'La acción solicitada no es válida.'}, status=400)
        if run.estado not in {'PENDING', 'RUNNING'}:
            return Response(
                {'detail': 'Solo se pueden cancelar ejecuciones pendientes o en curso.'},
                status=400,
            )
        _cancel_control_run(run)
        return Response(
            {
                'detail': 'La ejecución fue cancelada desde el panel.',
                'run': _serialize_control_run(run, include_full_output=True),
            }
        )

    run.delete()
    return Response({'detail': 'La ejecución fue eliminada del historial.'})


# ─── DISTRIBUCIÓN Y LECTURA ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_distribucion(request):
    """
    GET /api/monitoreo/distribucion/?rango=mes
    Tasa de lectura interna por oficina.
    """
    desde, hasta = _parse_rango(request)

    dist_base = DistribucionInternaUsuario.objects.all()
    if desde:
        dist_base = dist_base.filter(
            correspondencia__fecha_radicacion__gte=desde,
            correspondencia__fecha_radicacion__lte=hasta,
        )

    total_leidos = dist_base.filter(leido=True).count()
    total_sin_leer = dist_base.filter(leido=False).count()

    from documentos.models import OficinaProductora
    oficinas = OficinaProductora.objects.all()
    por_oficina = []
    for ofi in oficinas:
        ofi_dist = dist_base.filter(correspondencia__oficina_destino=ofi)
        total = ofi_dist.count()
        if total == 0:
            continue
        leidos = ofi_dist.filter(leido=True).count()
        sin_leer = total - leidos
        por_oficina.append({
            'oficina': ofi.nombre,
            'total': total,
            'leidos': leidos,
            'sin_leer': sin_leer,
            'reasignados': 0,
            'pct_lectura': round(leidos / total * 100, 1),
        })
    por_oficina.sort(key=lambda x: x['pct_lectura'])

    return Response({
        'global': {
            'leidos': total_leidos,
            'sin_leer': total_sin_leer,
            'reasignados': 0,
        },
        'por_oficina': por_oficina,
    })


# ─── COMUNICACIONES INTERNAS ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_internas(request):
    """
    GET /api/monitoreo/internas/?rango=semana
    Métricas de comunicaciones internas.
    """
    ahora = timezone.now()
    desde, hasta = _default_hoy(request)

    base = ComunicacionInterna.objects.filter(
        fecha_creacion__gte=desde, fecha_creacion__lte=hasta,
    )

    creadas = base.count()
    respondidas = base.filter(estado='APROBADA').count()
    pendientes = base.filter(estado='PENDIENTE_APROBACION').count()

    lunes = (ahora - timedelta(days=ahora.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    total_semana = ComunicacionInterna.objects.filter(
        fecha_creacion__gte=lunes,
    ).count()

    por_tipo = list(
        base.values('tipo_distribucion')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    oficinas_mas_activas = [
        {
            'oficina': (row['tipo_distribucion'] or 'Otro').replace('_', ' ').title(),
            'total': row['total'],
        }
        for row in por_tipo if row['total'] > 0
    ]

    return Response({
        'creadas_hoy': creadas,
        'respondidas': respondidas,
        'pendientes': pendientes,
        'total_semana': total_semana,
        'oficinas_mas_activas': oficinas_mas_activas,
    })


# ─── URGENCIAS ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_urgencias(request):
    """
    GET /api/monitoreo/urgencias/?rango=mes
    Correspondencias con urgencia activa.
    """
    desde, hasta = _parse_rango(request)

    base = CorrespondenciaUrgencia.objects.filter(
        estado__in=['PENDIENTE', 'EN_PROCESO'],
    )
    if desde:
        base = base.filter(fecha_radicacion__gte=desde, fecha_radicacion__lte=hasta)

    total = base.count()

    activas_raw = list(
        base.select_related('oficina_destino', 'usuario_asignado')
        .order_by('fecha_limite')[:20]
        .values(
            'radicado', 'prioridad', 'estado',
            'horas_transcurridas', 'fecha_radicacion',
            'oficina_destino__nombre',
            'usuario_asignado__first_name',
        )
    )

    urgencias = [
        {
            'radicado': u['radicado'] or '',
            'asunto': f"Urgencia {(u.get('prioridad') or '').title()} — {u['radicado']}",
            'oficina': u['oficina_destino__nombre'] or 'Sin asignar',
            'usuario': u['usuario_asignado__first_name'] or 'Sin asignar',
            'fecha': u['fecha_radicacion'].isoformat() if u.get('fecha_radicacion') else '',
            'dias_sin_respuesta': round((u.get('horas_transcurridas') or 0) / 24, 1),
        }
        for u in activas_raw
    ]

    return Response({
        'urgencias': urgencias,
        'total': total,
    })


# ─── TENDENCIAS (GRÁFICAS) ──────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_tendencias(request):
    """
    GET /api/monitoreo/tendencias/?rango=30d
    Series temporales combinadas para gráficas.
    """
    desde, hasta = _parse_rango(request)
    if not desde:
        dias = min(int(request.GET.get('dias', 30)), 90)
        ahora = timezone.now()
        desde = (ahora - timedelta(days=dias)).replace(hour=0, minute=0, second=0, microsecond=0)
        hasta = ahora

    # Entrantes por día
    entrantes_qs = (
        Correspondencia.objects
        .filter(fecha_radicacion__gte=desde, fecha_radicacion__lte=hasta)
        .annotate(dia=TruncDate('fecha_radicacion'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    entrantes_dict = {r['dia']: r['total'] for r in entrantes_qs}

    # Salientes por día
    salientes_qs = (
        CorrespondenciaSalida.objects
        .filter(fecha_envio__gte=desde, fecha_envio__lte=hasta, estado='ENVIADA')
        .annotate(dia=TruncDate('fecha_envio'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    salientes_dict = {r['dia']: r['total'] for r in salientes_qs}

    # Internos por día
    internos_qs = (
        ComunicacionInterna.objects
        .filter(fecha_creacion__gte=desde, fecha_creacion__lte=hasta)
        .annotate(dia=TruncDate('fecha_creacion'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    internos_dict = {r['dia']: r['total'] for r in internos_qs}

    # Combinar series
    all_days = sorted(set(
        list(entrantes_dict.keys()) +
        list(salientes_dict.keys()) +
        list(internos_dict.keys())
    ))
    series = [
        {
            'fecha': dia.isoformat(),
            'entrantes': entrantes_dict.get(dia, 0),
            'salientes': salientes_dict.get(dia, 0),
            'internos': internos_dict.get(dia, 0),
        }
        for dia in all_days
    ]

    return Response({
        'series': series,
    })


# ─── HISTORIAL DE ACTIVIDAD ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_actividad(request):
    """
    GET /api/monitoreo/actividad/?rango=semana&limit=50
    Timeline global de actividad reciente.
    """
    ahora = timezone.now()
    desde, hasta = _parse_rango(request)
    if not desde:
        desde = ahora - timedelta(hours=24)
        hasta = ahora

    limit = min(int(request.GET.get('limit', 50)), 100)

    hist_entrada = list(
        HistorialCorrespondencia.objects
        .filter(fecha_hora__gte=desde, fecha_hora__lte=hasta)
        .order_by('-fecha_hora')[:limit]
        .values(
            'evento', 'descripcion', 'fecha_hora',
            'usuario__username', 'usuario__first_name',
            'correspondencia__numero_radicado',
        )
    )

    hist_salida = list(
        HistorialSalida.objects
        .filter(fecha_hora__gte=desde, fecha_hora__lte=hasta)
        .order_by('-fecha_hora')[:limit]
        .values(
            'tipo_evento', 'descripcion', 'fecha_hora',
            'usuario__username', 'usuario__first_name',
            'correspondencia_salida__numero_radicado_salida',
        )
    )

    actividades = []
    for h in hist_entrada:
        actividades.append({
            'tipo': (h['evento'] or 'otro').lower(),
            'descripcion': h['descripcion'] or '',
            'usuario': h['usuario__first_name'] or h['usuario__username'] or 'Sistema',
            'fecha': h['fecha_hora'].isoformat() if h['fecha_hora'] else '',
            'radicado': h['correspondencia__numero_radicado'] or '',
        })
    for h in hist_salida:
        actividades.append({
            'tipo': (h['tipo_evento'] or 'envio').lower(),
            'descripcion': h['descripcion'] or '',
            'usuario': h['usuario__first_name'] or h['usuario__username'] or 'Sistema',
            'fecha': h['fecha_hora'].isoformat() if h['fecha_hora'] else '',
            'radicado': h['correspondencia_salida__numero_radicado_salida'] or '',
        })

    actividades.sort(key=lambda x: x['fecha'], reverse=True)
    actividades = actividades[:limit]

    return Response({
        'actividades': actividades,
    })


# ─── NOTIFICACIONES DEL SISTEMA ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_notificaciones(request):
    """
    GET /api/monitoreo/notificaciones/?rango=semana
    Métricas de notificaciones del sistema.
    """
    ahora = timezone.now()
    desde, hasta = _default_hoy(request)

    base = Notificacion.objects.filter(
        fecha_creacion__gte=desde, fecha_creacion__lte=hasta,
    )

    total_hoy = base.count()
    sin_leer = base.filter(leida=False).count()
    leidas = base.filter(leida=True).count()

    lunes = (ahora - timedelta(days=ahora.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    total_semana = Notificacion.objects.filter(
        fecha_creacion__gte=lunes,
    ).count()

    por_tipo = list(
        base.values('tipo')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return Response({
        'total_hoy': total_hoy,
        'sin_leer': sin_leer,
        'leidas': leidas,
        'total_semana': total_semana,
        'por_tipo': por_tipo,
    })


# ─── ERRORES DE SYNC (PAGINADO) ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_errores_sync(request):
    """
    GET /api/monitoreo/errores-sync/?page=1&page_size=20&q=busca&motivo=duplicado
    Lista paginada de correos en papelera (errores de sincronización).
    """
    desde, hasta = _parse_rango(request)

    qs = CorreoEntrante.objects.filter(en_papelera=True)
    if desde:
        qs = qs.filter(fecha_recibida_gmail__gte=desde, fecha_recibida_gmail__lte=hasta)

    # Filtro por motivo
    motivo = request.GET.get('motivo', '')
    if motivo:
        qs = qs.filter(motivo_papelera=motivo)

    # Búsqueda libre
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(remitente__icontains=q) | Q(asunto__icontains=q) | Q(message_id__icontains=q)
        )

    total = qs.count()

    # Resumen por motivo
    resumen_motivos = list(
        qs.values('motivo_papelera')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Paginación
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    offset = (page - 1) * page_size

    registros_raw = list(
        qs.order_by('-fecha_papelera', '-fecha_recibida_gmail')[offset:offset + page_size]
        .values(
            'id', 'remitente', 'asunto', 'motivo_papelera',
            'fecha_recibida_gmail', 'fecha_papelera',
            'procesado', 'requiere_revision_manual',
        )
    )

    registros = [
        {
            'id': r['id'],
            'remitente': r['remitente'],
            'asunto': (r['asunto'] or '')[:120],
            'motivo': r['motivo_papelera'] or 'sin_motivo',
            'fecha_correo': r['fecha_recibida_gmail'].isoformat() if r.get('fecha_recibida_gmail') else '',
            'fecha_papelera': r['fecha_papelera'].isoformat() if r.get('fecha_papelera') else '',
            'procesado': r['procesado'],
            'revision_manual': r['requiere_revision_manual'],
        }
        for r in registros_raw
    ]

    import math
    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': math.ceil(total / page_size) if total else 0,
        'resumen_motivos': [
            {'motivo': m['motivo_papelera'] or 'sin_motivo', 'total': m['total']}
            for m in resumen_motivos
        ],
        'registros': registros,
    })


# ─── REBOTES PAGINADO (TODOS LOS ERRORES) ───────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_rebotes(request):
    """
    GET /api/monitoreo/rebotes/?page=1&page_size=10&q=busca&tipo=REBOTE&oficina=X&order=desc
    Lista paginada de todos los errores de envío (FALLO + REBOTE).
    Default: último mes.
    """
    desde, hasta = _parse_rango(request)
    if not desde:
        ahora = timezone.now()
        desde = (ahora - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        hasta = ahora

    qs = SalidaDestinatario.objects.filter(
        estado__in=['FALLO', 'REBOTE'],
        ultimo_evento_at__gte=desde, ultimo_evento_at__lte=hasta,
    )

    # Filtro por tipo
    tipo = request.GET.get('tipo', '')
    if tipo in ('FALLO', 'REBOTE'):
        qs = qs.filter(estado=tipo)

    # Filtro por oficina
    oficina_filter = request.GET.get('oficina', '')
    if oficina_filter:
        qs = qs.filter(correspondencia_salida__oficina_emisora_nombre__icontains=oficina_filter)

    # Búsqueda libre
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(email_snapshot__icontains=q)
            | Q(nombre_snapshot__icontains=q)
            | Q(correspondencia_salida__numero_radicado_salida__icontains=q)
            | Q(correspondencia_salida__redactor_nombre__icontains=q)
        )

    total = qs.count()

    # Resumen por tipo
    resumen_tipos = list(
        qs.values('estado').annotate(total=Count('id')).order_by('-total')
    )

    # Resumen por oficina
    resumen_oficinas = list(
        qs.exclude(correspondencia_salida__oficina_emisora_nombre=None)
          .exclude(correspondencia_salida__oficina_emisora_nombre='')
          .values('correspondencia_salida__oficina_emisora_nombre')
          .annotate(total=Count('id'))
          .order_by('-total')[:20]
    )

    # Paginación
    page = max(int(request.GET.get('page', 1)), 1)
    page_size = min(int(request.GET.get('page_size', 10)), 100)
    offset = (page - 1) * page_size

    # Ordenamiento por fecha
    order = request.GET.get('order', 'desc')
    order_field = 'ultimo_evento_at' if order == 'asc' else '-ultimo_evento_at'

    registros_raw = list(
        qs.order_by(order_field)[offset:offset + page_size]
        .values(
            'email_snapshot', 'nombre_snapshot', 'estado',
            'detalle_error', 'smtp_code', 'dsn_status',
            'fecha_envio', 'id_mensaje_enviado', 'ultimo_evento_at',
            'correspondencia_salida__numero_radicado_salida',
            'correspondencia_salida_id',
            'correspondencia_salida__redactor_nombre',
            'correspondencia_salida__oficina_emisora_nombre',
        )
    )

    registros = [
        {
            'email': r['email_snapshot'],
            'nombre': r['nombre_snapshot'] or '',
            'tipo': r['estado'],
            'error': r['detalle_error'] or '',
            'motivo_resumen': _resumir_motivo_rebote(
                r.get('detalle_error'), r.get('smtp_code'),
                r.get('dsn_status'), r.get('estado'),
            ),
            'smtp_code': r['smtp_code'] or '',
            'dsn_status': r['dsn_status'] or '',
            'fecha_envio': r['fecha_envio'].isoformat() if r.get('fecha_envio') else '',
            'tiene_message_id': bool(r.get('id_mensaje_enviado')),
            'message_id': r.get('id_mensaje_enviado') or '',
            'fecha': r['ultimo_evento_at'].isoformat() if r.get('ultimo_evento_at') else '',
            'radicado': r['correspondencia_salida__numero_radicado_salida'] or '',
            'salida_id': r.get('correspondencia_salida_id'),
            'redactor_nombre': r.get('correspondencia_salida__redactor_nombre') or '',
            'oficina_nombre': r.get('correspondencia_salida__oficina_emisora_nombre') or '',
            'verificacion_envio': _verificacion_envio_destinatario(
                r.get('estado'),
                r.get('fecha_envio'),
                r.get('id_mensaje_enviado'),
                r.get('detalle_error'),
            ),
        }
        for r in registros_raw
    ]

    import math
    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': math.ceil(total / page_size) if total else 0,
        'desde': desde.isoformat(),
        'hasta': hasta.isoformat(),
        'resumen_tipos': [
            {'tipo': t['estado'], 'total': t['total']}
            for t in resumen_tipos
        ],
        'resumen_oficinas': [
            {'oficina': o['correspondencia_salida__oficina_emisora_nombre'], 'total': o['total']}
            for o in resumen_oficinas
        ],
        'registros': registros,
    })


# ─── DESPLIEGUE DE OFICINAS (ROLLOUT) ────────────────────────────────────────

MESES_INACTIVIDAD_DEFAULT = 3
LIDER_GRUPO_NOMBRE = 'Lider de Oficina'


def _meses_inactivos_param(request):
    try:
        meses = int(request.GET.get('meses', MESES_INACTIVIDAD_DEFAULT))
    except (TypeError, ValueError):
        meses = MESES_INACTIVIDAD_DEFAULT
    return max(1, min(meses, 24))


def _iso_dt(value):
    return value.isoformat() if value else None


def _estado_operativo_oficina(usuarios_activos, ultima_actividad, umbral):
    if usuarios_activos <= 0:
        return 'sin_usuarios'
    if not ultima_actividad or ultima_actividad < umbral:
        return 'inactiva'
    return 'operativa'


def _serializar_usuario_despliegue(user):
    grupos = list(user.groups.values_list('name', flat=True))
    nombre = (user.get_full_name() or '').strip() or user.username
    perfil = getattr(user, 'perfil', None)
    cargo = ''
    if perfil is not None:
        cargo = getattr(perfil, 'cargo', None) or ''
    return {
        'id': user.id,
        'username': user.username,
        'nombre': nombre,
        'cargo': cargo,
        'is_active': user.is_active,
        'es_lider': LIDER_GRUPO_NOMBRE in grupos,
        'last_login': _iso_dt(user.last_login),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_despliegue_oficinas(request):
    """
    GET /api/monitoreo/despliegue-oficinas/?meses=3&filtro=&q=&orden=&unidad_id=
    Panel de rollout: todas las oficinas con usuarios, actividad y visita manual.
    """
    from django.contrib.auth.models import User
    from documentos.models import OficinaProductora, DespliegueOficina

    meses = _meses_inactivos_param(request)
    ahora = timezone.now()
    umbral = ahora - timedelta(days=meses * 30)

    filtro = (request.GET.get('filtro') or '').strip().lower()
    busqueda = (request.GET.get('q') or '').strip().lower()
    orden = (request.GET.get('orden') or 'pendiente').strip().lower()
    unidad_id = request.GET.get('unidad_id')

    oficinas_qs = (
        OficinaProductora.objects
        .select_related('unidad_administrativa', 'proceso', 'despliegue')
        .annotate(
            usuarios_activos=Count(
                'perfilusuario',
                filter=Q(perfilusuario__user__is_active=True),
                distinct=True,
            ),
            usuarios_total=Count('perfilusuario', distinct=True),
            ultimo_login_activos=Max(
                'perfilusuario__user__last_login',
                filter=Q(perfilusuario__user__is_active=True),
            ),
        )
        .order_by('unidad_administrativa__nombre', 'nombre')
    )
    if unidad_id:
        try:
            oficinas_qs = oficinas_qs.filter(unidad_administrativa_id=int(unidad_id))
        except (TypeError, ValueError):
            pass

    actividad_corr = {
        row['oficina_destino_id']: row['ultima']
        for row in (
            Correspondencia.objects.filter(oficina_destino_id__isnull=False)
            .order_by()  # SQL Server: quitar Meta.ordering en agregados
            .values('oficina_destino_id')
            .annotate(ultima=Max('fecha_radicacion'))
        )
    }

    oficinas_con_lider = set(
        User.objects.filter(
            is_active=True,
            groups__name=LIDER_GRUPO_NOMBRE,
            perfil__oficina_id__isnull=False,
        ).values_list('perfil__oficina_id', flat=True)
    )

    usuarios_por_oficina = {}
    for user in (
        User.objects.filter(perfil__oficina_id__isnull=False)
        .select_related('perfil', 'perfil__oficina')
        .prefetch_related('groups')
        .order_by('-is_active', 'first_name', 'last_name', 'username')
    ):
        oid = user.perfil.oficina_id
        usuarios_por_oficina.setdefault(oid, []).append(_serializar_usuario_despliegue(user))

    usuarios_sin_oficina = [
        _serializar_usuario_despliegue(u)
        for u in User.objects.filter(is_active=True)
        .filter(Q(perfil__isnull=True) | Q(perfil__oficina__isnull=True))
        .select_related('perfil')
        .prefetch_related('groups')
        .order_by('username')[:50]
    ]

    items = []
    resumen = {
        'total_oficinas': 0,
        'operativa': 0,
        'sin_usuarios': 0,
        'inactiva': 0,
        'pendiente_visita': 0,
        'visitada': 0,
        'capacitada': 0,
        'sin_lider': 0,
        'sin_trd': 0,
    }

    for ofi in oficinas_qs:
        ultima_corr = actividad_corr.get(ofi.id)
        candidatos = [dt for dt in (ofi.ultimo_login_activos, ultima_corr) if dt]
        ultima_actividad = max(candidatos) if candidatos else None
        estado_operativo = _estado_operativo_oficina(
            ofi.usuarios_activos, ultima_actividad, umbral,
        )

        despliegue = getattr(ofi, 'despliegue', None)
        estado_visita = despliegue.estado_visita if despliegue else 'pendiente'
        tiene_lider = ofi.id in oficinas_con_lider
        tiene_trd = bool((ofi.codigo_trd_comunicacion_interna or '').strip()) or bool(
            (ofi.codigo or '').strip()
        )

        item = {
            'id': ofi.id,
            'nombre': ofi.nombre,
            'codigo': ofi.codigo or '',
            'unidad_id': ofi.unidad_administrativa_id,
            'unidad_nombre': ofi.unidad_administrativa.nombre if ofi.unidad_administrativa else '',
            'proceso_nombre': ofi.proceso.nombre if ofi.proceso else '',
            'usuarios_activos': ofi.usuarios_activos,
            'usuarios_total': ofi.usuarios_total,
            'tiene_lider': tiene_lider,
            'tiene_trd': tiene_trd,
            'estado_operativo': estado_operativo,
            'estado_visita': estado_visita,
            'fecha_visita': despliegue.fecha_visita.isoformat() if despliegue and despliegue.fecha_visita else None,
            'notas': (despliegue.notas if despliegue else '') or '',
            'ultimo_login_oficina': _iso_dt(ofi.ultimo_login_activos),
            'ultima_correspondencia': _iso_dt(ultima_corr),
            'ultima_actividad': _iso_dt(ultima_actividad),
            'usuarios': usuarios_por_oficina.get(ofi.id, []),
        }

        resumen['total_oficinas'] += 1
        resumen[estado_operativo] = resumen.get(estado_operativo, 0) + 1
        if estado_visita == 'pendiente':
            resumen['pendiente_visita'] += 1
        elif estado_visita == 'visitada':
            resumen['visitada'] += 1
        elif estado_visita == 'capacitada':
            resumen['capacitada'] += 1
        if not tiene_lider and ofi.usuarios_activos > 0:
            resumen['sin_lider'] += 1
        if not tiene_trd:
            resumen['sin_trd'] += 1

        if busqueda:
            haystack = ' '.join([
                item['nombre'],
                item['unidad_nombre'],
                item['proceso_nombre'],
                item['codigo'],
            ]).lower()
            if busqueda not in haystack:
                continue

        if filtro:
            if filtro == 'operativa' and estado_operativo != 'operativa':
                continue
            if filtro == 'sin_usuarios' and estado_operativo != 'sin_usuarios':
                continue
            if filtro == 'inactiva' and estado_operativo != 'inactiva':
                continue
            if filtro == 'pendiente_visita' and estado_visita != 'pendiente':
                continue
            if filtro == 'visitada' and estado_visita != 'visitada':
                continue
            if filtro == 'capacitada' and estado_visita != 'capacitada':
                continue
            if filtro == 'sin_lider' and (tiene_lider or ofi.usuarios_activos == 0):
                continue
            if filtro == 'sin_trd' and tiene_trd:
                continue
            if filtro == 'prioridad' and estado_operativo != 'sin_usuarios':
                continue

        items.append(item)

    prioridad = {'sin_usuarios': 0, 'inactiva': 1, 'operativa': 2}
    visita_prioridad = {'pendiente': 0, 'visitada': 1, 'capacitada': 2, 'no_aplica': 3}

    if orden == 'nombre':
        items.sort(key=lambda x: x['nombre'].lower())
    elif orden == 'usuarios_activos':
        items.sort(key=lambda x: (-x['usuarios_activos'], x['nombre'].lower()))
    elif orden == 'ultima_actividad':
        items.sort(key=lambda x: (x['ultima_actividad'] or '', x['nombre'].lower()))
    elif orden == 'unidad':
        items.sort(key=lambda x: (x['unidad_nombre'].lower(), x['nombre'].lower()))
    else:
        items.sort(key=lambda x: (
            visita_prioridad.get(x['estado_visita'], 9),
            prioridad.get(x['estado_operativo'], 9),
            x['nombre'].lower(),
        ))

    unidades = list(
        OficinaProductora.objects.filter(unidad_administrativa__isnull=False)
        .values('unidad_administrativa_id', 'unidad_administrativa__nombre')
        .distinct()
        .order_by('unidad_administrativa__nombre')
    )
    unidades_opts = [
        {'id': u['unidad_administrativa_id'], 'nombre': u['unidad_administrativa__nombre']}
        for u in unidades
    ]

    return Response({
        'meses_inactividad': meses,
        'umbral_actividad': umbral.isoformat(),
        'resumen': resumen,
        'unidades': unidades_opts,
        'usuarios_sin_oficina': usuarios_sin_oficina,
        'usuarios_sin_oficina_total': User.objects.filter(is_active=True).filter(
            Q(perfil__isnull=True) | Q(perfil__oficina__isnull=True)
        ).count(),
        'oficinas': items,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_despliegue_oficina_actualizar(request, oficina_id):
    """
    POST /api/monitoreo/despliegue-oficinas/<id>/
    Body: { estado_visita?, fecha_visita?, notas? }
    """
    from documentos.models import OficinaProductora, DespliegueOficina

    oficina = get_object_or_404(OficinaProductora, pk=oficina_id)
    payload = request.data if isinstance(request.data, dict) else {}

    despliegue, _created = DespliegueOficina.objects.get_or_create(oficina=oficina)

    estado_visita = payload.get('estado_visita')
    if estado_visita is not None:
        validos = {c[0] for c in DespliegueOficina.ESTADO_VISITA_CHOICES}
        if estado_visita not in validos:
            return Response(
                {'detail': f'estado_visita inválido. Valores: {sorted(validos)}'},
                status=400,
            )
        despliegue.estado_visita = estado_visita

    if 'fecha_visita' in payload:
        raw = payload.get('fecha_visita')
        if raw in (None, ''):
            despliegue.fecha_visita = None
        else:
            parsed = parse_date(str(raw))
            if not parsed:
                return Response({'detail': 'fecha_visita inválida (YYYY-MM-DD)'}, status=400)
            despliegue.fecha_visita = parsed

    if 'notas' in payload:
        despliegue.notas = str(payload.get('notas') or '')

    despliegue.actualizado_por = request.user
    despliegue.save()

    return Response({
        'id': oficina.id,
        'estado_visita': despliegue.estado_visita,
        'fecha_visita': despliegue.fecha_visita.isoformat() if despliegue.fecha_visita else None,
        'notas': despliegue.notas,
        'actualizado_en': despliegue.actualizado_en.isoformat(),
    })
