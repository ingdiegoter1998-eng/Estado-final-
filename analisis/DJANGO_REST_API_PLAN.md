# 🔌 Plan de Integración - Django REST API

## OBJETIVO
Crear los endpoints REST en Django para que Next.js pueda consumir las funcionalidades del calendario de informes.

---

## 📦 DEPENDENCIAS DJANGO

```bash
pip install djangorestframework
pip install django-cors-headers
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'rest_framework',
    'corsheaders',
    'correspondencia',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    ...
]

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Next.js dev
    "https://tu-dominio-nextjs.com",  # Producción
]

CORS_ALLOW_CREDENTIALS = True  # Para cookies de sesión

# Session Cookie Settings (si Next.js está en diferente dominio)
SESSION_COOKIE_SAMESITE = 'None'  # Permite cross-site
SESSION_COOKIE_SECURE = True      # Solo HTTPS (en prod)

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

---

## 📝 SERIALIZERS

```python
# correspondencia/serializers.py
from rest_framework import serializers
from .models import InformeDiarioCorrespondencia, Correspondencia, FirmaRecibida

class InformeDiarioSerializer(serializers.ModelSerializer):
    tiene_archivo = serializers.SerializerMethodField()
    
    class Meta:
        model = InformeDiarioCorrespondencia
        fields = [
            'id', 'fecha', 'estado', 'total_correspondencias',
            'archivo_firmado', 'tiene_archivo', 'fecha_subida_firma'
        ]
    
    def get_tiene_archivo(self, obj):
        return bool(obj.archivo_firmado)


class CorrespondenciaListSerializer(serializers.ModelSerializer):
    remitente_nombre = serializers.CharField(source='remitente.__str__', read_only=True)
    destinatario_nombre = serializers.SerializerMethodField()
    tiene_firma = serializers.SerializerMethodField()
    requiere_firma = serializers.SerializerMethodField()
    
    class Meta:
        model = Correspondencia
        fields = [
            'id', 'numero_radicado', 'asunto', 'fecha_radicacion',
            'remitente_nombre', 'destinatario_nombre',
            'tiene_firma', 'requiere_firma'
        ]
    
    def get_destinatario_nombre(self, obj):
        if obj.usuario_destino_inicial:
            perfil = getattr(obj.usuario_destino_inicial, 'perfil', None)
            if perfil and perfil.oficina:
                return f"{perfil.oficina.nombre}"
            return obj.usuario_destino_inicial.get_full_name() or obj.usuario_destino_inicial.username
        elif obj.oficina_destino:
            return obj.oficina_destino.nombre
        return "Sin destino"
    
    def get_tiene_firma(self, obj):
        return hasattr(obj, 'firma_recibida') and obj.firma_recibida is not None
    
    def get_requiere_firma(self, obj):
        # Lógica para determinar si requiere firma
        # Ajustar según tu modelo
        return True  # Por defecto todas requieren


class DiaCalendarioSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    es_mes_actual = serializers.BooleanField()
    es_hoy = serializers.BooleanField()
    es_futuro = serializers.BooleanField()
    total_correspondencias = serializers.IntegerField()
    tiene_correspondencias = serializers.BooleanField()
    informe = InformeDiarioSerializer(allow_null=True)


class CalendarioMesSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    month_name = serializers.CharField()
    prev_month = serializers.IntegerField()
    prev_year = serializers.IntegerField()
    next_month = serializers.IntegerField()
    next_year = serializers.IntegerField()
    dias = DiaCalendarioSerializer(many=True)


class StatsFiremasSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    firmadas = serializers.IntegerField()
    pendientes = serializers.IntegerField()
    porcentaje = serializers.FloatField()


class HistorialDescargaSerializer(serializers.Serializer):
    usuario = serializers.CharField()
    fecha_descarga = serializers.DateTimeField()
    tipo_formato = serializers.CharField()


class DetalleInformeSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    informe = InformeDiarioSerializer()
    correspondencias = CorrespondenciaListSerializer(many=True)
    historial_descargas = HistorialDescargaSerializer(many=True)
    stats_firmas = StatsFiremasSerializer()


class SubirArchivoFirmadoSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    archivo_firmado = serializers.FileField()
    
    def validate_archivo_firmado(self, value):
        # Validar tipo
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                'Tipo de archivo no permitido. Use PDF, JPG o PNG.'
            )
        
        # Validar tamaño (10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                'El archivo excede el tamaño máximo de 10MB.'
            )
        
        return value


class GuardarFirmaSerializer(serializers.Serializer):
    correspondencia_id = serializers.IntegerField()
    firma_base64 = serializers.CharField()
    
    def validate_firma_base64(self, value):
        # Validar que sea un data URL válido
        if not value.startswith('data:image/png;base64,'):
            raise serializers.ValidationError('Formato de firma inválido.')
        return value
```

---

## 🔌 VIEWS (API)

```python
# correspondencia/api_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import models
import calendar
from datetime import date, timedelta
from .models import (
    InformeDiarioCorrespondencia, 
    Correspondencia, 
    FirmaRecibida,
    HistorialDescargaInforme
)
from .serializers import (
    CalendarioMesSerializer,
    DetalleInformeSerializer,
    SubirArchivoFirmadoSerializer,
    GuardarFirmaSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendario_mes_api(request):
    """
    GET /api/correspondencia/calendario/informes/?year=2026&month=2
    """
    # Verificar que el usuario esté en grupo Ventanilla
    if not request.user.groups.filter(name='Ventanilla').exists():
        return Response(
            {'error': 'No tienes permisos para acceder a esta funcionalidad'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Calcular primer y último día del mes
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Obtener correspondencias del mes
    correspondencias_por_dia = {}
    correspondencias_mes = Correspondencia.objects.filter(
        tipo_radicado='ENTRANTE',
        fecha_radicacion__date__gte=first_day,
        fecha_radicacion__date__lte=last_day
    ).values('fecha_radicacion__date').annotate(
        total=models.Count('id')
    ).order_by('fecha_radicacion__date')
    
    for item in correspondencias_mes:
        correspondencias_por_dia[item['fecha_radicacion__date']] = item['total']
    
    # Obtener informes del mes
    informes_mes = {
        informe.fecha: informe
        for informe in InformeDiarioCorrespondencia.objects.filter(
            fecha__gte=first_day,
            fecha__lte=last_day
        )
    }
    
    # Construir datos del calendario
    cal = calendar.Calendar(firstweekday=0)
    dias = []
    
    for semana in cal.monthdatescalendar(year, month):
        for dia in semana:
            dia_data = {
                'fecha': dia,
                'es_mes_actual': dia.month == month,
                'es_hoy': dia == today,
                'es_futuro': dia > today,
                'total_correspondencias': correspondencias_por_dia.get(dia, 0),
                'tiene_correspondencias': dia in correspondencias_por_dia,
                'informe': informes_mes.get(dia),
            }
            dias.append(dia_data)
    
    # Calcular mes anterior y siguiente
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    data = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'dias': dias,
    }
    
    serializer = CalendarioMesSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_dia_api(request, fecha_str):
    """
    GET /api/correspondencia/informes/dia/2026-02-17/
    """
    if not request.user.groups.filter(name='Ventanilla').exists():
        return Response(
            {'error': 'No tienes permisos'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from datetime import datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Fecha inválida'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Correspondencias del día
    correspondencias = Correspondencia.objects.filter(
        tipo_radicado='ENTRANTE',
        fecha_radicacion__date=fecha
    ).select_related(
        'remitente',
        'remitente__entidad_externa',
        'usuario_destino_inicial',
        'usuario_destino_inicial__perfil',
        'usuario_destino_inicial__perfil__oficina',
        'oficina_destino',
    ).prefetch_related('firma_recibida').order_by('fecha_radicacion')
    
    # Informe
    informe, created = InformeDiarioCorrespondencia.objects.get_or_create(
        fecha=fecha,
        defaults={'total_correspondencias': correspondencias.count()}
    )
    
    if not created and informe.total_correspondencias != correspondencias.count():
        informe.total_correspondencias = correspondencias.count()
        informe.save(update_fields=['total_correspondencias'])
    
    # Historial
    historial = HistorialDescargaInforme.objects.filter(
        informe=informe
    ).select_related('usuario').order_by('-fecha_descarga')[:10]
    
    historial_data = [
        {
            'usuario': h.usuario.get_full_name() or h.usuario.username,
            'fecha_descarga': h.fecha_descarga,
            'tipo_formato': h.formato or 'Excel'
        }
        for h in historial
    ]
    
    # Stats
    total = correspondencias.count()
    firmadas = sum(1 for c in correspondencias if hasattr(c, 'firma_recibida'))
    pendientes = total - firmadas
    porcentaje = (firmadas / total * 100) if total > 0 else 0
    
    data = {
        'fecha': fecha,
        'informe': informe,
        'correspondencias': correspondencias,
        'historial_descargas': historial_data,
        'stats_firmas': {
            'total': total,
            'firmadas': firmadas,
            'pendientes': pendientes,
            'porcentaje': round(porcentaje, 1)
        }
    }
    
    serializer = DetalleInformeSerializer(data)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subir_archivo_firmado_api(request):
    """
    POST /api/correspondencia/informes/subir-firmado/
    """
    if not request.user.groups.filter(name='Ventanilla').exists():
        return Response({'error': 'No tienes permisos'}, status=403)
    
    serializer = SubirArchivoFirmadoSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    fecha = serializer.validated_data['fecha']
    archivo = serializer.validated_data['archivo_firmado']
    
    informe, created = InformeDiarioCorrespondencia.objects.get_or_create(
        fecha=fecha,
        defaults={'total_correspondencias': 0}
    )
    
    # Eliminar archivo anterior si existe
    if informe.archivo_firmado:
        informe.archivo_firmado.delete(save=False)
    
    informe.archivo_firmado = archivo
    informe.estado = 'FIRMADO'
    informe.fecha_subida_firma = timezone.now()
    informe.subido_por = request.user
    informe.save()
    
    return Response({
        'success': True,
        'message': f'Archivo firmado subido correctamente para {fecha.strftime("%d/%m/%Y")}',
        'informe': InformeDiarioSerializer(informe).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def guardar_firma_api(request):
    """
    POST /api/correspondencia/firmas/guardar/
    """
    serializer = GuardarFirmaSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    correspondencia_id = serializer.validated_data['correspondencia_id']
    firma_base64 = serializer.validated_data['firma_base64']
    
    try:
        correspondencia = Correspondencia.objects.get(id=correspondencia_id)
    except Correspondencia.DoesNotExist:
        return Response({'error': 'Correspondencia no encontrada'}, status=404)
    
    # Crear o actualizar firma
    firma, created = FirmaRecibida.objects.update_or_create(
        correspondencia=correspondencia,
        defaults={
            'firma_imagen': firma_base64,
            'firmado_por': request.user,
        }
    )
    
    return Response({
        'success': True,
        'firma_id': firma.id,
        'correspondencia_id': correspondencia_id,
        'message': 'Firma guardada correctamente'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def descargar_excel_dia_api(request, fecha_str):
    """
    GET /api/correspondencia/informes/dia/2026-02-17/descargar/
    """
    if not request.user.groups.filter(name='Ventanilla').exists():
        return Response({'error': 'No tienes permisos'}, status=403)
    
    try:
        from datetime import datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Fecha inválida'}, status=400)
    
    # Aquí va tu lógica existente de generación de Excel
    # Importar tu función actual y reutilizarla
    from .views import generar_excel_informe_dia  # Ajustar según tu código
    
    response = generar_excel_informe_dia(request, fecha)
    
    # Registrar descarga
    informe, _ = InformeDiarioCorrespondencia.objects.get_or_create(
        fecha=fecha,
        defaults={'total_correspondencias': 0}
    )
    
    HistorialDescargaInforme.objects.create(
        informe=informe,
        usuario=request.user,
        formato='Excel'
    )
    
    return response
```

---

## 🔗 URLS

```python
# correspondencia/urls.py
from django.urls import path
from . import api_views

api_patterns = [
    path('calendario/informes/', api_views.calendario_mes_api, name='api_calendario_mes'),
    path('informes/dia/<str:fecha_str>/', api_views.detalle_dia_api, name='api_detalle_dia'),
    path('informes/dia/<str:fecha_str>/descargar/', api_views.descargar_excel_dia_api, name='api_descargar_excel'),
    path('informes/subir-firmado/', api_views.subir_archivo_firmado_api, name='api_subir_firmado'),
    path('firmas/guardar/', api_views.guardar_firma_api, name='api_guardar_firma'),
]

# Incluir en urlpatterns principales
urlpatterns = [
    # ... rutas existentes ...
    path('api/correspondencia/', include(api_patterns)),
]
```

---

## 🧪 TESTING DE ENDPOINTS

### Con curl

```bash
# 1. Calendario
curl -X GET "http://localhost:8000/api/correspondencia/calendario/informes/?year=2026&month=2" \
  -H "Cookie: sessionid=TU_SESSION_ID"

# 2. Detalle del día
curl -X GET "http://localhost:8000/api/correspondencia/informes/dia/2026-02-17/" \
  -H "Cookie: sessionid=TU_SESSION_ID"

# 3. Subir archivo
curl -X POST "http://localhost:8000/api/correspondencia/informes/subir-firmado/" \
  -H "Cookie: sessionid=TU_SESSION_ID" \
  -F "fecha=2026-02-17" \
  -F "archivo_firmado=@/ruta/al/archivo.pdf"

# 4. Guardar firma
curl -X POST "http://localhost:8000/api/correspondencia/firmas/guardar/" \
  -H "Cookie: sessionid=TU_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "correspondencia_id": 123,
    "firma_base64": "data:image/png;base64,iVBORw0KGgoAAAA..."
  }'

# 5. Descargar Excel
curl -X GET "http://localhost:8000/api/correspondencia/informes/dia/2026-02-17/descargar/" \
  -H "Cookie: sessionid=TU_SESSION_ID" \
  --output informe.xlsx
```

---

## ✅ CHECKLIST DE INTEGRACIÓN

- [ ] Instalar djangorestframework y django-cors-headers
- [ ] Configurar CORS en settings.py
- [ ] Configurar cookies de sesión (SAMESITE, SECURE)
- [ ] Crear serializers.py
- [ ] Crear api_views.py
- [ ] Configurar rutas en urls.py
- [ ] Probar endpoints con curl o Postman
- [ ] Verificar permisos (grupo Ventanilla)
- [ ] Verificar CORS desde Next.js
- [ ] Documentar API (opcional: drf-spectacular)

---

## 🚨 TROUBLESHOOTING

### Error: CORS blocked
```python
# Verificar en settings.py
CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
CORS_ALLOW_CREDENTIALS = True
```

### Error: Cookie no se envía
```python
# En Next.js
apiClient.defaults.withCredentials = true

# En Django
SESSION_COOKIE_SAMESITE = 'None'  # Solo si están en dominios diferentes
SESSION_COOKIE_SECURE = True      # En producción con HTTPS
```

### Error: 403 Forbidden
```python
# Verificar que el usuario esté autenticado y en grupo Ventanilla
if not request.user.groups.filter(name='Ventanilla').exists():
    return Response({'error': 'No autorizado'}, status=403)
```

---

**¡Con esto Django estará listo para ser consumido por Next.js! 🔥**
