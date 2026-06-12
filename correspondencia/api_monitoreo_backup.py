"""
API REST para el Tablero de Monitoreo Operativo.
Solo accesible por superusuarios.
"""
from datetime import timedelta
from django.db.models import (
    Count, Q, Avg, F, Case, When, IntegerField, CharField, Value,
    Subquery, OuterRef, Exists,
)
from django.db.models.functions import TruncDate, TruncHour, Coalesce
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response

from .models import (
    Correspondencia, CorrespondenciaSalida, SalidaDestinatario,
    CorreoEntrante, AdjuntoCorreoEntrante,
    DistribucionInternaUsuario, ComunicacionInterna,
    CorrespondenciaUrgencia, HistorialCorrespondencia, HistorialSalida,
    Notificacion, EstadoSincronizacionCorreos,
    ComunicacionInternaDistribucion,
)


class IsSuperUser(BasePermission):
    """Solo superusuarios pueden acceder al monitoreo."""
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


# ─── PULSO EN TIEMPO REAL ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_pulso(request):
    """
    GET /api/monitoreo/pulso/
    Métricas en tiempo real del sistema.
    """
    ahora = timezone.now()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    correos_hoy = CorreoEntrante.objects.filter(
        fecha_recibida_gmail__gte=hoy_inicio
    ).count()

    pendientes_radicar = CorreoEntrante.objects.filter(
        procesado=False, en_papelera=False
    ).count()

    radicados_hoy = Correspondencia.objects.filter(
        fecha_radicacion__gte=hoy_inicio
    ).count()

    respuestas_enviadas_hoy = CorrespondenciaSalida.objects.filter(
        estado='ENVIADA', fecha_envio__gte=hoy_inicio
    ).count()

    com_internas_hoy = ComunicacionInterna.objects.filter(
        fecha_creacion__gte=hoy_inicio
    ).count()

    urgencias_activas = CorrespondenciaUrgencia.objects.filter(
        estado__in=['PENDIENTE', 'EN_PROCESO']
    ).count()

    # Tiempo promedio de radicación (minutos) - últimos 7 días
    hace_7d = ahora - timedelta(days=7)
    from django.db.models import Avg as DjAvg
    avg_radicacion = (
        Correspondencia.objects
        .filter(
            fecha_radicacion__gte=hace_7d,
            correo_origen__isnull=False,
        )
        .annotate(
            delta_min=F('fecha_radicacion') - F('correo_origen__fecha_recibida_gmail')
        )
        .aggregate(avg=Avg('delta_min'))
    )
    avg_min = None
    if avg_radicacion['avg']:
        avg_min = round(avg_radicacion['avg'].total_seconds() / 60, 1)

    return Response({
        'correos_hoy': correos_hoy,
        'pendientes_radicar': pendientes_radicar,
        'radicados_hoy': radicados_hoy,
        'respuestas_enviadas_hoy': respuestas_enviadas_hoy,
        'com_internas_hoy': com_internas_hoy,
        'urgencias_activas': urgencias_activas,
        'avg_radicacion_min': avg_min,
        'timestamp': ahora.isoformat(),
    })


# ─── SEMÁFORO SLA ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_sla(request):
    """
    GET /api/monitoreo/sla/
    Desglose de estados SLA global.
    """
    ahora = timezone.now()
    hoy = ahora.date()

    base = Correspondencia.objects.filter(requiere_respuesta=True)

    resp_valida = CorrespondenciaSalida.objects.filter(
        respuesta_a=OuterRef('pk'),
        estado__in=['APROBADA', 'ENVIADA'],
    )

    sin_respuesta = base.exclude(Exists(resp_valida))
    con_respuesta = base.filter(Exists(resp_valida))

    # Vencidas (sin respuesta, fecha límite pasada)
    vencidas = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__lt=ahora,
    ).count()

    # Críticas (0-1 día)
    criticas = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__gte=ahora,
        fecha_limite_respuesta_persist__lte=ahora + timedelta(days=1),
    ).count()

    # Urgentes (1-4 días)
    urgentes = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__gt=ahora + timedelta(days=1),
        fecha_limite_respuesta_persist__lte=ahora + timedelta(days=4),
    ).count()

    # Próximas (4-10 días)
    proximas = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__gt=ahora + timedelta(days=4),
        fecha_limite_respuesta_persist__lte=ahora + timedelta(days=10),
    ).count()

    # En plazo (>10 días)
    en_plazo = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=False,
        fecha_limite_respuesta_persist__gt=ahora + timedelta(days=10),
    ).count()

    # Sin plazo asignado
    sin_plazo = sin_respuesta.filter(
        fecha_limite_respuesta_persist__isnull=True,
    ).count()

    # Respondidas a tiempo
    respondidas_a_tiempo = 0
    respondidas_fuera = 0
    for c in con_respuesta.filter(fecha_limite_respuesta_persist__isnull=False):
        resp = (CorrespondenciaSalida.objects
                .filter(respuesta_a=c, estado__in=['APROBADA', 'ENVIADA'])
                .order_by('-fecha_envio', '-fecha_aprobacion')
                .values_list('fecha_envio', 'fecha_aprobacion', 'fecha_creacion')
                .first())
        if resp:
            fecha_resp = resp[0] or resp[1] or resp[2]
            if fecha_resp and c.fecha_limite_respuesta_persist:
                if fecha_resp <= c.fecha_limite_respuesta_persist:
                    respondidas_a_tiempo += 1
                else:
                    respondidas_fuera += 1

    return Response({
        'vencidas': vencidas,
        'criticas': criticas,
        'urgentes': urgentes,
        'proximas': proximas,
        'en_plazo': en_plazo,
        'sin_plazo': sin_plazo,
        'respondidas_a_tiempo': respondidas_a_tiempo,
        'respondidas_fuera_plazo': respondidas_fuera,
        'total_requieren': base.count(),
    })


# ─── PIPELINE DE ENVÍO ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_envio(request):
    """
    GET /api/monitoreo/envio/
    Estado del pipeline de envío de correspondencia saliente.
    """
    ahora = timezone.now()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    estados = SalidaDestinatario.objects.values('estado').annotate(total=Count('id')).order_by()
    mapa = {e['estado']: e['total'] for e in estados}

    pendientes = mapa.get('PENDIENTE', 0)
    enviados_total = mapa.get('ENVIADO', 0)
    fallos = mapa.get('FALLO', 0)
    rebotes = mapa.get('REBOTE', 0)

    enviados_hoy = SalidaDestinatario.objects.filter(
        estado='ENVIADO', fecha_envio__gte=hoy_inicio
    ).count()

    total_intentados = enviados_total + fallos + rebotes
    tasa_entrega = round((enviados_total / total_intentados * 100), 1) if total_intentados else 100.0

    # Respuestas por estado
    resp_estados = CorrespondenciaSalida.objects.values('estado').annotate(total=Count('id')).order_by()
    resp_mapa = {e['estado']: e['total'] for e in resp_estados}

    # Últimos errores
    errores_recientes = list(
        SalidaDestinatario.objects.filter(
            estado__in=['FALLO', 'REBOTE']
        ).select_related('correspondencia_salida')
        .order_by('-ultimo_evento_at')[:15]
        .values(
            'id',
            'email_snapshot',
            'nombre_snapshot',
            'estado',
            'smtp_code',
            'dsn_status',
            'detalle_error',
            'ultimo_evento_at',
            'correspondencia_salida__numero_radicado_salida',
        )
    )

    return Response({
        'pipeline': {
            'pendientes': pendientes,
            'enviados_total': enviados_total,
            'enviados_hoy': enviados_hoy,
            'fallos': fallos,
            'rebotes': rebotes,
            'tasa_entrega': tasa_entrega,
        },
        'respuestas': {
            'borrador': resp_mapa.get('BORRADOR', 0),
            'pendiente_aprobacion': resp_mapa.get('PENDIENTE_APROBACION', 0),
            'aprobada': resp_mapa.get('APROBADA', 0),
            'rechazada': resp_mapa.get('RECHAZADA', 0),
            'enviada': resp_mapa.get('ENVIADA', 0),
            'error_envio': resp_mapa.get('ERROR_ENVIO', 0),
        },
        'errores_recientes': errores_recientes,
    })


# ─── SINCRONIZACIÓN IMAP ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_imap(request):
    """
    GET /api/monitoreo/imap/
    Estado de sincronización IMAP y tareas Celery.
    """
    try:
        sync = EstadoSincronizacionCorreos.objects.first()
        imap_data = {
            'estado': sync.estado if sync else 'UNKNOWN',
            'ultimo_inicio': sync.ultimo_inicio.isoformat() if sync and sync.ultimo_inicio else None,
            'ultimo_fin': sync.ultimo_fin.isoformat() if sync and sync.ultimo_fin else None,
            'ultimo_error': sync.ultimo_error if sync else None,
            'actualizado_en': sync.actualizado_en.isoformat() if sync and sync.actualizado_en else None,
        }
    except Exception:
        imap_data = {'estado': 'UNKNOWN', 'ultimo_inicio': None, 'ultimo_fin': None, 'ultimo_error': None, 'actualizado_en': None}

    # Ejecuciones recientes del panel de control
    from .models import EjecucionControlCorreos
    ejecuciones = list(
        EjecucionControlCorreos.objects
        .order_by('-creado_en')[:10]
        .values(
            'id', 'tipo_operacion', 'estado',
            'total_encontrados', 'total_nuevos', 'total_guardados',
            'total_errores', 'total_duplicados',
            'creado_en', 'iniciado_en', 'finalizado_en',
            'ejecutado_por__username',
        )
    )

    # Correos en papelera por motivo
    papelera = list(
        CorreoEntrante.objects.filter(en_papelera=True)
        .values('motivo_papelera')
        .annotate(total=Count('id'))
        .order_by()
    )

    revision_manual = CorreoEntrante.objects.filter(
        requiere_revision_manual=True, procesado=False
    ).count()

    return Response({
        'imap': imap_data,
        'ejecuciones': ejecuciones,
        'papelera': papelera,
        'revision_manual': revision_manual,
    })


# ─── DISTRIBUCIÓN Y LECTURA ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_distribucion(request):
    """
    GET /api/monitoreo/distribucion/
    Métricas de distribución interna y lectura.
    """
    sin_distribuir = Correspondencia.objects.filter(
        estado='RADICADA',
    ).annotate(
        n_dist=Count('distribuciones_internas')
    ).filter(n_dist=0).count()

    sin_leer = DistribucionInternaUsuario.objects.filter(leido=False).count()

    # Tasa de lectura por oficina
    from documentos.models import OficinaProductora
    oficinas = OficinaProductora.objects.all()
    lectura_por_oficina = []
    for ofi in oficinas:
        total = DistribucionInternaUsuario.objects.filter(
            correspondencia__oficina_destino=ofi
        ).count()
        leidos = DistribucionInternaUsuario.objects.filter(
            correspondencia__oficina_destino=ofi, leido=True
        ).count()
        if total > 0:
            lectura_por_oficina.append({
                'oficina': ofi.nombre,
                'total': total,
                'leidos': leidos,
                'tasa': round(leidos / total * 100, 1),
            })
    lectura_por_oficina.sort(key=lambda x: x['tasa'])

    # Top usuarios con más sin leer
    top_sin_leer = list(
        DistribucionInternaUsuario.objects.filter(leido=False)
        .values('usuario_asignado__username', 'usuario_asignado__first_name', 'usuario_asignado__last_name')
        .annotate(pendientes=Count('id'))
        .order_by('-pendientes')[:10]
    )

    return Response({
        'sin_distribuir': sin_distribuir,
        'sin_leer': sin_leer,
        'lectura_por_oficina': lectura_por_oficina,
        'top_sin_leer': top_sin_leer,
    })


# ─── COMUNICACIONES INTERNAS ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_internas(request):
    """
    GET /api/monitoreo/internas/
    Métricas de comunicaciones internas.
    """
    ahora = timezone.now()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    hace_7d = ahora - timedelta(days=7)

    hoy = ComunicacionInterna.objects.filter(fecha_creacion__gte=hoy_inicio).count()
    pendiente_aprobacion = ComunicacionInterna.objects.filter(estado='PENDIENTE_APROBACION').count()
    rechazadas_7d = ComunicacionInterna.objects.filter(estado='RECHAZADA', fecha_creacion__gte=hace_7d).count()

    sin_leer = ComunicacionInternaDistribucion.objects.filter(leido=False).count()

    por_tipo = list(
        ComunicacionInterna.objects
        .values('tipo_distribucion')
        .annotate(total=Count('id'))
        .order_by()
    )

    por_estado = list(
        ComunicacionInterna.objects
        .values('estado')
        .annotate(total=Count('id'))
        .order_by()
    )

    return Response({
        'creadas_hoy': hoy,
        'pendiente_aprobacion': pendiente_aprobacion,
        'rechazadas_7d': rechazadas_7d,
        'sin_leer': sin_leer,
        'por_tipo': por_tipo,
        'por_estado': por_estado,
    })


# ─── URGENCIAS ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_urgencias(request):
    """
    GET /api/monitoreo/urgencias/
    Estado de correspondencias de urgencia.
    """
    activas = list(
        CorrespondenciaUrgencia.objects.filter(
            estado__in=['PENDIENTE', 'EN_PROCESO']
        ).select_related('oficina_destino', 'usuario_asignado')
        .order_by('fecha_limite')[:20]
        .values(
            'id', 'radicado', 'estado', 'prioridad',
            'horas_limite', 'fecha_limite', 'fecha_radicacion',
            'horas_transcurridas',
            'oficina_destino__nombre',
            'usuario_asignado__username',
            'usuario_asignado__first_name',
        )
    )

    stats = CorrespondenciaUrgencia.objects.values('estado').annotate(total=Count('id')).order_by()
    mapa = {s['estado']: s['total'] for s in stats}

    return Response({
        'activas': activas,
        'totales': {
            'pendiente': mapa.get('PENDIENTE', 0),
            'en_proceso': mapa.get('EN_PROCESO', 0),
            'respondida': mapa.get('RESPONDIDA', 0),
            'vencida': mapa.get('VENCIDA', 0),
        },
    })


# ─── TENDENCIAS (GRÁFICAS) ──────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_tendencias(request):
    """
    GET /api/monitoreo/tendencias/?dias=30
    Series temporales para gráficas.
    """
    dias = int(request.GET.get('dias', 30))
    dias = min(dias, 90)  # máximo 90 días
    ahora = timezone.now()
    desde = ahora - timedelta(days=dias)

    # Entrantes por día
    entrantes = list(
        Correspondencia.objects
        .filter(fecha_radicacion__gte=desde)
        .annotate(dia=TruncDate('fecha_radicacion'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )

    # Salientes por día
    salientes = list(
        CorrespondenciaSalida.objects
        .filter(fecha_envio__gte=desde, estado='ENVIADA')
        .annotate(dia=TruncDate('fecha_envio'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )

    # Errores por día
    errores = list(
        SalidaDestinatario.objects
        .filter(ultimo_evento_at__gte=desde, estado__in=['FALLO', 'REBOTE'])
        .annotate(dia=TruncDate('ultimo_evento_at'))
        .values('dia')
        .annotate(
            fallos=Count('id', filter=Q(estado='FALLO')),
            rebotes=Count('id', filter=Q(estado='REBOTE')),
        )
        .order_by('dia')
    )

    # Correos recibidos por día
    correos = list(
        CorreoEntrante.objects
        .filter(fecha_recibida_gmail__gte=desde)
        .annotate(dia=TruncDate('fecha_recibida_gmail'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )

    # Distribución por oficina (top 10)
    por_oficina = list(
        Correspondencia.objects
        .filter(fecha_radicacion__gte=desde)
        .values('oficina_destino__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    # Origen radicación
    por_origen = list(
        Correspondencia.objects
        .filter(fecha_radicacion__gte=desde)
        .values('origen_radicacion')
        .annotate(total=Count('id'))
        .order_by()
    )

    # Top remitentes (entidades)
    top_entidades = list(
        Correspondencia.objects
        .filter(fecha_radicacion__gte=desde, remitente__entidad_externa__isnull=False)
        .values('remitente__entidad_externa__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    return Response({
        'dias': dias,
        'entrantes': entrantes,
        'salientes': salientes,
        'errores': errores,
        'correos': correos,
        'por_oficina': por_oficina,
        'por_origen': por_origen,
        'top_entidades': top_entidades,
    })


# ─── HISTORIAL DE ACTIVIDAD ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_actividad(request):
    """
    GET /api/monitoreo/actividad/?limit=50
    Timeline global de actividad reciente.
    """
    limit = min(int(request.GET.get('limit', 50)), 100)

    # Historial entrada
    hist_entrada = list(
        HistorialCorrespondencia.objects
        .order_by('-fecha_hora')[:limit]
        .values(
            'id', 'evento', 'descripcion', 'fecha_hora',
            'usuario__username', 'usuario__first_name',
            'correspondencia__numero_radicado',
        )
    )

    # Historial salida
    hist_salida = list(
        HistorialSalida.objects
        .order_by('-fecha_hora')[:limit]
        .values(
            'id', 'tipo_evento', 'descripcion', 'fecha_hora',
            'usuario__username', 'usuario__first_name',
            'correspondencia_salida__numero_radicado_salida',
        )
    )

    # Eventos por tipo (últimas 24h)
    hace_24h = timezone.now() - timedelta(hours=24)
    por_tipo = list(
        HistorialCorrespondencia.objects
        .filter(fecha_hora__gte=hace_24h)
        .values('evento')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return Response({
        'entrada': hist_entrada,
        'salida': hist_salida,
        'por_tipo_24h': por_tipo,
    })


# ─── NOTIFICACIONES DEL SISTEMA ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_monitoreo_notificaciones(request):
    """
    GET /api/monitoreo/notificaciones/
    Métricas de notificaciones del sistema.
    """
    ahora = timezone.now()
    hace_24h = ahora - timedelta(hours=24)

    no_leidas = Notificacion.objects.filter(leida=False).count()

    por_tipo = list(
        Notificacion.objects
        .values('tipo')
        .annotate(
            total=Count('id'),
            no_leidas=Count('id', filter=Q(leida=False)),
        )
        .order_by('-total')
    )

    # Tasa lectura últimas 24h
    total_24h = Notificacion.objects.filter(fecha_creacion__gte=hace_24h).count()
    leidas_24h = Notificacion.objects.filter(fecha_creacion__gte=hace_24h, leida=True).count()
    tasa = round(leidas_24h / total_24h * 100, 1) if total_24h else 0

    return Response({
        'no_leidas_total': no_leidas,
        'por_tipo': por_tipo,
        'tasa_lectura_24h': tasa,
        'total_24h': total_24h,
    })
