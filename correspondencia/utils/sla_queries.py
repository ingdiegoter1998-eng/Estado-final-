"""Consultas SLA compartidas con caché (evita bloquear workers Gunicorn en SQL Server)."""
from django.core.cache import cache
from django.db import connection

IDS_ENTRANTES_RESPUESTA_CACHE_KEY = 'sla:ids_entrantes_con_respuesta:v1'
IDS_ENTRANTES_RESPUESTA_CACHE_TTL = 300  # segundos


def _fetch_ids_entrantes_con_respuesta():
    # Django ORM con estado__in dispara planes de ~30-100s en SQL Server; raw SQL ~0.01s.
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT respuesta_a_id
            FROM correspondencia_correspondenciasalida WITH (NOLOCK)
            WHERE estado IN (%s, %s) AND respuesta_a_id IS NOT NULL
            GROUP BY respuesta_a_id
            """,
            ['APROBADA', 'ENVIADA'],
        )
        return [row[0] for row in cursor.fetchall()]


def ids_entrantes_con_respuesta():
    """IDs de entrantes con salida APROBADA/ENVIADA (cache 2 min)."""
    cached = cache.get(IDS_ENTRANTES_RESPUESTA_CACHE_KEY)
    if cached is not None:
        return cached
    ids = _fetch_ids_entrantes_con_respuesta()
    cache.set(IDS_ENTRANTES_RESPUESTA_CACHE_KEY, ids, IDS_ENTRANTES_RESPUESTA_CACHE_TTL)
    return ids


def invalidate_ids_entrantes_con_respuesta_cache():
    cache.delete(IDS_ENTRANTES_RESPUESTA_CACHE_KEY)


def refresh_ids_entrantes_con_respuesta_cache():
    """Recalcula y guarda en cache (para Celery Beat, evita cache frío en HTTP)."""
    ids = _fetch_ids_entrantes_con_respuesta()
    cache.set(IDS_ENTRANTES_RESPUESTA_CACHE_KEY, ids, IDS_ENTRANTES_RESPUESTA_CACHE_TTL)
    return len(ids)


def excluir_entrantes_con_respuesta(qs):
    return qs.exclude(pk__in=ids_entrantes_con_respuesta())
