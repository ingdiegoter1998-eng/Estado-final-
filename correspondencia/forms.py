"""
Formularios del módulo de correspondencia.

Este módulo contiene todos los formularios necesarios para la gestión de
correspondencia entrante y saliente, incluyendo:

- Formularios de radicación de correspondencia
- Formularios de gestión de contactos y entidades externas
- Formularios de respuesta y distribución
- Validaciones personalizadas de lógica de negocio
- Integración con sistema SLA y TRD

Los formularios implementan:
- Validación de campos requeridos y opcionales
- Lógica de negocio específica (SLA, TRD)
- Integración con Crispy Forms para UI mejorada
- Carga dinámica de datos relacionados
- Manejo de archivos adjuntos

CARACTERÍSTICAS IMPLEMENTADAS EN ESTA RUN:
- Campo entidad_selector: Dropdown para filtrar contactos por entidad
- Campo oficina_selector: Dropdown para selección de oficina destino
- Selección jerárquica Entidad → Contacto (Remitente)
- Layout responsivo con Crispy Forms
- Integración con sistema SLA

Autor: Sistema de Gestión Documental
Fecha: 2025
"""

from django import forms
from .models import (
    Correspondencia, MEDIO_RECEPCION_CHOICES, MEDIO_RECIBIDO_CHOICES, TIEMPO_RESPUESTA_CHOICES,
    Contacto, EntidadExterna, CorrespondenciaSalida, AdjuntoSalida,
    ESTADOS_CORRESPONDENCIA, ESTADOS_SALIDA, GrupoAgenda, ComunicacionMasiva,
    AccesoCorrespondenciaOficina, ComunicacionInterna, CorrespondenciaUrgencia,
    ESTADO_RESPUESTA_RAPIDA_CHOICES, TIPO_TRAMITE_CHOICES, TipoTramite,
    extraer_dominios_candidatos
)
from documentos.models import SerieDocumental, SubserieDocumental, OficinaProductora, Proceso # Importar desde documentos
from documentos.forms import CustomSelect  # Importar widget personalizado
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, HTML, Div
from crispy_forms.bootstrap import AppendedText, PrependedText
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from .modelos_minimos_sla import SubserieTramite
from .trd_interna import (
    queryset_series_comunicacion_interna,
    queryset_subseries_comunicacion_interna,
    validar_clasificacion_comunicacion_interna,
)
from .utils_sla import get_cutoff_time, aplicar_corte, sumar_habiles
from django.utils import timezone
import datetime

class CorrespondenciaForm(forms.ModelForm):
    """
    Formulario principal para radicar nueva correspondencia entrante.
    
    Este formulario maneja la radicación de correspondencia entrante con
    validaciones específicas de lógica de negocio y integración con el
    sistema SLA/TRD.
    
    Características principales:
    - Carga dinámica de subseries basada en serie seleccionada
    - Validación de tiempo_respuesta cuando requiere_respuesta es True
    - Integración con sistema SLA para cálculo automático de plazos
    - Configuración automática de endpoint SLA en el campo subserie
    - Layout responsivo usando Crispy Forms
    
    Campos principales:
        remitente: Contacto externo que envía la correspondencia
        asunto: Descripción del contenido de la correspondencia
        serie/subserie: Clasificación documental
        medio_recepcion: Físico o electrónico
        requiere_respuesta: Si requiere respuesta
        tiempo_respuesta: Configuración de plazo (NORMAL/URGENTE/MUY_URGENTE)
        oficina_destino: Oficina responsable de procesar
        
    Validaciones:
        - remitente y oficina_destino son obligatorios
        - tiempo_respuesta es obligatorio si requiere_respuesta es True
        - subserie se valida dinámicamente según serie seleccionada
    """

    # CAMPOS VIRTUALES PARA MEJORAR UX:
    # entidad_selector: Campo de selección de entidad para filtrar contactos
    # oficina_selector: Campo de selección de oficina destino
    # Estos campos no se persisten, solo mejoran la experiencia de usuario
    entidad_selector = forms.ModelChoiceField(
        queryset=EntidadExterna.objects.order_by('nombre'),
        required=False,
        label="Entidad (para filtrar contactos)",
        empty_label="Seleccione una entidad...",
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Buscar entidad...'})
    )
    oficina_selector = forms.ModelChoiceField(
        queryset=OficinaProductora.objects.order_by('nombre'),
        required=False,
        label="Oficina Destino",
        empty_label="Seleccione una oficina...",
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Buscar oficina...'})
    )
    remitente = forms.ModelChoiceField(
        queryset=Contacto.objects.all().order_by('entidad_externa__nombre', 'apellidos', 'nombres'), # CORREGIDO: Ordenar por nombre de entidad externa
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Buscar contacto por nombre...'}),
        required=True, # Hacerlo requerido para asegurar que se seleccione uno
        label="Remitente (Contacto Externo)",
        empty_label="Seleccione un contacto..." # Texto para la opción vacía
    )
    asunto = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Asunto detallado'})
    )
    serie = forms.ModelChoiceField(
        queryset=SerieDocumental.objects.all(),
        widget=CustomSelect(attrs={'class': 'form-select', 'data-placeholder': 'Buscar serie documental...'}),
        required=False # Permitir no seleccionar serie/subserie inicialmente?
    )
    subserie = forms.ModelChoiceField(
        queryset=SubserieDocumental.objects.none(), # Se carga dinámicamente
        widget=CustomSelect(attrs={'class': 'form-select', 'data-placeholder': 'Buscar subserie documental...'}),
        required=False
    )
    medio_recepcion = forms.ChoiceField(
        choices=MEDIO_RECEPCION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    requiere_respuesta = forms.BooleanField(
        required=False, # No es obligatorio marcarlo
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    tiempo_respuesta = forms.ChoiceField(
        choices=[('', '--------- ')] + list(TIEMPO_RESPUESTA_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False # Solo será requerido si requiere_respuesta es True (se valida en clean)
    )
    oficina_destino = forms.ModelChoiceField(
        queryset=OficinaProductora.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Buscar oficina destino...'}),
        label="Oficina Destino Inicial"
    )
    codigo_trd = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': True,
            'placeholder': 'Se llenará automáticamente...'
        }),
        label="Código TRD (Tabla de Retención Documental)",
        help_text="Generado automáticamente: Oficina.Serie.Subserie"
    )

    class Meta:
        model = Correspondencia
        # Campos que se mostrarán en el formulario
        fields = [
            'remitente',
            'asunto', 
            'serie', 
            'subserie', 
            'medio_recepcion',
            'requiere_respuesta', 
            'tiempo_respuesta',
            'oficina_destino',
            # Añadir campo para adjunto si se implementa en el modelo
            # 'archivo_adjunto',
        ]
        # Widgets adicionales si no se personalizan arriba
        widgets = {
            'asunto': forms.Textarea(attrs={'rows': 3}),
            # Puedes personalizar otros widgets aquí si es necesario
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column(Field('entidad_selector'), css_class='form-group col-md-6 mb-3'),
                Column(Field('remitente'), css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column(Field('medio_recepcion'), css_class='form-group col-md-6 mb-3'),
                Column(Field('oficina_selector'), css_class='form-group col-md-6 mb-3'),
            ),
            Field('asunto', css_class='mb-3'),
            Row(
                Column(Field('serie'), css_class='form-group col-md-6 mb-3'),
                Column(Field('subserie'), css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column(Field('requiere_respuesta', css_class='form-check-input'), css_class='form-group col-md-6 mb-3'),
                Column(Field('tiempo_respuesta'), css_class='form-group col-md-6 mb-3', id='div_tiempo_respuesta'),
            ),
            # Nuevo campo para mostrar información SLA
            HTML("""
                <div class="row mb-3" id="sla-info" style="display: none;">
                    <div class="col-12">
                        <div class="alert alert-info">
                            <i class="bi bi-calendar-check me-2"></i>
                            <strong>Plazo Legal:</strong> <span id="plazo-dias">-</span> días hábiles
                            <br>
                            <strong>Fecha Límite:</strong> <span id="fecha-limite">-</span>
                            <br>
                            <small class="text-muted">
                                <span id="plazo-origen">-</span> | 
                                Corte horario: <span id="corte-horario">-</span>
                            </small>
                        </div>
                    </div>
                </div>
            """),
            Submit('submit', 'Radicar Correspondencia', css_class='btn btn-primary mt-3')
        )
        # Lógica para cargar subseries dinámicamente basada en la serie seleccionada
        if 'serie' in self.data:
            try:
                serie_id = int(self.data.get('serie'))
                self.fields['subserie'].queryset = SubserieDocumental.objects.filter(serie_id=serie_id).order_by('nombre')
            except (ValueError, TypeError):
                self.fields['subserie'].queryset = SubserieDocumental.objects.none()
        elif self.instance.pk and self.instance.serie:
            self.fields['subserie'].queryset = SubserieDocumental.objects.filter(serie=self.instance.serie).order_by('nombre')
        else:
            self.fields['subserie'].queryset = SubserieDocumental.objects.none()
            
        # Opcional: Ordenar queryset de OficinaProductora
        self.fields['oficina_destino'].queryset = OficinaProductora.objects.order_by('nombre')

        # Configurar Select2 para otros campos si es necesario
        if 'oficina_destino' in self.fields:
            self.fields['oficina_destino'].widget.attrs.update({'class': 'form-select select2'})
        if 'serie' in self.fields:
            self.fields['serie'].widget.attrs.update({'class': 'form-select select2'})
        if 'subserie' in self.fields:
            self.fields['subserie'].widget.attrs.update({
                'class': 'form-select select2',
                'data-sla-endpoint': '/registros/correspondencia/api/sla/calcular-plazo/'
            })
        if 'entidad_selector' in self.fields:
            self.fields['entidad_selector'].widget.attrs.update({'class': 'form-select select2'})
        if 'tiempo_respuesta' in self.fields:
            self.fields['tiempo_respuesta'].widget.attrs.update({
                'class': 'form-select',
                'data-sla-fallback': 'true'
            })
        if 'medio_recepcion' in self.fields:
            self.fields['medio_recepcion'].widget.attrs.update({'class': 'form-select'})
        if 'tiempo_respuesta' in self.fields:
             self.fields['tiempo_respuesta'].widget.attrs.update({'class': 'form-select'})

    def clean(self):
        """
        Validación personalizada del formulario de correspondencia.
        
        Este método implementa la lógica de validación específica para
        el formulario de radicación, incluyendo:
        
        Validaciones:
        1. Si requiere_respuesta es True:
           - Si hay mapeo TRD configurado: no requiere tiempo_respuesta
           - Si no hay mapeo TRD: tiempo_respuesta es obligatorio
        2. Si requiere_respuesta es False:
           - Limpia tiempo_respuesta automáticamente
           
        Lógica de negocio:
        - Verifica existencia de mapeo TRD para la subserie seleccionada
        - Aplica reglas de prioridad TRD > tiempo_respuesta
        - Mantiene consistencia con el sistema SLA
        
        Returns:
            dict: Datos limpios del formulario
            
        Raises:
            ValidationError: Si las validaciones no se cumplen
        """
        cleaned_data = super().clean()
        requiere_respuesta = cleaned_data.get("requiere_respuesta")
        tiempo_respuesta = cleaned_data.get("tiempo_respuesta")
        subserie = cleaned_data.get("subserie")
        remitente = cleaned_data.get("remitente")
        entidad_sel = cleaned_data.get("entidad_selector")
        
        # Verificar si hay mapeo TRD
        tiene_mapeo_trd = False
        if subserie:
            try:
                from .modelos_minimos_sla import SubserieTramite
                SubserieTramite.objects.get(subserie=subserie)
                tiene_mapeo_trd = True
            except SubserieTramite.DoesNotExist:
                pass
        
        if requiere_respuesta:
            # Nuevo comportamiento: permitir subserie vacía. Si no hay TRD, exigir tiempo_respuesta.
            if not tiene_mapeo_trd and not tiempo_respuesta:
                self.add_error('tiempo_respuesta',
                    'Debe seleccionar un Plazo de Respuesta cuando la correspondencia requiere respuesta y no hay TRD aplicada.')
        else:
            # Si no requiere respuesta, limpiar tiempo_respuesta
            cleaned_data['tiempo_respuesta'] = None
        
        # Validación de consistencia: el remitente debe pertenecer a la entidad seleccionada (si se usa el selector)
        if entidad_sel and remitente and remitente.entidad_externa_id != entidad_sel.id:
            self.add_error('remitente', 'El contacto seleccionado no pertenece a la entidad escogida.')
        
        return cleaned_data



class ContactoForm(forms.ModelForm):
    """Formulario para crear o editar Contactos Externos."""

    class Meta:
        model = Contacto
        fields = [
            'entidad_externa',
            'nombres', 
            'apellidos', 
            'cargo', 
            'correo_electronico',
            'telefono_contacto',
            'numero_documento',
        ]
        widgets = {
            # Usar Select para la ForeignKey entidad_externa
            'entidad_externa': forms.Select(attrs={
                'class': 'form-select select2', 
                'data-placeholder': 'Buscar entidad',
                'data-allow-clear': 'true'
            }),
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cargo (Opcional)'}),
            'correo_electronico': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@dominio.com'}),
            'telefono_contacto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono (Opcional)'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cédula, pasaporte, etc. (Opcional)'}),
        }
        labels = {
            'entidad_externa': 'Entidad Externa',
            'telefono_contacto': 'Teléfono del Contacto',
            'numero_documento': 'Número de Documento',
        }
        help_texts = {
             'entidad_externa': 'Seleccione la entidad a la que pertenece este contacto.'
        }

    def __init__(self, *args, **kwargs):
        # Extraer si el usuario es de Ventanilla o Admin
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        contacto = super().save(commit=False)
        if commit:
            contacto.save()

        return contacto

class CompartirCorrespondenciaForm(forms.Form):
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observaciones (opcional)"
    )

    def __init__(self, *args, **kwargs):
        self.oficina = kwargs.pop('oficina', None)
        self.usuario_actual = kwargs.pop('usuario_actual', None)
        self.correspondencia = kwargs.pop('correspondencia', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('observaciones', css_class='mb-3'),
            Submit('submit', 'Compartir', css_class='btn btn-primary')
        )

    def get_usuarios_destino(self):
        if not self.oficina:
            return User.objects.none()
        qs = User.objects.filter(
            perfil__oficina=self.oficina,
            is_active=True
        ).order_by('first_name', 'last_name')
        if self.usuario_actual:
            qs = qs.exclude(pk=self.usuario_actual.pk)
        return qs


class CompartirOtrasOficinasForm(forms.Form):
    oficinas = forms.ModelMultipleChoiceField(
        queryset=OficinaProductora.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Selecciona oficinas",
        help_text="Las oficinas seleccionadas tendrán acceso de solo lectura al radicado."
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Observaciones (opcional)"
    )

    def __init__(self, *args, **kwargs):
        self.correspondencia = kwargs.pop('correspondencia', None)
        self.oficina_origen = kwargs.pop('oficina_origen', None)
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('oficinas', css_class='mb-3'),
            Field('observaciones', css_class='mb-3'),
            Submit('submit', 'Compartir acceso', css_class='btn btn-primary')
        )

        oficinas_queryset = (
            OficinaProductora.objects
            .select_related('unidad_administrativa')
            .order_by('unidad_administrativa__nombre', 'nombre')
        )
        excluir_ids = set()
        if self.correspondencia and self.correspondencia.oficina_destino_id:
            excluir_ids.add(self.correspondencia.oficina_destino_id)
        if self.oficina_origen:
            excluir_ids.add(self.oficina_origen.pk)
        if self.correspondencia and hasattr(self.correspondencia, 'accesos_oficinas'):
            excluir_ids.update(self.correspondencia.accesos_oficinas.values_list('oficina_id', flat=True))

        if excluir_ids:
            oficinas_queryset = oficinas_queryset.exclude(pk__in=list(excluir_ids))

        self.fields['oficinas'].queryset = oficinas_queryset

# --- Nuevo Formulario para Radicación Manual desde Correo ---
class ManualRadicacionCorreoForm(forms.ModelForm):
    """
    Formulario específico para la radicación manual desde modales.
    
    Este formulario se utiliza en modales para radicar correspondencia manualmente,
    especialmente desde el dashboard de ventanilla y la vista de detalle de correos.
    
    CARACTERÍSTICAS ESPECÍFICAS:
    - Diseñado para uso en modales Bootstrap
    - Campos virtuales para UX mejorada (entidad_selector, oficina_selector)
    - Integración con sistema SLA
    - Carga dinámica de subseries
    - Layout optimizado para modales con Crispy Forms
    
    FLUJO DE SELECCIÓN JERÁRQUICA:
    1. Usuario selecciona Entidad → Se cargan contactos de esa entidad
    2. Usuario selecciona Contacto → Se establece como remitente
    3. Usuario selecciona Oficina → Se establece como oficina destino
    4. Usuario selecciona Subserie → Se calcula SLA automáticamente
    """
    # CAMPOS VIRTUALES (no se persisten):
    # entidad_selector: Para filtrar contactos por entidad
    entidad_selector = forms.ModelChoiceField(
        queryset=EntidadExterna.objects.order_by('nombre'),
        required=False,
        label="Entidad (para filtrar contactos)",
        empty_label="Seleccione una entidad...",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # oficina_selector: Para selección de oficina destino
    oficina_selector = forms.ModelChoiceField(
        queryset=OficinaProductora.objects.order_by('nombre'),
        required=False,
        label="Oficina Destino",
        empty_label="Seleccione una oficina...",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Buscar oficina destino...',
        })
    )
    distribuir_rapido = forms.BooleanField(
        required=False,
        label="¿Desea distribuir inmediatamente?",
        help_text="Si se activa, después de radicar podrá asignar responsable principal y compartir con otras oficinas.",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'data-distribucion-rapida-toggle': 'true',
        })
    )
    usuario_destino_rapido = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Responsable principal",
        empty_label="Seleccione un usuario...",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-usuarios-oficina': 'true',
        })
    )
    compartir_con_toda_oficina = forms.BooleanField(
        required=False,
        initial=False,
        label="Compartir con toda la oficina destino",
        help_text="Si no se marca, solo quedará asignada al responsable principal seleccionado.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    otras_oficinas = forms.ModelMultipleChoiceField(
        queryset=OficinaProductora.objects.order_by('nombre'),
        required=False,
        label="Compartir con otras oficinas",
        help_text="Otorga acceso de solo lectura a otras oficinas.",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '5',
            'data-otras-oficinas': 'true',
        })
    )
    observaciones_distribucion = forms.CharField(
        required=False,
        label="Observaciones de distribución",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'maxlength': '500',
            'placeholder': 'Observaciones para la asignación inicial (opcional)...',
        })
    )

    class Meta:
        model = Correspondencia
        # Campos estrictamente necesarios para la radicación manual desde correo
        fields = [
            'remitente',
            'asunto',
            'medio_recepcion',  # 🔥 AÑADIDO: Campo medio de recepción
            'oficina_destino',
            'tipo_tramite',  # 🔥 AÑADIDO: Tipo de trámite seleccionable
            'serie',
            'subserie',
            'requiere_respuesta',
            'tiempo_respuesta',
            'dias_personalizados',  # 🔥 NUEVO: Días personalizados (1-15)
        ]
        widgets = {
            'remitente': forms.Select(attrs={
                'class': 'form-select select2', 
                'data-placeholder': 'Buscar por nombre, apellido o correo...',
                'data-allow-clear': 'true'
            }),            
            'asunto': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'medio_recepcion': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Seleccionar medio de recepción...'}),  # 🔥 AÑADIDO
            'oficina_destino': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Buscar oficina destino...'}),
            'tipo_tramite': forms.Select(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Seleccionar tipo de trámite...',
                'data-calculo-fecha': 'true',
            }),
            'serie': CustomSelect(attrs={'class': 'form-select select2', 'data-placeholder': 'Buscar serie documental...'}),
            'subserie': CustomSelect(attrs={
                'class': 'form-select select2',
                'data-placeholder': 'Buscar subserie documental...',
                'data-sla-endpoint': '/registros/correspondencia/api/sla/calcular-plazo/'
            }),
            'tiempo_respuesta': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccionar plazo de respuesta...',
                'data-sla-fallback': 'true'
            }),
            'requiere_respuesta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_personalizados': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese días (1-15)',
                'min': '1',
                'max': '15',
                'step': '1'
            }),
        }
        labels = {
            'remitente': 'Remitente (Contacto Registrado)',
            'medio_recepcion': 'Medio de Recepción',  # 🔥 AÑADIDO
            'oficina_destino': 'Oficina Destino Inicial',
            'tipo_tramite': 'Tipo de Trámite',
            'serie': 'Serie Documental',
            'subserie': 'Subserie Documental',
            'requiere_respuesta': '¿Requiere Respuesta?',
            'tiempo_respuesta': 'Plazo de Respuesta (Estándar)',
            'dias_personalizados': 'Días Personalizados (Opcional)',
        }
        help_texts = {
            'remitente': 'Busque un contacto existente. Si no existe, debe crearlo usando el botón "Crear Contacto".',
            'subserie': 'Se carga automáticamente al seleccionar una serie.',
            'medio_recepcion': 'Indique si la correspondencia llegó físicamente o por medios electrónicos.',  # 🔥 AÑADIDO
            'tipo_tramite': 'Seleccione el tipo de trámite correspondiente. Puede influir en el plazo de respuesta.',
            'dias_personalizados': 'Si especifica días personalizados, tienen PRIORIDAD sobre tiempo_respuesta y TRD. Rango: 1-15 días hábiles.',
        }

    def __init__(self, *args, **kwargs):
        defer_select_options = kwargs.pop('defer_select_options', False)
        super().__init__(*args, **kwargs)
        # Ordenar Querysets para los Selects

        if defer_select_options:
            self.fields['oficina_destino'].queryset = OficinaProductora.objects.none()
            self.fields['entidad_selector'].queryset = EntidadExterna.objects.none()
            self.fields['oficina_selector'].queryset = OficinaProductora.objects.none()
            self.fields['otras_oficinas'].queryset = OficinaProductora.objects.none()
            self.fields['remitente'].queryset = Contacto.objects.none()
        else:
            # Configurar querysets ordenados
            self.fields['oficina_destino'].queryset = OficinaProductora.objects.order_by('nombre')
            # Cargar contactos con entidad para evitar N+1 queries, ordenados por entidad y nombre
            self.fields['remitente'].queryset = Contacto.objects.select_related('entidad_externa').order_by(
                'entidad_externa__nombre', 'apellidos', 'nombres'
            )

        self.fields['serie'].queryset = SerieDocumental.objects.order_by('nombre')

        # 🔥 Cargar tipos de trámite dinámicamente desde la base de datos
        if 'tipo_tramite' in self.fields:
            tipos_activos = TipoTramite.objects.filter(activo=True).order_by('orden', 'codigo')
            choices = [('', '---------')]
            for tipo in tipos_activos:
                choices.append((tipo.codigo, tipo.get_choice_display()))
            self.fields['tipo_tramite'].choices = choices
            self.fields['tipo_tramite'].required = False

        # Configurar Subserie: inicialmente vacío o basado en la instancia/datos
        # Tener en cuenta el prefijo del formulario dentro del modal (por ejemplo, "radicar")
        serie_actual = None
        try:
            serie_key = self.add_prefix('serie') if getattr(self, 'prefix', None) else 'serie'
        except Exception:
            serie_key = 'serie'

        if serie_key in self.data and self.data.get(serie_key):
            try:
                serie_id = int(self.data.get(serie_key))
                serie_actual = SerieDocumental.objects.get(pk=serie_id)
            except (ValueError, TypeError, SerieDocumental.DoesNotExist):
                serie_actual = None
        elif self.instance.pk and self.instance.serie:
            serie_actual = self.instance.serie

        if serie_actual:
            self.fields['subserie'].queryset = SubserieDocumental.objects.filter(serie=serie_actual).order_by('nombre')
            self.fields['subserie'].disabled = False
        else:
            self.fields['subserie'].queryset = SubserieDocumental.objects.none()
            self.fields['subserie'].disabled = True

        oficina_actual = None
        try:
            oficina_key = self.add_prefix('oficina_destino') if getattr(self, 'prefix', None) else 'oficina_destino'
        except Exception:
            oficina_key = 'oficina_destino'

        if oficina_key in self.data and self.data.get(oficina_key):
            try:
                oficina_actual = OficinaProductora.objects.get(pk=int(self.data.get(oficina_key)))
            except (ValueError, TypeError, OficinaProductora.DoesNotExist):
                oficina_actual = None
        elif self.instance.pk and self.instance.oficina_destino:
            oficina_actual = self.instance.oficina_destino
        elif self.initial.get('oficina_destino'):
            oficina_inicial = self.initial.get('oficina_destino')
            oficina_actual = oficina_inicial if isinstance(oficina_inicial, OficinaProductora) else None

        usuarios_queryset = User.objects.filter(is_active=True).select_related('perfil').order_by('first_name', 'last_name', 'username')
        if oficina_actual:
            usuarios_queryset = usuarios_queryset.filter(perfil__oficina=oficina_actual)
            self.fields['otras_oficinas'].queryset = OficinaProductora.objects.order_by('nombre').exclude(pk=oficina_actual.pk)
        else:
            usuarios_queryset = usuarios_queryset.none()
            self.fields['otras_oficinas'].queryset = OficinaProductora.objects.order_by('nombre')

        self.fields['usuario_destino_rapido'].queryset = usuarios_queryset

        # Crispy Forms Helper para el layout dentro del modal
        self.helper = FormHelper()
        self.helper.form_tag = False # Importante: El <form> estará en el HTML del modal
        self.helper.disable_csrf = True # CSRF token estará en el <form> del modal
        self.helper.layout = Layout(
            Div(
                HTML("""
                    <div class="wizard-step-header mb-3">
                        <span class="wizard-step-eyebrow">Paso 1</span>
                        <h6 class="wizard-step-title mb-1">Datos del radicado</h6>
                        <p class="wizard-step-copy mb-0">Complete la información principal, clasificación y plazo de respuesta.</p>
                    </div>
                """),
                Div(
                    HTML("""
                        <div class="wizard-section-title mb-3">
                            <i class="bi bi-person-vcard me-2 text-primary"></i>
                            Origen y recepción
                        </div>
                    """),
                    Row(
                        Column(Field('remitente'), css_class='col-lg-8 mb-3'),
                        Column(Field('medio_recepcion'), css_class='col-lg-4 mb-3'),
                    ),
                    Field('asunto', css_class='mb-0'),
                    css_class='wizard-card wizard-card-primary mb-3'
                ),
                Div(
                    HTML("""
                        <div class="wizard-section-title mb-3">
                            <i class="bi bi-diagram-2 me-2 text-primary"></i>
                            Clasificación y destino
                        </div>
                    """),
                    Row(
                        Column(Field('oficina_destino'), css_class='col-lg-6 mb-3'),
                        Column(Field('tipo_tramite'), css_class='col-lg-6 mb-3'),
                    ),
                    Row(
                        Column(Field('serie'), css_class='col-lg-6 mb-3'),
                        Column(Field('subserie'), css_class='col-lg-6 mb-3'),
                    ),
                    css_class='wizard-card mb-3'
                ),
                Div(
                    HTML("""
                        <div class="wizard-section-title mb-3">
                            <i class="bi bi-hourglass-split me-2 text-primary"></i>
                            SLA y adjuntos
                        </div>
                    """),
                    HTML("""
                        <div class="row mb-3" id="sla-status" style="display: none;">
                            <div class="col-12">
                                <div class="d-flex align-items-center rounded-3 px-3 py-2 bg-light border">
                                    <div class="spinner-border spinner-border-sm text-primary me-2" id="sla-loading" style="display: none;"></div>
                                    <span id="sla-message" class="text-muted small"></span>
                                </div>
                            </div>
                        </div>
                    """),
                    HTML("""
                        <div class="row mb-3" id="sla-info" style="display: none;">
                            <div class="col-12">
                                <div class="alert alert-info border-start border-4 border-info shadow-sm mb-0">
                                    <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
                                        <div class="d-flex align-items-center">
                                            <i class="bi bi-hourglass-split me-2 fs-5"></i>
                                            <h6 class="mb-0">Cálculo del plazo de respuesta</h6>
                                        </div>
                                        <span class="badge bg-light text-primary border" id="sla-pill">Según tipo de trámite</span>
                                    </div>

                                    <div class="row g-3 align-items-center">
                                        <div class="col-md-4">
                                            <div class="small text-muted text-uppercase fw-semibold mb-1">Plazo</div>
                                            <div>
                                                <span id="plazo-dias" class="badge bg-primary fs-6">-</span>
                                                <span class="ms-1">días hábiles</span>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="small text-muted text-uppercase fw-semibold mb-1">Fecha límite</div>
                                            <div id="fecha-limite" class="text-primary fw-bold">-</div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="small text-muted text-uppercase fw-semibold mb-1">Hora de corte</div>
                                            <div><span id="corte-horario">-</span></div>
                                        </div>
                                    </div>

                                    <hr class="my-3">

                                    <div class="small text-muted d-flex align-items-start">
                                        <i class="bi bi-info-circle me-2 mt-1"></i>
                                        <span id="plazo-origen">-</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    """),
                    Row(
                        Column(
                            HTML('<div class="form-check form-switch wizard-inline-switch mb-1">'),
                            Field('requiere_respuesta', css_class='form-check-input', id='id_radicar-requiere_respuesta'),
                            HTML('<span id="tipo-tramite-plazo-badge" class="badge bg-success ms-2" style="display:none;"><i class="bi bi-clock-fill me-1"></i>Plazo automático</span>'),
                            HTML('</div>'),
                            HTML('<small class="text-muted" id="sla-hint"><i class="bi bi-info-circle me-1"></i>Se activa automáticamente si el tipo de trámite tiene plazo de respuesta configurado.</small>'),
                            css_class='col-lg-6 mb-3'
                        ),
                        Column(Field('tiempo_respuesta'), css_class='col-lg-6 mb-3', id='div_id_radicar-tiempo_respuesta'),
                    ),
                    HTML("""
                        <div class="mb-0">
                            <label for="adjuntos_entrada" class="form-label fw-semibold">
                                <i class="bi bi-paperclip me-1"></i>Adjuntar documentos
                            </label>
                            <input type="file" name="adjuntos_entrada" id="adjuntos_entrada" multiple 
                                   class="form-control" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.tiff,.bmp,.xls,.xlsx,.zip">
                            <div class="form-text">
                                <small class="text-muted">
                                    <i class="bi bi-info-circle me-1"></i>
                                    Formatos permitidos: PDF, Word, imágenes, Excel y ZIP. 
                                    Máximo 10 archivos, 15MB total por correspondencia.
                                </small>
                            </div>
                            <div class="alert alert-info mt-2 mb-0" id="adjuntos-info" role="alert" style="display: none;">
                                <i class="bi bi-lightbulb me-1"></i>
                                <strong>Sugerencia:</strong> Si tiene el escaneo del documento físico, puede adjuntarlo aquí.
                            </div>
                        </div>
                    """),
                    css_class='wizard-card mb-0'
                ),
                css_id='wizard-step-radicacion-1',
                css_class='wizard-step-pane active'
            ),

            Div(
                HTML("""
                    <div class="wizard-step-header mb-3">
                        <span class="wizard-step-eyebrow">Paso 2</span>
                        <h6 class="wizard-step-title mb-1"><i class="bi bi-diagram-3 me-2 text-primary"></i>Segunda parte: distribución inicial</h6>
                        <p class="wizard-step-copy mb-0">Decida si quiere dejar el radicado asignado de inmediato o mantener la radicación convencional.</p>
                    </div>
                """),
                Div(
                    Div(
                        Field('distribuir_rapido'),
                        HTML('<small class="text-muted d-block mt-1">Si se activa, podrá dejarlo solo en el responsable principal o ampliar el acceso a toda la oficina destino y a oficinas adicionales.</small>'),
                        css_class='form-check form-switch wizard-toggle-block mb-0'
                    ),
                    css_class='wizard-card wizard-card-highlight mb-3'
                ),
                Div(
                    Row(
                        Column(Field('usuario_destino_rapido'), css_class='col-lg-5 mb-3'),
                        Column(Field('observaciones_distribucion'), css_class='col-lg-7 mb-3'),
                    ),
                    Div(
                        Field('compartir_con_toda_oficina'),
                        HTML('<small class="text-muted d-block mt-1">Desmarcado: solo verá el radicado el responsable principal. Marcado: también lo verá toda la oficina destino.</small>'),
                        css_class='form-check form-switch mb-3'
                    ),
                    HTML("""
                        <div class="alert alert-primary border small mb-3">
                            <i class="bi bi-person-badge me-1"></i>
                            El responsable principal siempre quedará asignado. Compartir con toda la oficina destino ahora es opcional.
                        </div>
                    """),
                    Field('otras_oficinas', css_class='mb-3'),
                    HTML("""
                        <div class="alert alert-light border small mb-0">
                            <i class="bi bi-info-circle me-1"></i>
                            Las oficinas adicionales recibirán acceso de solo lectura. La asignación principal seguirá siendo para un usuario de la oficina destino.
                        </div>
                    """),
                    css_id='quick-distribution-section',
                    css_class='wizard-card bg-light-subtle border rounded-3 p-3',
                    style='display:none;',
                ),
                css_id='wizard-step-radicacion-2',
                css_class='wizard-step-pane d-none'
            ),
            
            # No incluir botón Submit aquí, estará en el modal footer
        )

    def clean(self):
        cleaned_data = super().clean()
        requiere_respuesta = cleaned_data.get('requiere_respuesta')
        tiempo_respuesta = cleaned_data.get('tiempo_respuesta')
        tipo_tramite_codigo = cleaned_data.get('tipo_tramite')

        # Verificar si el tipo de trámite tiene días de respuesta configurados
        tiene_plazo_tipo_tramite = False
        if tipo_tramite_codigo:
            try:
                tipo_obj = TipoTramite.objects.get(codigo=tipo_tramite_codigo, activo=True)
                if tipo_obj.dias_respuesta is not None:
                    tiene_plazo_tipo_tramite = True
            except TipoTramite.DoesNotExist:
                pass

        # Validación: Si requiere respuesta y el tipo de trámite no tiene plazo,
        # el tiempo de respuesta manual es obligatorio
        if requiere_respuesta and not tiene_plazo_tipo_tramite and not tiempo_respuesta:
            self.add_error('tiempo_respuesta', 'Debe seleccionar un tiempo de respuesta si la correspondencia lo requiere y el tipo de trámite no tiene plazo configurado.')

        # Limpieza: Si no requiere respuesta, asegurar que tiempo_respuesta sea None
        if not requiere_respuesta:
            cleaned_data['tiempo_respuesta'] = None

        distribuir_rapido = cleaned_data.get('distribuir_rapido')
        usuario_destino_rapido = cleaned_data.get('usuario_destino_rapido')
        oficina_destino = cleaned_data.get('oficina_destino')
        otras_oficinas = cleaned_data.get('otras_oficinas')

        if distribuir_rapido:
            if not usuario_destino_rapido:
                self.add_error('usuario_destino_rapido', 'Debe seleccionar un responsable principal si activa la distribución inmediata.')
            elif not hasattr(usuario_destino_rapido, 'perfil') or usuario_destino_rapido.perfil.oficina_id != getattr(oficina_destino, 'id', None):
                self.add_error('usuario_destino_rapido', 'El usuario seleccionado debe pertenecer a la oficina destino elegida.')

        if oficina_destino and otras_oficinas and otras_oficinas.filter(pk=oficina_destino.pk).exists():
            self.add_error('otras_oficinas', 'La oficina destino principal no puede repetirse dentro de las oficinas adicionales.')

        return cleaned_data

# --- Formulario para Entidad Externa (NUEVO) ---
class EntidadExternaForm(forms.ModelForm):
    """Formulario para crear y editar Entidades Externas."""

    def clean_dominio(self):
        dominio = self.cleaned_data.get('dominio')
        self.dominios_extraidos = extraer_dominios_candidatos(dominio)
        return self.dominios_extraidos[0] if self.dominios_extraidos else None

    def save(self, commit=True):
        entidad = super().save(commit=commit)
        if commit:
            dominios_adicionales = getattr(self, 'dominios_extraidos', [])[1:]
            if dominios_adicionales:
                entidad.registrar_dominios(dominios_adicionales)
        return entidad

    class Meta:
        model = EntidadExterna
        fields = ['nombre', 'nit', 'direccion', 'telefono', 'dominio']  # 🔥 Añadido dominio
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Nombre completo de la entidad',
                'class': 'form-control'
            }),
            'nit': forms.TextInput(attrs={
                'placeholder': 'NIT o identificador (opcional)',
                'class': 'form-control'
            }),
            'direccion': forms.TextInput(attrs={
                'placeholder': 'Dirección (opcional)',
                'class': 'form-control'
            }),
            'telefono': forms.TextInput(attrs={
                'placeholder': 'Teléfono principal (opcional)',
                'class': 'form-control'
            }),
            'dominio': forms.TextInput(attrs={
                'placeholder': 'ejemplo.com o varios separados por coma',
                'class': 'form-control'
            })  # 🔥 Widget para dominio
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False  # No renderizar el tag <form>
        self.helper.layout = Layout(
            Field('nombre', css_class="mb-3"),
            Row(
                Column(Field('nit'), css_class='form-group col-md-6 mb-3'),
                Column(Field('telefono'), css_class='form-group col-md-6 mb-3')
            ),
            Field('direccion', css_class="mb-3"),
            Field('dominio', css_class="mb-3"),  # 🔥 Añadido dominio
        )


# ==============================================
# === FORMULARIOS PARA CORRESPONDENCIA SALIDA ===
# ==============================================
from django import forms
from django.forms.widgets import FileInput
from .models import CorrespondenciaSalida, Contacto

class RespuestaCorrespondenciaForm(forms.ModelForm):
    destinatarios = forms.ModelMultipleChoiceField(
        queryset=Contacto.objects.none(),
        required=False,
        label="Destinatarios (máx. 50)",
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2', 'data-placeholder': 'Seleccionar contactos...'})
    )
    motivo_respuesta_discrecional = forms.CharField(
        required=False,
        label='Motivo de la respuesta discrecional',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Explique por qué esta correspondencia se responderá aunque no requería respuesta.'
        })
    )

    class Meta:
        model = CorrespondenciaSalida
        fields = ['asunto', 'cuerpo', 'motivo_respuesta_discrecional']
        widgets = {
            'asunto': forms.TextInput(attrs={
                'placeholder': 'Asunto claro y conciso',
                'class': 'form-control'
            }),
            'cuerpo': forms.Textarea(attrs={
                'rows': 10,
                'placeholder': 'Escriba aquí el cuerpo de la respuesta...',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.oficina_emisora = kwargs.pop('oficina_emisora', None)
        self.es_respuesta_discrecional = kwargs.pop('es_respuesta_discrecional', False)
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        # Filtrar destinatarios por oficina emisora si se proporciona
        if self.oficina_emisora:
            self.fields['destinatarios'].queryset = Contacto.objects.order_by('entidad_externa__nombre', 'apellidos', 'nombres')
        else:
            self.fields['destinatarios'].queryset = Contacto.objects.order_by('entidad_externa__nombre', 'apellidos', 'nombres')

        # Inicializar selección en edición
        if instance:
            self.fields['destinatarios'].initial = instance.destinatarios.values_list('contacto_id', flat=True)

        if self.es_respuesta_discrecional:
            self.fields['motivo_respuesta_discrecional'].required = True
            self.fields['motivo_respuesta_discrecional'].help_text = (
                'Este motivo quedará registrado como trazabilidad de la respuesta discrecional.'
            )

    def clean_destinatarios(self):
        contactos = self.cleaned_data.get('destinatarios')
        # Permitir guardar borrador sin destinatarios; validaremos en aprobación
        if not contactos:
            return contactos
        # Validar límite y pertenencia a oficina
        if contactos.count() > 50:
            raise forms.ValidationError("No se permiten más de 50 destinatarios.")
        return contactos

    def clean(self):
        cleaned_data = super().clean()
        motivo = (cleaned_data.get('motivo_respuesta_discrecional') or '').strip()
        if self.es_respuesta_discrecional and not motivo:
            self.add_error('motivo_respuesta_discrecional', 'Debe indicar el motivo de la respuesta discrecional.')
        return cleaned_data

class AprobarRechazarRespuestaForm(forms.Form):
    motivo_rechazo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label="Motivo del Rechazo"
    )

# --- Formulario AVANZADO para Filtro de Historial ---

# Crear listas de opciones para estados combinados
ESTADOS_ENTRADA_CHOICES = [('', '--- Estado Entrada ---')] + [(k, f"Entrada - {v}") for k, v in ESTADOS_CORRESPONDENCIA]
ESTADOS_SALIDA_CHOICES = [('', '--- Estado Salida ---')] + [(k, f"Salida - {v}") for k, v in ESTADOS_SALIDA]
# Combinar todos los estados posibles para un único filtro (opcional, podría ser complejo) 
# ALL_STATUS_CHOICES = [('', '-- Cualquier Estado --')] + ESTADOS_ENTRADA_CHOICES[1:] + ESTADOS_SALIDA_CHOICES[1:]

TIPO_CHOICES = (
    ('', 'Entrada y Salida'),
    ('Entrada', 'Solo Entrada'),
    ('Salida', 'Solo Salida'),
)

class HistorialFilterForm(forms.Form):
    search_term = forms.CharField(
        required=False,
        label="Buscar (Asunto, Radicado...)",
        widget=forms.TextInput(attrs={'placeholder': 'Término de búsqueda...', 'class': 'form-control-sm'})
    )
    oficina = forms.CharField(
        required=False,
        label="Oficina",
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar por nombre de oficina...', 
            'class': 'form-control-sm',
            'list': 'oficinas-list'
        })
    )
    serie = forms.CharField(
        required=False,
        label="Serie",
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar por nombre de serie...', 
            'class': 'form-control-sm',
            'list': 'series-list'
        })
    )
    subserie = forms.CharField(
        required=False,
        label="Subserie",
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar por nombre de subserie...', 
            'class': 'form-control-sm',
            'list': 'subseries-list'
        })
    )
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        label="Tipo",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    # Usaremos dos campos de estado separados por simplicidad en el filtrado de la vista
    estado_entrada = forms.ChoiceField(
        choices=ESTADOS_ENTRADA_CHOICES,
        required=False,
        label="Estado Entrada",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    estado_salida = forms.ChoiceField(
        choices=ESTADOS_SALIDA_CHOICES,
        required=False,
        label="Estado Salida",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    fecha_inicio = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )
    fecha_fin = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )
    remitente = forms.CharField(
        required=False,
        label="De (Remitente)",
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar remitente...', 
            'class': 'form-control-sm',
        })
    )
    destinatario = forms.CharField(
        required=False,
        label="Para (Destinatario)",
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar destinatario...', 
            'class': 'form-control-sm',
        })
    )

    VENCIMIENTO_CHOICES = (
        ('', '--- Estado Vencimiento ---'),
        ('VENCIDO', 'Vencido'),
        ('HOY', 'Vence Hoy'),
        ('PROXIMO', 'Próximo a vencer (1-2 días)'),
        ('POR_VENCER', 'Por vencer (3-5 días)'),
        ('A_TIEMPO', 'A tiempo (+5 días)'),
        ('RESPONDIDA', 'Ya respondida'),
        ('NO_REQUIERE', 'No requiere respuesta'),
    )
    
    estado_vencimiento = forms.ChoiceField(
        choices=VENCIMIENTO_CHOICES,
        required=False,
        label="Vencimiento",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get' # El filtro se aplica vía GET
        self.helper.form_class = 'form-horizontal' # O form-vertical si prefieres
        self.helper.label_class = 'col-lg-3' # Ajustar según necesidad
        self.helper.field_class = 'col-lg-9' # Ajustar según necesidad
        self.helper.layout = Layout(
            Row(
                Column(Field('search_term'), css_class='col-md-4 mb-2'),
                Column(Field('tipo'), css_class='col-md-2 mb-2'),
                Column(Field('oficina'), css_class='col-md-3 mb-2'),
                Column(Field('usuario'), css_class='col-md-3 mb-2')
            ),
            Row(
                Column(Field('serie'), css_class='col-md-4 mb-2'),
                Column(Field('subserie'), css_class='col-md-4 mb-2'),
                Column(Field('estado_entrada'), css_class='col-md-2 mb-2'),
                Column(Field('estado_salida'), css_class='col-md-2 mb-2')
            ),
            Row(
                 Column(Field('fecha_inicio'), css_class='col-md-3 mb-2'),
                 Column(Field('fecha_fin'), css_class='col-md-3 mb-2'),
                 Column(
                     Submit('submit', 'Aplicar Filtros', css_class='btn btn-primary btn-sm w-100'), # Botón dentro de la última fila
                     css_class='col-md-3 align-self-end mb-2' # Alinear al final
                 ),
                 Column(
                     Submit('reset', 'Limpiar Filtros', css_class='btn btn-secondary btn-sm w-100'), # Usar Submit tipo reset como alternativa
                     css_class='col-md-3 align-self-end mb-2'
                 )
            ),
        )
        # No añadimos botón submit global, está en el layout
        # self.helper.add_input(Submit('submit', 'Filtrar'))


# ==============================================
# === FORMULARIOS PARA GRUPOS Y COMUNICACIONES ===
# ==============================================

class GrupoAgendaForm(forms.ModelForm):
    class Meta:
        model = GrupoAgenda
        fields = ['nombre', 'descripcion', 'contactos', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del grupo'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción (opcional)'}),
            'contactos': forms.SelectMultiple(attrs={'class': 'form-select select2', 'data-placeholder': 'Seleccionar contactos...'}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('oficina_propietaria', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('nombre'),
            Field('descripcion'),
            Field('contactos'),
            Field('activo'),
            Submit('submit', 'Guardar', css_class='btn btn-primary mt-3')
        )
        # Mostrar todos los contactos globales disponibles
        self.fields['contactos'].queryset = Contacto.objects.order_by('entidad_externa__nombre', 'apellidos', 'nombres')

    def clean_contactos(self):
        contactos = self.cleaned_data.get('contactos')
        if not contactos:
            return contactos
        # emails obligatorios
        sin_email = contactos.filter(correo_electronico__isnull=True) | contactos.filter(correo_electronico='')
        if sin_email.exists():
            raise forms.ValidationError('Todos los contactos del grupo deben tener correo electrónico.')
        return contactos


class ComunicacionMasivaForm(forms.ModelForm):
    grupos = forms.ModelMultipleChoiceField(
        queryset=GrupoAgenda.objects.none(),
        required=False,
        label='Grupos',
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2', 'data-placeholder': 'Seleccionar grupos...'})
    )

    class Meta:
        model = ComunicacionMasiva
        fields = ['asunto', 'cuerpo']
        widgets = {
            'asunto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Asunto de la comunicación'}),
            'cuerpo': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Cuerpo del mensaje'}),
        }

    def __init__(self, *args, **kwargs):
        self.oficina_emisora = kwargs.pop('oficina_emisora', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('asunto'),
            Field('cuerpo'),
            Field('grupos'),
            Submit('submit', 'Guardar borrador', css_class='btn btn-secondary mt-3'),
        )
        if self.oficina_emisora:
            self.fields['grupos'].queryset = GrupoAgenda.objects.filter(oficina_propietaria=self.oficina_emisora, activo=True).order_by('nombre')
        else:
            self.fields['grupos'].queryset = GrupoAgenda.objects.none()

# =============================================
# === COMUNICACIONES INTERNAS (OFICIOS) ===
# =============================================
from .models import ComunicacionInterna

class ComunicacionInternaForm(forms.ModelForm):
    """Formulario para crear comunicaciones internas (Oficios)."""
    
    # Campos virtuales para serie y subserie (no se guardan en el modelo)
    serie = forms.ModelChoiceField(
        queryset=SerieDocumental.objects.none(),
        required=False,
        label="Serie documental",
        empty_label="Seleccione una serie...",
        widget=CustomSelect(attrs={'class': 'form-select', 'id': 'id_serie_comunicacion'})
    )
    subserie = forms.ModelChoiceField(
        queryset=SubserieDocumental.objects.none(),
        required=False,
        label="Subserie documental",
        empty_label="Seleccione una serie primero...",
        widget=CustomSelect(attrs={'class': 'form-select', 'id': 'id_subserie_comunicacion'})
    )
    
    class Meta:
        model = ComunicacionInterna
        fields = [
            'tipo_distribucion',
            'fecha_documento',
            'ciudad',
            'trd',
            'es_a_toda_entidad',  # Mantener para compatibilidad
            'destinatario_oficina',
            'destinatario_usuario',
            'destinatario_proceso',
            'asunto',
            'cuerpo',
        ]
        widgets = {
            'tipo_distribucion': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_distribucion'}),
            'fecha_documento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control'}),
            'trd': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 300.25.05', 'readonly': True, 'id': 'id_trd'}),
            'es_a_toda_entidad': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_es_a_toda_entidad', 'style': 'display:none;'}),  # Oculto, se maneja con tipo_distribucion
            'destinatario_oficina': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Seleccionar Oficina Destino...'}),
            'destinatario_usuario': forms.Select(attrs={'class': 'form-select select2', 'data-placeholder': 'Seleccionar Usuario (Opcional)...'}),
            'destinatario_proceso': forms.Select(attrs={'class': 'form-select', 'data-placeholder': 'Seleccionar Proceso...'}),
            'asunto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Asunto del Oficio'}),
            'cuerpo': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Escriba el contenido del oficio aquí...'}),
        }
        labels = {
            'trd': 'Código TRD',
            'es_a_toda_entidad': 'Enviar a toda la entidad (requiere firma digital)',
            'destinatario_oficina': 'Para (Oficina)',
            'destinatario_usuario': 'Para (Funcionario Específico - Opcional)',
        }
        help_texts = {
            'es_a_toda_entidad': 'Si marca esta opción, la comunicación se enviará a todos los usuarios del sistema y requerirá firma digital del líder antes de distribuirse.',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.helper = FormHelper()
        self.helper.form_tag = False  # No generar <form> tag, lo manejamos en el template
        self.helper.layout = Layout(
            Row(
                Column(Field('ciudad'), css_class='col-md-6 mb-3'),
                Column(Field('fecha_documento'), css_class='col-md-6 mb-3'),
            ),
            Row(
                Column(Field('serie'), css_class='col-md-6 mb-3'),
                Column(Field('subserie'), css_class='col-md-6 mb-3'),
            ),
            Field('trd', css_class='mb-3'),
            # Checkbox para enviar a toda la entidad
            Div(
                Field('es_a_toda_entidad', wrapper_class='form-check'),
                css_class='mb-3 p-3 border rounded bg-light'
            ),
            # Campos de destinatario (se ocultan con JS si es a toda la entidad)
            Div(
                Row(
                    Column(Field('destinatario_oficina'), css_class='col-md-6 mb-3'),
                    Column(Field('destinatario_usuario'), css_class='col-md-6 mb-3'),
                ),
                css_id='destinatario_fields'
            ),
            Field('asunto', css_class='mb-3'),
            Field('cuerpo', css_class='mb-3'),
            # Los botones se manejan en el template para poder mostrar texto dinámico
            # según el rol del usuario (líder vs no líder)
        )
        
        self.fields['serie'].queryset = queryset_series_comunicacion_interna()
        self.fields['subserie'].queryset = queryset_subseries_comunicacion_interna()

        if self.fields['serie'].queryset.count() == 1:
            self.initial.setdefault('serie', self.fields['serie'].queryset.first())
        if self.fields['subserie'].queryset.count() == 1:
            self.initial.setdefault('subserie', self.fields['subserie'].queryset.first())
        
        # Filtro dinámico de usuarios por oficina destino se debería manejar con JS, 
        # pero aquí podemos precargar todos los usuarios ordenados.
        self.fields['destinatario_usuario'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Hacer destinatario_oficina no requerido (puede ser a toda la entidad/proceso)
        self.fields['destinatario_oficina'].required = False
        self.fields['destinatario_proceso'].required = False
        
        # Cargar procesos disponibles
        self.fields['destinatario_proceso'].queryset = Proceso.objects.all().order_by('nombre')
        
        # Configurar subseries dependientes de serie
        if 'serie' in self.data and self.data.get('serie'):
            try:
                serie_id = int(self.data.get('serie'))
                self.fields['subserie'].queryset = queryset_subseries_comunicacion_interna().filter(serie_id=serie_id)
            except (ValueError, TypeError):
                self.fields['subserie'].queryset = SubserieDocumental.objects.none()
        elif self.initial.get('serie'):
            self.fields['subserie'].queryset = queryset_subseries_comunicacion_interna().filter(serie=self.initial['serie'])
        
        # Inicializar fecha hoy
        if not self.instance.pk and not self.initial.get('fecha_documento'):
            self.initial['fecha_documento'] = timezone.now().date()
        
        # Inicializar tipo_distribucion si no existe
        if not self.instance.pk and not self.initial.get('tipo_distribucion'):
            self.initial['tipo_distribucion'] = 'USUARIO'

    def clean(self):
        """Validar que si no es a toda la entidad, se requiere oficina destino."""
        cleaned_data = super().clean()
        es_a_toda_entidad = cleaned_data.get('es_a_toda_entidad')
        destinatario_oficina = cleaned_data.get('destinatario_oficina')
        serie = cleaned_data.get('serie')
        subserie = cleaned_data.get('subserie')
        
        if not es_a_toda_entidad and not destinatario_oficina:
            self.add_error('destinatario_oficina', 'Debe seleccionar una oficina destino o marcar "Enviar a toda la entidad".')

        if not serie or not subserie:
            try:
                serie, subserie = obtener_clasificacion_comunicacion_interna()
                cleaned_data['serie'] = serie
                cleaned_data['subserie'] = subserie
            except ValidationError as exc:
                raise ValidationError(exc.message)

        if serie and subserie and subserie.serie_id != serie.id:
            self.add_error('subserie', 'La subserie seleccionada no pertenece a la serie indicada.')

        if serie and subserie:
            try:
                cleaned_data['serie'], cleaned_data['subserie'] = validar_clasificacion_comunicacion_interna(serie, subserie)
            except ValidationError as exc:
                self.add_error('serie', exc.message)
        
        # Si es a toda la entidad, limpiar destinatario_oficina y destinatario_usuario
        if es_a_toda_entidad:
            cleaned_data['destinatario_oficina'] = None
            cleaned_data['destinatario_usuario'] = None
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.serie_documental = self.cleaned_data.get('serie')
        instance.subserie_documental = self.cleaned_data.get('subserie')
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ComunicacionInternaRespuestaForm(forms.ModelForm):
    """Formulario simplificado para crear respuestas a comunicaciones internas.
    No incluye campos de destinatario ya que se asignan automáticamente.
    Incluye serie y subserie para calcular TRD automáticamente.
    """
    
    # Campos virtuales para serie y subserie
    serie = forms.ModelChoiceField(
        queryset=SerieDocumental.objects.none(),
        required=False,
        label="Serie documental",
        empty_label="Seleccione una serie (opcional)...",
        widget=CustomSelect(attrs={'class': 'form-select', 'id': 'id_serie_respuesta'})
    )
    subserie = forms.ModelChoiceField(
        queryset=SubserieDocumental.objects.none(),
        required=False,
        label="Subserie documental",
        empty_label="Seleccione una serie primero...",
        widget=CustomSelect(attrs={'class': 'form-select', 'id': 'id_subserie_respuesta'})
    )
    
    class Meta:
        model = ComunicacionInterna
        fields = [
            'fecha_documento',
            'ciudad',
            'trd',
            'asunto',
            'cuerpo',
        ]
        widgets = {
            'fecha_documento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control'}),
            'trd': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Se autocompleta al seleccionar subserie', 'readonly': True, 'style': 'background-color: #e9ecef; cursor: not-allowed;'}),
            'asunto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Asunto de la respuesta'}),
            'cuerpo': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Escriba el contenido de la respuesta aquí...'}),
        }
        labels = {
            'trd': 'Código TRD',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['serie'].queryset = queryset_series_comunicacion_interna()
        self.fields['subserie'].queryset = queryset_subseries_comunicacion_interna()

        if self.fields['serie'].queryset.count() == 1:
            self.initial.setdefault('serie', self.fields['serie'].queryset.first())
        if self.fields['subserie'].queryset.count() == 1:
            self.initial.setdefault('subserie', self.fields['subserie'].queryset.first())
        
        # Inicializar fecha hoy
        if not self.instance.pk and not self.initial.get('fecha_documento'):
            self.initial['fecha_documento'] = timezone.now().date()
        
        # Configurar subseries dependientes de serie
        if 'serie' in self.data and self.data.get('serie'):
            try:
                serie_id = int(self.data.get('serie'))
                self.fields['subserie'].queryset = queryset_subseries_comunicacion_interna().filter(serie_id=serie_id)
            except (ValueError, TypeError):
                self.fields['subserie'].queryset = SubserieDocumental.objects.none()
        elif self.initial.get('serie'):
            self.fields['subserie'].queryset = queryset_subseries_comunicacion_interna().filter(serie=self.initial['serie'])

    def clean(self):
        cleaned_data = super().clean()
        serie = cleaned_data.get('serie')
        subserie = cleaned_data.get('subserie')

        if not serie or not subserie:
            try:
                serie, subserie = obtener_clasificacion_comunicacion_interna()
                cleaned_data['serie'] = serie
                cleaned_data['subserie'] = subserie
            except ValidationError as exc:
                raise ValidationError(exc.message)

        if serie and subserie and subserie.serie_id != serie.id:
            self.add_error('subserie', 'La subserie seleccionada no pertenece a la serie indicada.')

        if serie and subserie:
            try:
                cleaned_data['serie'], cleaned_data['subserie'] = validar_clasificacion_comunicacion_interna(serie, subserie)
            except ValidationError as exc:
                self.add_error('serie', exc.message)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.serie_documental = self.cleaned_data.get('serie')
        instance.subserie_documental = self.cleaned_data.get('subserie')
        if commit:
            instance.save()
            self.save_m2m()
        return instance


# =============================================================================
# FORMULARIOS PARA CORRESPONDENCIA URGENTE
# =============================================================================

class UrgenciaRadicacionForm(forms.ModelForm):
    """
    Formulario para radicar correspondencia urgente desde correo entrante.
    Integrado con cascadas dinámicas Serie -> Subserie.
    """
    
    class Meta:
        model = CorrespondenciaUrgencia
        fields = [
            'serie',
            'subserie',
            'oficina_destino',
            'horas_limite',
            'prioridad',
            'motivo_urgencia',
            'observaciones'
        ]
        widgets = {
            'serie': forms.Select(attrs={'class': 'form-select', 'id': 'id_serie_urgencia'}),
            'subserie': forms.Select(attrs={'class': 'form-select', 'id': 'id_subserie_urgencia'}),
            'oficina_destino': forms.Select(attrs={'class': 'form-select'}),
            'horas_limite': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '72',
                'value': '24'
            }),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
            'motivo_urgencia': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Indique por qué esta correspondencia es urgente...'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales (opcional)...'
            })
        }
        labels = {
            'serie': 'Serie Documental *',
            'subserie': 'Subserie',
            'oficina_destino': 'Oficina Destino *',
            'horas_limite': 'Horas Límite (laborales) *',
            'prioridad': 'Prioridad *',
            'motivo_urgencia': 'Motivo de Urgencia *',
            'observaciones': 'Observaciones',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mostrar solo nombre de serie (sin código)
        self.fields['serie'].label_from_instance = lambda obj: obj.nombre
        
        # Subserie depende de Serie (cascade dinámico)
        self.fields['subserie'].queryset = SubserieDocumental.objects.none()
        self.fields['subserie'].required = False
        # Mostrar solo nombre de subserie (sin código ni serie)
        self.fields['subserie'].label_from_instance = lambda obj: obj.nombre
        
        if 'serie' in self.data:
            try:
                serie_id = int(self.data.get('serie'))
                self.fields['subserie'].queryset = SubserieDocumental.objects.filter(
                    serie_id=serie_id
                ).order_by('nombre')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.serie:
            self.fields['subserie'].queryset = self.instance.serie.subseries.order_by('nombre')
        
        # Crispy Forms Helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column(Field('serie'), css_class='col-md-6'),
                Column(Field('subserie'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('oficina_destino'), css_class='col-md-8'),
                Column(Field('horas_limite'), css_class='col-md-4'),
            ),
            Field('prioridad'),
            Field('motivo_urgencia'),
            Field('observaciones'),
        )
        self.helper.form_tag = False
    
    def clean_horas_limite(self):
        horas = self.cleaned_data.get('horas_limite')
        if horas < 1:
            raise ValidationError('Las horas límite deben ser al menos 1')
        if horas > 72:  # Máximo 72 horas (aprox 1 semana laboral)
            raise ValidationError('Las horas límite no pueden exceder 72 (1 semana laboral)')
        return horas


class UrgenciaRespuestaForm(forms.Form):
    """Formulario para responder una urgencia"""
    
    respuesta = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'class': 'form-control',
            'placeholder': 'Escriba la respuesta a la urgencia...'
        }),
        label='Respuesta *',
        required=True
    )
    
    adjuntos = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls'
        }),
        label='Archivo Adjunto (opcional)',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('respuesta'),
            Field('adjuntos'),
        )


# =============================================================================
# FORMULARIOS DE RADICACIÓN RÁPIDA (para período de transición)
# =============================================================================

class RadicacionRapidaEntranteForm(forms.ModelForm):
    """
    Formulario SIMPLIFICADO para radicación rápida de correspondencia entrante.
    
    Diseñado para el período de transición donde se necesita registrar
    correspondencia que llega por vías externas (correo normal, físico, etc.)
    con el mínimo de campos obligatorios.
    
    Campos mínimos:
    - asunto (obligatorio)
    - oficina_destino (obligatorio)
    - remitente (opcional, permite contacto o texto libre)
    """
    
    # Campo opcional para texto libre cuando no hay contacto registrado
    remitente_texto = forms.CharField(
        max_length=255,
        required=False,
        label="Remitente (texto libre)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Juan Pérez - Alcaldía Municipal'
        }),
        help_text="Use este campo si el remitente no está registrado como contacto."
    )
    
    # Medio de recepción: explícito para que carguen las opciones (Físico/Electrónico)
    medio_recepcion = forms.ChoiceField(
        choices=[('', '-- Seleccionar medio --')] + list(MEDIO_RECEPCION_CHOICES),
        required=True,
        label="Medio de Recepción",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
        })
    )
    
    # Campo para archivos adjuntos (escaneos) - se permite múltiples en el template
    adjuntos_archivos = forms.FileField(
        required=False,
        label="Adjuntar escaneos o documentos",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xls,.xlsx,.zip'
        }),
        help_text="Puede seleccionar múltiples archivos (PDF, Word, imágenes, Excel, ZIP)"
    )
    
    class Meta:
        model = Correspondencia
        fields = [
            'remitente',
            'asunto',
            'oficina_destino',
            'medio_recepcion',
            # Campos temporales (todos opcionales)
            'fecha_recepcion_documento',
            'tipo_tramite',
            'entidad_persona_remitente',
            'funcionario_responsable_tramite',
            'email_funcionario_responsable',
            'clasificacion_comunicacion',
            'numero_folios',
            'anexos',
            'medio_recibido',
            'direccion_correo_remitente',
            'empresa_transportadora',
            'numero_guia',
            'fecha_limite_respuesta_manual',
            'fecha_primer_seguimiento',
            'fecha_segundo_seguimiento',
            'fecha_notificacion_vencimiento',
            'fecha_respuesta',
            'estado_respuesta',
            'radicado_enviado_respuesta',
        ]
        widgets = {
            'remitente': forms.Select(attrs={'class': 'form-select select2'}),
            'asunto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Asunto de la correspondencia...',
                'required': 'required',
            }),
            'oficina_destino': forms.Select(attrs={
                'class': 'form-select select2',
                'required': 'required',
            }),
            'tipo_tramite': forms.Select(attrs={
                'class': 'form-select select2',
                'data-calculo-fecha': 'true',  # Para trigger JS automático
            }),
            'fecha_recepcion_documento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'entidad_persona_remitente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entidad o persona remitente',
            }),
            'funcionario_responsable_tramite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del funcionario responsable',
            }),
            'email_funcionario_responsable': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@funcionario.com',
            }),
            'clasificacion_comunicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Clasificación de la comunicación',
            }),
            'numero_folios': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de folios',
                'min': 0,
            }),
            'anexos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Anexos',
            }),
            'medio_recibido': forms.Select(attrs={'class': 'form-select select2'}),
            'direccion_correo_remitente': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
            }),
            'empresa_transportadora': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Empresa transportadora (opcional)',
            }),
            'numero_guia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de guía (opcional)',
            }),
            'fecha_limite_respuesta_manual': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'fecha_primer_seguimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'fecha_segundo_seguimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'fecha_notificacion_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'fecha_respuesta': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'estado_respuesta': forms.Select(attrs={'class': 'form-select'}),
            'radicado_enviado_respuesta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Radicado enviado para respuesta',
            }),
        }
        labels = {
            'remitente': 'Remitente (contacto registrado)',
            'asunto': 'Asunto *',
            'oficina_destino': 'Oficina Destino *',
            'fecha_recepcion_documento': 'Fecha de recepción del documento',
            'tipo_tramite': 'Tipo de trámite',
            'entidad_persona_remitente': 'Entidad o persona remitente',
            'funcionario_responsable_tramite': 'Nombre del funcionario responsable del trámite',
            'email_funcionario_responsable': 'Correo electrónico del funcionario responsable',
            'clasificacion_comunicacion': 'Clasificación de la comunicación',
            'numero_folios': 'Número de folios',
            'anexos': 'Anexos',
            'medio_recibido': 'Medio de recibido',
            'direccion_correo_remitente': 'Dirección de correo del remitente',
            'empresa_transportadora': 'Empresa transportadora (opcional)',
            'numero_guia': 'Número de guía (opcional)',
            'fecha_limite_respuesta_manual': 'Fecha límite de respuesta',
            'fecha_primer_seguimiento': 'Fecha de 1° seguimiento',
            'fecha_segundo_seguimiento': 'Fecha de 2° seguimiento',
            'fecha_notificacion_vencimiento': 'Fecha de notificación de vencimiento (si aplica)',
            'fecha_respuesta': 'Fecha de respuesta',
            'estado_respuesta': 'Estado de la respuesta',
            'radicado_enviado_respuesta': 'Radicado enviado para respuesta',
        }
    
    def __init__(self, *args, **kwargs):
        defer_select_options = kwargs.pop('defer_select_options', False)
        super().__init__(*args, **kwargs)
        # Remitente: permitir vacio y mostrar todos los contactos
        self.fields['remitente'].required = False
        self.fields['remitente'].empty_label = "-- Seleccionar contacto --"
        if defer_select_options:
            self.fields['remitente'].queryset = Contacto.objects.none()
            self.fields['oficina_destino'].queryset = OficinaProductora.objects.none()
        else:
            self.fields['remitente'].queryset = Contacto.objects.all().select_related('entidad_externa')
            self.fields['oficina_destino'].queryset = OficinaProductora.objects.order_by('nombre')
        self.fields['oficina_destino'].empty_label = "-- Seleccionar oficina --"
        
        # Cargar tipos de trámite dinámicamente desde la base de datos
        if 'tipo_tramite' in self.fields:
            tipos_activos = TipoTramite.objects.filter(activo=True).order_by('orden', 'codigo')
            choices = [('', '---------')]
            for tipo in tipos_activos:
                choices.append((tipo.codigo, tipo.get_choice_display()))
            self.fields['tipo_tramite'].choices = choices
            # Actualizar widget con data attribute para JavaScript
            self.fields['tipo_tramite'].widget.attrs['data-tipo-tramite'] = 'true'
        
        # Campos temporales: todos opcionales
        for f in [
            'fecha_recepcion_documento', 'tipo_tramite', 'entidad_persona_remitente', 'funcionario_responsable_tramite',
            'email_funcionario_responsable', 'clasificacion_comunicacion',
            'numero_folios', 'anexos', 'medio_recibido', 'direccion_correo_remitente',
            'empresa_transportadora', 'numero_guia', 'fecha_limite_respuesta_manual',
            'fecha_primer_seguimiento', 'fecha_segundo_seguimiento', 'fecha_notificacion_vencimiento',
            'fecha_respuesta', 'estado_respuesta', 'radicado_enviado_respuesta'
        ]:
            if f in self.fields:
                self.fields[f].required = False

        # Estado de respuesta: solo tres opciones (radicación rápida)
        if 'estado_respuesta' in self.fields:
            self.fields['estado_respuesta'].choices = [
                c for c in ESTADO_RESPUESTA_RAPIDA_CHOICES if c[0]
            ]
    
    def clean(self):
        cleaned_data = super().clean()
        remitente = cleaned_data.get('remitente')
        remitente_texto = cleaned_data.get('remitente_texto', '').strip()

        # Auto-asignar estado de la respuesta según fechas (solo para radicación rápida)
        fecha_respuesta = cleaned_data.get('fecha_respuesta')
        fecha_limite = cleaned_data.get('fecha_limite_respuesta_manual')
        hoy = datetime.date.today()

        if fecha_respuesta and fecha_limite and fecha_respuesta <= fecha_limite:
            cleaned_data['estado_respuesta'] = 'RESPONDIDA'
        elif fecha_limite and not fecha_respuesta and hoy > fecha_limite:
            cleaned_data['estado_respuesta'] = 'VENCIDA'
        elif not fecha_respuesta:
            cleaned_data['estado_respuesta'] = cleaned_data.get('estado_respuesta') or 'PENDIENTE'

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)
        remitente_texto = (self.cleaned_data.get('remitente_texto') or '').strip()
        if remitente_texto:
            obj.entidad_persona_remitente = remitente_texto
        if commit:
            obj.save()
        return obj


class RadicacionRapidaSalienteForm(forms.ModelForm):
    """
    Formulario SIMPLIFICADO para radicación rápida de correspondencia saliente.
    
    Diseñado para el período de transición donde se necesita registrar
    correspondencia que sale por vías externas (correo normal, físico, etc.)
    con el mínimo de campos obligatorios.
    
    Campos mínimos:
    - asunto (obligatorio)
    - cuerpo (obligatorio - puede ser breve descripción)
    - destinatario (contacto o texto libre)
    - oficina_emisora (obligatorio)
    """
    
    # Campo para destinatario (contacto registrado)
    destinatario_contacto = forms.ModelChoiceField(
        queryset=Contacto.objects.all(),
        required=False,
        label="Destinatario (contacto registrado)",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
        }),
    )
    
    # Campo opcional para texto libre cuando no hay contacto registrado
    destinatario_texto = forms.CharField(
        max_length=255,
        required=False,
        label="Destinatario (texto libre)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Dr. García - Secretaría de Salud'
        }),
        help_text="Use este campo si el destinatario no está registrado como contacto."
    )
    
    # Campo para seleccionar la oficina emisora
    oficina_emisora = forms.ModelChoiceField(
        queryset=OficinaProductora.objects.all(),
        required=True,
        label="Oficina Emisora *",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'required': 'required',
        }),
        help_text="Oficina que genera esta correspondencia de salida."
    )
    
    class Meta:
        model = CorrespondenciaSalida
        fields = [
            'asunto',
            'cuerpo',
            'funcionario_envia',
            'fue_respondida',
            'evidencia_respuesta',
        ]
        widgets = {
            'asunto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asunto de la correspondencia...'
            }),
            'cuerpo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción breve del contenido o referencia al documento físico...'
            }),
            'funcionario_envia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Dr. Juan Pérez - Coordinador de Calidad'
            }),
            'fue_respondida': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'evidencia_respuesta': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'asunto': 'Asunto *',
            'cuerpo': 'Descripción/Contenido *',
            'funcionario_envia': 'Funcionario que envía',
            'fue_respondida': '¿Ya fue respondida?',
            'evidencia_respuesta': 'Evidencia de respuesta',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        defer_select_options = kwargs.pop('defer_select_options', False)
        super().__init__(*args, **kwargs)

        if defer_select_options:
            self.fields['destinatario_contacto'].queryset = Contacto.objects.none()
            self.fields['oficina_emisora'].queryset = OficinaProductora.objects.none()
        else:
            # Configurar destinatario
            self.fields['destinatario_contacto'].queryset = Contacto.objects.select_related(
                'entidad_externa'
            ).order_by('entidad_externa__nombre', 'apellidos', 'nombres')
            # Ordenar oficinas
            self.fields['oficina_emisora'].queryset = OficinaProductora.objects.order_by('nombre')
        self.fields['destinatario_contacto'].empty_label = "-- Sin contacto registrado --"
        self.fields['oficina_emisora'].empty_label = "-- Seleccionar oficina --"
        
        # Si hay usuario, preseleccionar su oficina
        if self.user and hasattr(self.user, 'perfil') and self.user.perfil.oficina:
            self.fields['oficina_emisora'].initial = self.user.perfil.oficina
    
    def clean(self):
        cleaned_data = super().clean()
        destinatario = cleaned_data.get('destinatario_contacto')
        destinatario_texto = cleaned_data.get('destinatario_texto', '').strip()
        
        # Validar que al menos uno esté presente
        if not destinatario and not destinatario_texto:
            raise ValidationError(
                'Debe especificar un destinatario (contacto registrado o texto libre).'
            )
        
        return cleaned_data
