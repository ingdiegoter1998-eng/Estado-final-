"""Context processors para la app documentos."""
from django.core.cache import cache

PRESTAMOS_NUEVOS_CACHE_KEY = 'sidebar:prestamos_nuevos_count:v1'
PRESTAMOS_NUEVOS_CACHE_TTL = 60


def prestamos_nuevos_sidebar(request):
    """Contador de solicitudes de préstamo pendientes de gestión (sidebar)."""
    if not request.user.is_authenticated:
        return {'prestamos_nuevos_count': 0}

    from documentos.models import PrestamoDocumental

    count = cache.get(PRESTAMOS_NUEVOS_CACHE_KEY)
    if count is None:
        count = PrestamoDocumental.objects.filter(estado='SOLICITADO').count()
        cache.set(PRESTAMOS_NUEVOS_CACHE_KEY, count, PRESTAMOS_NUEVOS_CACHE_TTL)
    return {'prestamos_nuevos_count': count}
