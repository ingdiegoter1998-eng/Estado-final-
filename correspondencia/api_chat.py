"""
API REST para el chat de soporte interno.
- Usuarios autenticados: CRUD de sus propias conversaciones / mensajes.
- Superusuarios: acceso a todas las conversaciones.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q, OuterRef, Subquery, Count, Max, F, Value, CharField
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework import status

from .chat_models import ChatConversation, ChatMessage, ChatAdjunto

User = get_user_model()

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def serialize_adjunto(adjunto):
    return {
        'id': adjunto.id,
        'url': adjunto.archivo.url,
        'nombre': adjunto.nombre_original,
    }


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


# ─── LISTAR CONVERSACIONES ───────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_chat_conversaciones(request):
    """
    GET /api/chat/conversaciones/
    - Usuarios normales: solo sus conversaciones.
    - Superusuarios: todas.
    Query params opcionales: ?estado=abierta|cerrada
    """
    qs = ChatConversation.objects.all()

    if not request.user.is_superuser:
        qs = qs.filter(usuario=request.user)

    estado = request.query_params.get('estado')
    if estado in ('abierta', 'cerrada'):
        qs = qs.filter(estado=estado)

    ultimo_mensaje = ChatMessage.objects.filter(
        conversacion=OuterRef('pk')
    ).order_by('-creado')

    qs = qs.annotate(
        total_mensajes=Count('mensajes'),
        no_leidos=Count(
            'mensajes',
            filter=Q(mensajes__leido=False) & (
                Q(mensajes__es_admin=True) if not request.user.is_superuser
                else Q(mensajes__es_admin=False)
            ),
        ),
        ultimo_texto=Subquery(ultimo_mensaje.values('texto')[:1]),
        ultimo_autor_es_admin=Subquery(ultimo_mensaje.values('es_admin')[:1]),
    )

    data = []
    for c in qs[:50]:
        data.append({
            'id': c.id,
            'asunto': c.asunto,
            'estado': c.estado,
            'prioridad': c.prioridad,
            'usuario': {
                'id': c.usuario_id,
                'nombre': c.usuario.get_full_name() or c.usuario.username,
            },
            'total_mensajes': c.total_mensajes,
            'no_leidos': c.no_leidos,
            'ultimo_texto': (c.ultimo_texto or '')[:100],
            'ultimo_autor_es_admin': c.ultimo_autor_es_admin,
            'creado': c.creado.isoformat(),
            'actualizado': c.actualizado.isoformat(),
        })

    return Response(data)


# ─── CREAR CONVERSACIÓN ──────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_chat_crear_conversacion(request):
    """
    POST /api/chat/conversaciones/crear/
    Body: { "asunto": "...", "mensaje": "...", "prioridad": "normal"|"urgente" }
    """
    asunto = (request.data.get('asunto') or '').strip()
    mensaje_texto = (request.data.get('mensaje') or '').strip()
    prioridad = request.data.get('prioridad', 'normal')

    if not asunto or not mensaje_texto:
        return Response(
            {'error': 'Se requiere asunto y mensaje.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if prioridad not in ('normal', 'urgente'):
        prioridad = 'normal'

    conv = ChatConversation.objects.create(
        usuario=request.user,
        asunto=asunto[:200],
        prioridad=prioridad,
    )
    ChatMessage.objects.create(
        conversacion=conv,
        autor=request.user,
        texto=mensaje_texto,
        es_admin=request.user.is_superuser,
        leido=False,
    )

    return Response({
        'id': conv.id,
        'asunto': conv.asunto,
        'estado': conv.estado,
        'creado': conv.creado.isoformat(),
    }, status=status.HTTP_201_CREATED)


# ─── MENSAJES DE UNA CONVERSACIÓN ────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_chat_mensajes(request, conversacion_id):
    """
    GET /api/chat/conversaciones/<id>/mensajes/
    Query params: ?despues=<iso_datetime>  (para polling incremental)
    """
    try:
        conv = ChatConversation.objects.get(pk=conversacion_id)
    except ChatConversation.DoesNotExist:
        return Response({'error': 'No encontrada.'}, status=404)

    if not request.user.is_superuser and conv.usuario_id != request.user.id:
        return Response({'error': 'Sin acceso.'}, status=403)

    qs = conv.mensajes.all()

    despues = request.query_params.get('despues')
    if despues:
        qs = qs.filter(creado__gt=despues)

    # Marcar como leídos los mensajes del otro lado
    if request.user.is_superuser:
        qs.filter(es_admin=False, leido=False).update(leido=True)
    else:
        qs.filter(es_admin=True, leido=False).update(leido=True)

    mensajes = []
    for m in qs[:200]:
        adjuntos = [serialize_adjunto(a) for a in m.adjuntos.all()]
        mensajes.append({
            'id': m.id,
            'texto': m.texto,
            'es_admin': m.es_admin,
            'autor': m.autor.get_full_name() or m.autor.username if m.autor else 'Sistema',
            'leido': m.leido,
            'creado': m.creado.isoformat(),
            'adjuntos': adjuntos,
        })

    return Response({
        'conversacion': {
            'id': conv.id,
            'asunto': conv.asunto,
            'estado': conv.estado,
            'prioridad': conv.prioridad,
            'usuario': {
                'id': conv.usuario_id,
                'nombre': conv.usuario.get_full_name() or conv.usuario.username,
            },
        },
        'mensajes': mensajes,
    })


# ─── ENVIAR MENSAJE ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def api_chat_enviar_mensaje(request, conversacion_id):
    """
    POST /api/chat/conversaciones/<id>/mensajes/enviar/
    Acepta multipart/form-data con:
      - texto: string
      - imagenes: archivos de imagen (hasta 5, max 5MB cada uno)
    También acepta JSON: { "texto": "..." }
    """
    try:
        conv = ChatConversation.objects.get(pk=conversacion_id)
    except ChatConversation.DoesNotExist:
        return Response({'error': 'No encontrada.'}, status=404)

    if not request.user.is_superuser and conv.usuario_id != request.user.id:
        return Response({'error': 'Sin acceso.'}, status=403)

    if conv.estado == 'cerrada':
        return Response(
            {'error': 'La conversación está cerrada.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    texto = (request.data.get('texto') or '').strip()
    archivos = request.FILES.getlist('imagenes')

    if not texto and not archivos:
        return Response(
            {'error': 'Se requiere texto o al menos una imagen.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validar archivos
    if len(archivos) > 5:
        return Response(
            {'error': 'Máximo 5 imágenes por mensaje.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    for f in archivos:
        if f.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                {'error': f'Tipo no permitido: {f.content_type}. Solo imágenes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if f.size > MAX_IMAGE_SIZE:
            return Response(
                {'error': f'"{f.name}" excede 5 MB.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    msg = ChatMessage.objects.create(
        conversacion=conv,
        autor=request.user,
        texto=texto,
        es_admin=request.user.is_superuser,
        leido=False,
    )

    adjuntos_data = []
    for f in archivos:
        adj = ChatAdjunto.objects.create(
            mensaje=msg,
            archivo=f,
            nombre_original=f.name[:255],
        )
        adjuntos_data.append(serialize_adjunto(adj))

    conv.save()  # actualiza 'actualizado'

    return Response({
        'id': msg.id,
        'texto': msg.texto,
        'es_admin': msg.es_admin,
        'autor': request.user.get_full_name() or request.user.username,
        'creado': msg.creado.isoformat(),
        'adjuntos': adjuntos_data,
    }, status=status.HTTP_201_CREATED)


# ─── CERRAR / REABRIR CONVERSACIÓN ───────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_chat_cambiar_estado(request, conversacion_id):
    """
    POST /api/chat/conversaciones/<id>/estado/
    Body: { "estado": "abierta"|"cerrada" }
    Solo superusuarios.
    """
    try:
        conv = ChatConversation.objects.get(pk=conversacion_id)
    except ChatConversation.DoesNotExist:
        return Response({'error': 'No encontrada.'}, status=404)

    nuevo_estado = request.data.get('estado')
    if nuevo_estado not in ('abierta', 'cerrada'):
        return Response(
            {'error': 'Estado inválido.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    conv.estado = nuevo_estado
    conv.save()
    return Response({'id': conv.id, 'estado': conv.estado})


# ─── RESUMEN PARA BADGE (ADMIN) ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_chat_resumen(request):
    """
    GET /api/chat/resumen/
    Retorna conteos para badges.
    """
    if request.user.is_superuser:
        abiertas = ChatConversation.objects.filter(estado='abierta').count()
        no_leidos = ChatMessage.objects.filter(
            leido=False, es_admin=False,
            conversacion__estado='abierta',
        ).count()
    else:
        abiertas = ChatConversation.objects.filter(
            usuario=request.user, estado='abierta',
        ).count()
        no_leidos = ChatMessage.objects.filter(
            leido=False, es_admin=True,
            conversacion__usuario=request.user,
            conversacion__estado='abierta',
        ).count()

    return Response({
        'abiertas': abiertas,
        'no_leidos': no_leidos,
    })


# ─── RESUMEN EXTENDIDO DE TICKETS ────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_chat_resumen_tickets(request):
    """
    GET /api/chat/resumen-tickets/
    Estadísticas extendidas para el panel admin.
    """
    total = ChatConversation.objects.count()
    abiertas = ChatConversation.objects.filter(estado='abierta').count()
    cerradas = ChatConversation.objects.filter(estado='cerrada').count()
    urgentes = ChatConversation.objects.filter(
        estado='abierta', prioridad='urgente'
    ).count()
    no_leidos = ChatMessage.objects.filter(
        leido=False, es_admin=False,
        conversacion__estado='abierta',
    ).count()

    # Últimas 24h
    hace_24h = timezone.now() - timezone.timedelta(hours=24)
    nuevos_hoy = ChatConversation.objects.filter(creado__gte=hace_24h).count()
    resueltos_hoy = ChatConversation.objects.filter(
        estado='cerrada', actualizado__gte=hace_24h
    ).count()

    return Response({
        'total': total,
        'abiertas': abiertas,
        'cerradas': cerradas,
        'urgentes': urgentes,
        'no_leidos': no_leidos,
        'nuevos_hoy': nuevos_hoy,
        'resueltos_hoy': resueltos_hoy,
    })


# ─── DIRECTORIO USUARIOS POR OFICINA ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_chat_directorio(request):
    """
    GET /api/chat/directorio/
    Lista usuarios activos agrupados por oficina.
    Query params: ?q=búsqueda  (busca en nombre/username/oficina)
    """
    from documentos.models import OficinaProductora, PerfilUsuario

    q = (request.query_params.get('q') or '').strip()

    perfiles = PerfilUsuario.objects.filter(
        user__is_active=True,
    ).select_related('user', 'oficina', 'oficina__unidad_administrativa')

    if q:
        perfiles = perfiles.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(oficina__nombre__icontains=q) |
            Q(cargo__icontains=q)
        )

    # Agrupar por oficina
    oficinas_dict = {}
    sin_oficina = []

    for p in perfiles:
        nombre = p.user.get_full_name() or p.user.username
        user_data = {
            'id': p.user.id,
            'username': p.user.username,
            'nombre': nombre,
            'cargo': p.cargo or '',
            'email': p.user.email or '',
            'is_superuser': p.user.is_superuser,
            'last_login': p.user.last_login.isoformat() if p.user.last_login else None,
        }

        if p.oficina:
            ofi_id = p.oficina.id
            if ofi_id not in oficinas_dict:
                oficinas_dict[ofi_id] = {
                    'id': ofi_id,
                    'nombre': p.oficina.nombre,
                    'codigo': p.oficina.codigo or '',
                    'unidad': p.oficina.unidad_administrativa.nombre if p.oficina.unidad_administrativa else '',
                    'usuarios': [],
                }
            oficinas_dict[ofi_id]['usuarios'].append(user_data)
        else:
            sin_oficina.append(user_data)

    oficinas = sorted(oficinas_dict.values(), key=lambda o: o['nombre'])

    # Agregar grupo "Sin oficina" si hay usuarios
    if sin_oficina:
        oficinas.append({
            'id': 0,
            'nombre': 'Sin oficina asignada',
            'codigo': '',
            'unidad': '',
            'usuarios': sin_oficina,
        })

    return Response({
        'oficinas': oficinas,
        'total_usuarios': sum(len(o['usuarios']) for o in oficinas),
        'total_oficinas': len(oficinas),
    })


# ─── DETALLE DE USUARIO ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_chat_usuario_detalle(request, user_id):
    """
    GET /api/chat/usuarios/<id>/
    Detalle de un usuario + historial de conversaciones con admin.
    """
    try:
        usuario = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Usuario no encontrado.'}, status=404)

    perfil = getattr(usuario, 'perfil', None)

    convs = ChatConversation.objects.filter(usuario=usuario).order_by('-actualizado')[:10]

    return Response({
        'id': usuario.id,
        'username': usuario.username,
        'nombre': usuario.get_full_name() or usuario.username,
        'email': usuario.email or '',
        'is_active': usuario.is_active,
        'is_superuser': usuario.is_superuser,
        'last_login': usuario.last_login.isoformat() if usuario.last_login else None,
        'date_joined': usuario.date_joined.isoformat(),
        'perfil': {
            'oficina': perfil.oficina.nombre if perfil and perfil.oficina else None,
            'cargo': perfil.cargo if perfil else None,
            'telefono': perfil.telefono if perfil else None,
        } if perfil else None,
        'conversaciones': [
            {
                'id': c.id,
                'asunto': c.asunto,
                'estado': c.estado,
                'prioridad': c.prioridad,
                'creado': c.creado.isoformat(),
                'actualizado': c.actualizado.isoformat(),
            }
            for c in convs
        ],
    })


# ─── NOTIFICACIONES ADMIN ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperUser])
def api_chat_notificaciones(request):
    """
    GET /api/chat/notificaciones/
    Últimas actividades para el panel de notificaciones del admin.
    """
    items = []

    # Conversaciones nuevas (últimas 24h)
    hace_24h = timezone.now() - timezone.timedelta(hours=24)
    convs_nuevas = ChatConversation.objects.filter(
        creado__gte=hace_24h
    ).select_related('usuario').order_by('-creado')[:15]

    for c in convs_nuevas:
        items.append({
            'tipo': 'nueva_conversacion',
            'texto': f'{c.usuario.get_full_name() or c.usuario.username} abrió: {c.asunto}',
            'prioridad': c.prioridad,
            'conversacion_id': c.id,
            'fecha': c.creado.isoformat(),
        })

    # Mensajes no leídos de usuarios
    msgs_no_leidos = ChatMessage.objects.filter(
        leido=False,
        es_admin=False,
        conversacion__estado='abierta',
    ).select_related(
        'autor', 'conversacion'
    ).order_by('-creado')[:20]

    for m in msgs_no_leidos:
        items.append({
            'tipo': 'mensaje_no_leido',
            'texto': f'{m.autor.get_full_name() or m.autor.username}: {(m.texto or "📷 Imagen")[:60]}',
            'conversacion_id': m.conversacion_id,
            'asunto': m.conversacion.asunto,
            'fecha': m.creado.isoformat(),
        })

    # Ordenar por fecha descendente
    items.sort(key=lambda x: x['fecha'], reverse=True)

    return Response({
        'items': items[:30],
        'total': len(items),
    })
