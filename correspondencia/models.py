from django.db import IntegrityError, models, transaction
from django.conf import settings
from django.utils import timezone
from documentos.models import OficinaProductora, SerieDocumental, SubserieDocumental, Proceso
import os # Necesario para os.path
import json
import re
from datetime import timedelta # Necesario para cálculos de fecha
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q

# =============================================================================
# CONSTANTES Y CHOICES PARA EL MÓDULO DE CORRESPONDENCIA
# =============================================================================

# Tipos de radicado disponibles
TIPO_RADICADO_CHOICES = [
    ('ENTRANTE', 'Entrante'),
    # ('CIRCULAR', 'Circular Interna'), # Descomentar si se añade en el futuro
]

# Medios de recepción de correspondencia
MEDIO_RECEPCION_CHOICES = [
    ('FISICO', 'Físico'),
    ('ELECTRONICO', 'Electrónico'),
]

# Medios de recibido (temporal, para radicación rápida)
MEDIO_RECIBIDO_CHOICES = [
    ('', '---------'),
    ('EMAIL', 'Email'),
    ('CORREO_CERTIFICADO', 'Correo certificado'),
    ('PERSONAL', 'Personal'),
]

# Origen de la radicación
ORIGEN_RADICACION_CHOICES = [
    ('NORMAL', 'Radicación Normal'),
    ('RAPIDA', 'Radicación Rápida'),
    ('CORREO', 'Desde Correo Electrónico'),
]

# Estado de la respuesta (solo para radicación rápida entrante; no mezclar con estados de correspondencia normal)
ESTADO_RESPUESTA_RAPIDA_CHOICES = [
    ('', '---------'),
    ('PENDIENTE', 'Pendiente'),
    ('RESPONDIDA', 'Respondida'),
    ('VENCIDA', 'Vencida'),
]

# Tipos de trámite para radicación rápida entrante
TIPO_TRAMITE_CHOICES = [
    ('', '---------'),
    ('PT', 'Petición (PT)'),
    ('PTA', 'Petición Anticipada (PTA)'),
    ('DM', 'Documento Médico (DM)'),
    ('HC', 'Historia Clínica (HC)'),
    ('CMC', 'Cita Médica/Consulta (CMC)'),
    ('PQRSF', 'PQRSF'),
    ('GLA', 'Queja/Reclamo (GLA)'),
    ('SD', 'Solicitud de Documentos (SD)'),
    ('AT', 'Asunto Técnico (AT)'),
    ('NA', 'No Aplica (NA)'),
]

# Días hábiles de respuesta según tipo de trámite
# Clave: código del tipo de trámite, Valor: días hábiles
DIAS_RESPUESTA_POR_TIPO_TRAMITE = {
    'PT': 15,      # Petición: 15 días hábiles
    'PTA': 4,      # Petición Anticipada: 4 días hábiles
    'DM': 5,       # Documento Médico: 5 días hábiles
    'HC': 3,       # Historia Clínica: 3 días hábiles
    'CMC': 2,      # Cita Médica/Consulta: 2 días hábiles
    'PQRSF': 15,   # PQRSF: 15 días hábiles
    'GLA': 15,     # Queja/Reclamo: 15 días hábiles
    'SD': 10,      # Solicitud de Documentos: 10 días hábiles
    'AT': 8,       # Asunto Técnico: 8 días hábiles
    'NA': None,    # No Aplica: sin plazo definido
}

# Estados del flujo de correspondencia entrante
ESTADOS_CORRESPONDENCIA = (
    ('RADICADA', 'Radicada'),
    ('ASIGNADA_USUARIO', 'Asignada a Usuario'),
    ('LEIDA', 'Leída por Oficina'),
    ('RESPONDIDA', 'Respondida'),
    # Añadir otros estados si existen en el modelo Correspondencia
)

# Eventos adicionales para el historial (incluye estados y acciones complementarias)
HISTORIAL_EVENTOS_CHOICES = ESTADOS_CORRESPONDENCIA + (
    ('SELLO_IMPRESO', 'Sello impreso'),
    ('REDISTRIBUIDA_INTERNA', 'Redistribuida internamente'),
    ('COMPARTIDA_OFICINA', 'Compartida con oficina'),
)

# Configuraciones de tiempo de respuesta estándar
TIEMPO_RESPUESTA_CHOICES = [
    ('1_DIA', '1 día hábil'),
    ('2_DIAS', '2 días hábiles'),
    ('MUY_URGENTE', 'Muy Urgente (3 días hábiles)'),
    ('URGENTE', 'Urgente (5 días hábiles)'),
    ('NORMAL', 'Normal (15 días hábiles)'),
]

# Origen del plazo calculado para trazabilidad
PLAZO_ORIGEN_CHOICES = (
    ('TRD', 'TRD (Trámite por Subserie)'),
    ('TIPO_TRAMITE', 'Tipo de Trámite'),
    ('PERSONALIZADO', 'Días Personalizados'),
    ('MANUAL', 'Fecha Manual'),
    ('FALLBACK', 'Configuración (Tiempo de Respuesta)'),
    ('NONE', 'No Aplica'),
)

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

DOMAIN_TOKEN_REGEX = re.compile(r'([a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,})')


def normalizar_dominio_correo(valor):
    """Normaliza un dominio o email a un dominio comparable."""
    if not valor:
        return ''

    dominio = str(valor).strip().lower()
    if '@' in dominio:
        dominio = dominio.split('@')[-1]

    dominio = dominio.strip(' .')
    if dominio.startswith('www.'):
        dominio = dominio[4:]

    try:
        dominio = dominio.encode('idna').decode('ascii')
    except Exception:
        pass

    return dominio


def extraer_dominios_candidatos(valor):
    """Extrae y normaliza dominios desde texto libre, dominios o emails."""
    if not valor:
        return []

    dominios = []
    texto = str(valor).replace(';', ' ').replace(',', ' ').replace('\n', ' ')
    for token in texto.split():
        coincidencias = DOMAIN_TOKEN_REGEX.findall(token)
        if not coincidencias:
            coincidencias = [token]

        for coincidencia in coincidencias:
            dominio = normalizar_dominio_correo(coincidencia)
            if dominio and dominio not in dominios:
                dominios.append(dominio)

    return dominios

def calcular_dias_habiles(fecha_inicio, dias_habiles):
    """
    Calcula la fecha límite sumando días hábiles (excluyendo sábados y domingos).
    
    Args:
        fecha_inicio: datetime.date o datetime.datetime de inicio
        dias_habiles: int, número de días hábiles a sumar
    
    Returns:
        datetime.date con la fecha límite calculada
    """
    from datetime import timedelta, date, datetime
    
    # Convertir datetime a date si es necesario
    if isinstance(fecha_inicio, datetime):
        fecha_actual = fecha_inicio.date()
    else:
        fecha_actual = fecha_inicio
    
    dias_agregados = 0
    
    while dias_agregados < dias_habiles:
        fecha_actual += timedelta(days=1)
        # Si no es sábado (5) ni domingo (6), contar el día
        if fecha_actual.weekday() < 5:
            dias_agregados += 1
    
    return fecha_actual

# =============================================================================
# MODELOS DE CONFIGURACIÓN
# =============================================================================

class TipoTramite(models.Model):
    """
    Tipo de trámite para radicación rápida con días de respuesta configurables.
    
    Permite administrar desde el panel de administración los tipos de trámite
    disponibles y sus tiempos de respuesta en días hábiles.
    """
    codigo = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Código",
        help_text="Código único del tipo de trámite (ej: PT, PTA, PQRSF)"
    )
    nombre = models.CharField(
        max_length=100, 
        verbose_name="Nombre",
        help_text="Nombre descriptivo del tipo de trámite"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción detallada del tipo de trámite (opcional)"
    )
    dias_respuesta = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Días Hábiles de Respuesta",
        help_text="Número de días hábiles para responder. Dejar vacío si no aplica plazo."
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Solo los tipos activos aparecen en los formularios"
    )
    orden = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
        help_text="Orden de aparición en los formularios (menor número = primera posición)"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        verbose_name = "Tipo de Trámite"
        verbose_name_plural = "Tipos de Trámite"
        ordering = ['orden', 'codigo']
        
    def __str__(self):
        if self.dias_respuesta:
            return f"{self.codigo} - {self.nombre} ({self.dias_respuesta} días)"
        return f"{self.codigo} - {self.nombre} (Sin plazo)"
    
    def get_choice_display(self):
        """Retorna el texto para usar en choices de formularios."""
        if self.dias_respuesta:
            return f"{self.nombre} ({self.codigo}) - {self.dias_respuesta} días"
        return f"{self.nombre} ({self.codigo})"

# === NUEVO MODELO ENTIDAD EXTERNA ===
class EntidadExterna(models.Model):
    """Representa una entidad externa (empresa, institución, etc.)."""
    nombre = models.CharField(max_length=255, unique=True, help_text="Nombre completo de la entidad externa")
    nit = models.CharField(max_length=20, blank=True, null=True, help_text="NIT o identificador fiscal (opcional)")
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    dominio = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Dominio de correo asociado (opcional)")

    # Otros campos que consideres necesarios (ciudad, etc.)

    class Meta:
        verbose_name = "Entidad Externa"
        verbose_name_plural = "Entidades Externas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.dominio = normalizar_dominio_correo(self.dominio) or None
        super().save(*args, **kwargs)

    def dominios_configurados(self):
        dominios = []
        if self.dominio:
            dominio_principal = normalizar_dominio_correo(self.dominio)
            if dominio_principal:
                dominios.append(dominio_principal)

        secundarios = self.dominios_secundarios.filter(activo=True).order_by('dominio')
        for item in secundarios:
            dominio_secundario = normalizar_dominio_correo(item.dominio)
            if dominio_secundario and dominio_secundario not in dominios:
                dominios.append(dominio_secundario)

        return dominios

    def tiene_dominio_autorizado(self, dominio):
        dominio_normalizado = normalizar_dominio_correo(dominio)
        return bool(dominio_normalizado) and dominio_normalizado in self.dominios_configurados()

    def registrar_dominios(self, dominios):
        dominios_extraidos = extraer_dominios_candidatos(dominios)
        registrados = []
        conflictos = []

        for dominio in dominios_extraidos:
            if dominio == normalizar_dominio_correo(self.dominio):
                continue

            entidad_existente = EntidadExterna.buscar_por_dominio(dominio)
            if entidad_existente and entidad_existente.pk != self.pk:
                conflictos.append({
                    'dominio': dominio,
                    'entidad_id': entidad_existente.pk,
                    'entidad_nombre': entidad_existente.nombre,
                })
                continue

            dominio_obj, created = EntidadExternaDominio.objects.get_or_create(
                entidad_externa=self,
                dominio=dominio,
                defaults={'activo': True}
            )

            if not created and not dominio_obj.activo:
                dominio_obj.activo = True
                dominio_obj.save(update_fields=['activo'])

            registrados.append(dominio)

        return {
            'registrados': registrados,
            'conflictos': conflictos,
        }

    @classmethod
    def buscar_por_dominio(cls, dominio):
        dominio_normalizado = normalizar_dominio_correo(dominio)
        if not dominio_normalizado:
            return None

        return cls.objects.filter(
            Q(dominio__iexact=dominio_normalizado) |
            Q(dominios_secundarios__dominio__iexact=dominio_normalizado, dominios_secundarios__activo=True)
        ).distinct().first()

    @classmethod
    def dominios_registrados(cls):
        dominios = []
        primarios = cls.objects.exclude(dominio__isnull=True).exclude(dominio='').values_list('dominio', flat=True)
        secundarios = EntidadExternaDominio.objects.filter(activo=True).values_list('dominio', flat=True)

        for valor in list(primarios) + list(secundarios):
            dominio = normalizar_dominio_correo(valor)
            if dominio and dominio not in dominios:
                dominios.append(dominio)

        return dominios

    @classmethod
    def get_entidad_por_defecto(cls):
        """Obtiene o crea la entidad por defecto 'Sin entidad'."""
        entidad, created = cls.objects.get_or_create(
            nombre="Sin entidad",
            defaults={
                'nit': None,
                'direccion': None,
                'telefono': None
            }
        )
        return entidad


class EntidadExternaDominio(models.Model):
    """Dominios adicionales autorizados para una entidad externa."""

    entidad_externa = models.ForeignKey(
        EntidadExterna,
        on_delete=models.CASCADE,
        related_name='dominios_secundarios',
        verbose_name='Entidad Externa'
    )
    dominio = models.CharField(max_length=120, unique=True, verbose_name='Dominio')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dominio autorizado de entidad'
        verbose_name_plural = 'Dominios autorizados de entidades'
        ordering = ['dominio']

    def __str__(self):
        return f"{self.dominio} -> {self.entidad_externa.nombre}"

    def save(self, *args, **kwargs):
        self.dominio = normalizar_dominio_correo(self.dominio)
        super().save(*args, **kwargs)

# === FIN MODELO ENTIDAD EXTERNA ===

# === MODELO CONTACTO MODIFICADO ===
class Contacto(models.Model):
    """Representa un contacto externo (persona) asociado a una EntidadExterna."""
    entidad_externa = models.ForeignKey(
        EntidadExterna,
        on_delete=models.PROTECT,  # Proteger para no borrar entidades con contactos asociados
        related_name='contactos',
        verbose_name="Entidad Externa",
        default=1  # Asumimos que la entidad "Sin entidad" tendrá ID 1
    )
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150, blank=True, null=True)
    cargo = models.CharField(max_length=150, blank=True, null=True, help_text="Cargo del contacto dentro de la entidad (opcional)")
    correo_electronico = models.EmailField(max_length=254, unique=True)
    telefono_contacto = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono del Contacto")
    numero_documento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de Documento",
        help_text="Cédula, pasaporte u otro documento de identificación (opcional)"
    )

    class Meta:
        verbose_name = "Contacto Externo"
        verbose_name_plural = "Contactos Externos"
        ordering = ['entidad_externa__nombre', 'apellidos', 'nombres']  # Ordenar por entidad, luego apellido

    @property
    def nombre_completo(self):
        if self.apellidos:
            return f"{self.nombres} {self.apellidos}"
        return self.nombres

    def __str__(self):
        # Mostrar Nombre (Entidad) - Correo si existe
        identificador = f" ({self.correo_electronico})" if self.correo_electronico else ""
        return f"{self.nombre_completo} ({self.entidad_externa.nombre}){identificador}"
    
    @property
    def nombre_entidad(self):
        """Devuelve solo el nombre completo y la entidad, sin correo electrónico."""
        return f"{self.nombre_completo}, {self.entidad_externa.nombre}"
    
    def clean(self):
        """Validaciones adicionales al guardar."""
        from django.core.exceptions import ValidationError
        if not self.correo_electronico:
            raise ValidationError("El correo electrónico es obligatorio para todos los contactos.")

        correo_normalizado = self.correo_electronico.strip().lower()
        if not correo_normalizado:
            raise ValidationError("El correo electrónico no puede estar vacío.")

        self.correo_electronico = correo_normalizado

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
# === FIN MODELO CONTACTO ===


# === MODELO AUDITORÍA DE CONTACTOS ===
TIPO_CAMBIO_CONTACTO_CHOICES = (
    ('CREACION', 'Creación'),
    ('EDICION', 'Edición'),
    ('ELIMINACION', 'Eliminación'),
)

class AuditoriaContacto(models.Model):
    """Registra cambios realizados sobre los contactos externos para trazabilidad."""
    contacto = models.ForeignKey(
        Contacto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditoria_cambios',
        help_text="Contacto afectado por el cambio"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias_contactos',
        help_text="Usuario que realizó el cambio"
    )
    tipo_cambio = models.CharField(
        max_length=20,
        choices=TIPO_CAMBIO_CONTACTO_CHOICES,
        default='EDICION'
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    campos_modificados = models.JSONField(
        default=dict,
        blank=True,
        help_text="Diccionario con campos modificados: {campo: {antes, despues}}"
    )
    contacto_nombre_snapshot = models.CharField(
        max_length=300,
        blank=True,
        help_text="Nombre del contacto al momento del cambio (para si se elimina)"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Auditoría de Contacto"
        verbose_name_plural = "Auditorías de Contactos"
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.contacto_nombre_snapshot} por {self.usuario} ({self.fecha_cambio:%Y-%m-%d %H:%M})"

    @classmethod
    def registrar_cambio(cls, contacto, usuario, tipo_cambio, campos_modificados=None, request=None):
        """Método helper para registrar un cambio de auditoría."""
        ip = None
        if request:
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
        
        return cls.objects.create(
            contacto=contacto,
            usuario=usuario,
            tipo_cambio=tipo_cambio,
            campos_modificados=campos_modificados or {},
            contacto_nombre_snapshot=contacto.nombre_completo if contacto else 'Desconocido',
            ip_address=ip,
        )
# === FIN MODELO AUDITORÍA DE CONTACTOS ===

class Correspondencia(models.Model):
    """
    Modelo principal para gestionar la correspondencia entrante del sistema.
    
    Este modelo centraliza toda la información relacionada con documentos
    que ingresan a la entidad, incluyendo su radicación, asignación, seguimiento
    y cálculo automático de plazos de respuesta (SLA).
    
    Características principales:
    - Generación automática de números de radicado
    - Cálculo y persistencia de plazos SLA basados en TRD o configuración
    - Trazabilidad completa del flujo de correspondencia
    - Integración con calendario laboral para cálculos de fechas límite
    
    Attributes:
        numero_radicado (str): Número único generado automáticamente
        tipo_radicado (str): Tipo de radicado (ENTRANTE, etc.)
        fecha_radicacion (datetime): Fecha y hora de radicación
        usuario_radicador (User): Usuario que realizó la radicación
        remitente (Contacto): Contacto externo que envió la correspondencia
        asunto (str): Descripción del contenido de la correspondencia
        medio_recepcion (str): Medio por el cual llegó (FISICO/ELECTRONICO)
        requiere_respuesta (bool): Indica si requiere respuesta
        tiempo_respuesta (str): Configuración de tiempo (NORMAL/URGENTE/MUY_URGENTE)
        oficina_destino (OficinaProductora): Oficina responsable de procesar
        serie/subserie (FK): Clasificación documental
        estado (str): Estado actual en el flujo de trabajo
        usuario_destino_inicial (User): Usuario asignado inicialmente
        leido_por_oficina (bool): Indica si fue leído por la oficina
        fecha_limite_respuesta (datetime): Fecha límite calculada dinámicamente
        plazo_respuesta_dias (int): Días hábiles persistidos para reportes
        fecha_limite_respuesta_persist (datetime): Fecha límite persistida
        plazo_origen (str): Origen del plazo (TRD/FALLBACK/NONE)
        tramite_aplicado (TramiteTipo): Trámite aplicado si hay TRD
    """
    
    # --- Campos de Radicación --- 
    numero_radicado = models.CharField(max_length=50, unique=True, editable=False)
    tipo_radicado = models.CharField(max_length=20, choices=TIPO_RADICADO_CHOICES, default='ENTRANTE')
    fecha_radicacion = models.DateTimeField(default=timezone.now, editable=False)
    usuario_radicador = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='correspondencia_radicada'
    )
    
    # --- Información del Documento (REEMPLAZAR remitente_externo) --- 
    # remitente_externo = models.CharField(max_length=255, help_text="Nombre de la persona o entidad externa que envía") # CAMPO ANTIGUO
    remitente = models.ForeignKey(
        Contacto, # Ahora se refiere al Contacto (persona)
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='correspondencias_enviadas',
        help_text="Seleccione el contacto (persona) que envía"
    )
    # Podríamos añadir opcionalmente una FK directa a EntidadExterna si queremos registrarla 
    # explícitamente en la correspondencia, aunque ya está implícita a través del Contacto.
    # entidad_remitente = models.ForeignKey(EntidadExterna, on_delete=models.SET_NULL, null=True, blank=True)
    asunto = models.TextField()
    serie = models.ForeignKey(SerieDocumental, on_delete=models.SET_NULL, null=True, blank=True)
    subserie = models.ForeignKey(SubserieDocumental, on_delete=models.SET_NULL, null=True, blank=True)
    medio_recepcion = models.CharField(
        max_length=50,
        choices=MEDIO_RECEPCION_CHOICES, 
        default='FISICO'
    )
    # Podríamos añadir un campo FileField aquí o un modelo relacionado para adjuntos más adelante
    # archivo_adjunto = models.FileField(upload_to='correspondencia_adjuntos/', null=True, blank=True)
    
    # --- Respuesta y Estado --- 
    requiere_respuesta = models.BooleanField(default=False)
    tiempo_respuesta = models.CharField(max_length=20, choices=TIEMPO_RESPUESTA_CHOICES, null=True, blank=True)
    dias_personalizados = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Días de respuesta personalizados (1-15). Si se especifica, tiene prioridad sobre tiempo_respuesta y TRD."
    )

    # --- Campos persistidos de SLA (denormalizados para reporte y trazabilidad) ---
    plazo_respuesta_dias = models.IntegerField(null=True, blank=True)
    fecha_limite_respuesta_persist = models.DateTimeField(null=True, blank=True)
    plazo_origen = models.CharField(max_length=20, choices=PLAZO_ORIGEN_CHOICES, default='NONE')
    # Guardamos el trámite aplicado si el origen fue TRD
    # Importación diferida para evitar import circular (se usa string de app_label.model_name)
    tramite_aplicado = models.ForeignKey('correspondencia.TramiteTipo', on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(
        max_length=50,
        choices=ESTADOS_CORRESPONDENCIA, # Usar la constante definida
        default='RADICADA'
    )
    leido_por_oficina = models.BooleanField(default=False, help_text="Indica si alguien de la oficina destino ya lo leyó")
    resumen_ia = models.TextField(blank=True, null=True, help_text="Resumen del contenido generado por IA")
    
    # --- Sello físico (radicado en papel) ---
    sellado = models.BooleanField(default=False, db_index=True, help_text="Indica si el documento físico ya fue sellado/imprimido")
    fecha_sellado = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora del primer sellado")
    
    # --- Control de Planillas ---
    en_planilla = models.BooleanField(default=False, db_index=True, help_text="Indica si esta correspondencia ya fue descargada e incluida en una planilla")
    
    # --- Distribución Inicial (Ventanilla) --- 
    oficina_destino = models.ForeignKey(
        OficinaProductora, 
        on_delete=models.PROTECT, # Evitar borrar oficinas con correspondencia pendiente?
        related_name='correspondencia_recibida'
    )
    usuario_destino_inicial = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='correspondencia_asignada_directa'
    )

    # --- Origen de la radicación ---
    origen_radicacion = models.CharField(
        max_length=20,
        choices=ORIGEN_RADICACION_CHOICES,
        default='NORMAL',
        db_index=True,
        help_text="Indica cómo fue radicada esta correspondencia"
    )

    # --- Campos temporales para radicación rápida (todos opcionales) ---
    fecha_recepcion_documento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que se recibió físicamente el documento (importante para calcular plazo de respuesta)"
    )
    tipo_tramite = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=TIPO_TRAMITE_CHOICES,
        help_text="Tipo de trámite (radicación rápida)"
    )
    entidad_persona_remitente = models.CharField(max_length=255, null=True, blank=True)
    funcionario_responsable_tramite = models.CharField(max_length=255, null=True, blank=True)
    email_funcionario_responsable = models.EmailField(
        max_length=254, null=True, blank=True,
        help_text="Correo electrónico del funcionario responsable del trámite"
    )
    clasificacion_comunicacion = models.CharField(max_length=255, null=True, blank=True)
    numero_folios = models.PositiveIntegerField(null=True, blank=True)
    anexos = models.CharField(max_length=500, null=True, blank=True)
    medio_recibido = models.CharField(max_length=50, null=True, blank=True, choices=MEDIO_RECIBIDO_CHOICES)
    direccion_correo_remitente = models.EmailField(max_length=254, null=True, blank=True)
    empresa_transportadora = models.CharField(max_length=255, null=True, blank=True)
    numero_guia = models.CharField(max_length=100, null=True, blank=True)
    fecha_limite_respuesta_manual = models.DateField(null=True, blank=True)
    fecha_primer_seguimiento = models.DateField(null=True, blank=True)
    fecha_segundo_seguimiento = models.DateField(null=True, blank=True)
    fecha_notificacion_vencimiento = models.DateField(null=True, blank=True)
    fecha_respuesta = models.DateField(null=True, blank=True)
    estado_respuesta = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=ESTADO_RESPUESTA_RAPIDA_CHOICES,
        help_text="Solo para radicación rápida: Pendiente, Respondida o Vencida."
    )
    radicado_enviado_respuesta = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "Correspondencia" # Nombre singular
        verbose_name_plural = "Correspondencias" # Nombre plural
        ordering = ['-fecha_radicacion'] # Ordenar por fecha descendente por defecto
        permissions = [
            (
                'responder_correspondencia_discrecional',
                'Puede responder discrecionalmente correspondencias que no requieren respuesta',
            ),
        ]

    def __str__(self):
        return f"{self.numero_radicado} - {self.asunto[:50]}..."

    def marcar_sellado(self):
        """Marca la correspondencia como sellada si aún no lo está y actualiza fecha.

        Reglas:
        - Requiere número de radicado existente.
        - Si ya estaba sellada, solo asegura que haya fecha.
        """
        if not self.numero_radicado:
            raise ValueError("No se puede sellar una correspondencia sin número de radicado.")
        now = timezone.now()
        if not self.sellado:
            self.sellado = True
            # Si no tiene fecha previa, registrar ahora
            if not self.fecha_sellado:
                self.fecha_sellado = now
        else:
            # Si ya estaba sellado pero no hay fecha (datos antiguos), registrar ahora
            if not self.fecha_sellado:
                self.fecha_sellado = now
        self.save(update_fields=['sellado', 'fecha_sellado'])

    def _datetime_desde_fecha_manual(self, fecha_manual):
        from datetime import datetime, time

        vencimiento = datetime.combine(fecha_manual, time(23, 59, 59))
        if timezone.is_naive(vencimiento):
            vencimiento = timezone.make_aware(vencimiento, timezone.get_default_timezone())
        return vencimiento

    def _resolver_plazo_dias_sla(self):
        """Resuelve días hábiles y origen según prioridad de negocio."""
        from .modelos_minimos_sla import SubserieTramite

        if self.dias_personalizados:
            return int(self.dias_personalizados), 'PERSONALIZADO', None

        if self.subserie_id:
            try:
                tramite = self.subserie.tramite_map.tramite  # type: ignore[attr-defined]
                return int(tramite.plazo_dias_habiles), 'TRD', tramite
            except (SubserieTramite.DoesNotExist, AttributeError):
                pass

        if self.tipo_tramite:
            try:
                tipo = TipoTramite.objects.get(codigo=self.tipo_tramite, activo=True)
                if tipo.dias_respuesta is not None:
                    return int(tipo.dias_respuesta), 'TIPO_TRAMITE', None
            except TipoTramite.DoesNotExist:
                pass

        mapping = {'NORMAL': 15, 'URGENTE': 5, 'MUY_URGENTE': 3}
        plazo = mapping.get(self.tiempo_respuesta or '')
        if plazo is not None:
            return plazo, 'FALLBACK', None

        return None, 'NONE', None

    # --- Propiedades Calculadas para Plazo de Respuesta ---
    @property
    def fecha_limite_respuesta(self):
        """Calcula la fecha límite de respuesta considerando días hábiles."""
        from .utils_sla import aplicar_corte, sumar_habiles

        fecha_inicio = self._fecha_inicio_terminos()
        if not self.requiere_respuesta or not fecha_inicio:
            return None

        if self.fecha_limite_respuesta_persist:
            return self.fecha_limite_respuesta_persist

        if self.fecha_limite_respuesta_manual:
            return self._datetime_desde_fecha_manual(self.fecha_limite_respuesta_manual)

        plazo_dias, _, _ = self._resolver_plazo_dias_sla()
        if plazo_dias is None:
            return None

        inicio = aplicar_corte(fecha_inicio)
        vencimiento = sumar_habiles(inicio, plazo_dias)
        if timezone.is_naive(vencimiento):
            vencimiento = timezone.make_aware(vencimiento, timezone.get_default_timezone())
        return vencimiento

    @property
    def dias_restantes(self):
        """Calcula los días restantes hasta la fecha límite. Negativo si ya pasó."""
        fecha_limite = self.fecha_limite_respuesta
        if not fecha_limite:
            return None
        
        hoy = timezone.now().date()
        # Necesitamos comparar solo las fechas
        fecha_limite_date = fecha_limite.date()
        
        # Calcular diferencia en días
        delta = fecha_limite_date - hoy
        
        # --- Lógica simple de días restantes --- 
        # return delta.days

        # --- Lógica Mejorada (contando días hábiles restantes) --- 
        # Si ya pasó la fecha, los días restantes son negativos (diferencia calendario)
        if delta.days < 0:
             return delta.days
             
        # Si no ha pasado, contar días hábiles entre hoy y la fecha límite (incluyendo hoy si es hábil?)
        dias_habiles_restantes = 0
        fecha_actual = hoy
        while fecha_actual <= fecha_limite_date:
             # Contar si no es sábado o domingo
             if fecha_actual.weekday() < 5:
                 dias_habiles_restantes += 1
             fecha_actual += timedelta(days=1)
             
        # Restamos 1 porque el bucle incluye el día de hoy, 
        # queremos los días que *faltan* sin contar hoy.
        # Si hoy es un día hábil, el resultado debe ser >= 0
        # Si hoy es fin de semana, el primer día hábil contará como 1 día restante.
        return max(0, dias_habiles_restantes -1) if hoy.weekday() < 5 else dias_habiles_restantes
        
    @property
    def estado_plazo(self):
        """Devuelve una cadena indicando el estado del plazo para usar en clases CSS, etc."""
        dias = self.dias_restantes
        if dias is None:
            return 'na' # No aplica o no requiere respuesta
        
        if dias < 0:
            return 'vencido' # Rojo Fuerte
        elif dias <= 1: # Último día o mañana
            return 'critico' # Rojo
        elif dias <= 4: # Urgente (2-4 días)
            return 'urgente' # Naranja
        elif dias <= 10: # Próximo (5-10 días)
            return 'proximo' # Amarillo
        else:
            return 'ok' # Verde o normal (> 10 días)
            
    # --- Fin Propiedades Calculadas ---

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para implementar lógica de negocio automática.
        
        Este método se ejecuta cada vez que se guarda una correspondencia y:
        1. Genera automáticamente el número de radicado para nuevos registros
        2. Recalcula y persiste los campos SLA (plazos y fechas límite)
        3. Aplica las reglas de negocio para determinar el origen del plazo
        
        Args:
            *args: Argumentos posicionales del método save original
            **kwargs: Argumentos nombrados del método save original
        """
        if not self.pk:  # Si es un objeto nuevo (no tiene Primary Key aún)
            # Si ya se asignó un número (ej. radicado manual desde formulario), no sobrescribir
            if not (self.numero_radicado and str(self.numero_radicado).strip()):
                self.numero_radicado = self._generar_numero_radicado()
        
        # Recalcular y persistir campos SLA antes de guardar definitivamente
        self._recalcular_sla_persistido()

        super().save(*args, **kwargs) # Llamar al método save original

    def _generar_numero_radicado(self):
        """Genera un número de radicado único basado en tipo y año."""
        from django.utils import timezone
        now = timezone.now()
        current_year = now.year
        tipo_prefijo = self.tipo_radicado # Ej: ENTRANTE
        
        # Buscar el último radicado de este tipo y año
        last_radicado = Correspondencia.objects.filter(
            tipo_radicado=self.tipo_radicado,
            fecha_radicacion__year=current_year
        ).order_by('fecha_radicacion').last() # Podría ser más eficiente ordenar por ID o radicado si el formato es consistente
        
        if last_radicado and last_radicado.numero_radicado:
            try:
                # Intentar extraer el último consecutivo
                parts = last_radicado.numero_radicado.split('-')
                last_consecutive = int(parts[-1])
                next_consecutive = last_consecutive + 1
            except (IndexError, ValueError):
                # Si el formato anterior es inesperado, empezar de 1
                next_consecutive = 1
        else:
            next_consecutive = 1
            
        # Formatear el nuevo número
        # Asegura 5 dígitos con ceros a la izquierda (ej: 00001, 00123, 12345)
        return f"{tipo_prefijo}-{current_year}-{next_consecutive:05d}"

    # ======================
    # LÓGICA SLA PERSISTENTE
    # ======================
    def _fecha_inicio_terminos(self):
        """Determina la fecha de inicio para el conteo de términos legales.

        Regla de negocio (Área Jurídica):
        - Si la correspondencia proviene de un correo electrónico, los términos
          se cuentan desde la fecha/hora de **recepción del correo**, no desde
          la fecha de radicación manual.  Esto es crítico para tutelas y otros
          documentos con plazos legales perentorios.
        - Se prioriza ``fecha_recepcion_original`` (encabezado Date del correo),
          luego ``fecha_recibida_gmail`` (INTERNALDATE), y finalmente
          ``fecha_lectura_imap`` como fallback.
        - Para correspondencia sin correo origen se usa ``fecha_radicacion``.

        Returns:
            datetime | None: La fecha desde la cual contar términos.
        """
        # Consulta explícita a BD para evitar problemas de caché del
        # reverse-manager cuando el objeto aún está en memoria tras el primer save().
        if not self.pk:
            return self.fecha_radicacion

        try:
            correo = CorreoEntrante.objects.filter(
                radicado_asociado_id=self.pk
            ).only(
                'fecha_recepcion_original',
                'fecha_recibida_gmail',
                'fecha_lectura_imap',
            ).first()
        except Exception:
            correo = None

        if correo is not None:
            # Priorizar la fecha más precisa del correo
            fecha_correo = (
                correo.fecha_recepcion_original
                or correo.fecha_recibida_gmail
                or correo.fecha_lectura_imap
            )
            if fecha_correo is not None:
                return fecha_correo

        # Fallback: fecha de radicación (correspondencia manual / física)
        return self.fecha_radicacion

    def _recalcular_sla_persistido(self) -> None:
        """
        Calcula y persiste en campos denormalizados el SLA (plazo y fecha límite).
        
        Este método implementa la lógica central de cálculo de plazos de respuesta
        siguiendo las reglas de negocio establecidas:
        
        Reglas de prioridad:
        1. Si no requiere respuesta: limpia todos los campos SLA y establece origen NONE
        2. Si hay fecha_limite_respuesta_manual: persiste esa fecha (origen MANUAL)
        3. Si hay dias_personalizados: usa ese plazo (origen PERSONALIZADO)
        4. Si hay TRD en la subserie: usa el plazo del trámite (origen TRD)
        5. Si hay tipo_tramite con días configurados: usa ese plazo (origen TIPO_TRAMITE)
        6. Si no, usa tiempo_respuesta como fallback (NORMAL/URGENTE/MUY_URGENTE)
        7. Si no hay plazo determinable: limpia campos SLA y establece origen NONE
        
        Los campos que se calculan y persisten son:
        - plazo_respuesta_dias: Número de días hábiles para respuesta
        - fecha_limite_respuesta_persist: Fecha límite calculada considerando calendario laboral
        - plazo_origen: Origen del plazo (TRD/FALLBACK/NONE)
        - tramite_aplicado: Referencia al trámite aplicado si existe TRD
        
        Este método se llama automáticamente en cada save() para mantener
        la consistencia de los datos SLA.
        """
        from .utils_sla import aplicar_corte, sumar_habiles

        if not self.requiere_respuesta:
            self.tiempo_respuesta = None
            self.plazo_respuesta_dias = None
            self.fecha_limite_respuesta_persist = None
            self.plazo_origen = 'NONE'
            self.tramite_aplicado = None
            return

        if self.fecha_limite_respuesta_manual:
            self.plazo_respuesta_dias = None
            self.fecha_limite_respuesta_persist = self._datetime_desde_fecha_manual(
                self.fecha_limite_respuesta_manual,
            )
            self.plazo_origen = 'MANUAL'
            self.tramite_aplicado = None
            return

        plazo_dias, plazo_origen, tramite = self._resolver_plazo_dias_sla()
        fecha_inicio = self._fecha_inicio_terminos()
        if plazo_dias is None or not fecha_inicio:
            self.plazo_respuesta_dias = None
            self.fecha_limite_respuesta_persist = None
            self.plazo_origen = 'NONE'
            self.tramite_aplicado = None
            return

        inicio = aplicar_corte(fecha_inicio)
        vencimiento = sumar_habiles(inicio, int(plazo_dias))
        if timezone.is_naive(vencimiento):
            vencimiento = timezone.make_aware(vencimiento, timezone.get_default_timezone())

        self.plazo_respuesta_dias = int(plazo_dias)
        self.fecha_limite_respuesta_persist = vencimiento
        self.plazo_origen = plazo_origen
        if tramite is not None:
            self.tramite_aplicado = tramite
            self.tiempo_respuesta = None
        else:
            self.tramite_aplicado = None

class HistorialCorrespondencia(models.Model):
    """Registra los eventos y cambios de estado de una correspondencia."""
    correspondencia = models.ForeignKey(
        Correspondencia, 
        on_delete=models.CASCADE, 
        related_name='historial'
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    # Usamos los mismos choices de estado para registrar el evento
    evento = models.CharField(max_length=30, choices=HISTORIAL_EVENTOS_CHOICES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, # Puede haber eventos sin usuario (ej: lectura automática IA?)
        related_name='acciones_correspondencia'
    )
    # Campo opcional para añadir detalles o notas sobre el evento
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Historial de Correspondencia"
        verbose_name_plural = "Historiales de Correspondencia"
        ordering = ['-fecha_hora'] # Mostrar el evento más reciente primero

    def __str__(self):
        user_display = f" por {self.usuario.username}" if self.usuario else ""
        return f"{self.correspondencia.numero_radicado} - {self.get_evento_display()}{user_display} el {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"


# === Señal para crear historial automáticamente al crear una correspondencia ===
@receiver(post_save, sender=Correspondencia)
def crear_historial_radicada(sender, instance: Correspondencia, created: bool, **kwargs):
    """Crea un registro en `HistorialCorrespondencia` al crear una correspondencia."""
    if created:
        try:
            HistorialCorrespondencia.objects.create(
                correspondencia=instance,
                evento='RADICADA',
                usuario=instance.usuario_radicador,
                descripcion='Radicación inicial creada automáticamente.'
            )
        except Exception:
            # Evitar que una falla de historial bloquee la creación
            pass

# === MODELO ADJUNTO CORRESPONDENCIA (Radicación Rápida) ===
def ruta_adjunto_correspondencia_rapida(instance, filename):
    """Genera la ruta donde se guardarán los adjuntos de correspondencia de radicación rápida."""
    # archivo va a /media/correspondencia/adjuntos_rapidos/<correspondencia_id>/<filename>
    correspondencia_id = instance.correspondencia.id if instance.correspondencia and instance.correspondencia.id else 'sin_asignar'
    return os.path.join('correspondencia', 'adjuntos_rapidos', str(correspondencia_id), filename)

class AdjuntoCorrespondenciaRapida(models.Model):
    """Representa un archivo adjunto (escaneo) asociado a una correspondencia de radicación rápida."""
    correspondencia = models.ForeignKey(
        Correspondencia,
        on_delete=models.CASCADE,
        related_name='adjuntos_rapidos'
    )
    archivo = models.FileField(
        upload_to=ruta_adjunto_correspondencia_rapida,
        max_length=255,
        help_text="Escaneo o documento adjunto de la correspondencia"
    )
    nombre_original = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nombre original del archivo"
    )
    tipo_mime = models.CharField(
        max_length=100,
        blank=True,
        help_text="Tipo MIME del archivo (ej: application/pdf, image/jpeg)"
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Adjunto de Correspondencia Rápida"
        verbose_name_plural = "Adjuntos de Correspondencia Rápida"
        ordering = ['-fecha_carga']
    
    def __str__(self):
        return self.nombre_original or os.path.basename(self.archivo.name) if self.archivo else "(Sin archivo)"
    
    def save(self, *args, **kwargs):
        # Guardar nombre original si no se proporcionó
        if not self.nombre_original and self.archivo and hasattr(self.archivo, 'name'):
            try:
                self.nombre_original = os.path.basename(self.archivo.name)
            except Exception:
                self.nombre_original = "adjunto_rapido"
        super().save(*args, **kwargs)

# --- ¿Modelo para Distribución a Oficina? --- 
# Si la distribución inicial solo va a UNA oficina, el campo `oficina_destino` 
# en `Correspondencia` podría ser suficiente. Si una correspondencia pudiera 
# distribuirse a MÚLTIPLES oficinas INICIALMENTE (poco común para entrante),
# necesitaríamos un modelo ManyToMany aquí.

# --- ¿Modelo para Redistribución Interna a Usuarios? ---
# Podríamos necesitar un modelo ManyToMany para rastrear a qué usuarios específicos
# dentro de la `oficina_destino` se les ha redistribuido.
# Ejemplo:
# class DistribucionInternaUsuario(models.Model):
#     correspondencia = models.ForeignKey(Correspondencia, on_delete=models.CASCADE)
#     usuario_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     fecha_asignacion = models.DateTimeField(default=timezone.now)
#     asignado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='asignaciones_realizadas', on_delete=models.SET_NULL, null=True)
#     leido = models.BooleanField(default=False)

# Por ahora, nos enfocaremos en añadir HistorialCorrespondencia.

# === NUEVO MODELO ADJUNTO CORREO ===
def ruta_adjunto_correo(instance, filename):
    """Genera la ruta donde se guardarán los adjuntos de correos."""
    # archivo va a /media/correspondencia/email_adjuntos/<correspondencia_id>/<filename>
    # Asegurarse que instance.correspondencia exista y tenga id
    correspondencia_id = instance.correspondencia.id if instance.correspondencia and instance.correspondencia.id else 'sin_asignar'
    return os.path.join('correspondencia', 'email_adjuntos', str(correspondencia_id), filename)

class AdjuntoCorreo(models.Model):
    """Representa un archivo adjunto asociado a una correspondencia electrónica."""
    correspondencia = models.ForeignKey(
        Correspondencia,
        on_delete=models.CASCADE, # Si se borra la correspondencia, se borran sus adjuntos
        related_name='adjuntos_correo'
    )
    archivo = models.FileField(
        upload_to=ruta_adjunto_correo,
        max_length=255 # Aumentar si nombres de archivo pueden ser muy largos
    )
    nombre_original = models.CharField(max_length=255, blank=True, help_text="Nombre original del archivo en el correo")
    tipo_mime = models.CharField(max_length=100, blank=True, help_text="Tipo MIME detectado del archivo")
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto de Correo"
        verbose_name_plural = "Adjuntos de Correo"
        ordering = ['-fecha_carga']

    def __str__(self):
        # Devolver solo el nombre del archivo
        return os.path.basename(self.archivo.name) if self.archivo else "(Sin archivo)"

    def save(self, *args, **kwargs):
        # Guardar nombre original si no se proporcionó
        if not self.nombre_original and self.archivo:
            # Asegurarse que el archivo tenga nombre antes de accederlo
            try:
                 self.nombre_original = os.path.basename(self.archivo.name)
            except Exception:
                 self.nombre_original = "archivo_desconocido"
        super().save(*args, **kwargs)

# === FIN MODELO ADJUNTO CORREO ===

# Motivos para enviar un correo entrante a papelera (excluir del flujo sin borrar; trazabilidad y retención)
MOTIVO_PAPELERA_CHOICES = [
    ('NO_APLICABLE', 'No aplicable (no es correspondencia institucional)'),
    ('NOTIFICACION_AUTOMATICA', 'Notificación automática (recibidos, avisos de sistema)'),
    ('INVITACION_PROMOCIONAL', 'Invitación o promocional'),
    ('SPAM', 'Spam o correo no deseado'),
    ('OTRO', 'Otro'),
]

# === NUEVO MODELO CORREO ENTRANTE (FASE 2) ===
class CorreoEntrante(models.Model):
    """Almacena temporalmente correos leídos de IMAP antes de procesarlos."""
    message_id = models.CharField(max_length=255, unique=True, help_text="Message-ID único del correo")
    remitente = models.EmailField()
    asunto = models.CharField(max_length=500, blank=True) # Aumentar longitud para asuntos largos
    cuerpo_texto = models.TextField(blank=True, help_text="Cuerpo del mensaje en texto plano")
    cuerpo_html = models.TextField(blank=True, help_text="Cuerpo del mensaje en HTML (si existe)")
    fecha_recepcion_original = models.DateTimeField(null=True, blank=True, help_text="Fecha del encabezado 'Date' del correo")
    fecha_recibida_gmail = models.DateTimeField(null=True, blank=True, help_text="Fecha INTERNALDATE registrada por Gmail/IMAP (recepción en servidor)")
    fecha_lectura_imap = models.DateTimeField(default=timezone.now)
    procesado = models.BooleanField(default=False, db_index=True, help_text="Indica si ya se intentó la clasificación IA")
    radicado_asociado = models.ForeignKey(
        'Correspondencia', # Usar string para evitar importación circular si Correspondencia está después
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='correo_origen',
        help_text="Correspondencia creada a partir de este correo (si aplica)"
    )
    urgencia_asociada = models.ForeignKey(
        'CorrespondenciaUrgencia',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='correo_origen',
        help_text="Urgencia creada a partir de este correo (si aplica)"
    )
    # Campo para marcar si necesita revisión humana
    requiere_revision_manual = models.BooleanField(default=False, help_text="Marcar si la radicación automática falló y necesita intervención.")
    
    # --- Papelera: excluir del flujo de radicación sin borrar (retención documental) ---
    en_papelera = models.BooleanField(default=False, db_index=True, help_text="En papelera: no se muestra en bandeja activa; se conserva para registro.")
    motivo_papelera = models.CharField(max_length=32, choices=MOTIVO_PAPELERA_CHOICES, blank=True, help_text="Motivo por el cual se envió a papelera.")
    fecha_papelera = models.DateTimeField(null=True, blank=True, help_text="Fecha en que se envió a papelera.")
    usuario_papelera = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='correos_enviados_papelera',
        help_text="Usuario que envió el correo a papelera."
    )
    
    # --- Campos para clasificación IA (sin tipo_clasificado) ---
    oficina_clasificada = models.ForeignKey(
        OficinaProductora,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='correos_clasificados_oficina', # Cambiado related_name para evitar conflicto
        help_text="Oficina destino predicha por IA"
    )
    serie_clasificada = models.ForeignKey(
        SerieDocumental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='correos_clasificados_serie',
        help_text="Serie documental predicha por IA"
    )
    subserie_clasificada = models.ForeignKey(
        SubserieDocumental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='correos_clasificados_subserie',
        help_text="Subserie documental predicha por IA (relacionada a la serie)"
    )
    fecha_clasificacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que se realizó la clasificación IA"
    )
    # --- Fin campos IA ---

    class Meta:
        verbose_name = "Correo Entrante IMAP"
        verbose_name_plural = "Correos Entrantes IMAP"
        ordering = ['-fecha_lectura_imap']

    def __str__(self):
        return f"De: {self.remitente} - Asunto: {self.asunto[:60]}... ({self.fecha_lectura_imap.strftime('%Y-%m-%d %H:%M')})"

    @staticmethod
    def _normalizar_content_id(value):
        if not value:
            return ''
        return str(value).strip().strip('<>').strip().lower()

    def obtener_cuerpo_html_renderizado(self):
        """Reemplaza referencias `cid:` por URLs locales de adjuntos cuando es posible."""
        cuerpo_html = self.cuerpo_html or ""
        if not cuerpo_html or 'cid:' not in cuerpo_html.lower():
            return cuerpo_html

        adjuntos = list(self.adjuntos.all())
        if not adjuntos:
            return cuerpo_html

        cid_pattern = re.compile(r'cid:(?P<cid>[^"\'\s>]+)', re.IGNORECASE)
        cid_to_url = {}
        filename_to_url = {}
        image_adjuntos = []

        for adjunto in adjuntos:
            if not adjunto.archivo:
                continue

            url = adjunto.archivo.url
            content_id_normalizado = self._normalizar_content_id(adjunto.content_id)
            if content_id_normalizado:
                cid_to_url[content_id_normalizado] = url

            nombre_archivo = (adjunto.nombre_original or os.path.basename(adjunto.archivo.name or '')).strip().lower()
            if nombre_archivo:
                filename_to_url[nombre_archivo] = url
                filename_to_url[os.path.basename(nombre_archivo)] = url

            if (adjunto.tipo_mime or '').lower().startswith('image/'):
                image_adjuntos.append(adjunto)

        def resolver_cid(raw_cid):
            cid_normalizado = self._normalizar_content_id(raw_cid)
            if not cid_normalizado:
                return ''

            if cid_normalizado in cid_to_url:
                return cid_to_url[cid_normalizado]

            if cid_normalizado in filename_to_url:
                return filename_to_url[cid_normalizado]

            base_cid = cid_normalizado.split('@', 1)[0]
            if base_cid in filename_to_url:
                return filename_to_url[base_cid]

            return ''

        cids_en_html = [match.group('cid') for match in cid_pattern.finditer(cuerpo_html)]
        cids_sin_resolver = {
            self._normalizar_content_id(cid)
            for cid in cids_en_html
            if not resolver_cid(cid)
        }

        if len(cids_sin_resolver) == 1 and len(image_adjuntos) == 1 and image_adjuntos[0].archivo:
            cid_to_url[next(iter(cids_sin_resolver))] = image_adjuntos[0].archivo.url

        def reemplazar(match):
            cid_original = match.group('cid')
            url = resolver_cid(cid_original)
            return url or match.group(0)

        return cid_pattern.sub(reemplazar, cuerpo_html)

# === FIN MODELO CORREO ENTRANTE ===


def ruta_respaldo_correo_problematico(instance, filename):
    """Genera la ruta donde se guardará el respaldo .eml del correo problemático."""
    problem_id = instance.id if instance and instance.id else 'sin_asignar'
    clean_filename = "".join([
        c for c in filename if c.isalpha() or c.isdigit() or c.isspace() or c in ['.', '-', '_']
    ]).rstrip()
    return os.path.join('correos_problematicos', 'eml', str(problem_id), clean_filename)


class CorreoProblematico(models.Model):
    """Correos detectados por IMAP que no entraron al flujo normal y requieren tratamiento aparte."""

    message_id = models.CharField(max_length=255, unique=True, help_text="Message-ID único del correo problemático")
    remitente = models.EmailField(blank=True)
    asunto = models.CharField(max_length=500, blank=True)
    cuerpo_texto = models.TextField(blank=True, help_text="Cuerpo en texto plano para revisión operativa")
    cuerpo_html = models.TextField(blank=True, help_text="Cuerpo HTML para revisión operativa")
    fecha_recepcion_original = models.DateTimeField(null=True, blank=True)
    fecha_recibida_gmail = models.DateTimeField(null=True, blank=True)
    fecha_lectura_imap = models.DateTimeField(default=timezone.now)
    carpeta_origen = models.CharField(max_length=128, blank=True, default='')
    flujo_origen = models.CharField(max_length=32, blank=True, default='')
    motivo_problema = models.CharField(max_length=64, default='VALIDACION_ADJUNTO')
    detalle_problema = models.TextField(blank=True, default='')
    adjuntos_resumen = models.TextField(blank=True, default='[]')
    respaldo_eml = models.FileField(
        upload_to=ruta_respaldo_correo_problematico,
        max_length=255,
        blank=True,
        null=True,
        help_text='Respaldo RFC822/.eml del correo original para permitir su admisión manual posterior.'
    )
    resuelto = models.BooleanField(default=False, db_index=True)
    fecha_resuelto = models.DateTimeField(null=True, blank=True)
    correo_entrante_asociado = models.ForeignKey(
        'CorreoEntrante',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='problemas_origen',
        help_text="Correo entrante creado posteriormente cuando el incidente se resolvió."
    )

    class Meta:
        verbose_name = "Correo Problemático"
        verbose_name_plural = "Correos Problemáticos"
        ordering = ['resuelto', '-fecha_recibida_gmail', '-fecha_lectura_imap']

    def __str__(self):
        estado = 'RESUELTO' if self.resuelto else 'PENDIENTE'
        return f"[{estado}] {self.remitente} - {self.asunto[:60]}"

    @property
    def adjuntos_resumen_list(self):
        try:
            data = json.loads(self.adjuntos_resumen or '[]')
        except Exception:
            return []
        return data if isinstance(data, list) else []


class EstadoSincronizacionCorreos(models.Model):
    """
    Estado resumido de la sincronización de correos entrantes (IMAP).

    Nota: esto NO depende de que hayan llegado correos nuevos. Sirve para saber
    cuándo corrió Celery por última vez, si fue exitoso y, si falló, ver el error.
    """

    ESTADO_CHOICES = [
        ('RUNNING', 'En ejecución'),
        ('SUCCESS', 'Exitosa'),
        ('FAIL', 'Fallida'),
    ]

    fuente = models.CharField(max_length=32, default='GMAIL_IMAP', help_text="Origen de la sincronización (ej: GMAIL_IMAP).")
    ultimo_inicio = models.DateTimeField(null=True, blank=True)
    ultimo_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=16, choices=ESTADO_CHOICES, default='SUCCESS')
    ultimo_error = models.TextField(blank=True, default='')
    ultimo_history_id = models.CharField(max_length=64, blank=True, default='')
    ultima_renovacion_watch = models.DateTimeField(null=True, blank=True)
    watch_expira_en = models.DateTimeField(null=True, blank=True)
    watch_topic = models.CharField(max_length=255, blank=True, default='')
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de Sincronización de Correos"
        verbose_name_plural = "Estado de Sincronización de Correos"

    def __str__(self):
        return f"{self.fuente}: {self.estado} (fin={self.ultimo_fin})"


class EjecucionControlCorreos(models.Model):
    """Bitácora de verificaciones, recuperaciones y diagnósticos operativos de correos."""

    TIPO_CHOICES = [
        ('VERIFY', 'Verificar cobertura Gmail vs BD'),
        ('RECOVER', 'Recuperar faltantes'),
        ('DUPLICATES', 'Verificar duplicados'),
        ('DIAGNOSE', 'Diagnóstico operativo'),
        ('IMAP_TEST', 'Probar conexión IMAP'),
        ('SYNC_NOW', 'Sincronización inmediata'),
        ('GMAIL_PUBSUB_PULL', 'Consumir Pub/Sub Gmail'),
        ('GMAIL_WATCH_RENEW', 'Renovar watch Gmail'),
        ('GMAIL_HISTORY_SYNC', 'Sincronizar history Gmail'),
        ('GMAIL_PIPELINE_TICK', 'Ciclo Gmail (watch + Pub/Sub)'),
        ('GMAIL_STATUS', 'Estado operativo Gmail API'),
    ]

    ESTADO_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('RUNNING', 'En ejecución'),
        ('SUCCESS', 'Exitosa'),
        ('WARN', 'Exitosa con advertencias'),
        ('FAIL', 'Fallida'),
    ]

    tipo_operacion = models.CharField(max_length=24, choices=TIPO_CHOICES)
    estado = models.CharField(max_length=16, choices=ESTADO_CHOICES, default='PENDING')
    ejecutado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ejecuciones_control_correos'
    )
    task_id = models.CharField(max_length=255, blank=True, default='')
    parametros = models.TextField(blank=True, default='{}')
    resumen = models.TextField(blank=True, default='{}')
    salida = models.TextField(blank=True, default='')
    error = models.TextField(blank=True, default='')

    total_encontrados = models.PositiveIntegerField(null=True, blank=True)
    total_nuevos = models.PositiveIntegerField(null=True, blank=True)
    total_guardados = models.PositiveIntegerField(null=True, blank=True)
    total_rechazados = models.PositiveIntegerField(null=True, blank=True)
    total_adjuntos = models.PositiveIntegerField(null=True, blank=True)
    total_duplicados = models.PositiveIntegerField(null=True, blank=True)
    total_sospechosos = models.PositiveIntegerField(null=True, blank=True)
    total_errores = models.PositiveIntegerField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    iniciado_en = models.DateTimeField(null=True, blank=True)
    finalizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Ejecución de Control de Correos'
        verbose_name_plural = 'Ejecuciones de Control de Correos'
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.get_tipo_operacion_display()} - {self.estado} - {self.creado_en:%Y-%m-%d %H:%M}"

# --- Función para ruta de adjuntos de CorreoEntrante ---
def ruta_adjunto_correo_entrante(instance, filename):
    """Genera la ruta donde se guardarán los adjuntos de correos entrantes."""
    # archivo va a /media/correos_entrantes/adjuntos/<correo_entrante_id>/<filename>
    correo_id = instance.correo_entrante.id if instance.correo_entrante and instance.correo_entrante.id else 'sin_asignar'
    # Limpiar nombre de archivo para evitar problemas de ruta
    clean_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c.isspace() or c in ['.','-','_']]).rstrip()
    return os.path.join('correos_entrantes', 'adjuntos', str(correo_id), clean_filename)

# --- NUEVO MODELO ADJUNTO CORREO ENTRANTE ---
class AdjuntoCorreoEntrante(models.Model):
    """Representa un archivo adjunto asociado a un CorreoEntrante."""
    correo_entrante = models.ForeignKey(
        CorreoEntrante,
        on_delete=models.CASCADE, # Si se borra el CorreoEntrante, se borran sus adjuntos
        related_name='adjuntos' # Nombre de relación simple
    )
    archivo = models.FileField(
        upload_to=ruta_adjunto_correo_entrante,
        max_length=255
    )
    nombre_original = models.CharField(max_length=255, blank=True, help_text="Nombre original del archivo en el correo")
    tipo_mime = models.CharField(max_length=100, blank=True, help_text="Tipo MIME detectado del archivo")
    content_id = models.CharField(max_length=255, blank=True, db_index=True, help_text="Content-ID del adjunto, útil para imágenes inline del HTML")
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto de Correo Entrante"
        verbose_name_plural = "Adjuntos de Correo Entrante"
        ordering = ['-fecha_carga']

    def __str__(self):
        return os.path.basename(self.archivo.name) if self.archivo else "(Sin archivo)"

    def save(self, *args, **kwargs):
        # Guardar nombre original si no se proporcionó y existe archivo
        if not self.nombre_original and self.archivo and hasattr(self.archivo, 'name'):
             try:
                 self.nombre_original = os.path.basename(self.archivo.name)
             except Exception:
                 self.nombre_original = "archivo_adjunto" # Fallback
        super().save(*args, **kwargs)
# === FIN MODELO ADJUNTO CORREO ENTRANTE ===

class DistribucionInternaUsuario(models.Model):
    """Modelo para rastrear la redistribución de correspondencia a usuarios específicos dentro de una oficina."""
    correspondencia = models.ForeignKey(Correspondencia, on_delete=models.CASCADE, related_name='distribuciones_internas')
    usuario_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='correspondencia_asignada')
    fecha_asignacion = models.DateTimeField(default=timezone.now)
    asignado_por = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='asignaciones_realizadas', on_delete=models.SET_NULL, null=True)
    leido = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora en que se marcó como leído")
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Distribución Interna"
        verbose_name_plural = "Distribuciones Internas"
        ordering = ['-fecha_asignacion']
        unique_together = ['correspondencia', 'usuario_asignado']

    def __str__(self):
        return f"{self.correspondencia.numero_radicado} -> {self.usuario_asignado.username}"


class AccesoCorrespondenciaOficina(models.Model):
    """
    Modelo que gestiona los accesos de solo lectura a la correspondencia para oficinas distintas a la destino.
    """
    correspondencia = models.ForeignKey(
        Correspondencia,
        on_delete=models.CASCADE,
        related_name='accesos_oficinas'
    )
    oficina = models.ForeignKey(
        OficinaProductora,
        on_delete=models.CASCADE,
        related_name='correspondencias_con_acceso'
    )
    compartido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accesos_interoficina_creados'
    )
    fecha_compartido = models.DateTimeField(default=timezone.now)
    observaciones = models.TextField(blank=True, null=True)
    leido = models.BooleanField(default=False, help_text="Indica si la oficina abrió por primera vez el detalle.")
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    solo_lider = models.BooleanField(
        default=True, 
        help_text="Si es True, solo los usuarios del grupo 'Lider' de la oficina podrán ver esto."
    )
    puede_responder = models.BooleanField(
        default=False, 
        help_text="Indica si esta oficina externa tiene permiso para generar respuestas."
    )

    class Meta:
        verbose_name = "Acceso de Oficina a Correspondencia"
        verbose_name_plural = "Accesos de Oficinas a Correspondencias"
        constraints = [
            models.UniqueConstraint(
                fields=['correspondencia', 'oficina'],
                name='unique_correspondencia_oficina_acceso'
            )
        ]
        ordering = ['-fecha_compartido']

    def __str__(self):
        return f"{self.correspondencia.numero_radicado} -> {self.oficina.nombre}"

    def marcar_leido(self):
        if not self.leido:
            self.leido = True
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['leido', 'fecha_lectura'])


class Notificacion(models.Model):
    """Modelo para notificaciones del usuario"""
    TIPO_CHOICES = [
        ('asignacion', 'Nueva Asignación'),
        ('compartido', 'Correspondencia Compartida'),
        ('respuesta', 'Nueva Respuesta'),
        ('vencimiento', 'Próximo a Vencer'),
        ('acceso_oficina', 'Acceso para otra oficina'),
        ('comunicacion_interna', 'Comunicación Interna'),
        ('aprobacion_pendiente', 'Aprobación Pendiente'),
        ('urgencia', 'Urgencia'),  # NUEVO: Tipo para notificaciones de urgencias
        ('rebote', 'Rebote de Envío'),
        ('otro', 'Otro'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES, default='asignacion')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    correspondencia = models.ForeignKey(Correspondencia, on_delete=models.CASCADE, null=True, blank=True, related_name='notificaciones')
    comunicacion_interna = models.ForeignKey(
        'ComunicacionInterna', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='notificaciones',
        help_text="Comunicación interna asociada (si aplica)"
    )
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    url = models.CharField(max_length=500, blank=True, null=True, help_text="URL de destino al hacer clic")
    
    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['usuario', 'leida', 'fecha_creacion']),
        ]
    
    def __str__(self):
        return f"{self.usuario.username} - {self.titulo}"
    
    def marcar_leida(self):
        """Marca la notificación como leída"""
        if not self.leida:
            self.leida = True
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['leida', 'fecha_lectura'])

# =============================================
# === MODELOS PARA CORRESPONDENCIA DE SALIDA ===
# =============================================

# Estados para CorrespondenciaSalida
ESTADOS_SALIDA = (
    ('BORRADOR', 'Borrador'),
    ('PENDIENTE_APROBACION', 'Pendiente Aprobación'),
    ('APROBADA', 'Aprobada'),
    ('RECHAZADA', 'Rechazada'),
    ('ENVIADA', 'Enviada'),
    ('ERROR_ENVIO', 'Error de Envío'),
)

TIPO_RESPUESTA_SALIDA_CHOICES = (
    ('OBLIGATORIA', 'Obligatoria'),
    ('DISCRECIONAL', 'Discrecional'),
)

class CorrespondenciaSalida(models.Model):
    """Representa una respuesta o comunicación de salida."""
    respuesta_a = models.ForeignKey(
        Correspondencia, 
        on_delete=models.PROTECT, # Proteger la entrada original
        related_name='respuestas_salientes',
        null=True,
        blank=True,
        help_text="Correspondencia entrante a la que responde este documento (opcional para salidas independientes)."
    )
    respuesta_a_urgencia = models.ForeignKey(
        'CorrespondenciaUrgencia',
        on_delete=models.PROTECT,
        related_name='respuestas_salientes',
        null=True,
        blank=True,
        help_text="Urgencia a la que responde este documento (opcional)."
    )
    numero_radicado_salida = models.CharField(max_length=50, unique=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario_redactor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='correspondencia_redactada'
    )
    fecha_ultima_modificacion = models.DateTimeField(auto_now=True)

    # Oficina emisora (derivada) y snapshots del redactor
    oficina_emisora = models.ForeignKey(
        OficinaProductora,
        on_delete=models.PROTECT,
        related_name='salidas_emitidas',
        editable=False,
        null=True,
        help_text="Oficina emisora de la correspondencia de salida (derivada de la entrante)"
    )
    oficina_emisora_nombre = models.CharField(max_length=255, null=True, blank=True, editable=False)
    redactor_nombre = models.CharField(max_length=255, null=True, blank=True, editable=False)
    redactor_cargo = models.CharField(max_length=255, null=True, blank=True, editable=False)

    # Destinatario (opcional para radicación rápida sin contacto registrado)
    destinatario_contacto = models.ForeignKey(
        Contacto, 
        on_delete=models.PROTECT, # Proteger al contacto 
        related_name='correspondencia_recibida_saliente',
        editable=False, # No editable en el formulario
        null=True,  # Permitir null para radicación rápida
        blank=True,
        help_text="Contacto externo al que se dirige la respuesta (automático o seleccionado)."
    )
    destinatario_email = models.EmailField(
        editable=False, # No editable, se llena al aprobar
        blank=True,
        default='',  # Default vacío para radicación rápida
        help_text="Email del destinatario al momento de la aprobación (automático)."
    )

    asunto = models.CharField(max_length=255)
    cuerpo = models.TextField()
    tipo_respuesta = models.CharField(
        max_length=20,
        choices=TIPO_RESPUESTA_SALIDA_CHOICES,
        default='OBLIGATORIA',
        help_text='Indica si la salida corresponde a una respuesta obligatoria o discrecional.'
    )
    motivo_respuesta_discrecional = models.TextField(
        blank=True,
        default='',
        help_text='Motivo obligatorio cuando la respuesta es discrecional.'
    )

    # Flujo de Aprobación y Envío
    estado = models.CharField(
        max_length=50, 
        choices=ESTADOS_SALIDA, # Usar la constante definida
        default='BORRADOR'
    )
    usuario_aprobador = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='correspondencia_aprobada'
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True, null=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    id_mensaje_enviado = models.CharField(max_length=255, null=True, blank=True)
    postmark_message_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text='MessageID UUID devuelto por Postmark al enviar.',
    )

    # --- Trazabilidad de modalidad de envío (opcional) ---
    ENVIO_TIPO_CHOICES = (
        ('INDIVIDUAL', 'Individual/Dirigido'),
        ('GRUPO', 'Grupo/Categoría'),
        ('MULTIPLE_SELECTIVO', 'Selección múltiple'),
    )
    envio_tipo = models.CharField(
        max_length=20,
        choices=ENVIO_TIPO_CHOICES,
        null=True,
        blank=True,
        help_text="Modalidad de envío registrada al crear la salida. Opcional para trazabilidad."
    )
    envio_grupo = models.ForeignKey(
        'correspondencia.GrupoAgenda',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salidas_asociadas',
        help_text="Grupo/Categoría utilizado para el envío cuando aplica."
    )
    envio_total_destinatarios = models.IntegerField(null=True, blank=True)
    envio_detalle_snapshot = models.CharField(max_length=255, null=True, blank=True)

    # Funcionario que envía (texto libre, para radicación rápida)
    funcionario_envia = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nombre del funcionario que envía la correspondencia."
    )

    # Campo de trazabilidad: indica si la correspondencia fue respondida
    fue_respondida = models.BooleanField(default=False)
    evidencia_respuesta = models.FileField(
        upload_to='salidas/evidencias/%Y/%m/',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Correspondencia de Salida"
        verbose_name_plural = "Correspondencias de Salida"
        ordering = ['-fecha_creacion']

    def __str__(self):
        if self.respuesta_a:
            return f"Respuesta {self.numero_radicado_salida} a {self.respuesta_a.numero_radicado}"
        return f"Salida {self.numero_radicado_salida}"

    def save(self, *args, **kwargs):
        if not self.pk: # Si es nuevo
            # Asegurar que el destinatario_contacto se establezca al crear
            if not self.destinatario_contacto and self.respuesta_a and self.respuesta_a.remitente:
                 self.destinatario_contacto = self.respuesta_a.remitente
            # Generar radicado solo al crear
            self.numero_radicado_salida = self._generar_numero_radicado_salida()
            # Derivar oficina emisora de la correspondencia entrante
            if not self.oficina_emisora and self.respuesta_a and self.respuesta_a.oficina_destino:
                self.oficina_emisora = self.respuesta_a.oficina_destino
        
        # Rellenar email justo antes de intentar enviar (o al aprobar)
        if self.estado == 'APROBADA' and not self.destinatario_email and self.destinatario_contacto:
             self.destinatario_email = self.destinatario_contacto.correo_electronico
        # Congelar snapshots de oficina y redactor al aprobar
        if self.estado == 'APROBADA':
            if self.oficina_emisora and not self.oficina_emisora_nombre:
                self.oficina_emisora_nombre = self.oficina_emisora.nombre
            if self.usuario_redactor and not self.redactor_nombre:
                try:
                    self.redactor_nombre = f"{self.usuario_redactor.first_name} {self.usuario_redactor.last_name}".strip() or self.usuario_redactor.username
                except Exception:
                    self.redactor_nombre = self.usuario_redactor.username if self.usuario_redactor else None
            if self.usuario_redactor and not self.redactor_cargo:
                try:
                    self.redactor_cargo = getattr(self.usuario_redactor, 'perfil', None).cargo if hasattr(self.usuario_redactor, 'perfil') else None
                except Exception:
                    self.redactor_cargo = None
             
        super().save(*args, **kwargs)

    def _generar_numero_radicado_salida(self):
        """Genera un número de radicado único para la correspondencia de salida."""
        now = timezone.now()
        current_year = now.year
        prefijo = "SALIENTE" 
        
        last_radicado = CorrespondenciaSalida.objects.filter(
            fecha_creacion__year=current_year
        ).order_by('fecha_creacion').last()
        
        next_consecutive = 1
        if last_radicado and last_radicado.numero_radicado_salida:
            try:
                parts = last_radicado.numero_radicado_salida.split('-')
                last_consecutive = int(parts[-1])
                next_consecutive = last_consecutive + 1
            except (IndexError, ValueError):
                pass # Mantener next_consecutive = 1
                
        return f"{prefijo}-{current_year}-{next_consecutive:05d}"

# --- Modelo para Adjuntos de Salida ---
def ruta_adjunto_salida(instance, filename):
    """Genera la ruta para guardar adjuntos de salida."""
    salida_id = instance.correspondencia_salida.id if instance.correspondencia_salida and instance.correspondencia_salida.id else 'sin_asignar'
    # Limpiar nombre de archivo 
    clean_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c.isspace() or c in ['.','-','_']]).rstrip()
    return os.path.join('correspondencia', 'salida_adjuntos', str(salida_id), clean_filename)

class AdjuntoSalida(models.Model):
    """Representa un archivo adjunto asociado a una correspondencia de salida."""
    correspondencia_salida = models.ForeignKey(
        CorrespondenciaSalida,
        on_delete=models.CASCADE,
        related_name='adjuntos'
    )
    archivo = models.FileField(upload_to=ruta_adjunto_salida, max_length=255)
    nombre_original = models.CharField(max_length=255, blank=True)
    tipo_mime = models.CharField(max_length=100, blank=True)
    fecha_carga = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto de Salida"
        verbose_name_plural = "Adjuntos de Salida"
        ordering = ['-fecha_carga']

    def __str__(self):
        return self.nombre_original or os.path.basename(self.archivo.name)

    def save(self, *args, **kwargs):
        if not self.nombre_original and self.archivo and hasattr(self.archivo, 'name'):
             try:
                 self.nombre_original = os.path.basename(self.archivo.name)
             except Exception:
                 self.nombre_original = "adjunto_salida"
        super().save(*args, **kwargs)

# --- Modelo de Historial para Salida ---
TIPO_EVENTO_SALIDA_CHOICES = [
    ('CREACION', 'Creación Borrador'),
    ('RESPUESTA_DISCRECIONAL', 'Respuesta Discrecional'),
    ('MODIFICACION', 'Modificación Borrador'),
    ('ENVIO_APROBACION', 'Enviado a Aprobación'),
    ('APROBACION', 'Aprobado por Ventanilla'),
    ('RECHAZO', 'Rechazado por Ventanilla'),
    ('INTENTO_ENVIO', 'Intento de Envío Email'),
    ('ENVIO_EXITOSO', 'Email Enviado Exitosamente'),
    ('ENVIO_FALLIDO', 'Error al Enviar Email'),
    ('ENTREGA_CONFIRMADA', 'Entrega Confirmada por Postmark'),
]

class HistorialSalida(models.Model):
    """Registra los eventos clave en el ciclo de vida de una correspondencia de salida."""
    correspondencia_salida = models.ForeignKey(
        CorrespondenciaSalida, 
        on_delete=models.CASCADE, 
        related_name='historial'
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    tipo_evento = models.CharField(max_length=30, choices=TIPO_EVENTO_SALIDA_CHOICES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    descripcion = models.TextField(blank=True, null=True, help_text="Detalles adicionales, motivo rechazo, error envío...")
    
    class Meta:
        verbose_name = "Historial de Correspondencia Salida"
        verbose_name_plural = "Historiales de Correspondencia Salida"
        ordering = ['-fecha_hora']

    def __str__(self):
        user_display = f" por {self.usuario.username}" if self.usuario else ""
        return f"{self.correspondencia_salida.numero_radicado_salida} - {self.get_tipo_evento_display()}{user_display}"

# --- Destinatarios de Correspondencia de Salida ---
ESTADO_DESTINATARIO_CHOICES = (
    ('PENDIENTE', 'Pendiente'),
    ('ENVIADO', 'Enviado'),
    ('FALLO', 'Fallo'),
    ('REBOTE', 'Rebote'),
)

class SalidaDestinatario(models.Model):
    """Destinatario individual para una correspondencia de salida."""
    correspondencia_salida = models.ForeignKey(
        CorrespondenciaSalida,
        on_delete=models.CASCADE,
        related_name='destinatarios'
    )
    contacto = models.ForeignKey(
        Contacto,
        on_delete=models.PROTECT,
        related_name='destinatario_en_salidas',
        help_text="Contacto destinatario (debe pertenecer a la oficina emisora)"
    )
    # Snapshots
    email_snapshot = models.EmailField()
    nombre_snapshot = models.CharField(max_length=255, blank=True)
    # Estado de envío por destinatario
    estado = models.CharField(max_length=20, choices=ESTADO_DESTINATARIO_CHOICES, default='PENDIENTE')
    fecha_envio = models.DateTimeField(null=True, blank=True)
    id_mensaje_enviado = models.CharField(max_length=255, null=True, blank=True)
    postmark_message_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text='MessageID UUID devuelto por Postmark al enviar.',
    )
    detalle_error = models.TextField(blank=True, null=True)
    # Campos para trazabilidad de rebotes (DSN)
    smtp_code = models.CharField(max_length=20, null=True, blank=True)
    dsn_status = models.CharField(max_length=20, null=True, blank=True)
    ultimo_evento_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Destinatario de Salida"
        verbose_name_plural = "Destinatarios de Salida"
        ordering = ['id']

    def __str__(self):
        return f"{self.correspondencia_salida.numero_radicado_salida} -> {self.email_snapshot}"

    def clean(self):
        # Validar que el contacto tiene email
        if not self.contacto or not self.contacto.correo_electronico:
            raise ValidationError("El contacto seleccionado no tiene correo electrónico.")
        oficina_emisora = getattr(self.correspondencia_salida, 'oficina_emisora', None)
        if oficina_emisora is None:
            raise ValidationError("La correspondencia de salida no tiene definida la oficina emisora.")

    def save(self, *args, **kwargs):
        # Completar snapshots si faltan
        if not self.email_snapshot and self.contacto and self.contacto.correo_electronico:
            self.email_snapshot = self.contacto.correo_electronico
        if not self.nombre_snapshot and self.contacto:
            self.nombre_snapshot = self.contacto.nombre_completo
        super().save(*args, **kwargs)


class PostmarkWebhookEvento(models.Model):
    """Bitácora idempotente de webhooks recibidos desde Postmark."""
    record_type = models.CharField(max_length=32)
    postmark_message_id = models.CharField(max_length=64, db_index=True)
    recipient = models.EmailField(blank=True, default='')
    payload = models.JSONField(default=dict, blank=True)
    recibido_at = models.DateTimeField(auto_now_add=True)
    procesado = models.BooleanField(default=False)
    resultado = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        verbose_name = 'Evento webhook Postmark'
        verbose_name_plural = 'Eventos webhook Postmark'
        constraints = [
            models.UniqueConstraint(
                fields=['record_type', 'postmark_message_id', 'recipient'],
                name='uniq_postmark_webhook_evento',
            ),
        ]
        ordering = ['-recibido_at']

    def __str__(self):
        return f'{self.record_type} {self.postmark_message_id} -> {self.recipient or "?"}'


    
# =============================================
# === GRUPOS DE AGENDA Y COMUNICACIÓN MASIVA ===
# =============================================

class GrupoAgenda(models.Model):
    """Agrupa contactos de una misma oficina para envíos masivos controlados."""
    oficina_propietaria = models.ForeignKey(
        OficinaProductora,
        on_delete=models.PROTECT,
        related_name='grupos_agenda'
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    contactos = models.ManyToManyField(Contacto, related_name='grupos_agenda', blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('oficina_propietaria', 'nombre')]
        ordering = ['nombre']
        verbose_name = "Grupo de Agenda"
        verbose_name_plural = "Grupos de Agenda"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.oficina_propietaria.nombre})"

    def clean(self):
        """No se requiere validar la oficina de los contactos al ser agenda global."""


ESTADOS_COMUNICACION_CHOICES = (
    ('BORRADOR', 'Borrador'),
    ('ENVIADA', 'Enviada'),
    ('PARCIAL', 'Enviada Parcialmente'),
    ('ERROR', 'Error General de Envío'),
)

class ComunicacionMasiva(models.Model):
    """Representa una comunicación masiva independiente de una entrada específica."""
    oficina_emisora = models.ForeignKey(
        OficinaProductora,
        on_delete=models.PROTECT,
        related_name='comunicaciones_masivas'
    )
    usuario_creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    asunto = models.CharField(max_length=255)
    cuerpo = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS_COMUNICACION_CHOICES, default='BORRADOR')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Comunicación Masiva"
        verbose_name_plural = "Comunicaciones Masivas"

    def __str__(self) -> str:
        return f"{self.asunto} ({self.get_estado_display()})"

    def contar_destinatarios(self) -> int:
        return self.destinatarios.count()


class ComunicacionDestinatario(models.Model):
    """Destinatario individual de una comunicación masiva."""
    comunicacion = models.ForeignKey(
        ComunicacionMasiva,
        on_delete=models.CASCADE,
        related_name='destinatarios'
    )
    contacto = models.ForeignKey(Contacto, on_delete=models.PROTECT, related_name='comunicaciones_recibidas')
    email_snapshot = models.EmailField()
    nombre_snapshot = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_DESTINATARIO_CHOICES, default='PENDIENTE')
    fecha_envio = models.DateTimeField(null=True, blank=True)
    id_mensaje_enviado = models.CharField(max_length=255, null=True, blank=True)
    postmark_message_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text='MessageID UUID devuelto por Postmark al enviar.',
    )
    detalle_error = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']
        verbose_name = "Destinatario de Comunicación"
        verbose_name_plural = "Destinatarios de Comunicación"
        unique_together = [('comunicacion', 'contacto')]

    def __str__(self) -> str:
        return f"{self.comunicacion_id} -> {self.email_snapshot}"

    def clean(self):
        # Validar pertenencia de oficina y correo
        if not self.contacto or not self.contacto.correo_electronico:
            raise ValidationError("El contacto seleccionado no tiene correo electrónico.")
        oficina_emisora = getattr(self.comunicacion, 'oficina_emisora', None)
        if oficina_emisora is None:
            raise ValidationError("La comunicación masiva no tiene definida la oficina emisora.")

    def save(self, *args, **kwargs):
        if not self.email_snapshot and self.contacto and self.contacto.correo_electronico:
            self.email_snapshot = self.contacto.correo_electronico
        if not self.nombre_snapshot and self.contacto:
            self.nombre_snapshot = self.contacto.nombre_completo
        super().save(*args, **kwargs)


# =============================================
# === INFORMES DIARIOS DE CORRESPONDENCIA ===
# =============================================

def ruta_informe_firmado(instance, filename):
    """Genera la ruta para guardar informes firmados."""
    return os.path.join('informes_firmados', str(instance.fecha.year), str(instance.fecha.month), filename)


class InformeDiarioCorrespondencia(models.Model):
    """
    Almacena los informes diarios de correspondencia con su archivo firmado.
    
    Cada día tiene un único informe que puede ser descargado (Excel vacío)
    y posteriormente subido con las firmas escaneadas.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Firma'),
        ('FIRMADO', 'Firmado'),
    ]
    
    fecha = models.DateField(unique=True, help_text="Fecha del informe (un informe por día)")
    archivo_firmado = models.FileField(
        upload_to=ruta_informe_firmado, 
        null=True, 
        blank=True,
        help_text="Archivo escaneado con las firmas"
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    total_correspondencias = models.IntegerField(default=0, help_text="Total de correspondencias del día")
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_subida_firma = models.DateTimeField(null=True, blank=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='informes_subidos'
    )
    
    class Meta:
        verbose_name = "Informe Diario de Correspondencia"
        verbose_name_plural = "Informes Diarios de Correspondencia"
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Informe {self.fecha.strftime('%d/%m/%Y')} - {self.get_estado_display()}"
    
    def actualizar_total(self):
        """Actualiza el total de correspondencias del día."""
        from .models import Correspondencia
        self.total_correspondencias = Correspondencia.objects.filter(
            tipo_radicado='ENTRANTE',
            fecha_radicacion__date=self.fecha
        ).count()
        self.save(update_fields=['total_correspondencias'])


class HistorialDescargaInforme(models.Model):
    """
    Registra el historial de descargas de informes.
    Útil para auditoría y seguimiento.
    """
    informe = models.ForeignKey(
        InformeDiarioCorrespondencia, 
        on_delete=models.CASCADE, 
        related_name='descargas'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='descargas_informes'
    )
    fecha_descarga = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Historial de Descarga"
        verbose_name_plural = "Historial de Descargas"
        ordering = ['-fecha_descarga']
    
    def __str__(self):
        return f"Descarga {self.informe.fecha} por {self.usuario} - {self.fecha_descarga.strftime('%d/%m/%Y %H:%M')}"


# =============================================
# === FIRMAS DIGITALES DE CORRESPONDENCIA ===
# =============================================

def ruta_firma_correspondencia(instance, filename):
    """Genera la ruta para guardar firmas de correspondencia."""
    from django.utils import timezone
    now = timezone.now()
    return os.path.join('firmas_correspondencias', str(now.year), str(now.month), filename)


class FirmaCorrespondencia(models.Model):
    """
    Firma digital individual de una correspondencia recibida.
    Capturada con tablet/pantalla táctil por el usuario recolector.
    """
    correspondencia = models.OneToOneField(
        Correspondencia, 
        on_delete=models.CASCADE,
        related_name='firma_recibida'
    )
    firma_imagen = models.ImageField(
        upload_to=ruta_firma_correspondencia,
        help_text="Imagen de la firma digital capturada"
    )
    fecha_firma = models.DateTimeField(auto_now_add=True)
    
    # Información del firmante (funcionario que recibe)
    firmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='correspondencias_firmadas',
        help_text="Usuario del sistema que firmó (si aplica)"
    )
    nombre_firmante = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nombre del funcionario que firmó (snapshot, opcional)"
    )
    cargo_firmante = models.CharField(
        max_length=255, 
        blank=True,
        null=True,
        help_text="Cargo del firmante (snapshot)"
    )
    oficina_firmante = models.ForeignKey(
        'documentos.OficinaProductora',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='firmas_recibidas',
        help_text="Oficina del firmante"
    )
    
    # Recolector (usuario de ventanilla que capturó la firma)
    recolector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='firmas_recolectadas',
        help_text="Usuario que recolectó la firma"
    )
    
    # Auditoría
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Firma de Correspondencia"
        verbose_name_plural = "Firmas de Correspondencias"
        ordering = ['-fecha_firma']
    
    def __str__(self):
        return f"Firma {self.correspondencia.numero_radicado} - {self.nombre_firmante}"


class FirmaAuxiliarCorrespondencia(models.Model):
    """
    Firma auxiliar adicional asociada a una correspondencia recibida.
    Permite registrar una o varias firmas complementarias sin reemplazar
    la firma principal ya existente.
    """
    correspondencia = models.ForeignKey(
        Correspondencia,
        on_delete=models.CASCADE,
        related_name='firmas_auxiliares'
    )
    firma_imagen = models.ImageField(
        upload_to=ruta_firma_correspondencia,
        help_text="Imagen de la firma auxiliar capturada"
    )
    fecha_firma = models.DateTimeField(auto_now_add=True)
    nombre_firmante = models.CharField(
        max_length=255,
        help_text="Nombre del firmante auxiliar"
    )
    cargo_firmante = models.CharField(
        max_length=255,
        help_text="Cargo del firmante auxiliar"
    )
    recolector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='firmas_auxiliares_recolectadas',
        help_text="Usuario que recolectó la firma auxiliar"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Firma Auxiliar de Correspondencia"
        verbose_name_plural = "Firmas Auxiliares de Correspondencia"
        ordering = ['-fecha_firma']

    def __str__(self):
        return f"Firma auxiliar {self.correspondencia.numero_radicado} - {self.nombre_firmante}"


# =============================================
# === COMUNICACIONES INTERNAS (OFICIOS) ===
# =============================================

class ComunicacionInterna(models.Model):
    """
    Modelo para gestionar las comunicaciones internas (Oficios) entre oficinas.
    Genera un documento Word basado en plantilla.
    
    Flujo de estados:
    - BORRADOR: Usuario puede editar.
    - PENDIENTE_APROBACION: Esperando aprobación del líder.
    - RECHAZADA: Líder rechazó. Fin del flujo.
    - APROBADA: Líder aprobó. Si es a toda la entidad, requiere firma antes de distribuir.
    - DISTRIBUIDA: Comunicación enviada a destinatarios.
    - RESPONDIDA: Se creó una respuesta a esta comunicación.
    """
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('PENDIENTE_APROBACION', 'Pendiente de Aprobación'),
        ('RECHAZADA', 'Rechazada'),
        ('APROBADA', 'Aprobada (Pendiente Firma/Distribución)'),
        ('DISTRIBUIDA', 'Distribuida'),
        ('RESPONDIDA', 'Respondida'),
        ('ANULADA', 'Anulada')
    ]
    
    TIPO_DISTRIBUCION_CHOICES = [
        ('USUARIO', 'Usuario Específico'),
        ('OFICINA', 'Oficina Completa (Subproceso)'),
        ('PROCESO', 'Proceso Completo'),
        ('ENTIDAD', 'Toda la Entidad'),
    ]

    # --- Identificación ---
    radicado = models.CharField(max_length=50, unique=True, editable=False, blank=True, null=True)
    codigo_dependencia = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        editable=False,
        help_text="Código jerárquico de la dependencia/oficina productora"
    )
    anio_radicado = models.PositiveSmallIntegerField(blank=True, null=True, editable=False)
    consecutivo_radicado = models.PositiveIntegerField(blank=True, null=True, editable=False)
    serie_documental = models.ForeignKey(
        SerieDocumental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='comunicaciones_internas',
        help_text="Serie documental asociada a la comunicación interna"
    )
    subserie_documental = models.ForeignKey(
        SubserieDocumental,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='comunicaciones_internas',
        help_text="Subserie documental asociada a la comunicación interna"
    )
    trd = models.CharField(max_length=100, blank=True, null=True, help_text="Código TRD (Tabla de Retención Documental)")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # --- Datos del Formulario ---
    ciudad = models.CharField(max_length=100, default="Saravena") 
    fecha_documento = models.DateField(help_text="Fecha que aparecerá en el documento impreso")
    
    # --- Tipo de distribución ---
    tipo_distribucion = models.CharField(
        max_length=20,
        choices=TIPO_DISTRIBUCION_CHOICES,
        default='USUARIO',
        null=True,  # Temporal: se hará no nullable después de migrar
        blank=True,  # Temporal: se hará no nullable después de migrar
        help_text="Tipo de distribución de la comunicación"
    )
    es_a_toda_entidad = models.BooleanField(
        default=False, 
        help_text="Si es True, va a todos los usuarios del sistema y requiere firma digital. (DEPRECADO: usar tipo_distribucion='ENTIDAD')"
    )
    
    # --- Remitente (Snapshot al momento de crear/enviar) ---
    remitente_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='comunicaciones_enviadas')
    remitente_nombre = models.CharField(max_length=255) # Snapshot
    remitente_cargo = models.CharField(max_length=255, null=True, blank=True) # Snapshot
    remitente_oficina = models.ForeignKey(OficinaProductora, on_delete=models.PROTECT, related_name='internas_enviadas')
    
    # --- Destinatario (Seleccionable) ---
    destinatario_oficina = models.ForeignKey(
        OficinaProductora, 
        on_delete=models.PROTECT, 
        related_name='internas_recibidas',
        null=True,
        blank=True,
        help_text="Oficina destino. Dejar vacío si es a toda la entidad."
    )
    destinatario_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="Opcional: Si va dirigido a una persona específica")
    destinatario_proceso = models.ForeignKey(
        Proceso,
        on_delete=models.PROTECT,
        related_name='comunicaciones_internas',
        null=True,
        blank=True,
        help_text="Proceso destino (solo cuando tipo_distribucion = 'PROCESO')"
    )
    
    # --- Contenido ---
    asunto = models.CharField(max_length=255)
    cuerpo = models.TextField(help_text="Contenido principal de la comunicación")
    
    # --- Archivo Generado ---
    archivo_generado = models.FileField(upload_to='interna/generados/', null=True, blank=True)
    
    # --- Firma Digital (para comunicaciones a oficina/proceso/entidad) ---
    archivo_firmado = models.FileField(
        upload_to='interna/firmados/', 
        null=True, 
        blank=True,
        help_text="PDF firmado digitalmente por el líder (requerido para distribución a oficina/proceso/entidad)"
    )
    fecha_firma = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora en que se subió el archivo firmado")
    
    # --- Revisión y Aprobación ---
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='comunicaciones_revisadas',
        help_text="Líder de oficina que revisó y aprobó la comunicación"
    )
    revisado_nombre = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del revisor (snapshot)")
    revisado_cargo = models.CharField(max_length=255, blank=True, null=True, help_text="Cargo del revisor (snapshot)")
    fecha_revision = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de revisión/aprobación")
    motivo_rechazo = models.TextField(blank=True, null=True, help_text="Motivo del rechazo (si aplica)")
    
    # --- Respuesta (vínculo a comunicación original) ---
    comunicacion_origen = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='respuestas',
        help_text="Comunicación original a la que responde (múltiples respuestas permitidas)"
    )
    es_respuesta_destacada = models.BooleanField(
        default=False,
        help_text="Indica si esta respuesta está destacada (estrellita). Líderes y usuarios asignados inicialmente tienen respuestas destacadas."
    )
    
    # --- Distribución ---
    fecha_distribucion = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de distribución")
    
    # --- Estado ---
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='BORRADOR')

    class Meta:
        verbose_name = "Comunicación Interna"
        verbose_name_plural = "Comunicaciones Internas"
        ordering = ['-fecha_creacion']
        # NOTA: Se eliminó el constraint unique_respuesta_por_comunicacion
        # Ahora se permiten múltiples respuestas por comunicación

    def __str__(self):
        return f"{self.radicado or 'BORRADOR'} - {self.asunto}"

    def save(self, *args, **kwargs):
        self._sincronizar_clasificacion_documental()

        if self.trd:
            self.trd = self.trd.strip() or None

        estados_oficiales = ('APROBADA', 'DISTRIBUIDA', 'RESPONDIDA')
        requiere_radicado = self.estado in estados_oficiales
        hidratar_desde_radicado = bool(
            self.radicado and (not self.codigo_dependencia or not self.anio_radicado or not self.consecutivo_radicado)
        )
        regenerar_radicado = False

        for intento in range(3):
            if requiere_radicado and (not self.radicado or regenerar_radicado):
                self._asignar_radicado()
                hidratar_desde_radicado = False
            elif hidratar_desde_radicado:
                self._hidratar_componentes_desde_radicado()
                hidratar_desde_radicado = False

            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                return
            except IntegrityError as exc:
                if not (
                    requiere_radicado
                    and self._es_colision_radicado(exc)
                    and intento < 2
                ):
                    raise

                self.radicado = None
                self.codigo_dependencia = None
                self.anio_radicado = None
                self.consecutivo_radicado = None
                regenerar_radicado = True

    @staticmethod
    def _es_colision_radicado(error):
        mensaje = str(error).lower()
        return (
            'comunicacioninterna' in mensaje
            and 'radicado' in mensaje
            and (
                'duplic' in mensaje
                or 'unique' in mensaje
                or 'constraint failed' in mensaje
                or '2601' in mensaje
                or '2627' in mensaje
            )
        )

    @classmethod
    def construir_trd_desde_estructura(cls, oficina, serie=None, subserie=None):
        if not oficina or not serie or not subserie:
            return None

        oficina_trd = (getattr(oficina, 'codigo_trd_comunicacion_interna', None) or '').strip()
        return oficina_trd or None

    def _sincronizar_clasificacion_documental(self):
        if self.subserie_documental and not self.serie_documental:
            self.serie_documental = self.subserie_documental.serie

        if self.serie_documental and self.subserie_documental and self.subserie_documental.serie_id != self.serie_documental.id:
            raise ValidationError("La subserie documental no pertenece a la serie documental seleccionada.")

        if self.serie_documental and self.subserie_documental:
            trd_calculada = self.construir_trd_desde_estructura(
                self.remitente_oficina,
                serie=self.serie_documental,
                subserie=self.subserie_documental,
            )
            if not trd_calculada:
                aviso_trd = getattr(
                    self.remitente_oficina,
                    'codigo_trd_comunicacion_interna_display',
                    'sin trd por falta de mapeo',
                )
                raise ValidationError(
                    f"No fue posible calcular la TRD de la comunicación interna porque la oficina remitente está {aviso_trd}."
                )
            self.trd = trd_calculada

    def _obtener_codigo_dependencia(self):
        if not self.remitente_oficina:
            raise ValueError("No se puede generar radicado sin oficina remitente.")

        codigo_sis = self.remitente_oficina.get_codigo_sis()
        if codigo_sis:
            return codigo_sis

        proceso = getattr(self.remitente_oficina, 'proceso', None)
        if not proceso:
            raise ValueError("No se puede generar radicado sin proceso asociado a la oficina remitente.")

        sigla = (getattr(proceso, 'sigla', '') or '').strip().upper()
        if not sigla:
            raise ValueError("El proceso asociado a la oficina remitente no tiene sigla configurada.")

        try:
            codigo_oficina = int(str(self.remitente_oficina.codigo).strip())
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("La oficina remitente no tiene un código numérico válido.") from exc

        return f"{sigla}-{codigo_oficina:02d}"

    def _obtener_anio_radicado(self):
        if self.fecha_documento:
            return self.fecha_documento.year
        return timezone.now().year

    def _asignar_radicado(self):
        codigo_dependencia = self._obtener_codigo_dependencia()
        anio_radicado = self._obtener_anio_radicado()
        consecutivo = self._generar_consecutivo_radicado(codigo_dependencia, anio_radicado)

        self.codigo_dependencia = codigo_dependencia
        self.anio_radicado = anio_radicado
        self.consecutivo_radicado = consecutivo
        self.radicado = f"{codigo_dependencia}-{consecutivo:03d}"

    def _hidratar_componentes_desde_radicado(self):
        if not self.radicado:
            return

        radicado = str(self.radicado).strip().upper()
        patrones = (
            r'^(?P<codigo_dependencia>[A-Z0-9]+-\d{2})-(?P<consecutivo>\d{3})$',
            r'^(?P<codigo_dependencia>[A-Z0-9]+-\d{2})-(?P<anio>\d{4})-(?P<consecutivo>\d{4})$',
            r'^(?P<codigo_dependencia>[A-Z0-9]+-\d{2}-\d{3})-(?P<anio>\d{4})-(?P<consecutivo>\d{5})$',
        )

        match = None
        for patron in patrones:
            match = re.match(patron, radicado)
            if match:
                break

        if not match:
            return

        self.codigo_dependencia = match.group('codigo_dependencia')
        anio = match.groupdict().get('anio')
        self.anio_radicado = int(anio) if anio else self._obtener_anio_radicado()
        self.consecutivo_radicado = int(match.group('consecutivo'))

    def _generar_consecutivo_radicado(self, codigo_dependencia, anio_radicado):
        ultimo = (
            ComunicacionInterna.objects.select_for_update().filter(
                codigo_dependencia=codigo_dependencia,
                anio_radicado=anio_radicado,
            )
            .exclude(pk=self.pk)
            .order_by('-consecutivo_radicado')
            .first()
        )
        if ultimo and ultimo.consecutivo_radicado:
            return ultimo.consecutivo_radicado + 1
        return 1

    def _generar_radicado(self):
        """
        Genera radicado archivístico en formato: SIGLA-OFICINA-NNN
        - SIGLA-OFICINA: Sigla del proceso y código de la oficina remitente
        - NNN: Consecutivo por oficina
        """
        codigo_dependencia = self._obtener_codigo_dependencia()
        anio_radicado = self._obtener_anio_radicado()
        consecutivo = self._generar_consecutivo_radicado(codigo_dependencia, anio_radicado)
        return f"{codigo_dependencia}-{consecutivo:03d}"
    
    @property
    def requiere_firma(self):
        """Retorna True si la comunicación requiere firma digital antes de distribuir."""
        # Mantener compatibilidad con es_a_toda_entidad
        if self.es_a_toda_entidad:
            return True
        # OFICINA, PROCESO y ENTIDAD requieren firma
        return self.tipo_distribucion in ('OFICINA', 'PROCESO', 'ENTIDAD')
    
    def puede_distribuir(self):
        """Retorna True si la comunicación puede ser distribuida."""
        if self.estado != 'APROBADA':
            return False
        if self.requiere_firma:
            return bool(self.archivo_firmado)
        return True
    
    def puede_responder(self, usuario):
        """
        Retorna True si el usuario puede responder a esta comunicación.
        
        Reglas:
        - PROCESO: Nadie puede responder (normativas)
        - Las respuestas NO se pueden responder (solo ida y vuelta)
        - Cualquier usuario que recibió la comunicación puede responder
        
        NOTA: Ahora soporta múltiples respuestas por comunicación.
        """
        # No se pueden responder normativas (procesos completos)
        if self.tipo_distribucion == 'PROCESO':
            return False
        
        # IMPORTANTE: Las respuestas NO se pueden responder (solo ida y vuelta)
        if self.es_respuesta():
            return False
        
        # Verificar que el usuario tiene perfil
        try:
            perfil = usuario.perfil
            oficina_usuario = perfil.oficina
        except AttributeError:
            return False
        
        # Importar modelo de destinatarios múltiples
        from .models import ComunicacionInternaDestinatario, ComunicacionInternaDistribucion
        
        # Verificar si el usuario está en la distribución (recibió la comunicación)
        esta_en_distribucion = ComunicacionInternaDistribucion.objects.filter(
            comunicacion=self,
            usuario=usuario
        ).exists()
        
        if esta_en_distribucion:
            return True
        
        # Verificar si el usuario está en los destinatarios múltiples directamente
        es_destinatario_directo = ComunicacionInternaDestinatario.objects.filter(
            comunicacion=self,
            tipo='USUARIO',
            usuario=usuario
        ).exists()
        
        if es_destinatario_directo:
            return True
        
        # Verificar si la oficina del usuario está en los destinatarios
        if oficina_usuario:
            oficina_es_destinataria = ComunicacionInternaDestinatario.objects.filter(
                comunicacion=self,
                tipo='OFICINA',
                oficina=oficina_usuario
            ).exists()
            
            if oficina_es_destinataria:
                return True
            
            # Fallback: campos legacy
            if self.destinatario_oficina and self.destinatario_oficina == oficina_usuario:
                return True
        
        # Fallback: campo legacy destinatario_usuario
        if self.destinatario_usuario and self.destinatario_usuario == usuario:
            return True
        
        # Por defecto, no permitir respuesta
        return False
    
    def es_respuesta_de_lider_o_asignado(self, usuario):
        """
        Determina si una respuesta de este usuario debería ser destacada (estrellita).
        
        Criterios para respuesta destacada:
        - El usuario es líder de oficina Y su oficina es destinataria
        - El usuario está en la lista de destinatarios directos (asignados inicialmente)
        """
        if not self.comunicacion_origen:
            return False  # Solo aplica a respuestas
        
        comunicacion_original = self.comunicacion_origen
        
        # Verificar si es líder de oficina
        es_lider = usuario.groups.filter(name='Lider de Oficina').exists()
        
        try:
            perfil = usuario.perfil
            oficina_usuario = perfil.oficina
        except AttributeError:
            return False
        
        from .models import ComunicacionInternaDestinatario
        
        # Si es líder y su oficina fue destinataria original, es destacada
        if es_lider and oficina_usuario:
            oficina_era_destinataria = ComunicacionInternaDestinatario.objects.filter(
                comunicacion=comunicacion_original,
                tipo='OFICINA',
                oficina=oficina_usuario
            ).exists()
            
            if oficina_era_destinataria:
                return True
            
            # Fallback legacy
            if comunicacion_original.destinatario_oficina == oficina_usuario:
                return True
        
        # Si el usuario estaba como destinatario directo (asignado inicialmente), es destacada
        usuario_era_destinatario_directo = ComunicacionInternaDestinatario.objects.filter(
            comunicacion=comunicacion_original,
            tipo='USUARIO',
            usuario=usuario
        ).exists()
        
        if usuario_era_destinatario_directo:
            return True
        
        # Fallback legacy
        if comunicacion_original.destinatario_usuario == usuario:
            return True
        
        return False
    
    def tiene_respuestas(self):
        """Retorna True si existe al menos una respuesta a esta comunicación."""
        return self.respuestas.exists()
    
    # Alias para compatibilidad
    def tiene_respuesta(self):
        """Alias de tiene_respuestas() para compatibilidad."""
        return self.tiene_respuestas()
    
    def es_respuesta(self):
        """Retorna True si esta comunicación es una respuesta a otra."""
        return self.comunicacion_origen is not None
    
    def contar_respuestas(self):
        """Retorna el número de respuestas a esta comunicación."""
        return self.respuestas.count()
    
    def get_respuestas_ordenadas(self):
        """Retorna las respuestas ordenadas: destacadas primero, luego por fecha."""
        return self.respuestas.order_by('-es_respuesta_destacada', '-fecha_creacion')


# =============================================
# === DESTINATARIOS DE COMUNICACIONES INTERNAS ===
# =============================================

class ComunicacionInternaDestinatario(models.Model):
    """
    Modelo para manejar múltiples destinatarios (usuarios u oficinas) 
    de una comunicación interna.
    Permite enviar a múltiples usuarios de la misma o diferentes oficinas.
    """
    TIPO_CHOICES = [
        ('USUARIO', 'Usuario'),
        ('OFICINA', 'Oficina'),
    ]
    
    comunicacion = models.ForeignKey(
        ComunicacionInterna,
        on_delete=models.CASCADE,
        related_name='destinatarios_multiples'
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        help_text="Tipo de destinatario: Usuario específico o Oficina completa"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comunicaciones_internas_destinatario',
        null=True,
        blank=True,
        help_text="Usuario destinatario (si tipo='USUARIO')"
    )
    oficina = models.ForeignKey(
        OficinaProductora,
        on_delete=models.CASCADE,
        related_name='comunicaciones_internas_destinatario',
        null=True,
        blank=True,
        help_text="Oficina destinataria (si tipo='OFICINA')"
    )
    
    class Meta:
        verbose_name = "Destinatario de Comunicación Interna"
        verbose_name_plural = "Destinatarios de Comunicaciones Internas"
        ordering = ['tipo', 'oficina', 'usuario']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(tipo='USUARIO', usuario__isnull=False, oficina__isnull=True) |
                    models.Q(tipo='OFICINA', usuario__isnull=True, oficina__isnull=False)
                ),
                name='destinatario_tipo_valido'
            ),
        ]
        unique_together = [
            ['comunicacion', 'usuario'],  # Un usuario solo puede aparecer una vez por comunicación
            ['comunicacion', 'oficina'],  # Una oficina solo puede aparecer una vez por comunicación
        ]
    
    def __str__(self):
        if self.tipo == 'USUARIO' and self.usuario:
            return f"{self.comunicacion.radicado or 'BORRADOR'} -> {self.usuario.get_full_name() or self.usuario.username}"
        elif self.tipo == 'OFICINA' and self.oficina:
            return f"{self.comunicacion.radicado or 'BORRADOR'} -> {self.oficina.nombre}"
        return f"{self.comunicacion.radicado or 'BORRADOR'} -> {self.tipo}"


# =============================================
# === DISTRIBUCIÓN DE COMUNICACIONES INTERNAS ===
# =============================================

class ComunicacionInternaDistribucion(models.Model):
    """
    Registra la distribución de una comunicación interna a usuarios específicos.
    Permite rastrear quién recibió, quién leyó y cuándo.
    """
    comunicacion = models.ForeignKey(
        ComunicacionInterna,
        on_delete=models.CASCADE,
        related_name='distribuciones'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comunicaciones_internas_recibidas'
    )
    fecha_distribucion = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Distribución de Comunicación Interna"
        verbose_name_plural = "Distribuciones de Comunicaciones Internas"
        ordering = ['-fecha_distribucion']
        unique_together = ['comunicacion', 'usuario']

    def __str__(self):
        return f"{self.comunicacion.radicado} -> {self.usuario.username}"

    def marcar_leido(self):
        """Marca la distribución como leída."""
        if not self.leido:
            self.leido = True
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['leido', 'fecha_lectura'])


# =============================================
# === HISTORIAL DE COMUNICACIONES INTERNAS ===
# =============================================

class HistorialComunicacionInterna(models.Model):
    """
    Registra todos los eventos/cambios de estado de una comunicación interna.
    Proporciona trazabilidad completa del flujo.
    """
    EVENTO_CHOICES = [
        ('CREADA', 'Comunicación Creada'),
        ('EDITADA', 'Comunicación Editada'),
        ('ENVIADA_APROBACION', 'Enviada a Aprobación'),
        ('APROBADA', 'Aprobada por Líder'),
        ('RECHAZADA', 'Rechazada por Líder'),
        ('FIRMA_SUBIDA', 'Firma Digital Subida'),
        ('DISTRIBUIDA', 'Distribuida a Destinatarios'),
        ('LEIDA', 'Leída por Usuario'),
        ('RESPUESTA_CREADA', 'Respuesta Creada'),
        ('ANULADA', 'Comunicación Anulada'),
    ]

    comunicacion = models.ForeignKey(
        ComunicacionInterna,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    evento = models.CharField(max_length=30, choices=EVENTO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_comunicaciones_internas'
    )
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción adicional del evento")

    class Meta:
        verbose_name = "Historial de Comunicación Interna"
        verbose_name_plural = "Historiales de Comunicaciones Internas"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.comunicacion.radicado or 'BORRADOR'} - {self.get_evento_display()} ({self.fecha})"


# =============================================
# === ANEXOS DE COMUNICACIONES INTERNAS ===
# =============================================

def validate_file_type_anexo(value):
    """Valida que el archivo sea PDF, Word o Excel."""
    import os
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Tipo de archivo no permitido: {ext}. '
            f'Solo se permiten: {", ".join(allowed_extensions)}'
        )

def validate_file_size_anexo(value):
    """Valida que el archivo no exceda 25MB."""
    max_size = 25 * 1024 * 1024  # 25MB
    if value.size > max_size:
        raise ValidationError(
            f'El archivo excede el tamaño máximo de 25MB. '
            f'Tamaño actual: {value.size / (1024 * 1024):.2f}MB'
        )

def ruta_anexo_comunicacion_interna(instance, filename):
    """
    Genera la ruta para guardar anexos de comunicaciones internas.
    Estructura: interna/anexos/YYYY/MM/comunicacion_id/filename
    Si hay duplicados, agrega sufijo numérico.
    """
    from django.utils import timezone
    import os
    
    now = timezone.now()
    comunicacion_id = instance.comunicacion_id or 'temp'
    
    # Base directory
    base_path = f'interna/anexos/{now.year}/{now.month:02d}/{comunicacion_id}'
    
    # Nombre del archivo - mantener original pero manejar duplicados
    name, ext = os.path.splitext(filename)
    
    # Verificar si ya existe y agregar sufijo si es necesario
    from django.core.files.storage import default_storage
    
    final_path = os.path.join(base_path, filename)
    counter = 1
    
    while default_storage.exists(final_path):
        new_filename = f"{name}_{counter}{ext}"
        final_path = os.path.join(base_path, new_filename)
        counter += 1
    
    return final_path


class AnexoComunicacionInterna(models.Model):
    """
    Modelo para almacenar anexos adjuntos a comunicaciones internas.
    Permite adjuntar archivos Word, PDF o Excel.
    Límite: 10 anexos por comunicación, 25MB por archivo, 25MB total.
    """
    comunicacion = models.ForeignKey(
        ComunicacionInterna,
        on_delete=models.CASCADE,
        related_name='anexos',
        help_text="Comunicación interna a la que pertenece este anexo"
    )
    archivo = models.FileField(
        upload_to=ruta_anexo_comunicacion_interna,
        validators=[validate_file_type_anexo, validate_file_size_anexo],
        max_length=300,
        help_text="Archivo anexo (PDF, Word o Excel)"
    )
    nombre_original = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nombre original del archivo"
    )
    fecha_carga = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora en que se subió el archivo"
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anexos_comunicacion_subidos',
        help_text="Usuario que subió el anexo"
    )
    
    class Meta:
        verbose_name = "Anexo de Comunicación Interna"
        verbose_name_plural = "Anexos de Comunicaciones Internas"
        ordering = ['fecha_carga']
        indexes = [
            models.Index(fields=['comunicacion', 'fecha_carga']),
        ]
    
    def __str__(self):
        nombre = self.nombre_original or (os.path.basename(self.archivo.name) if self.archivo else "Sin nombre")
        return f"{self.comunicacion.radicado or 'BORRADOR'} - {nombre}"
    
    def save(self, *args, **kwargs):
        # Guardar nombre original si no se proporcionó
        if not self.nombre_original and self.archivo:
            try:
                self.nombre_original = os.path.basename(self.archivo.name)
            except Exception:
                self.nombre_original = "archivo_anexo"
        super().save(*args, **kwargs)
    
    def get_tipo_archivo(self):
        """Retorna el tipo de archivo basado en la extensión"""
        if not self.archivo:
            return None
        ext = os.path.splitext(self.archivo.name)[1].lower()
        tipo_map = {
            '.pdf': 'PDF',
            '.doc': 'Word',
            '.docx': 'Word',
            '.xls': 'Excel',
            '.xlsx': 'Excel'
        }
        return tipo_map.get(ext, 'Desconocido')
    
    def es_pdf(self):
        """Retorna True si el archivo es PDF"""
        if not self.archivo:
            return False
        ext = os.path.splitext(self.archivo.name)[1].lower()
        return ext == '.pdf'
    
    def get_extension(self):
        """Retorna la extensión del archivo"""
        if not self.archivo:
            return ''
        return os.path.splitext(self.archivo.name)[1].lower()


# Signal para eliminar archivo físico cuando se elimina el anexo
from django.db.models.signals import pre_delete

@receiver(pre_delete, sender=AnexoComunicacionInterna)
def eliminar_archivo_anexo(sender, instance, **kwargs):
    """Elimina el archivo físico cuando se elimina el registro del anexo."""
    if instance.archivo:
        try:
            from django.core.files.storage import default_storage
            if default_storage.exists(instance.archivo.name):
                default_storage.delete(instance.archivo.name)
        except Exception as e:
            # Log the error but don't prevent deletion
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"No se pudo eliminar archivo de anexo {instance.archivo.name}: {e}")


# =============================================================================
# CORRESPONDENCIA URGENTE
# =============================================================================

class CorrespondenciaUrgencia(models.Model):
    """
    Modelo para correspondencia de carácter urgente que se trabaja en horas laborales.
    
    A diferencia de la correspondencia normal, las urgencias:
    - Se miden en HORAS laborales (no días)
    - Saltan el proceso de distribución
    - Llegan directamente a TODA la oficina destino
    - Cualquier usuario de la oficina puede responder
    - Comparten la secuencia de radicado con Correspondencia normal
    
    Atributos principales:
        numero_radicado: Número secuencial compartido con Correspondencia
        radicado: Formato URGENCIA-YYYY-NNNNN
        horas_limite: Horas laborales (8am-5pm, Lun-Vie) para responder
        fecha_limite: Fecha límite calculada automáticamente
        estado: PENDIENTE | EN_PROCESO | RESPONDIDA | VENCIDA
        prioridad: ALTA | CRITICA
    """
    
    # --- Relación con correo entrante ---
    correo_entrante = models.ForeignKey(
        'CorreoEntrante',
        on_delete=models.CASCADE,
        related_name='urgencias_radicadas',
        help_text="Correo entrante que origina esta urgencia"
    )
    
    # --- Radicación - Comparte secuencia con Correspondencia ---
    numero_radicado = models.PositiveIntegerField(
        unique=True,
        db_index=True,
        editable=False,
        help_text="Número secuencial compartido con correspondencia ENTRANTE"
    )
    radicado = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Formato: ENTRANTE-YYYY-NNNNN compartido con Correspondencia"
    )
    fecha_radicacion = models.DateTimeField(default=timezone.now)
    usuario_radica = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='urgencias_radicadas',
        help_text="Usuario de ventanilla que radica la urgencia"
    )
    
    # --- Clasificación documental ---
    serie = models.ForeignKey(
        'documentos.SerieDocumental',
        on_delete=models.PROTECT,
        related_name='urgencias'
    )
    subserie = models.ForeignKey(
        'documentos.SubserieDocumental',
        on_delete=models.PROTECT,
        related_name='urgencias',
        null=True,
        blank=True
    )
    
    # --- Oficina destino - SIN distribución individual ---
    oficina_destino = models.ForeignKey(
        'documentos.OficinaProductora',
        on_delete=models.PROTECT,
        related_name='urgencias_recibidas',
        help_text="Toda la oficina recibe la urgencia, sin distribución"
    )
    
    # --- SLA en HORAS laborales ---
    horas_limite = models.PositiveSmallIntegerField(
        default=24,
        help_text="Horas laborales (8am-5pm, Lun-Vie) para responder"
    )
    fecha_limite = models.DateTimeField(
        help_text="Fecha límite calculada automáticamente"
    )
    
    # --- Estado ---
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('RESPONDIDA', 'Respondida'),
        ('VENCIDA', 'Vencida'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        db_index=True
    )
    
    # --- Usuario que trabaja la urgencia (opcional) ---
    usuario_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='urgencias_asignadas',
        help_text="Usuario que tomó la urgencia para trabajarla"
    )
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    
    # --- Respuesta ---
    usuario_responde = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='urgencias_respondidas'
    )
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    respuesta = models.TextField(blank=True)
    
    # --- Prioridad ---
    PRIORIDAD_CHOICES = [
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='ALTA',
        db_index=True
    )
    
    # --- Observaciones ---
    observaciones = models.TextField(blank=True)
    motivo_urgencia = models.TextField(
        help_text="Justificación de por qué es urgente"
    )
    
    # --- Métricas calculadas ---
    horas_transcurridas = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Horas laborales transcurridas desde radicación"
    )
    
    class Meta:
        db_table = 'correspondencia_urgencia'
        verbose_name = 'Correspondencia Urgente'
        verbose_name_plural = 'Correspondencias Urgentes'
        ordering = ['-fecha_radicacion']
        indexes = [
            models.Index(fields=['estado', 'oficina_destino']),
            models.Index(fields=['prioridad', 'estado']),
            models.Index(fields=['fecha_limite']),
        ]
    
    def __str__(self):
        return f"{self.radicado} - {self.correo_entrante.asunto[:50]}"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.numero_radicado:
                self.numero_radicado = self._generar_numero_radicado()
            if not self.radicado:
                self.radicado = self._generar_radicado()
            if not self.fecha_limite:
                self.fecha_limite = self._calcular_fecha_limite()
        super().save(*args, **kwargs)
    
    def _generar_numero_radicado(self):
        """Genera número secuencial compartido con Correspondencia ENTRANTE."""
        from django.db import transaction

        with transaction.atomic():
            año_actual = timezone.now().year
            prefijo = 'ENTRANTE'

            def _extraer_consecutivo(radicado_str: str) -> int:
                try:
                    return int((radicado_str or '').split('-')[-1])
                except (ValueError, IndexError):
                    return 0

            # Último radicado de correspondencia ENTRANTE en el año
            ultimo_correspondencia = (
                Correspondencia.objects
                .select_for_update()
                .filter(tipo_radicado=prefijo, fecha_radicacion__year=año_actual)
                .order_by('fecha_radicacion')
                .last()
            )

            # Último radicado de urgencia en el año (ya formateado como ENTRANTE-YYYY-XXXXX)
            ultimo_urgencia = (
                CorrespondenciaUrgencia.objects
                .select_for_update()
                .filter(fecha_radicacion__year=año_actual)
                .order_by('fecha_radicacion')
                .last()
            )

            consecutivo_max = 0
            if ultimo_correspondencia:
                consecutivo_max = max(consecutivo_max, _extraer_consecutivo(ultimo_correspondencia.numero_radicado))
            if ultimo_urgencia:
                consecutivo_max = max(
                    consecutivo_max,
                    _extraer_consecutivo(ultimo_urgencia.radicado),
                    int(ultimo_urgencia.numero_radicado or 0)
                )

            return consecutivo_max + 1
    
    def _generar_radicado(self):
        """Genera radicado con el mismo formato de Correspondencia ENTRANTE."""
        año = timezone.now().year
        return f"ENTRANTE-{año}-{self.numero_radicado:05d}"
    
    def _calcular_fecha_limite(self):
        """Calcula fecha límite sumando horas laborales"""
        from .utils_sla import sumar_horas_laborales
        return sumar_horas_laborales(self.fecha_radicacion, self.horas_limite)
    
    def actualizar_horas_transcurridas(self):
        """Actualiza horas laborales transcurridas"""
        from .utils_sla import calcular_horas_laborales
        
        fecha_fin = self.fecha_respuesta if self.estado == 'RESPONDIDA' else timezone.now()
        self.horas_transcurridas = calcular_horas_laborales(
            self.fecha_radicacion,
            fecha_fin
        )
        self.save(update_fields=['horas_transcurridas'])
    
    def marcar_vencida(self):
        """Marca como vencida si superó el límite"""
        if self.estado not in ['RESPONDIDA'] and timezone.now() > self.fecha_limite:
            self.estado = 'VENCIDA'
            self.save(update_fields=['estado'])
            return True
        return False
    
    def tomar(self, usuario):
        """Un usuario toma la urgencia para trabajarla"""
        if self.estado == 'PENDIENTE':
            self.usuario_asignado = usuario
            self.fecha_asignacion = timezone.now()
            self.estado = 'EN_PROCESO'
            self.save()
            return True
        return False
    
    def responder(self, usuario, texto_respuesta):
        """Registra respuesta de la urgencia"""
        self.usuario_responde = usuario
        self.fecha_respuesta = timezone.now()
        self.respuesta = texto_respuesta
        self.estado = 'RESPONDIDA'
        self.actualizar_horas_transcurridas()
        self.save()
    
    @property
    def porcentaje_tiempo_usado(self):
        """Porcentaje de tiempo usado vs límite"""
        if self.horas_limite == 0:
            return 100
        porcentaje = (float(self.horas_transcurridas) / self.horas_limite) * 100
        return min(porcentaje, 100)
    
    @property
    def horas_restantes(self):
        """Horas laborales restantes"""
        from .utils_sla import calcular_horas_laborales
        if self.estado == 'RESPONDIDA':
            return 0
        restantes = self.horas_limite - calcular_horas_laborales(
            self.fecha_radicacion,
            timezone.now()
        )
        return max(restantes, 0)
    
    @property
    def color_alerta(self):
        """Color según porcentaje usado: success, warning, danger"""
        porcentaje = self.porcentaje_tiempo_usado
        if porcentaje < 50:
            return 'success'
        elif porcentaje < 80:
            return 'warning'
        else:
            return 'danger'
    
    # --- Propiedades de compatibilidad con modal de correspondencia ---
    # El modal espera 'numero_radicado' pero CorrespondenciaUrgencia usa 'radicado'
    # Esta propiedad permite que el modal funcione sin modificaciones
    # Alias eliminado ya que ambos modelos comparten 'numero_radicado' en integer
    # y el template usa el campo radicado que tiene el formato completo
    
    @property
    def asunto(self):
        """Alias para acceder al asunto del correo entrante"""
        return self.correo_entrante.asunto if self.correo_entrante else ""
    
    @property
    def remitente(self):
        """Objeto remitente simulado para compatibilidad con modal"""
        class RemitenteSimulado:
            def __init__(self, correo):
                self.nombre_completo = correo.remitente  # EmailField en CorreoEntrante
                self.correo_electronico = correo.remitente  # Mismo campo (es el email)
                self.entidad_externa = type('obj', (object,), {'nombre': 'Correo Entrante'})()
        
        return RemitenteSimulado(self.correo_entrante) if self.correo_entrante else None


class AdjuntoUrgencia(models.Model):
    """Adjuntos de respuestas de urgencias"""
    urgencia = models.ForeignKey(
        CorrespondenciaUrgencia,
        on_delete=models.CASCADE,
        related_name='adjuntos_respuesta'
    )
    archivo = models.FileField(
        upload_to='urgencias/respuestas/%Y/%m/'
    )
    nombre_original = models.CharField(max_length=255)
    tipo_mime = models.CharField(max_length=100, blank=True)
    tamaño_bytes = models.PositiveIntegerField(default=0)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = 'adjuntos_urgencia'
        verbose_name = 'Adjunto Urgencia'
        verbose_name_plural = 'Adjuntos Urgencias'
    
    def __str__(self):
        return f"{self.nombre_original} - {self.urgencia.radicado}"


class AsistenteConversacion(models.Model):
    """Sesión de conversación del asistente documental."""

    class Estado(models.TextChoices):
        ACTIVA = 'ACTIVA', 'Activa'
        ARCHIVADA = 'ARCHIVADA', 'Archivada'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='asistente_conversaciones'
    )
    titulo = models.CharField(max_length=160, default='Nueva conversación')
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVA)
    ultima_pregunta_at = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistente_conversacion'
        verbose_name = 'Conversación del asistente'
        verbose_name_plural = 'Conversaciones del asistente'
        ordering = ['-actualizado_en']

    def __str__(self):
        return f"{self.titulo} - {self.usuario}"


class AsistenteDocumento(models.Model):
    """Documento fuente indexado para recuperación documental."""

    ruta_relativa = models.CharField(max_length=500, unique=True)
    titulo = models.CharField(max_length=255)
    checksum = models.CharField(max_length=64)
    tipo_fuente = models.CharField(max_length=40, default='archivo')
    activo = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    indexado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistente_documento'
        verbose_name = 'Documento del asistente'
        verbose_name_plural = 'Documentos del asistente'
        ordering = ['ruta_relativa']

    def __str__(self):
        return self.ruta_relativa


class AsistenteChunk(models.Model):
    """Fragmento indexado de un documento fuente."""

    documento = models.ForeignKey(
        AsistenteDocumento,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    orden = models.PositiveIntegerField()
    heading = models.CharField(max_length=255, blank=True)
    contenido = models.TextField()
    search_text = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'asistente_chunk'
        verbose_name = 'Chunk del asistente'
        verbose_name_plural = 'Chunks del asistente'
        ordering = ['documento_id', 'orden']
        unique_together = ('documento', 'orden')

    def __str__(self):
        return f"{self.documento.ruta_relativa}#{self.orden}"

    def save(self, *args, **kwargs):
        self.search_text = (self.contenido or '').lower()
        super().save(*args, **kwargs)


class AsistenteMensaje(models.Model):
    """Mensajes intercambiados en una conversación del asistente."""

    class Rol(models.TextChoices):
        USER = 'user', 'Usuario'
        ASSISTANT = 'assistant', 'Asistente'
        SYSTEM = 'system', 'Sistema'

    conversacion = models.ForeignKey(
        AsistenteConversacion,
        on_delete=models.CASCADE,
        related_name='mensajes'
    )
    rol = models.CharField(max_length=20, choices=Rol.choices)
    contenido = models.TextField()
    citas = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'asistente_mensaje'
        verbose_name = 'Mensaje del asistente'
        verbose_name_plural = 'Mensajes del asistente'
        ordering = ['creado_en', 'id']

    def __str__(self):
        return f"{self.conversacion_id} - {self.rol}"


# Chat de soporte interno
from .chat_models import ChatConversation, ChatMessage, ChatAdjunto  # noqa: E402, F401
