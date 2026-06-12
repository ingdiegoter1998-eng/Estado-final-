from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Correspondencia, 
    HistorialCorrespondencia, 
    Contacto, 
    CorreoEntrante, 
    CorreoProblematico,
    AdjuntoCorreoEntrante, 
    AdjuntoCorreo,
    EntidadExterna,
    TipoTramite,
    # Correspondencia de Salida
    CorrespondenciaSalida,
    AdjuntoSalida,
    SalidaDestinatario,
    HistorialSalida,
    # Grupos de Agenda y Comunicaciones
    GrupoAgenda,
    ComunicacionMasiva,
    ComunicacionDestinatario,
    # Distribución Interna
    DistribucionInternaUsuario,
    # Notificaciones
    Notificacion,
    # Urgencias
    CorrespondenciaUrgencia,
    AdjuntoUrgencia,
    # Radicación Rápida
    AdjuntoCorrespondenciaRapida,
    AsistenteConversacion,
    AsistenteMensaje,
    AsistenteDocumento,
    AsistenteChunk,
    # Comunicaciones Internas
    ComunicacionInterna,
    ComunicacionInternaDestinatario,
    ComunicacionInternaDistribucion,
    HistorialComunicacionInterna,
    AnexoComunicacionInterna,
)
from .modelos_minimos_sla import TramiteTipo, SubserieTramite, CalendarioLaboral

# Modelos básicos para visualización y gestión simple

@admin.register(Correspondencia)
class CorrespondenciaAdmin(admin.ModelAdmin):
    list_display = ('numero_radicado', 'fecha_radicacion', 'asunto', 'remitente', 'oficina_destino', 'estado', 'leido_por_oficina', 'requiere_respuesta')
    list_filter = ('estado', 'leido_por_oficina', 'oficina_destino', 'serie', 'requiere_respuesta', 'fecha_radicacion')
    search_fields = ('numero_radicado', 'asunto', 'remitente__nombres', 'remitente__apellidos', 'remitente__entidad_externa__nombre')
    readonly_fields = (
        'numero_radicado',
        'fecha_radicacion',
        'plazo_respuesta_dias',
        'fecha_limite_respuesta_persist',
        'plazo_origen',
        'correo_origen_info',
        'correo_origen_cuerpo',
    )
    list_select_related = ('remitente', 'remitente__entidad_externa', 'oficina_destino', 'serie', 'subserie')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_radicado', 'fecha_radicacion', 'asunto', 'remitente', 'medio_recepcion')
        }),
        ('Clasificación Documental', {
            'fields': ('serie', 'subserie')
        }),
        ('Destino y Estado', {
            'fields': ('oficina_destino', 'usuario_destino_inicial', 'estado', 'leido_por_oficina')
        }),
        ('Respuesta', {
            'fields': ('requiere_respuesta', 'tiempo_respuesta')
        }),
        ('SLA y Plazos', {
            'fields': ('plazo_respuesta_dias', 'fecha_limite_respuesta_persist', 'plazo_origen', 'tramite_aplicado'),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': ('resumen_ia', 'sellado', 'fecha_sellado'),
            'classes': ('collapse',)
        }),
        ('Correo Origen Asociado', {
            'fields': ('correo_origen_info', 'correo_origen_cuerpo'),
        }),
    )

    def correo_origen_info(self, obj):
        correo = obj.correo_origen.first()
        if not correo:
            return 'Sin correo origen asociado.'
        return format_html(
            '<div><strong>Remitente:</strong> {}<br><strong>Asunto:</strong> {}<br><strong>Fecha IMAP:</strong> {}</div>',
            correo.remitente or '-',
            correo.asunto or '-',
            correo.fecha_lectura_imap.strftime('%Y-%m-%d %H:%M:%S') if correo.fecha_lectura_imap else '-',
        )

    correo_origen_info.short_description = 'Información del correo origen'

    def correo_origen_cuerpo(self, obj):
        correo = obj.correo_origen.first()
        if not correo:
            return 'Sin correo origen asociado.'

        modal_id = f'correo-origen-modal-{obj.pk}'
        asunto = correo.asunto or 'Sin asunto'
        cuerpo_html = correo.obtener_cuerpo_html_renderizado()
        if cuerpo_html:
            return format_html(
                '''
                <div>
                    <div style="margin-bottom:10px;"><strong>Asunto:</strong> {}</div>
                    <button type="button" class="button" onclick="document.getElementById('{}').style.display='flex'">Ver asunto y cuerpo</button>
                    <div id="{}" style="display:none; position:fixed; inset:0; background:rgba(15,23,42,.55); z-index:9999; align-items:center; justify-content:center; padding:24px;">
                        <div style="background:#fff; width:min(1100px, 96vw); max-height:90vh; border-radius:12px; overflow:hidden; box-shadow:0 20px 60px rgba(0,0,0,.25);">
                            <div style="display:flex; align-items:center; justify-content:space-between; padding:14px 18px; border-bottom:1px solid #e5e7eb;">
                                <div>
                                    <div style="font-size:12px; color:#6b7280; text-transform:uppercase; letter-spacing:.04em;">Correo origen asociado</div>
                                    <div style="font-size:16px; font-weight:600; color:#111827;">{}</div>
                                </div>
                                <button type="button" class="button" onclick="document.getElementById('{}').style.display='none'">Cerrar</button>
                            </div>
                            <div style="padding:16px; overflow:auto; max-height:calc(90vh - 70px); background:#f8fafc;">
                                <iframe sandbox="allow-same-origin" style="width:100%; min-height:68vh; border:1px solid #d1d5db; border-radius:8px; background:#fff;" srcdoc="{}"></iframe>
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                asunto,
                modal_id,
                modal_id,
                asunto,
                modal_id,
                cuerpo_html,
            )

        if correo.cuerpo_texto:
            return format_html(
                '''
                <div>
                    <div style="margin-bottom:10px;"><strong>Asunto:</strong> {}</div>
                    <button type="button" class="button" onclick="document.getElementById('{}').style.display='flex'">Ver asunto y cuerpo</button>
                    <div id="{}" style="display:none; position:fixed; inset:0; background:rgba(15,23,42,.55); z-index:9999; align-items:center; justify-content:center; padding:24px;">
                        <div style="background:#fff; width:min(1100px, 96vw); max-height:90vh; border-radius:12px; overflow:hidden; box-shadow:0 20px 60px rgba(0,0,0,.25);">
                            <div style="display:flex; align-items:center; justify-content:space-between; padding:14px 18px; border-bottom:1px solid #e5e7eb;">
                                <div>
                                    <div style="font-size:12px; color:#6b7280; text-transform:uppercase; letter-spacing:.04em;">Correo origen asociado</div>
                                    <div style="font-size:16px; font-weight:600; color:#111827;">{}</div>
                                </div>
                                <button type="button" class="button" onclick="document.getElementById('{}').style.display='none'">Cerrar</button>
                            </div>
                            <div style="padding:16px; overflow:auto; max-height:calc(90vh - 70px); background:#f8fafc;">
                                <pre style="white-space:pre-wrap; word-wrap:break-word; min-height:68vh; overflow:auto; padding:12px; border:1px solid #d1d5db; border-radius:8px; background:#fff; margin:0;">{}</pre>
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                asunto,
                modal_id,
                modal_id,
                asunto,
                modal_id,
                correo.cuerpo_texto,
            )

        return 'El correo origen no tiene cuerpo disponible.'

    correo_origen_cuerpo.short_description = 'Visualización del correo origen'

@admin.register(CorreoEntrante)
class CorreoEntranteAdmin(admin.ModelAdmin):
    list_display = ('fecha_lectura_imap', 'remitente', 'asunto', 'procesado', 'oficina_clasificada', 'serie_clasificada', 'radicado_asociado')
    list_filter = ('procesado', 'fecha_lectura_imap', 'oficina_clasificada', 'serie_clasificada')
    search_fields = ('remitente', 'asunto', 'cuerpo')
    readonly_fields = ('fecha_lectura_imap',)


@admin.register(CorreoProblematico)
class CorreoProblematicoAdmin(admin.ModelAdmin):
    list_display = ('fecha_lectura_imap', 'remitente', 'asunto', 'motivo_problema', 'resuelto', 'correo_entrante_asociado')
    list_filter = ('motivo_problema', 'resuelto', 'flujo_origen', 'carpeta_origen', 'fecha_lectura_imap')
    search_fields = ('remitente', 'asunto', 'message_id', 'detalle_problema')
    readonly_fields = ('fecha_lectura_imap', 'fecha_recibida_gmail', 'fecha_recepcion_original', 'adjuntos_resumen')

@admin.register(HistorialCorrespondencia)
class HistorialCorrespondenciaAdmin(admin.ModelAdmin):
    list_display = ('correspondencia', 'fecha_hora', 'evento', 'usuario', 'descripcion')
    list_filter = ('evento', 'fecha_hora', 'usuario')
    readonly_fields = ('fecha_hora',)

@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'entidad_externa', 'cargo', 'correo_electronico', 'telefono_contacto', 'numero_documento')
    list_filter = ('entidad_externa',)
    search_fields = ('nombres', 'apellidos', 'correo_electronico', 'numero_documento', 'entidad_externa__nombre')
    list_select_related = ('entidad_externa',)
    readonly_fields = ()

    fieldsets = (
        (None, {
            'fields': ('entidad_externa', 'nombres', 'apellidos', 'cargo')
        }),
        ('Información de Contacto', {
            'fields': ('correo_electronico', 'telefono_contacto', 'numero_documento')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Bloquear edición de correo electrónico en contactos existentes."""
        if obj:
            return ('correo_electronico',)
        return ()

    def has_delete_permission(self, request, obj=None):
        """Restringir eliminación de contactos desde el admin."""
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='Ventanilla').exists()

# Registrar modelos de adjuntos si se necesita gestión directa
admin.site.register(AdjuntoCorreoEntrante)
admin.site.register(AdjuntoCorreo)


@admin.register(AsistenteDocumento)
class AsistenteDocumentoAdmin(admin.ModelAdmin):
    list_display = ('ruta_relativa', 'titulo', 'activo', 'indexado_en')
    list_filter = ('activo', 'tipo_fuente', 'indexado_en')
    search_fields = ('ruta_relativa', 'titulo')
    readonly_fields = ('checksum', 'indexado_en')


@admin.register(AsistenteChunk)
class AsistenteChunkAdmin(admin.ModelAdmin):
    list_display = ('documento', 'orden', 'heading')
    list_filter = ('documento',)
    search_fields = ('documento__ruta_relativa', 'heading', 'contenido')


@admin.register(AsistenteConversacion)
class AsistenteConversacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'estado', 'ultima_pregunta_at', 'actualizado_en')
    list_filter = ('estado', 'actualizado_en')
    search_fields = ('titulo', 'usuario__username', 'usuario__first_name', 'usuario__last_name')


@admin.register(AsistenteMensaje)
class AsistenteMensajeAdmin(admin.ModelAdmin):
    list_display = ('conversacion', 'rol', 'creado_en')
    list_filter = ('rol', 'creado_en')
    search_fields = ('contenido', 'conversacion__titulo', 'conversacion__usuario__username')

@admin.register(EntidadExterna)
class EntidadExternaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono')
    search_fields = ('nombre', 'nit')

# Registrar modelos de SLA
@admin.register(TramiteTipo)
class TramiteTipoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "plazo_dias_habiles", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(SubserieTramite)
class SubserieTramiteAdmin(admin.ModelAdmin):
    list_display = ("subserie", "tramite")
    list_filter = ("tramite",)
    search_fields = ("subserie__codigo", "tramite__codigo", "tramite__nombre")
    # Removido autocomplete_fields para evitar dependencia con SubserieDocumental


@admin.register(CalendarioLaboral)
class CalendarioLaboralAdmin(admin.ModelAdmin):
    list_display = ("fecha", "es_habil")
    list_filter = ("es_habil",)
    date_hierarchy = "fecha"

# === CORRESPONDENCIA DE SALIDA ===

@admin.register(CorrespondenciaSalida)
class CorrespondenciaSalidaAdmin(admin.ModelAdmin):
    list_display = ('numero_radicado_salida', 'respuesta_a', 'usuario_redactor', 'asunto', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion', 'oficina_emisora')
    search_fields = ('numero_radicado_salida', 'asunto', 'respuesta_a__numero_radicado')
    readonly_fields = ('numero_radicado_salida', 'fecha_creacion', 'fecha_ultima_modificacion')
    date_hierarchy = 'fecha_creacion'

@admin.register(SalidaDestinatario)
class SalidaDestinatarioAdmin(admin.ModelAdmin):
    list_display = ('correspondencia_salida', 'contacto', 'email_snapshot', 'estado', 'fecha_envio')
    list_filter = ('estado', 'fecha_envio')
    search_fields = ('email_snapshot', 'nombre_snapshot', 'correspondencia_salida__numero_radicado_salida')

@admin.register(AdjuntoSalida)
class AdjuntoSalidaAdmin(admin.ModelAdmin):
    list_display = ('correspondencia_salida', 'nombre_original', 'fecha_carga')
    list_filter = ('fecha_carga',)
    search_fields = ('nombre_original', 'correspondencia_salida__numero_radicado_salida')

@admin.register(AdjuntoCorrespondenciaRapida)
class AdjuntoCorrespondenciaRapidaAdmin(admin.ModelAdmin):
    list_display = ('correspondencia', 'nombre_original', 'tipo_mime', 'fecha_carga')
    list_filter = ('fecha_carga', 'tipo_mime')
    search_fields = ('nombre_original', 'correspondencia__numero_radicado')
    readonly_fields = ('fecha_carga',)

@admin.register(HistorialSalida)
class HistorialSalidaAdmin(admin.ModelAdmin):
    list_display = ('correspondencia_salida', 'tipo_evento', 'usuario', 'fecha_hora')
    list_filter = ('tipo_evento', 'fecha_hora', 'usuario')
    readonly_fields = ('fecha_hora',)

# === GRUPOS DE AGENDA ===

@admin.register(GrupoAgenda)
class GrupoAgendaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'oficina_propietaria', 'creado_por', 'activo', 'created_at')
    list_filter = ('activo', 'oficina_propietaria', 'created_at')
    search_fields = ('nombre', 'descripcion', 'oficina_propietaria__nombre')
    filter_horizontal = ('contactos',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('oficina_propietaria', 'nombre', 'descripcion', 'activo')
        }),
        ('Contactos', {
            'fields': ('contactos',)
        }),
        ('Metadatos', {
            'fields': ('creado_por', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# === COMUNICACIONES MASIVAS ===

@admin.register(ComunicacionMasiva)
class ComunicacionMasivaAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'oficina_emisora', 'usuario_creador', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'oficina_emisora', 'fecha_creacion')
    search_fields = ('asunto', 'cuerpo', 'oficina_emisora__nombre')
    readonly_fields = ('fecha_creacion',)

@admin.register(ComunicacionDestinatario)
class ComunicacionDestinatarioAdmin(admin.ModelAdmin):
    list_display = ('comunicacion', 'contacto', 'email_snapshot', 'estado', 'fecha_envio')
    list_filter = ('estado', 'fecha_envio')
    search_fields = ('email_snapshot', 'nombre_snapshot')

# === DISTRIBUCIÓN INTERNA ===

@admin.register(DistribucionInternaUsuario)
class DistribucionInternaUsuarioAdmin(admin.ModelAdmin):
    list_display = ('correspondencia', 'usuario_asignado', 'asignado_por', 'leido', 'fecha_asignacion')
    list_filter = ('leido', 'fecha_asignacion')
    search_fields = ('correspondencia__numero_radicado', 'usuario_asignado__username')
    readonly_fields = ('fecha_asignacion',)


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'titulo', 'leida', 'fecha_creacion')
    list_filter = ('tipo', 'leida', 'fecha_creacion')
    search_fields = ('usuario__username', 'titulo', 'mensaje')
    readonly_fields = ('fecha_creacion', 'fecha_lectura')
    list_per_page = 50
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('usuario', 'correspondencia')


# === URGENCIAS ===

class AdjuntoUrgenciaInline(admin.TabularInline):
    model = AdjuntoUrgencia
    extra = 0
    readonly_fields = ('fecha_carga', 'tamaño_bytes')
    fields = ('archivo', 'nombre_original', 'subido_por', 'fecha_carga', 'tamaño_bytes')


@admin.register(CorrespondenciaUrgencia)
class CorrespondenciaUrgenciaAdmin(admin.ModelAdmin):
    list_display = ('radicado', 'fecha_radicacion', 'estado', 'prioridad', 'oficina_destino', 
                    'horas_transcurridas', 'horas_limite', 'porcentaje_tiempo_usado', 'usuario_asignado')
    list_filter = ('estado', 'prioridad', 'oficina_destino', 'fecha_radicacion', 'serie', 'subserie')
    search_fields = ('radicado', 'correo_entrante__asunto', 'correo_entrante__email_remitente', 'motivo_urgencia')
    readonly_fields = ('numero_radicado', 'radicado', 'fecha_radicacion', 'fecha_limite', 
                       'horas_transcurridas', 'porcentaje_tiempo_usado', 'fecha_respuesta', 
                       'horas_restantes', 'color_alerta')
    list_per_page = 50
    inlines = [AdjuntoUrgenciaInline]
    
    fieldsets = (
        ('Información de Radicación', {
            'fields': ('numero_radicado', 'radicado', 'correo_entrante', 'fecha_radicacion', 'usuario_radica')
        }),
        ('Clasificación Documental', {
            'fields': ('serie', 'subserie', 'prioridad', 'motivo_urgencia')
        }),
        ('Destino y Asignación', {
            'fields': ('oficina_destino', 'usuario_asignado', 'fecha_asignacion')
        }),
        ('Control de Tiempos', {
            'fields': ('horas_limite', 'fecha_limite', 'horas_transcurridas', 
                       'horas_restantes', 'porcentaje_tiempo_usado', 'color_alerta')
        }),
        ('Estado y Respuesta', {
            'fields': ('estado', 'fecha_respuesta', 'usuario_responde', 'respuesta')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'correo_entrante', 'serie', 'subserie', 'oficina_destino', 
            'usuario_radica', 'usuario_asignado', 'usuario_responde'
        )


@admin.register(AdjuntoUrgencia)
class AdjuntoUrgenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre_original', 'urgencia', 'subido_por', 'fecha_carga', 'tamaño_bytes')
    list_filter = ('fecha_carga',)
    search_fields = ('nombre_original', 'urgencia__radicado', 'subido_por__username')
    readonly_fields = ('fecha_carga', 'tamaño_bytes')
    list_per_page = 50
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('urgencia', 'subido_por')

@admin.register(TipoTramite)
class TipoTramiteAdmin(admin.ModelAdmin):
    """
    Administración de Tipos de Trámite para radicación rápida.
    
    Permite configurar los códigos de trámite disponibles y sus tiempos de respuesta
    en días hábiles directamente desde el panel de administración.
    """
    list_display = (
        'codigo', 
        'nombre', 
        'dias_respuesta_display', 
        'activo', 
        'orden',
        'fecha_modificacion'
    )
    list_filter = ('activo', 'dias_respuesta')
    search_fields = ('codigo', 'nombre', 'descripcion')
    ordering = ('orden', 'codigo')
    list_editable = ('activo', 'orden')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'descripcion')
        }),
        ('Configuración de Tiempo', {
            'fields': ('dias_respuesta',),
            'description': 'Número de días hábiles para responder. Dejar vacío si no aplica plazo.'
        }),
        ('Visualización', {
            'fields': ('activo', 'orden'),
            'description': 'Solo los tipos activos aparecen en los formularios. '
                          'El orden determina la posición en la lista desplegable.'
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def dias_respuesta_display(self, obj):
        """Muestra los días de respuesta en formato amigable."""
        if obj.dias_respuesta:
            return f"{obj.dias_respuesta} días hábiles"
        return "Sin plazo definido"
    dias_respuesta_display.short_description = "Tiempo de Respuesta"
    
    def save_model(self, request, obj, form, change):
        """
        Guarda el modelo y muestra mensaje informativo sobre actualización de formularios.
        """
        super().save_model(request, obj, form, change)
        if change:
            self.message_user(
                request,
                f'Tipo de trámite "{obj.codigo}" actualizado. '
                'Los cambios se reflejarán automáticamente en los formularios.',
                level='SUCCESS'
            )
    
    class Media:
        css = {
            'all': ('admin/css/changelists.css',)
        }


# =============================================
# === COMUNICACIONES INTERNAS ===
# =============================================

class ComunicacionInternaDestinatarioInline(admin.TabularInline):
    model = ComunicacionInternaDestinatario
    extra = 0
    raw_id_fields = ('usuario', 'oficina')


class HistorialComunicacionInternaInline(admin.TabularInline):
    model = HistorialComunicacionInterna
    extra = 0
    readonly_fields = ('evento', 'fecha', 'usuario', 'descripcion')
    can_delete = False


class AnexoComunicacionInternaInline(admin.TabularInline):
    model = AnexoComunicacionInterna
    extra = 0


@admin.register(ComunicacionInterna)
class ComunicacionInternaAdmin(admin.ModelAdmin):
    list_display = ('radicado', 'asunto', 'remitente_nombre', 'remitente_oficina', 'estado', 'tipo_distribucion', 'fecha_creacion')
    list_filter = ('estado', 'tipo_distribucion', 'remitente_oficina', 'fecha_creacion')
    search_fields = ('radicado', 'asunto', 'remitente_nombre', 'cuerpo')
    readonly_fields = ('radicado', 'codigo_dependencia', 'anio_radicado', 'consecutivo_radicado', 'fecha_creacion')
    raw_id_fields = ('remitente_usuario', 'destinatario_usuario', 'remitente_oficina', 'destinatario_oficina', 'destinatario_proceso')
    inlines = [ComunicacionInternaDestinatarioInline, AnexoComunicacionInternaInline, HistorialComunicacionInternaInline]
    list_per_page = 25


@admin.register(ComunicacionInternaDestinatario)
class ComunicacionInternaDestinatarioAdmin(admin.ModelAdmin):
    list_display = ('comunicacion', 'tipo', 'usuario', 'oficina')
    list_filter = ('tipo',)
    raw_id_fields = ('comunicacion', 'usuario', 'oficina')


@admin.register(ComunicacionInternaDistribucion)
class ComunicacionInternaDistribucionAdmin(admin.ModelAdmin):
    list_display = ('comunicacion', 'usuario', 'fecha_distribucion', 'leido', 'fecha_lectura')
    list_filter = ('leido', 'fecha_distribucion')
    raw_id_fields = ('comunicacion', 'usuario')


@admin.register(HistorialComunicacionInterna)
class HistorialComunicacionInternaAdmin(admin.ModelAdmin):
    list_display = ('comunicacion', 'evento', 'fecha', 'usuario')
    list_filter = ('evento', 'fecha')
    raw_id_fields = ('comunicacion', 'usuario')
    readonly_fields = ('comunicacion', 'evento', 'fecha', 'usuario', 'descripcion')


@admin.register(AnexoComunicacionInterna)
class AnexoComunicacionInternaAdmin(admin.ModelAdmin):
    list_display = ('comunicacion', 'nombre_original', 'fecha_carga')
    raw_id_fields = ('comunicacion',)