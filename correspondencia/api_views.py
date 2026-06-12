import base64
import calendar
import mimetypes
from datetime import datetime, date
from django.core.files.base import ContentFile
from django.db.models import Count
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response

from .models import (
    InformeDiarioCorrespondencia,
    Correspondencia,
    FirmaCorrespondencia,
    FirmaAuxiliarCorrespondencia,
    HistorialDescargaInforme,
    ComunicacionInterna,
    AnexoComunicacionInterna,
    HistorialComunicacionInterna,
)
from .serializers import (
    InformeDiarioSerializer,
    CorrespondenciaListSerializer,
    FirmaAuxiliarCorrespondenciaSerializer,
)


# Permiso custom para grupo Ventanilla
class IsVentanillaGroup(BasePermission):
    """
    Permiso que verifica si el usuario pertenece al grupo 'Ventanilla'
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Ventanilla').exists()


class CalendarioViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones del calendario de informes
    """
    permission_classes = [IsAuthenticated, IsVentanillaGroup]

    @action(detail=False, methods=['get'])
    def informes(self, request):
        """
        GET /api/calendario/informes/?year=2026&month=2

        Retorna los datos del calendario mensual con información de
        correspondencias e informes diarios.
        """
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))

        # Calcular rango de fechas del mes
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Obtener correspondencias agrupadas por día
        correspondencias_por_dia = Correspondencia.objects.filter(
            tipo_radicado='ENTRANTE',
            fecha_radicacion__date__gte=first_day,
            fecha_radicacion__date__lte=last_day
        ).values('fecha_radicacion__date').annotate(
            total=Count('id')
        ).order_by('fecha_radicacion__date')

        # Mapear correspondencias por fecha
        correspondencias_map = {
            item['fecha_radicacion__date']: item['total']
            for item in correspondencias_por_dia
        }

        # Obtener informes del mes
        informes = InformeDiarioCorrespondencia.objects.filter(
            fecha__gte=first_day, fecha__lte=last_day
        )
        informes_map = {inf.fecha: inf for inf in informes}

        # Generar estructura del calendario
        cal = calendar.Calendar(firstweekday=0)  # Lunes como primer día
        dias = []

        for dia in cal.itermonthdates(year, month):
            total_corr = correspondencias_map.get(dia, 0)
            informe = informes_map.get(dia)

            dia_data = {
                'fecha': dia.isoformat(),
                'es_mes_actual': dia.month == month,
                'es_hoy': dia == date.today(),
                'es_futuro': dia > date.today(),
                'total_correspondencias': total_corr,
                'tiene_correspondencias': total_corr > 0,
                'informe': InformeDiarioSerializer(informe).data if informe else None
            }
            dias.append(dia_data)

        # Calcular navegación entre meses
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        return Response({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
            'dias': dias
        })


class InformesViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones de informes diarios
    """
    permission_classes = [IsAuthenticated, IsVentanillaGroup]

    @action(detail=False, methods=['get'], url_path='dia/(?P<fecha>[^/.]+)')
    def detalle_dia(self, request, fecha=None):
        """
        GET /api/informes/dia/2026-02-17/

        Retorna el detalle completo de un día específico incluyendo
        correspondencias, estadísticas de firmas e historial de descargas.
        """
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener correspondencias del día con relaciones optimizadas
        correspondencias = Correspondencia.objects.filter(
            tipo_radicado='ENTRANTE',
            fecha_radicacion__date=fecha_obj
        ).select_related(
            'remitente',
            'remitente__entidad_externa',
            'usuario_destino_inicial',
            'usuario_destino_inicial__perfil',
            'oficina_destino',
            'firma_recibida'
        ).prefetch_related(
            'correo_origen',
            'firmas_auxiliares'
        ).order_by('fecha_radicacion')

        # Obtener o crear informe del día
        informe, created = InformeDiarioCorrespondencia.objects.get_or_create(
            fecha=fecha_obj,
            defaults={'total_correspondencias': correspondencias.count()}
        )

        # Actualizar total de correspondencias si ya existía
        if not created:
            informe.total_correspondencias = correspondencias.count()
            informe.save(update_fields=['total_correspondencias'])

        # Obtener historial de descargas (últimas 10)
        historial = HistorialDescargaInforme.objects.filter(
            informe=informe
        ).select_related('usuario').order_by('-fecha_descarga')[:10]

        # Calcular estadísticas de firmas
        total = correspondencias.count()
        firmadas = sum(
            1 for c in correspondencias
            if hasattr(c, 'firma_recibida') and c.firma_recibida is not None
        )
        pendientes = total - firmadas
        porcentaje = (firmadas / total * 100) if total > 0 else 0

        return Response({
            'fecha': fecha,
            'informe': InformeDiarioSerializer(informe).data,
            'correspondencias': CorrespondenciaListSerializer(
                correspondencias, many=True
            ).data,
            'historial_descargas': [{
                'usuario': h.usuario.get_full_name(),
                'fecha_descarga': h.fecha_descarga.isoformat(),
                'ip_address': h.ip_address
            } for h in historial],
            'stats_firmas': {
                'total': total,
                'firmadas': firmadas,
                'pendientes': pendientes,
                'porcentaje': round(porcentaje, 1)
            }
        })

    @action(detail=False, methods=['post'], url_path='subir-firmado')
    def subir_firmado(self, request):
        """
        POST /api/informes/subir-firmado/

        Sube un archivo firmado para un informe diario.
        Requiere: fecha (YYYY-MM-DD) y archivo_firmado (PDF/JPG/PNG)
        """
        fecha_str = request.data.get('fecha')
        archivo = request.FILES.get('archivo_firmado')

        # Validaciones básicas
        if not fecha_str or not archivo:
            return Response(
                {'error': 'Fecha y archivo son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar tipo MIME
        tipos_permitidos = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/jpg'
        ]
        if archivo.content_type not in tipos_permitidos:
            return Response(
                {'error': f'Tipo de archivo no permitido. Solo: PDF, JPG, PNG'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar tamaño (10MB)
        if archivo.size > 10 * 1024 * 1024:
            return Response(
                {'error': 'El archivo no debe superar 10MB'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener o crear informe
        informe, created = InformeDiarioCorrespondencia.objects.get_or_create(
            fecha=fecha_obj,
            defaults={'total_correspondencias': 0}
        )

        # Eliminar archivo previo si existe
        if informe.archivo_firmado:
            informe.archivo_firmado.delete(save=False)

        # Guardar nuevo archivo
        informe.archivo_firmado = archivo
        informe.estado = 'FIRMADO'
        informe.fecha_subida_firma = timezone.now()
        informe.subido_por = request.user
        informe.save()

        return Response({
            'success': True,
            'message': 'Archivo subido correctamente',
            'informe': InformeDiarioSerializer(informe).data
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVentanillaGroup])
def guardar_firma(request):
    """
    POST /api/firmas/guardar/

    Guarda la firma digital capturada mediante canvas para una correspondencia.

    Requiere:
    - correspondencia_id: ID de la correspondencia
    - firma_base64: Imagen en formato base64 (data:image/png;base64,...)
    - nombre_firmante: Nombre del funcionario que firma
    - cargo_firmante: Cargo (opcional)
    - observaciones: Notas adicionales (opcional)
    """
    correspondencia_id = request.data.get('correspondencia_id')
    firma_base64 = request.data.get('firma_base64')
    nombre_firmante = request.data.get('nombre_firmante', '')
    cargo_firmante = request.data.get('cargo_firmante', '')
    observaciones = request.data.get('observaciones', '')

    # Validaciones
    if not all([correspondencia_id, firma_base64]):
        return Response(
            {'error': 'correspondencia_id y firma_base64 son requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        correspondencia = Correspondencia.objects.get(id=correspondencia_id)
    except Correspondencia.DoesNotExist:
        return Response(
            {'error': 'Correspondencia no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Verificar que no tenga firma previa
    if hasattr(correspondencia, 'firma_recibida') and correspondencia.firma_recibida is not None:
        return Response(
            {'error': 'Esta correspondencia ya tiene una firma registrada'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Decodificar imagen base64
    try:
        if ',' in firma_base64:
            header, firma_data = firma_base64.split(',', 1)
        else:
            firma_data = firma_base64

        imagen_bytes = base64.b64decode(firma_data)
    except Exception as e:
        return Response(
            {'error': f'Error al decodificar imagen base64: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Obtener datos adicionales
    oficina_firmante = None
    if correspondencia.usuario_destino_inicial:
        try:
            oficina_firmante = correspondencia.usuario_destino_inicial.perfil.oficina
        except:
            pass

    ip_address = request.META.get('REMOTE_ADDR')

    # Crear registro de firma
    firma = FirmaCorrespondencia(
        correspondencia=correspondencia,
        nombre_firmante=nombre_firmante,
        cargo_firmante=cargo_firmante or None,
        oficina_firmante=oficina_firmante,
        firmado_por=correspondencia.usuario_destino_inicial,
        recolector=request.user,
        ip_address=ip_address,
        observaciones=observaciones or None
    )

    # Guardar imagen con nombre único
    filename = f"firma_{correspondencia_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
    firma.firma_imagen.save(filename, ContentFile(imagen_bytes), save=True)

    return Response({
        'success': True,
        'message': 'Firma guardada correctamente',
        'firma_id': firma.id,
        'correspondencia_id': correspondencia.id,
        'fecha_firma': firma.fecha_firma.strftime('%d/%m/%Y %H:%M')
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVentanillaGroup])
def guardar_firma_auxiliar(request):
    """
    POST /api/firmas/guardar-auxiliar/

    Guarda una firma auxiliar para una correspondencia existente.

    Requiere:
    - correspondencia_id: ID de la correspondencia
    - firma_base64: Imagen en formato base64
    - nombre_firmante: Nombre del firmante auxiliar
    - cargo_firmante: Cargo del firmante auxiliar
    """
    correspondencia_id = request.data.get('correspondencia_id')
    firma_base64 = request.data.get('firma_base64')
    nombre_firmante = (request.data.get('nombre_firmante') or '').strip()
    cargo_firmante = (request.data.get('cargo_firmante') or '').strip()

    if not correspondencia_id or not firma_base64:
        return Response(
            {'error': 'correspondencia_id y firma_base64 son requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not nombre_firmante or not cargo_firmante:
        return Response(
            {'error': 'nombre_firmante y cargo_firmante son requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        correspondencia = Correspondencia.objects.get(id=correspondencia_id)
    except Correspondencia.DoesNotExist:
        return Response(
            {'error': 'Correspondencia no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        if ',' in firma_base64:
            _, firma_data = firma_base64.split(',', 1)
        else:
            firma_data = firma_base64

        imagen_bytes = base64.b64decode(firma_data)
    except Exception as e:
        return Response(
            {'error': f'Error al decodificar imagen base64: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    ip_address = request.META.get('REMOTE_ADDR')

    firma_auxiliar = FirmaAuxiliarCorrespondencia(
        correspondencia=correspondencia,
        nombre_firmante=nombre_firmante,
        cargo_firmante=cargo_firmante,
        recolector=request.user,
        ip_address=ip_address,
    )

    filename = f"firma_auxiliar_{correspondencia_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
    firma_auxiliar.firma_imagen.save(filename, ContentFile(imagen_bytes), save=True)

    return Response({
        'success': True,
        'message': 'Firma auxiliar guardada correctamente',
        'firma_auxiliar': FirmaAuxiliarCorrespondenciaSerializer(firma_auxiliar).data,
    }, status=status.HTTP_201_CREATED)


# ─── Endpoints de Autenticación para Next.js ─────────────────────────────────

@api_view(['POST'])
@permission_classes([])  # Público - no requiere auth
def api_login(request):
    """
    POST /api/auth/login/

    Autentica un usuario de Django y retorna cookie de sesión.
    Requiere: { "username": "...", "password": "..." }
    """
    from django.contrib.auth import authenticate, login

    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response(
            {'error': 'Usuario y contraseña son requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {'error': 'Usuario o contraseña incorrectos'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'Esta cuenta está desactivada'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Crear sesión Django
    login(request, user)

    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.username,
            'is_staff': user.is_staff,
            'groups': list(user.groups.values_list('name', flat=True)),
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([])  # Público
def api_logout(request):
    """
    POST /api/auth/logout/
    Cierra la sesión Django del usuario.
    """
    from django.contrib.auth import logout
    logout(request)
    return Response({'success': True, 'message': 'Sesión cerrada'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """
    GET /api/auth/me/
    Retorna el usuario autenticado actualmente (verifica sesión activa).
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name() or user.username,
        'is_staff': user.is_staff,
        'groups': list(user.groups.values_list('name', flat=True)),
    })


# =============================================
# === API COMUNICACIONES INTERNAS (Visor) ===
# =============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_interna_documento_meta(request, pk):
    """
    GET /api/interna/<pk>/documento/
    Retorna metadata de la comunicación interna para el visor de documentos.
    """
    from .views import _usuario_puede_ver_comunicacion_interna
    from django.shortcuts import get_object_or_404

    obj = get_object_or_404(ComunicacionInterna, pk=pk)

    if not _usuario_puede_ver_comunicacion_interna(request.user, obj):
        return Response({'error': 'No tienes acceso a esta comunicación.'}, status=403)

    def _build_anexo_payload(anexo):
        content_type = mimetypes.guess_type(anexo.archivo.name or '')[0] or 'application/octet-stream'
        return {
            'id': anexo.pk,
            'nombre': anexo.nombre_original or 'Archivo',
            'fecha': anexo.fecha_carga.isoformat(),
            'content_type': content_type,
            'es_previsualizable': content_type == 'application/pdf' or content_type.startswith('image/'),
        }

    anexos = AnexoComunicacionInterna.objects.filter(comunicacion=obj).order_by('fecha_carga')
    historial = HistorialComunicacionInterna.objects.filter(comunicacion=obj).order_by('-fecha')[:10]

    return Response({
        'id': obj.pk,
        'radicado': obj.radicado or 'Sin radicar',
        'asunto': obj.asunto,
        'estado': obj.estado,
        'estado_display': obj.get_estado_display(),
        'tipo_distribucion': obj.tipo_distribucion,
        'tipo_distribucion_display': obj.get_tipo_distribucion_display() if obj.tipo_distribucion else '',
        'fecha_creacion': obj.fecha_creacion.isoformat(),
        'fecha_documento': obj.fecha_documento.isoformat() if obj.fecha_documento else None,
        'ciudad': obj.ciudad,
        'remitente': {
            'nombre': obj.remitente_nombre,
            'cargo': obj.remitente_cargo or '',
            'oficina': obj.remitente_oficina.nombre if obj.remitente_oficina else '',
        },
        'destinatario': {
            'oficina': obj.destinatario_oficina.nombre if obj.destinatario_oficina else '',
            'usuario': obj.destinatario_usuario.get_full_name() if obj.destinatario_usuario else '',
        },
        'cuerpo': obj.cuerpo,
        'tiene_pdf': bool(obj.archivo_generado),
        'tiene_firmado': bool(obj.archivo_firmado),
        'anexos': [_build_anexo_payload(a) for a in anexos],
        'historial': [
            {
                'evento': h.get_evento_display(),
                'fecha': h.fecha.isoformat(),
                'usuario': h.usuario.get_full_name() if h.usuario else '',
                'descripcion': h.descripcion or '',
            }
            for h in historial
        ],
    })


@xframe_options_sameorigin
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_interna_documento_pdf(request, pk):
    """
    GET /api/interna/<pk>/documento/pdf/
    Sirve el PDF de la comunicación interna inline (para visor embebido).
    Query param ?tipo=firmado para el archivo firmado.
    """
    from .views import _usuario_puede_ver_comunicacion_interna
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse as DjangoHttpResponse

    obj = get_object_or_404(ComunicacionInterna, pk=pk)

    if not _usuario_puede_ver_comunicacion_interna(request.user, obj):
        return Response({'error': 'No tienes acceso a esta comunicación.'}, status=403)

    tipo = request.query_params.get('tipo', 'generado')
    archivo = obj.archivo_firmado if tipo == 'firmado' else obj.archivo_generado

    if not archivo:
        return Response({'error': 'El documento no ha sido generado.'}, status=404)

    response = DjangoHttpResponse(archivo, content_type='application/pdf')
    response['Content-Disposition'] = 'inline'
    response['Cache-Control'] = 'private, max-age=300'
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response


@xframe_options_sameorigin
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_interna_anexo_pdf(request, pk, anexo_id):
    """
    GET /api/interna/<pk>/documento/anexo/<anexo_id>/
    Sirve un anexo de la comunicación interna inline.
    """
    from .views import _usuario_puede_ver_comunicacion_interna
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse as DjangoHttpResponse
    obj = get_object_or_404(ComunicacionInterna, pk=pk)

    if not _usuario_puede_ver_comunicacion_interna(request.user, obj):
        return Response({'error': 'No tienes acceso a esta comunicación.'}, status=403)

    anexo = get_object_or_404(AnexoComunicacionInterna, pk=anexo_id, comunicacion=obj)

    if not anexo.archivo:
        return Response({'error': 'El anexo no tiene archivo.'}, status=404)

    content_type, _ = mimetypes.guess_type(anexo.archivo.name)
    content_type = content_type or 'application/octet-stream'

    response = DjangoHttpResponse(anexo.archivo, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{anexo.nombre_original or "anexo"}"'
    response['Cache-Control'] = 'private, max-age=300'
    response['X-Frame-Options'] = 'SAMEORIGIN'
    return response
