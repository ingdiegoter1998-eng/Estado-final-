import os
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

TRD_INTERNA_SIN_MAPEO_LABEL = "sin trd por falta de mapeo"

def validate_file_size(value):
    max_size = 2 * 1024 * 1024  # 2 MB - corregido de comentario original
    if value.size > max_size:
        raise ValidationError(f"El archivo no puede superar los 2 MB. Tamaño actual: {value.size / (1024 * 1024):.2f} MB")

def normalize_filename(filename):
    """Normaliza el nombre del archivo eliminando caracteres especiales y espacios"""
    name, extension = os.path.splitext(filename)
    return f"{slugify(name)}{extension.lower()}"

def documento_upload_path(instance, filename):
    """
    Construye la ruta de almacenamiento basada en la oficina, serie, subserie y registro.
    """
    filename = normalize_filename(filename)
    
    try:
        if instance.registro.creado_por.perfil.oficina:
            oficina = slugify(instance.registro.creado_por.perfil.oficina.nombre)
        else:
            oficina = "sin_oficina"
    except AttributeError:
        oficina = "sin_oficina"
    
    try:
        # Usamos el nombre de la serie/subserie
        serie = slugify(instance.registro.codigo_serie.nombre)
        subserie = slugify(instance.registro.codigo_subserie.nombre) if instance.registro.codigo_subserie else "00"
        registro_id = str(instance.registro.id)
    except AttributeError:
        serie = "serie_default"
        subserie = "subserie_default"
        registro_id = "0"
    
    ruta = os.path.join("documentos", oficina, f"serie_{serie}", f"subserie_{subserie}", f"registro_{registro_id}")
    
    ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta)
    os.makedirs(ruta_completa, exist_ok=True)
    return os.path.join(ruta, filename)


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()  # p. ej. ".pdf"
    valid_extensions = ['.pdf', '.xls', '.xlsx', '.doc', '.docx']
    if ext not in valid_extensions:
        raise ValidationError("Solo se permiten archivos PDF, Excel o Word.")


def documento_escaneado_prestamo_upload_path(instance, filename):
    """
    Construye la ruta de almacenamiento para documentos escaneados de préstamos.
    """
    filename = normalize_filename(filename)
    prestamo_id = instance.prestamo.id if instance.prestamo else "sin_prestamo"
    ruta = os.path.join("prestamos", "escaneados", f"prestamo_{prestamo_id}")
    ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta)
    os.makedirs(ruta_completa, exist_ok=True)
    return os.path.join(ruta, filename)


def validate_file_type_prestamo(value):
    """
    Valida que el archivo sea PDF, Word o Excel para préstamos.
    """
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.pdf', '.xls', '.xlsx', '.doc', '.docx']
    if ext not in valid_extensions:
        raise ValidationError("Solo se permiten archivos PDF, Word o Excel.")


class SerieDocumental(models.Model):
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    codigo_trd = models.CharField(max_length=255, blank=True, null=True, help_text="Código TRD de la serie")
    oficinas_productoras = models.ManyToManyField(
        'OficinaProductora',
        related_name='series_documentales',
        blank=True,
        help_text="Oficinas productoras (subprocesos) que utilizan esta serie documental"
    )
    
    class Meta:
        verbose_name = "Serie Documental"
        verbose_name_plural = "Series Documentales"
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class SubserieDocumental(models.Model):
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    codigo_trd = models.CharField(max_length=255, blank=True, null=True, help_text="Código TRD de la subserie")
    serie = models.ForeignKey(SerieDocumental, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre} (Serie: {self.serie.nombre})"

class EntidadProductora(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.nombre


class MacroProceso(models.Model):
    """Macroproceso organizacional (Estratégicos, Misionales, de Apoyo, de Control y Seguimiento)"""
    numero = models.IntegerField(unique=True, help_text="Número secuencial del macroproceso")
    nombre = models.CharField(max_length=255, help_text="Nombre del macroproceso (ej: ESTRATÉGICOS, MISIONALES)")
    
    class Meta:
        verbose_name = "Macroproceso"
        verbose_name_plural = "Macroprocesos"
        ordering = ['numero']
    
    def __str__(self):
        return f"{self.numero} - {self.nombre}"


class Proceso(models.Model):
    """Proceso organizacional que pertenece a un macroproceso"""
    numero = models.IntegerField(help_text="Número del proceso")
    nombre = models.CharField(max_length=255, help_text="Nombre del proceso")
    sigla = models.CharField(max_length=20, help_text="Sigla del proceso (ej: DIR, THS, SIG)")
    macroproceso = models.ForeignKey(MacroProceso, on_delete=models.CASCADE, related_name='procesos')
    
    class Meta:
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"
        ordering = ['macroproceso__numero', 'numero']
        unique_together = [('numero', 'macroproceso')]
    
    def __str__(self):
        return f"{self.numero} - {self.nombre} ({self.sigla})"


class UnidadAdministrativa(models.Model):
    nombre = models.CharField(max_length=255)
    entidad_productora = models.ForeignKey(EntidadProductora, on_delete=models.CASCADE, related_name='unidades')
    
    def __str__(self):
        return f"{self.nombre} ({self.entidad_productora.nombre})"

class OficinaProductora(models.Model):
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=50, blank=True, null=True, help_text="Código de la oficina (opcional)")
    codigo_trd = models.CharField(max_length=255, blank=True, null=True, help_text="Código TRD de la oficina (solo el número, ej: 300)")
    codigo_trd_comunicacion_interna = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Código TRD autoritativo para comunicaciones internas de esta oficina"
    )
    codigo_sis = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Código SIS de la dependencia para comunicaciones internas (ej: SUC-00, DIR-03). Si se define, tiene prioridad sobre el cálculo automático."
    )
    unidad_administrativa = models.ForeignKey(UnidadAdministrativa, on_delete=models.CASCADE, related_name='oficinas')
    proceso = models.ForeignKey(
        'Proceso', 
        on_delete=models.PROTECT,
        related_name='oficinas',
        help_text="Proceso al que pertenece esta oficina (Subproceso)"
    )

    def _codigo_numerico(self):
        if self.codigo in (None, ''):
            raise ValidationError("La oficina no tiene código numérico asignado.")

        try:
            return int(str(self.codigo).strip())
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"El código de la oficina no es válido: {self.codigo}") from exc

    def get_codigo_sis(self):
        """Código SIS para comunicaciones internas: explícito en oficina o cálculo legacy."""
        valor = (self.codigo_sis or '').strip().upper()
        if valor:
            return valor

        if not self.proceso:
            return ''

        sigla = (self.proceso.sigla or '').strip().upper()
        if not sigla:
            return ''

        try:
            codigo_oficina = self._codigo_numerico()
        except ValidationError:
            return ''

        return f"{sigla}-{codigo_oficina:02d}"

    @property
    def codigo_dependencia(self):
        """Código jerárquico de dependencia para comunicaciones internas."""
        codigo_sis = self.get_codigo_sis()
        if codigo_sis and self.codigo_sis:
            return codigo_sis

        if not self.proceso:
            raise ValidationError("La oficina no tiene proceso asociado.")

        sigla = (self.proceso.sigla or '').strip().upper()
        if not sigla:
            raise ValidationError("El proceso asociado no tiene sigla configurada.")

        return f"{sigla}-{int(self.proceso.numero):02d}-{self._codigo_numerico():03d}"

    @property
    def tiene_trd_comunicacion_interna(self):
        return bool((self.codigo_trd_comunicacion_interna or '').strip())

    @property
    def codigo_trd_comunicacion_interna_display(self):
        if self.tiene_trd_comunicacion_interna:
            return self.codigo_trd_comunicacion_interna.strip()
        return TRD_INTERNA_SIN_MAPEO_LABEL
    
    def __str__(self):
        return f"{self.nombre} ({self.unidad_administrativa.nombre})"

class Objeto(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.nombre

class FUID(models.Model):
    entidad_productora = models.ForeignKey(EntidadProductora, on_delete=models.SET_NULL, null=True)
    unidad_administrativa = models.ForeignKey(UnidadAdministrativa, on_delete=models.SET_NULL, null=True)
    oficina_productora = models.ForeignKey(OficinaProductora, on_delete=models.SET_NULL, null=True)
    objeto = models.ForeignKey(Objeto, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='fuids')
    registros = models.ManyToManyField('RegistroDeArchivo', related_name='fuids', blank=True)
    notas = models.CharField(max_length=245, null=True, blank=True) #actualizacion del 22 de julio
    
    elaborado_por_nombre = models.CharField(max_length=255, null=True, blank=True)
    elaborado_por_cargo = models.CharField(max_length=255, null=True, blank=True)
    elaborado_por_lugar = models.CharField(max_length=255, null=True, blank=True)
    elaborado_por_fecha = models.DateField(null=True, blank=True)
    
    entregado_por_nombre = models.CharField(max_length=255, null=True, blank=True)
    entregado_por_cargo = models.CharField(max_length=255, null=True, blank=True)
    entregado_por_lugar = models.CharField(max_length=255, null=True, blank=True)
    entregado_por_fecha = models.DateField(null=True, blank=True)
    
    recibido_por_nombre = models.CharField(max_length=255, null=True, blank=True)
    recibido_por_cargo = models.CharField(max_length=255, null=True, blank=True)
    recibido_por_lugar = models.CharField(max_length=255, null=True, blank=True)
    recibido_por_fecha = models.DateField(null=True, blank=True)

    class Meta:
        permissions = [
            ("view_own_fuid", "Puede ver sus propios FUIDs"),
            ("edit_own_fuid", "Puede editar sus propios FUIDs"),
            ("delete_own_fuid", "Puede eliminar sus propios FUIDs"),
        ]
    
    def __str__(self):
        return f"FUID #{self.id} - {self.entidad_productora.nombre if self.entidad_productora else 'Sin Entidad'}"




class RegistroDeArchivo(models.Model):  
    Estado_archivo = models.BooleanField(default=True)
    numero_orden = models.IntegerField(default=0)  # Identificador único
    codigo = models.CharField(max_length=50, blank=True, null=True)
    codigo_serie = models.ForeignKey(SerieDocumental, on_delete=models.CASCADE, related_name="registros")
    codigo_subserie = models.ForeignKey(SubserieDocumental, on_delete=models.CASCADE, blank=True, null=True, related_name="registros")
    unidad_documental = models.CharField(max_length=255)
    fecha_archivo = models.DateField(blank=True, null=True) #va al final
    fecha_inicial = models.DateField(blank=True, null=True)
    fecha_final = models.DateField(blank=True, null=True)
    soporte_fisico = models.BooleanField(default=False)
    soporte_electronico = models.BooleanField(default=False)

    # llave foreanea para el fuid
    # fuid = models.ForeignKey(FUID, on_delete=models.SET_NULL, null=True, blank=True, related_name='registros')

    # campos fisicos
    caja = models.IntegerField(blank=True, null=True)
    carpeta = models.IntegerField(blank=True, null=True)
    tomo_legajo_libro = models.CharField(max_length=50, blank=True, null=True)
    numero_folios = models.IntegerField(blank=True, null=True)
    tipo = models.CharField(max_length=100, blank=True, null=True)
    cantidad = models.IntegerField(blank=True, null=True)
    # campos electronicos
    ubicacion = models.CharField(max_length=255, null=True)
    cantidad_documentos_electronicos = models.IntegerField(null=True, blank=True)
    tamano_documentos_electronicos = models.CharField(max_length=50, null=True, blank=True)

    # agrego identificacion del documento para casos como la historia clinica
    identificador_documento  = models.CharField(max_length=150, null=True, blank=True)

    notas = models.TextField(max_length=250,blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='registros_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_edicion = models.DateTimeField(auto_now=True, null=True, blank=True)
    editado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registros_editados',
        help_text='Último usuario que editó este registro'
    )

    class Meta:
        permissions = [
            ("view_own_registro", "Puede ver sus propios registros"),
            ("edit_own_registro", "Puede editar sus propios registros"),
            ("delete_own_registro", "Puede eliminar sus propios registros"),
        ]


from django.core.exceptions import ValidationError

class Documento(models.Model):
    registro = models.ForeignKey('RegistroDeArchivo', on_delete=models.CASCADE, related_name='documentos')
    archivo = models.FileField(upload_to=documento_upload_path, validators=[validate_file_size],max_length=300)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.pk and self.registro.documentos.count() >= 3:
            raise ValidationError("Solo se permiten 3 archivos por registro.")
        
        # Antes de guardar, asegurarse de que el directorio existe
        if self.archivo:
            ruta_destino = os.path.dirname(os.path.join(settings.MEDIA_ROOT, self.archivo.field.upload_to(self, self.archivo.name)))
            try:
                os.makedirs(ruta_destino, exist_ok=True, mode=0o755)  # Crea el directorio con permisos adecuados
                logger.info(f"Directorio creado/verificado: {ruta_destino}")
            except PermissionError as e:
                logger.error(f"Error de permisos al crear directorio {ruta_destino}: {str(e)}")
                raise ValidationError(f"No se pueden crear los directorios necesarios debido a permisos insuficientes. Por favor contacte al administrador del sistema.")
            except Exception as e:
                logger.error(f"Error al crear directorio {ruta_destino}: {str(e)}")
                raise ValidationError(f"Error al crear directorio para almacenar el archivo: {str(e)}")
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Documento para registro {self.registro.numero_orden}"


    


class PermisoUsuarioSerie(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    serie = models.ForeignKey(SerieDocumental, on_delete=models.CASCADE)
    permiso_crear = models.BooleanField(default=False)
    permiso_editar = models.BooleanField(default=False)
    permiso_consultar = models.BooleanField(default=True)
    permiso_eliminar = models.BooleanField(default=False)

    def __str__(self):
        return f"Permisos de {self.usuario.username} sobre {self.serie.nombre}"


class TipoDocumento(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Nacionalidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True, db_index=True)

    class Meta:
        verbose_name_plural = "Nacionalidades"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

def nacionalidad_colombiana_default():
    return Nacionalidad.objects.get_or_create(nombre="Colombiano")[0].id


class FichaPaciente(models.Model):
    consecutivo = models.AutoField(primary_key=True)
    primer_nombre = models.CharField(max_length=50, db_index=True)
    segundo_nombre = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    primer_apellido = models.CharField(max_length=50, db_index=True)
    segundo_apellido = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    num_identificacion = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    tipo_identificacion = models.ForeignKey(
        'TipoDocumento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    num_identificacion_secundario = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    tipo_identificacion_secundario = models.ForeignKey(
        'TipoDocumento',
        related_name='segundario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    fecha_nacimiento = models.DateField(blank=True, null=True, db_index=True)
    primer_nombre_padre = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    segundo_nombre_padre = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    primer_apellido_padre = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    segundo_apellido_padre = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    Numero_historia_clinica = models.BigIntegerField(unique=True, db_index=True)
    caja = models.CharField(blank=True, max_length=20, db_index=True)
    carpeta = models.CharField(blank=True, max_length=20, db_index=True)
    gabeta = models.IntegerField(null=True, blank=True, db_index=True)
    sexo = models.CharField(max_length=10, default='Masculino', db_index=True)
    activo = models.BooleanField(default=True, db_index=True)
    estado_de_migracion = models.BooleanField(default=False, db_index=True)
    Fecha_de_visita_de_la_tarjeta = models.DateField(blank=True, null=True, db_index=True)
    ultimo_registro_de_visita_en_la_base_de_datos = models.DateField(blank=True, null=True, db_index=True)
    año_de_registro = models.IntegerField(null=True, blank=True, db_index=True)

    
    # Nuevo campo nacionalidad
    nacionalidad = models.ForeignKey(Nacionalidad, 
            on_delete=models.SET_NULL,
            default=nacionalidad_colombiana_default,
            null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['num_identificacion', 'tipo_identificacion'],
                name='unique_identificacion_tipo'
            ),
        ]


    def __str__(self):
        return f"Ficha del paciente {self.primer_nombre} {self.primer_apellido} - {self.num_identificacion or self.num_identificacion_secundario}"
    

# models.py

from django.db import models
from django.contrib.auth.models import User

class PerfilUsuario(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PA', 'Pasaporte'),
        ('RC', 'Registro Civil'),
        ('NIT', 'NIT'),
        ('PEP', 'Permiso Especial de Permanencia'),
        ('PPT', 'Permiso por Protección Temporal'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    oficina = models.ForeignKey(OficinaProductora, on_delete=models.SET_NULL, null=True, blank=False)
    cargo = models.CharField(max_length=150, blank=True, null=True, help_text="Cargo del usuario (opcional)")
    
    # Datos de identificación
    tipo_documento = models.CharField(
        max_length=3, 
        choices=TIPO_DOCUMENTO_CHOICES, 
        default='CC',
        help_text="Tipo de documento de identidad"
    )
    numero_documento = models.CharField(
        max_length=20, 
        unique=True,
        null=True,
        blank=True,
        help_text="Número de documento de identidad"
    )
    
    # Datos personales
    fecha_nacimiento = models.DateField(null=True, blank=True, help_text="Fecha de nacimiento")
    direccion = models.CharField(max_length=200, blank=True, null=True, help_text="Dirección de residencia")
    telefono = models.CharField(max_length=20, blank=True, null=True, help_text="Número de teléfono")
    
    # Firma digital manuscrita
    firma_digital = models.ImageField(
        upload_to='firmas/',
        null=True,
        blank=True,
        help_text="Firma manuscrita del usuario para usar en documentos"
    )
    fecha_firma_creada = models.DateTimeField(null=True, blank=True, help_text="Fecha en que se creó la firma")
    
    # Control
    fecha_registro = models.DateTimeField(null=True, blank=True, help_text="Fecha de registro del usuario")
    solicita_lider = models.BooleanField(default=False, help_text="El usuario solicita ser líder de oficina")

    def __str__(self):
        if self.oficina:
            return f"{self.user.username} - {self.oficina.nombre}"
        return f"{self.user.username} - Sin oficina asignada"
    
    def es_lider_oficina(self):
        """Verifica si el usuario pertenece al grupo 'Lider de Oficina'"""
        return self.user.groups.filter(name='Lider de Oficina').exists()
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"


class DespliegueOficina(models.Model):
    """Seguimiento manual del rollout por oficina (panel de monitoreo)."""

    ESTADO_VISITA_CHOICES = [
        ('pendiente', 'Pendiente de visita'),
        ('visitada', 'Visitada'),
        ('capacitada', 'Capacitada'),
        ('no_aplica', 'No aplica'),
    ]

    oficina = models.OneToOneField(
        OficinaProductora,
        on_delete=models.CASCADE,
        related_name='despliegue',
    )
    estado_visita = models.CharField(
        max_length=20,
        choices=ESTADO_VISITA_CHOICES,
        default='pendiente',
    )
    fecha_visita = models.DateField(null=True, blank=True)
    notas = models.TextField(blank=True, default='')
    actualizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='despliegues_oficina_actualizados',
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Despliegue de oficina"
        verbose_name_plural = "Despliegues de oficinas"

    def __str__(self):
        return f"Despliegue — {self.oficina.nombre} ({self.get_estado_visita_display()})"


class PrestamoDocumental(models.Model):
    """Modelo principal para préstamos documentales"""
    
    ESTADO_CHOICES = [
        ('SOLICITADO', 'Solicitado'),
        ('ENTREGADO', 'Entregado'),
        ('PRESTAMO_ACTIVO', 'Préstamo Activo'),
        ('DEVOLUCION_SOLICITADA', 'Devolución Solicitada'),
        ('DEVUELTO', 'Devuelto'),
        ('REINTEGRADO', 'Reintegrado'),
        ('RECHAZADO', 'Rechazado'),
        ('RECHAZADO_USUARIO', 'Rechazado por Usuario'),
        ('VENCIDO', 'Vencido'),
    ]
    
    TIPO_PRESTAMO_CHOICES = [
        ('FISICO', 'Físico'),
        ('VIRTUAL', 'Virtual'),
    ]
    
    # Relaciones principales
    registro = models.ForeignKey(RegistroDeArchivo, on_delete=models.CASCADE, related_name='prestamos', null=True, blank=True)
    fuid = models.ForeignKey(FUID, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos')
    
    # Información del solicitante
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prestamos_solicitados')
    oficina_solicitante = models.ForeignKey(OficinaProductora, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_oficina')
    oficina_responsable = models.ForeignKey(
        OficinaProductora,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prestamos_responsables',
        help_text="Oficina a la que se dirige la solicitud de préstamo"
    )
    subproceso_solicitante = models.CharField(max_length=255, blank=True, null=True, help_text="Subproceso que solicita")
    
    # Información del documento
    codigo_trd = models.CharField(max_length=50, blank=True, null=True, help_text="Código TRD")
    serie = models.ForeignKey(SerieDocumental, on_delete=models.SET_NULL, null=True, blank=True)
    subserie = models.ForeignKey(SubserieDocumental, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion_documento = models.TextField(blank=True, null=True, help_text="Descripción del documento (serie/subserie y fecha)")
    
    # Tipo y estado
    tipo_prestamo = models.CharField(max_length=10, choices=TIPO_PRESTAMO_CHOICES)
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='SOLICITADO')
    
    # Fechas
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, help_text="Solo para préstamos físicos (10 días hábiles para Historia Clínica, 20 días hábiles para otros)")
    fecha_devolucion = models.DateTimeField(null=True, blank=True, help_text="Fecha en que el usuario devolvió el documento")
    fecha_reintegracion = models.DateTimeField(null=True, blank=True, help_text="Fecha en que Archivo Central reintegró el documento a su ubicación física")
    
    # Aprobación y procesamiento
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_aprobados')
    procesado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prestamos_procesados')
    
    # Vo.Bo. del jefe (automatizable)
    vobo_jefe_nombre = models.CharField(max_length=255, blank=True, null=True, default="Eliana Gelves", help_text="Nombre del jefe que aprueba")
    vobo_jefe_cargo = models.CharField(max_length=255, blank=True, null=True)
    vobo_jefe_fecha = models.DateField(null=True, blank=True)
    
    # Documentos
    documento_escaneado = models.FileField(upload_to='prestamos/escaneados/', null=True, blank=True, help_text="PDF escaneado del documento")
    documento_virtual = models.FileField(upload_to='prestamos/virtuales/', null=True, blank=True, help_text="PDF generado para préstamo virtual")
    
    # Motivos de rechazo
    motivo_rechazo = models.TextField(blank=True, null=True)
    motivo_rechazo_usuario = models.TextField(blank=True, null=True, help_text="Motivo si el usuario rechaza el documento")
    documento_rechazo = models.FileField(upload_to='prestamos/rechazos/', null=True, blank=True, help_text="Documento adjunto explicando los motivos del rechazo")
    
    # Devolución física
    documento_devuelto = models.BooleanField(default=False)
    documento_danado = models.BooleanField(default=False)
    observaciones_dano = models.TextField(blank=True, null=True, help_text="Observaciones sobre daños o faltantes")
    
    # Confirmación del usuario
    confirmado_por_usuario = models.BooleanField(default=False, help_text="Usuario confirma que recibió el documento correcto")
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    
    # Notas adicionales
    notas = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Préstamo Documental"
        verbose_name_plural = "Préstamos Documentales"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['estado', 'fecha_solicitud']),
            models.Index(fields=['solicitante', 'fecha_solicitud']),
            models.Index(fields=['tipo_prestamo', 'estado']),
        ]
    
    def __str__(self):
        return f"Préstamo #{self.id} - {self.get_tipo_prestamo_display()} - {self.estado}"
    
    def calcular_fecha_vencimiento(self):
        """
        Calcula fecha de vencimiento solo para físicos.
        - Historia Clínica: 10 días hábiles
        - Archivo Central (otros): 20 días hábiles
        """
        if self.tipo_prestamo == 'FISICO' and self.fecha_entrega:
            from datetime import timedelta
            
            # Determinar si es historia clínica
            es_historia_clinica = False
            if self.subserie:
                nombre_subserie = self.subserie.nombre.lower()
                if 'historia clínica' in nombre_subserie or 'historia clinica' in nombre_subserie:
                    es_historia_clinica = True
            if not es_historia_clinica and self.serie:
                nombre_serie = self.serie.nombre.lower()
                if 'historia clínica' in nombre_serie or 'historia clinica' in nombre_serie:
                    es_historia_clinica = True
            
            # Días hábiles según el tipo
            dias_habiles_requeridos = 10 if es_historia_clinica else 20
            
            fecha = self.fecha_entrega.date()
            dias_habiles = 0
            while dias_habiles < dias_habiles_requeridos:
                fecha += timedelta(days=1)
                # Excluir sábados (5) y domingos (6)
                if fecha.weekday() < 5:
                    dias_habiles += 1
            return fecha
        return None
    
    def verificar_vencimiento(self):
        """Verifica si el préstamo está vencido"""
        if self.tipo_prestamo == 'FISICO' and self.fecha_vencimiento and self.estado == 'PRESTAMO_ACTIVO':
            from django.utils import timezone
            if timezone.now().date() > self.fecha_vencimiento:
                self.estado = 'VENCIDO'
                self.save(update_fields=['estado'])
                return True
        return False

class DocumentoEscaneadoPrestamo(models.Model):
    """Modelo para almacenar múltiples documentos escaneados por préstamo"""
    prestamo = models.ForeignKey(PrestamoDocumental, on_delete=models.CASCADE, related_name='documentos_escaneados')
    archivo = models.FileField(
        upload_to=documento_escaneado_prestamo_upload_path,
        validators=[validate_file_type_prestamo, validate_file_size],
        max_length=300,
        help_text="Documento escaneado (PDF, Word o Excel)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    nombre_archivo_original = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Nombre original del archivo"
    )
    confirmado = models.BooleanField(
        default=False,
        help_text="Confirmado que el archivo se subió correctamente"
    )
    fecha_confirmacion = models.DateTimeField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_escaneados_subidos'
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Documento Escaneado de Préstamo"
        verbose_name_plural = "Documentos Escaneados de Préstamos"
    
    def __str__(self):
        return f"Documento #{self.id} - Préstamo #{self.prestamo.id}"


class NotificacionAvisoPrestamo(models.Model):
    """Notificaciones de aviso enviadas por Archivo Central sobre retrasos en préstamos"""
    prestamo = models.ForeignKey(PrestamoDocumental, on_delete=models.CASCADE, related_name='notificaciones_aviso')
    documento_oficio = models.FileField(
        upload_to='prestamos/notificaciones/',
        help_text="Documento oficio de notificación"
    )
    observaciones = models.TextField(blank=True, null=True, help_text="Observaciones adicionales")
    fecha_notificacion = models.DateTimeField(auto_now_add=True)
    notificado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='notificaciones_enviadas')
    oficina_notificada = models.ForeignKey(OficinaProductora, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_notificacion']
        verbose_name = "Notificación de Aviso"
        verbose_name_plural = "Notificaciones de Aviso"
    
    def __str__(self):
        return f"Notificación #{self.id} - Préstamo #{self.prestamo.id} - {self.fecha_notificacion.strftime('%d/%m/%Y')}"


class HistorialPrestamo(models.Model):
    """Historial de cambios en préstamos para trazabilidad"""
    prestamo = models.ForeignKey(PrestamoDocumental, on_delete=models.CASCADE, related_name='historial')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    evento = models.CharField(max_length=100, help_text="Tipo de evento: estado cambiado, documento subido, etc.")
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name = "Historial de Préstamo"
        verbose_name_plural = "Historiales de Préstamos"
    
    def __str__(self):
        return f"{self.prestamo.id} - {self.evento} - {self.fecha}"


class HistorialDescargaPrestamo(models.Model):
    """Auditoría de descargas de reportes mensuales de préstamos."""
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='descargas_reportes_prestamos')
    fecha_descarga = models.DateTimeField(auto_now_add=True)
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()
    nombre_archivo = models.CharField(max_length=255)
    total_registros = models.PositiveIntegerField(default=0)
    filtro_estado = models.CharField(max_length=25, blank=True, null=True)
    filtro_tipo = models.CharField(max_length=10, blank=True, null=True)
    filtro_alerta = models.CharField(max_length=40, blank=True, null=True)
    filtro_tipo_archivo = models.CharField(max_length=40, blank=True, null=True)
    filtro_oficina = models.CharField(max_length=255, blank=True, null=True)
    busqueda = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_descarga']
        verbose_name = 'Historial de Descarga de Préstamo'
        verbose_name_plural = 'Historiales de Descarga de Préstamos'
        indexes = [
            models.Index(fields=['anio', 'mes', 'fecha_descarga']),
            models.Index(fields=['usuario', 'fecha_descarga']),
        ]

    def __str__(self):
        return f"Reporte {self.anio}-{self.mes:02d} por {self.usuario or 'Sistema'}"

# Util function added here as per plan
def es_usuario_archivo_central(user):
    """Verifica si el usuario pertenece a Archivo Central"""
    try:
        if user.perfil.oficina.nombre.lower() == 'archivo central':
            return True
    except AttributeError:
        pass
    return False
