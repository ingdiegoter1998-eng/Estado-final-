"""KPIs del dashboard ventanilla con caché Redis (reduce round-trips bajo concurrencia)."""
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from correspondencia.models import (
    CorreoEntrante,
    Correspondencia,
    CorrespondenciaSalida,
)
from correspondencia.utils.sla_queries import ids_entrantes_con_respuesta

DASHBOARD_VENTANILLA_KPIS_CACHE_TTL = 90  # segundos


def _cache_key_for_day(day_start):
    day_label = day_start.astimezone(timezone.get_current_timezone()).strftime('%Y%m%d')
    return f'ventanilla:dashboard_kpis:v1:{day_label}'


def _fetch_ventanilla_dashboard_kpis(hoy_inicio, hoy_fin, ahora):
    entrantes_con_respuesta_ids = ids_entrantes_con_respuesta()
    qs_sla_pendiente = Correspondencia.objects.filter(
        tipo_radicado='ENTRANTE',
        requiere_respuesta=True,
    ).exclude(pk__in=entrantes_con_respuesta_ids)
    sla_limite_48h = ahora + timedelta(hours=48)
    sla_counts = qs_sla_pendiente.aggregate(
        vencido=Count(
            'pk',
            filter=Q(fecha_limite_respuesta_persist__lt=ahora),
        ),
        por_vencer=Count(
            'pk',
            filter=Q(
                fecha_limite_respuesta_persist__gte=ahora,
                fecha_limite_respuesta_persist__lte=sla_limite_48h,
            ),
        ),
    )

    kpi_pendientes_radicacion = CorreoEntrante.objects.filter(
        radicado_asociado__isnull=True,
        urgencia_asociada__isnull=True,
    ).count()
    kpi_radicados_hoy = Correspondencia.objects.filter(
        tipo_radicado='ENTRANTE',
        fecha_radicacion__gte=hoy_inicio,
        fecha_radicacion__lt=hoy_fin,
    ).count()
    correos_recibidos_hoy = CorreoEntrante.objects.filter(
        fecha_lectura_imap__gte=hoy_inicio,
        fecha_lectura_imap__lt=hoy_fin,
    ).count()
    respuestas_enviadas_hoy = CorrespondenciaSalida.objects.filter(
        fecha_creacion__gte=hoy_inicio,
        fecha_creacion__lt=hoy_fin,
        estado='ENVIADA',
    ).count()
    pendientes_distribucion = Correspondencia.objects.filter(
        tipo_radicado='ENTRANTE',
        oficina_destino__isnull=True,
    ).count()

    eficiencia_radicacion = 0
    if correos_recibidos_hoy > 0:
        eficiencia_radicacion = int((kpi_radicados_hoy / correos_recibidos_hoy) * 100)

    return {
        'kpi_pendientes_radicacion': kpi_pendientes_radicacion,
        'kpi_radicados_hoy': kpi_radicados_hoy,
        'kpi_sla_vencido': sla_counts['vencido'] or 0,
        'kpi_sla_por_vencer': sla_counts['por_vencer'] or 0,
        'correos_recibidos_hoy': correos_recibidos_hoy,
        'respuestas_enviadas_hoy': respuestas_enviadas_hoy,
        'pendientes_distribucion': pendientes_distribucion,
        'eficiencia_radicacion': eficiencia_radicacion,
    }


def get_ventanilla_dashboard_kpis():
    """KPIs cacheados 90s; la clave incluye el día para refrescar al cambiar de fecha."""
    ahora = timezone.now()
    hoy_inicio = ahora.astimezone(timezone.get_current_timezone()).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    hoy_fin = hoy_inicio + timedelta(days=1)
    cache_key = _cache_key_for_day(hoy_inicio)

    kpis = cache.get(cache_key)
    if kpis is None:
        kpis = _fetch_ventanilla_dashboard_kpis(hoy_inicio, hoy_fin, ahora)
        cache.set(cache_key, kpis, DASHBOARD_VENTANILLA_KPIS_CACHE_TTL)
    return kpis


def invalidate_ventanilla_dashboard_kpis_cache():
    ahora = timezone.now()
    hoy_inicio = ahora.astimezone(timezone.get_current_timezone()).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    cache.delete(_cache_key_for_day(hoy_inicio))
