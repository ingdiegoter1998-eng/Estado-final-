import os
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.timezone import now, timedelta
from django.conf import settings
from django.contrib.auth.models import User

from .models import (
    RegistroDeArchivo, 
    SerieDocumental, 
    SubserieDocumental, 
    FUID, 
    Documento, 
    FichaPaciente,
    PrestamoDocumental,
    PerfilUsuario,
    OficinaProductora
)


class CustomSelect(forms.Select):
    """Widget Select personalizado que muestra solo el nombre, no el __str__"""
    def optgroups(self, name, value, attrs=None):
        """Renderizar opciones mostrando solo el nombre"""
        for group_name, group_choices, group_index in super().optgroups(name, value, attrs):
            yield group_name, [
                {'name': option['name'], 'value': option['value'], 'label': option['label'].split(' - ', 1)[-1] if ' - ' in str(option['label']) else option['label'], 'selected': option['selected'], 'index': option['index'], 'attrs': option['attrs'], 'template_name': option['template_name']}
                for option in group_choices
            ], group_index


class MultipleFileInput(forms.FileInput):
    """Widget personalizado para múltiples archivos"""
    def __init__(self, attrs=None):
        # Crear una copia de attrs sin 'multiple' para pasarla al constructor
        if attrs is None:
            clean_attrs = {}
        else:
            clean_attrs = {k: v for k, v in attrs.items() if k != 'multiple'}
        # Llamar al constructor sin 'multiple'
        super().__init__(clean_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        # Combinar attrs del widget con los attrs pasados
        if attrs is None:
            attrs = {}
        # Combinar self.attrs con attrs pasados
        final_attrs = {**self.attrs, **attrs}
        # Agregar 'multiple' siempre
        final_attrs['multiple'] = True
        # Llamar al render del padre
        return super().render(name, value, final_attrs, renderer)

# Tu validador de tamaño
def validate_file_size(value):
    max_size = 10 * 1024 * 1024  # 10 MB
    if value.size > max_size:
        raise ValidationError("El archivo no puede superar los 10 MB.")

class RegistroDeArchivoForm(forms.ModelForm):
    # Aplica el validador al campo archivo
    archivo = forms.FileField(
        required=False,
        help_text="Sube un documento (máx 10 MB).",
        validators=[validate_file_size]
    )

    fecha_archivo = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    )

    fecha_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    )

    fecha_final = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    )

    class Meta:
        model = RegistroDeArchivo
        exclude = ['creado_por', 'numero_orden']
        widgets = {
            'Estado_archivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tamano_documentos_electronicos': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Evitar que 'ubicacion' sea requerida
        self.fields['ubicacion'].required = False

        # Asignar fecha_archivo por defecto en el formulario
        if not self.instance.pk:
            self.fields['fecha_archivo'].initial = now().date()

        # Configuración dinámica de subseries
        if 'codigo_serie' in self.data:
            try:
                serie_id = int(self.data.get('codigo_serie'))
                self.fields['codigo_subserie'].queryset = SubserieDocumental.objects.filter(serie_id=serie_id)
            except (ValueError, TypeError):
                self.fields['codigo_subserie'].queryset = SubserieDocumental.objects.none()
        elif self.instance.pk and self.instance.codigo_serie:
            self.fields['codigo_subserie'].queryset = SubserieDocumental.objects.filter(serie_id=self.instance.codigo_serie.id)
        else:
            self.fields['codigo_subserie'].queryset = SubserieDocumental.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        # Si fecha_archivo está vacío, asignar la fecha actual
        if not cleaned_data.get('fecha_archivo'):
            cleaned_data['fecha_archivo'] = now().date()

        # Soporte Físico
        if not cleaned_data.get('soporte_fisico'):
            cleaned_data['caja'] = 0
            cleaned_data['carpeta'] = 0
            cleaned_data['tomo_legajo_libro'] = "N/A"
            cleaned_data['numero_folios'] = 0
            cleaned_data['tipo'] = "N/A"
            cleaned_data['cantidad'] = 0

        # Soporte Electrónico
        if not cleaned_data.get('soporte_electronico'):
            cleaned_data['ubicacion'] = "N/A"
            cleaned_data['cantidad_documentos_electronicos'] = 0
            cleaned_data['tamano_documentos_electronicos'] = "N/A"

        return cleaned_data




class FUIDForm(forms.ModelForm):
    # Campos y configuración del formulario
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Filtrar por Usuario",
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Buscar usuario...'})
    )
    fecha_inicio = forms.DateField(
        required=False,
        label="Fecha Inicio",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        required=False,
        label="Fecha Fin",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    registros = forms.ModelMultipleChoiceField(
        queryset=RegistroDeArchivo.objects.none(),  
        widget=forms.HiddenInput(),  # Campo oculto, se rellenará con JS
        required=False,
        label="Registros Asociados"
    )
    
    # Campo de búsqueda para registros
    registros_busqueda = forms.CharField(
        required=False,
        max_length=255,
        label="Buscar Registros",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'registros_busqueda',
            'placeholder': 'Busca registros por referencia, asunto, etc...',
            'autocomplete': 'off',
            'data-role': 'tagsinput'
        })
    )

    elaborado_por_nombre = forms.CharField(
        required=False,
        max_length=255,
        label="Elaborado Por (Nombre)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    elaborado_por_cargo = forms.CharField(
        required=False,
        max_length=255,
        label="Elaborado Por (Cargo)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    elaborado_por_lugar = forms.CharField(
        required=False,
        max_length=255,
        label="Elaborado Por (Lugar)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    elaborado_por_fecha = forms.DateField(
        required=False,
        label="Elaborado Por (Fecha)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    entregado_por_nombre = forms.CharField(
        required=False,
        max_length=255,
        label="Entregado Por (Nombre)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    entregado_por_cargo = forms.CharField(
        required=False,
        max_length=255,
        label="Entregado Por (Cargo)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    entregado_por_lugar = forms.CharField(
        required=False,
        max_length=255,
        label="Entregado Por (Lugar)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    entregado_por_fecha = forms.DateField(
        required=False,
        label="Entregado Por (Fecha)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    recibido_por_nombre = forms.CharField(
        required=False,
        max_length=255,
        label="Recibido Por (Nombre)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    recibido_por_cargo = forms.CharField(
        required=False,
        max_length=255,
        label="Recibido Por (Cargo)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    recibido_por_lugar = forms.CharField(
        required=False,
        max_length=255,
        label="Recibido Por (Lugar)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    recibido_por_fecha = forms.DateField(
        required=False,
        label="Recibido Por (Fecha)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = FUID
        fields = [
            'entidad_productora', 'unidad_administrativa', 'oficina_productora', 'objeto',
            'registros', 'registros_busqueda',
            'elaborado_por_nombre', 'elaborado_por_cargo', 'elaborado_por_lugar', 'elaborado_por_fecha',
            'entregado_por_nombre', 'entregado_por_cargo', 'entregado_por_lugar', 'entregado_por_fecha',
            'recibido_por_nombre', 'recibido_por_cargo', 'recibido_por_lugar', 'recibido_por_fecha'
        ]
        widgets = {
            'entidad_productora': forms.Select(attrs={'class': 'form-select'}),
            'unidad_administrativa': forms.Select(attrs={'class': 'form-select'}),
            'oficina_productora': forms.Select(attrs={'class': 'form-select'}),
            'objeto': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Usuario autenticado
        # No es necesario asignar self.instance aquí, ModelForm ya lo hace
        super().__init__(*args, **kwargs)

        # Configura el queryset de registros
        if self.instance and self.instance.pk:
            registros_actuales = self.instance.registros.all()
            self.fields['registros'].queryset = registros_actuales
            # Inicializa el campo de búsqueda con los IDs de los registros actuales
            registro_ids = registros_actuales.values_list('id', flat=True)
            self.fields['registros_busqueda'].initial = ','.join(str(id) for id in registro_ids)
        else:
            self.fields['registros'].queryset = RegistroDeArchivo.objects.none()
            self.fields['registros_busqueda'].initial = ''
  

class FichaPacienteForm(forms.ModelForm):
    class Meta:
        model = FichaPaciente
        fields = '__all__'
        widgets = {
            'primer_nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el primer nombre',
                'autofocus': 'autofocus',  # Enfocar este campo automáticamente
            }),
            'segundo_nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el segundo nombre (opcional)',
            }),
            'primer_apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el primer apellido',
            }),
            'segundo_apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el segundo apellido (opcional)',
            }),
            'num_identificacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de identificación único',
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',  # Mostrar un selector de fecha
            }),
            'primer_nombre_padre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el primer nombre del padre',
            }),
            'segundo_nombre_padre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Segundo nombre del padre (opcional)',
            }),
            'primer_apellido_padre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa el primer apellido del padre',
            }),
            'segundo_apellido_padre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Segundo apellido del padre (opcional)',
            }),
            'Numero_historia_clinica': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de historia clínica único',
            }),
            'caja': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de caja',
            }),
            'carpeta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de carpeta',

            }),
            'Activo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estado',
                
            }),                 
        }

    def clean_Numero_historia_clinica(self):
        numero_historia_clinica = self.cleaned_data.get('Numero_historia_clinica')
        if FichaPaciente.objects.filter(Numero_historia_clinica=numero_historia_clinica).exists():
            raise forms.ValidationError("El número de historia clínica ya está registrado. Por favor, verifica los datos.")
        return numero_historia_clinica

    def clean_num_identificacion(self):
        num_identificacion = self.cleaned_data.get('num_identificacion')
        if FichaPaciente.objects.filter(num_identificacion=num_identificacion).exists():
            raise forms.ValidationError("El número de identificación ya está registrado. Por favor, verifica los datos.")
        return num_identificacion


# ---- Formularios para el flujo de fichas de pacientes --------------------

# ---- Paso 0: Selección de Ubicación Física ------------------------------
class UbicacionFisicaForm(forms.Form):
    """Se rellena 1 vez por sesión; guarda los valores en `request.session`.
       Deje en blanco los campos que no desee prefijar."""
    gabeta   = forms.IntegerField(required=False, min_value=1, label="Gabeta")
    caja     = forms.CharField(required=False, max_length=20, label="Caja")
    carpeta  = forms.CharField(required=False, max_length=20, label="Carpeta")

# ---- Paso 1: Búsqueda Rápida --------------------------------------------
class BuscaFichaForm(forms.Form):
    """El funcionario introduce un ID o historia clínica para ver si ya existe."""
    num_identificacion = forms.CharField(max_length=50, required=False, label="Número de Identificación")
    Numero_historia_clinica = forms.IntegerField(required=False, label="Número de Historia Clínica")

    def clean(self):
        cd = super().clean()
        if not cd.get("num_identificacion") and not cd.get("Numero_historia_clinica"):
            raise forms.ValidationError("Ingresa un número de identificación o de historia clínica.")
        return cd

# ---- Formularios para Préstamos Documentales ----------------------------

class SolicitudPrestamoForm(forms.ModelForm):
    class Meta:
        model = PrestamoDocumental
        fields = [
            'oficina_responsable', 'serie', 'subserie',
            'descripcion_documento', 'tipo_prestamo', 'notas'
        ]
        widgets = {
            'oficina_responsable': CustomSelect(attrs={'class': 'form-select'}),
            'serie': CustomSelect(attrs={'class': 'form-select'}),
            'subserie': CustomSelect(attrs={'class': 'form-select'}),
            'descripcion_documento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo_prestamo': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['oficina_responsable'].required = True
        self.fields['oficina_responsable'].label = "Oficina a la que se solicita"
        self.fields['oficina_responsable'].help_text = "Selecciona la oficina que debe gestionar este préstamo."
        oficinas_gestoras = OficinaProductora.objects.filter(
            Q(nombre__icontains='gestión documental') |
            Q(nombre__icontains='gestion documental') |
            Q(nombre__icontains='archivo central') |
            Q(nombre__icontains='historias clínicas') |
            Q(nombre__icontains='historias clinicas') |
            Q(nombre__icontains='historia clínica') |
            Q(nombre__icontains='historia clinica')
        ).order_by('nombre').distinct()
        self.fields['oficina_responsable'].queryset = oficinas_gestoras
        # Subseries dependientes de serie
        if 'serie' in self.data:
            try:
                serie_id = int(self.data.get('serie'))
                self.fields['subserie'].queryset = SubserieDocumental.objects.filter(serie_id=serie_id)
            except (ValueError, TypeError):
                self.fields['subserie'].queryset = SubserieDocumental.objects.none()
        elif self.instance.pk and self.instance.serie:
            self.fields['subserie'].queryset = SubserieDocumental.objects.filter(serie_id=self.instance.serie.id)
        else:
            self.fields['subserie'].queryset = SubserieDocumental.objects.none()

class GestionPrestamoForm(forms.ModelForm):
    """
    Formulario para gestionar préstamos desde Archivo Central.
    Cuando el estado es SOLICITADO, solo permite cargar evidencia o rechazar.
    """
    ACCION_CHOICES = [
        ('cargar_evidencia', 'Cargar evidencia escaneada'),
        ('rechazar', 'Rechazar préstamo'),
    ]
    
    accion = forms.ChoiceField(
        choices=ACCION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'prestamo-radio'}),
        required=False,
        label="Acción a realizar"
    )
    
    finalizar_prestamo = forms.BooleanField(
        required=False,
        label="Finalizar proceso de préstamo",
        help_text="Marcar esta opción para dar por concluido el préstamo y cambiar su estado a DEVUELTO",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Campo para múltiples archivos
    documentos_escaneados = forms.FileField(
        widget=MultipleFileInput(attrs={
            'class': 'prestamo-form-control',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx'
        }),
        required=False,
        help_text="Puedes subir múltiples archivos (PDF, Word o Excel). Máximo 10 MB en total."
    )
    
    class Meta:
        model = PrestamoDocumental
        fields = [
            'documento_escaneado', 
            'documento_virtual', 
            'motivo_rechazo',
            'documento_rechazo',
            'observaciones_dano', 
            'documento_devuelto', 
            'documento_danado'
        ]
        widgets = {
            'documento_escaneado': forms.FileInput(attrs={
                'class': 'prestamo-form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx'
            }),
            'documento_virtual': forms.FileInput(attrs={
                'class': 'prestamo-form-control',
                'accept': '.pdf'
            }),
            'motivo_rechazo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Indica el motivo del rechazo'}),
            'documento_rechazo': forms.FileInput(attrs={
                'class': 'prestamo-form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'observaciones_dano': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'documento_devuelto': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'documento_danado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prestamo = self.instance
        
        # Si el préstamo está SOLICITADO, mostrar solo opciones de cargar evidencia o rechazar
        if self.prestamo.estado == 'SOLICITADO':
            # Hacer que documento_escaneado sea requerido solo si se selecciona cargar evidencia
            self.fields['documento_escaneado'].required = False
            self.fields['documento_virtual'].required = False
            # Dejamos accion como no requerido a nivel de campo para manejar la validación en clean()
            # y evitar mensajes duplicados o problemas de validación por defecto
            self.fields['accion'].required = False
            # Mostrar el campo de múltiples archivos
            self.fields['documentos_escaneados'].required = False
        else:
            # Para otros estados, ocultar el campo accion
            self.fields['accion'].widget = forms.HiddenInput()
            self.fields['accion'].required = False
            # También mostrar múltiples archivos en otros estados
            self.fields['documentos_escaneados'].required = False
            # Mostrar finalizar_prestamo solo para préstamos físicos que ya estén en uso
            if self.prestamo.tipo_prestamo == 'FISICO' and self.prestamo.estado in ['PRESTAMO_ACTIVO', 'DEVOLUCION_SOLICITADA', 'VENCIDO']:
                self.fields['finalizar_prestamo'].widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})
            else:
                self.fields['finalizar_prestamo'].widget = forms.HiddenInput()
        
        # Ocultar finalizar_prestamo para préstamos SOLICITADOS
        if self.prestamo.estado == 'SOLICITADO':
            self.fields['finalizar_prestamo'].widget = forms.HiddenInput()
    
    def clean_documentos_escaneados(self):
        """Valida múltiples archivos: tipos permitidos y tamaño total máximo de 10 MB"""
        archivos = self.files.getlist('documentos_escaneados')
        
        if not archivos or all(not f for f in archivos):
            return None
        
        # Filtrar archivos vacíos
        archivos = [f for f in archivos if f]
        
        if not archivos:
            return None
        
        # Validar tipos de archivo
        tipos_permitidos = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        total_size = 0
        max_size_total = 10 * 1024 * 1024  # 10 MB
        
        for archivo in archivos:
            # Validar extensión
            import os
            ext = os.path.splitext(archivo.name)[1].lower()
            if ext not in tipos_permitidos:
                raise ValidationError(f'El archivo "{archivo.name}" no es válido. Solo se permiten archivos PDF, Word o Excel.')
            
            # Acumular tamaño
            total_size += archivo.size
        
        # Validar tamaño total
        if total_size > max_size_total:
            size_mb = total_size / (1024 * 1024)
            raise ValidationError(f'El tamaño total de los archivos ({size_mb:.2f} MB) excede el límite de 10 MB.')
        
        # Devolver None porque Django FileField solo acepta un archivo
        # Los archivos se procesan directamente desde request.FILES.getlist() en la vista
        return None
    
    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get('accion')
        documento_escaneado = cleaned_data.get('documento_escaneado')
        # Usar getlist directamente de self.files para obtener todos los archivos
        documentos_escaneados = self.files.getlist('documentos_escaneados') if hasattr(self, 'files') else []
        motivo_rechazo = cleaned_data.get('motivo_rechazo')
        
        # Si el préstamo está SOLICITADO
        if self.prestamo.estado == 'SOLICITADO':
            if not accion:
                raise ValidationError('Debe seleccionar una acción: cargar evidencia o rechazar el préstamo.')
            
            if accion == 'cargar_evidencia':
                # Si es un préstamo físico, no se requiere documento
                if self.prestamo.tipo_prestamo == 'FISICO':
                    # Para préstamos físicos, no es necesario adjuntar documentos
                    pass
                else:
                    # Para préstamos virtuales, al menos un documento es requerido
                    # Filtrar archivos vacíos
                    documentos_escaneados_validos = [f for f in documentos_escaneados if f]
                    tiene_documentos = (documento_escaneado or documentos_escaneados_validos or 
                                       self.instance.documento_escaneado or
                                       self.instance.documentos_escaneados.exists())
                    if not tiene_documentos:
                        self.add_error('documentos_escaneados', 'Debe subir al menos un documento escaneado para procesar el préstamo.')
            
            elif accion == 'rechazar':
                # Si se rechaza, el motivo es obligatorio
                if not motivo_rechazo:
                    self.add_error('motivo_rechazo', 'Debe indicar el motivo del rechazo.')
        
        return cleaned_data


class ConfirmacionPrestamoForm(forms.Form):
    ACCION_CHOICES = [
        ('confirmar', 'Sí, recibí el documento correcto'),
        ('rechazar', 'No corresponde / necesito ajustes'),
    ]

    accion = forms.ChoiceField(
        choices=ACCION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'prestamo-radio'}),
        initial='confirmar',
        label="¿Cómo quieres cerrar esta entrega?"
    )
    motivo_rechazo_usuario = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'prestamo-form-control',
            'rows': 3,
            'placeholder': 'Describe qué falta o qué problema encontraste'
        }),
        label="Motivo del rechazo"
    )

    def clean(self):
        cleaned_data = super().clean()
        accion = cleaned_data.get('accion')
        motivo = cleaned_data.get('motivo_rechazo_usuario')

        if accion == 'rechazar' and not motivo:
            self.add_error('motivo_rechazo_usuario', 'Cuéntanos el motivo del rechazo para poder ayudarte.')

        if accion == 'confirmar':
            cleaned_data['motivo_rechazo_usuario'] = ''

        return cleaned_data


# ---- Formulario de Registro de Usuario ----------------------------------

class RegistroUsuarioForm(forms.ModelForm):
    """Formulario para registro de nuevos usuarios en el sistema"""
    
    # Campos del modelo User
    username = forms.CharField(
        max_length=150,
        label="Nombre de usuario",
        help_text="Requerido. 150 caracteres o menos. Letras, dígitos y @/./+/-/_ solamente.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'usuario123'})
    )
    first_name = forms.CharField(
        max_length=150,
        label="Nombres",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres completos'})
    )
    last_name = forms.CharField(
        max_length=150,
        label="Apellidos",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos completos'})
    )
    email = forms.EmailField(
        required=False,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        help_text="Tu contraseña debe tener al menos 8 caracteres."
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        help_text="Ingresa la misma contraseña para verificación."
    )
    
    # Checkbox de términos y condiciones
    acepta_terminos = forms.BooleanField(
        required=True,
        label="Acepto los términos y condiciones del sistema",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={'required': 'Debe aceptar los términos y condiciones para registrarse.'}
    )
    
    class Meta:
        model = PerfilUsuario
        fields = [
            'tipo_documento', 'numero_documento', 'fecha_nacimiento', 
            'direccion', 'telefono', 'oficina', 'cargo', 'solicita_lider'
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle 123 # 45-67'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '3001234567'}),
            'oficina': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo o función'}),
            'solicita_lider': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tipo_documento': 'Tipo de documento',
            'numero_documento': 'Número de documento',
            'fecha_nacimiento': 'Fecha de nacimiento',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'oficina': 'Oficina productora',
            'cargo': 'Cargo',
            'solicita_lider': 'Solicito ser líder de oficina',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargar todas las oficinas productoras disponibles
        self.fields['oficina'].queryset = OficinaProductora.objects.all().order_by('nombre')
        # Hacer oficina requerida con mensaje personalizado
        self.fields['oficina'].required = True
        self.fields['oficina'].error_messages = {'required': 'Debes seleccionar una oficina productora.'}
        # Hacer cargo opcional en el formulario
        self.fields['cargo'].required = False
        self.fields['telefono'].required = False
        self.fields['direccion'].required = False
    
    def clean_username(self):
        """Valida que el nombre de usuario sea único"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Este nombre de usuario ya está en uso. Por favor, elige otro.')
        return username
    
    def clean_numero_documento(self):
        """Valida que el número de documento sea único"""
        numero_documento = self.cleaned_data.get('numero_documento')
        if PerfilUsuario.objects.filter(numero_documento=numero_documento).exists():
            raise ValidationError('Este número de documento ya está registrado.')
        return numero_documento
    
    def clean_email(self):
        """Valida que el email sea único si se proporciona"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('Este correo electrónico ya está registrado.')
        return email
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        oficina = cleaned_data.get('oficina')
        
        # Validar que la oficina esté seleccionada
        if not oficina:
            self.add_error('oficina', 'Debes seleccionar una oficina productora para registrarte.')
        
        # Validar que las contraseñas coincidan
        if password1 and password2 and password1 != password2:
            raise ValidationError('Las contraseñas no coinciden.')
        
        # Validar longitud mínima de contraseña
        if password1 and len(password1) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        # Validar fecha de nacimiento (mayor de 18 años)
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        if fecha_nacimiento:
            from datetime import date
            hoy = date.today()
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            if edad < 18:
                self.add_error('fecha_nacimiento', 'Debe ser mayor de 18 años para registrarse.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Crea el usuario y el perfil asociado"""
        from django.utils import timezone
        
        # Crear el usuario
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data.get('email', ''),
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            is_active=True  # Usuario activo de inmediato al registrarse
        )
        
        # Crear el perfil
        perfil = super().save(commit=False)
        perfil.user = user
        perfil.fecha_registro = timezone.now()
        
        if commit:
            perfil.save()
        
        return perfil

