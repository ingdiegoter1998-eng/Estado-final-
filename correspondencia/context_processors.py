"""
Context processors para correspondencia
"""
from django.conf import settings
from django.core.cache import cache

from .models import (
    AsistenteDocumento,
    AsistenteChunk,
    CorrespondenciaUrgencia,
    CorreoEntrante,
)
from .services_chatbot import GeminiFlashService

CORREOS_PENDIENTES_CACHE_KEY = 'sidebar:correos_pendientes_count:v1'
CORREOS_PENDIENTES_CACHE_TTL = 60
CHATBOT_STATS_CACHE_KEY = 'sidebar:chatbot_stats:v1'
CHATBOT_STATS_CACHE_TTL = 300
GEMINI_CONFIGURED_CACHE_KEY = 'sidebar:gemini_configured:v1'
GEMINI_CONFIGURED_CACHE_TTL = 300


def monitoreo_chat_url(request):
    """URL del panel de monitoreo/chat (Next.js); vacío si no está configurado."""
    return {'monitoreo_chat_url': getattr(settings, 'MONITOREO_CHAT_URL', '') or ''}


def blocked_recipients_context(request):
    """Blocklist de buzones institucionales para modales de salida/respuesta."""
    from correspondencia.utils.blocked_recipients import (
        AVISO_UI_DESTINATARIOS,
        emails_destinatarios_bloqueados,
    )

    emails = sorted(emails_destinatarios_bloqueados())
    return {
        'blocked_recipient_emails': emails,
        'blocked_recipient_message': AVISO_UI_DESTINATARIOS,
    }


def outbound_attachments_limits(request):
    """Límites de adjuntos salientes para templates y validación cliente."""
    from correspondencia.utils.postmark_outbound import (
        envio_usara_postmark,
        postmark_attachments_limit_bytes,
        salida_adjuntos_upload_limit_bytes,
    )

    upload_bytes = salida_adjuntos_upload_limit_bytes()
    postmark_bytes = postmark_attachments_limit_bytes()
    return {
        'outbound_adjuntos_upload_bytes': upload_bytes,
        'outbound_adjuntos_upload_mb': upload_bytes // (1024 * 1024),
        'outbound_adjuntos_postmark_bytes': postmark_bytes,
        'outbound_adjuntos_postmark_mb': postmark_bytes // (1024 * 1024),
        'outbound_envio_usa_postmark': envio_usara_postmark(),
    }


def urgencias_pendientes(request):
    """
    Agrega contador de urgencias pendientes al contexto global.
    Solo para usuarios autenticados con oficina asignada.
    """
    if not request.user.is_authenticated:
        return {'urgencias_count': 0}
    
    try:
        oficina_id = request.user.perfil.oficina_id
    except AttributeError:
        return {'urgencias_count': 0}
    
    if not oficina_id:
        return {'urgencias_count': 0}

    cache_key = f'sidebar:urgencias_count:v1:{oficina_id}'
    count = cache.get(cache_key)
    if count is None:
        count = CorrespondenciaUrgencia.objects.filter(
            oficina_destino_id=oficina_id,
            estado__in=['PENDIENTE', 'EN_PROCESO'],
        ).count()
        cache.set(cache_key, count, CORREOS_PENDIENTES_CACHE_TTL)
    
    return {'urgencias_count': count}


def correos_pendientes_sidebar(request):
    """
    Agrega el número de correos pendientes (bandeja activa, sin radicar) para el badge del sidebar.
    Solo para usuarios del grupo Ventanilla; resto recibe 0.
    """
    if not request.user.is_authenticated:
        return {'correos_pendientes_count': 0}
    if not request.user.groups.filter(name='Ventanilla').exists():
        return {'correos_pendientes_count': 0}

    count = cache.get(CORREOS_PENDIENTES_CACHE_KEY)
    if count is None:
        count = CorreoEntrante.objects.filter(
            radicado_asociado__isnull=True,
            urgencia_asociada__isnull=True,
            en_papelera=False,
        ).count()
        cache.set(CORREOS_PENDIENTES_CACHE_KEY, count, CORREOS_PENDIENTES_CACHE_TTL)

    return {'correos_pendientes_count': count}


def _chatbot_stats():
    stats = cache.get(CHATBOT_STATS_CACHE_KEY)
    if stats is not None:
        return stats
    stats = {
        'documents_count': AsistenteDocumento.objects.filter(activo=True).count(),
        'chunks_count': AsistenteChunk.objects.count(),
    }
    cache.set(CHATBOT_STATS_CACHE_KEY, stats, CHATBOT_STATS_CACHE_TTL)
    return stats


def _gemini_configured_cached():
    configured = cache.get(GEMINI_CONFIGURED_CACHE_KEY)
    if configured is None:
        configured = GeminiFlashService().is_configured()
        cache.set(GEMINI_CONFIGURED_CACHE_KEY, configured, GEMINI_CONFIGURED_CACHE_TTL)
    return configured


def chatbot_global_context(request):
    """Inyecta contexto del chatbot IA en todas las páginas autenticadas."""
    if not request.user.is_authenticated:
        return {}
    stats = _chatbot_stats()
    return {
        # Las conversaciones se cargan vía API al abrir el modal (chatbot-mvp.js).
        'chatbot_conversations': [],
        'chatbot_documents_count': stats['documents_count'],
        'chatbot_chunks_count': stats['chunks_count'],
        'gemini_configured': _gemini_configured_cached(),
    }
