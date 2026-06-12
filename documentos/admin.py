from django.contrib import admin
from .models import (
    SerieDocumental, SubserieDocumental, RegistroDeArchivo, PermisoUsuarioSerie, 
    EntidadProductora, MacroProceso, Proceso, UnidadAdministrativa, OficinaProductora, Objeto, FUID, FichaPaciente
)

# 1) Importaciones adicionales
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario
from .models import Documento


# 2) Definir un inline para mostrar/editar PerfilUsuario dentro del formulario de User
class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = "Perfil (Oficina)"
    fk_name = "user"

# 3) Crear un CustomUserAdmin que inyecte ese Inline
class CustomUserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)
    
    # Agregar las columnas de oficina productora, documento y fecha de registro
    list_display = BaseUserAdmin.list_display + ('get_oficina_productora', 'get_documento', 'get_fecha_registro', 'get_solicita_lider')
    list_filter = BaseUserAdmin.list_filter + ('is_active', 'perfil__oficina', 'perfil__solicita_lider')
    search_fields = BaseUserAdmin.search_fields + ('perfil__oficina__nombre', 'perfil__numero_documento')
    
    # Acciones personalizadas
    actions = ['activar_usuarios', 'desactivar_usuarios', 'aprobar_como_lider']
    
    def get_oficina_productora(self, obj):
        """Obtiene la oficina productora del perfil del usuario"""
        try:
            if obj.perfil.oficina:
                return obj.perfil.oficina.nombre
            return "-"
        except PerfilUsuario.DoesNotExist:
            return "-"
    get_oficina_productora.short_description = 'Oficina'
    get_oficina_productora.admin_order_field = 'perfil__oficina__nombre'
    
    def get_documento(self, obj):
        """Obtiene el tipo y número de documento"""
        try:
            perfil = obj.perfil
            if perfil.numero_documento:
                return f"{perfil.get_tipo_documento_display()}: {perfil.numero_documento}"
            return "-"
        except PerfilUsuario.DoesNotExist:
            return "-"
    get_documento.short_description = 'Documento'
    
    def get_fecha_registro(self, obj):
        """Obtiene la fecha de registro del usuario"""
        try:
            if obj.perfil.fecha_registro:
                return obj.perfil.fecha_registro.strftime('%Y-%m-%d %H:%M')
            return "-"
        except PerfilUsuario.DoesNotExist:
            return "-"
    get_fecha_registro.short_description = 'Fecha de registro'
    get_fecha_registro.admin_order_field = 'perfil__fecha_registro'
    
    def get_solicita_lider(self, obj):
        """Indica si el usuario solicita ser líder"""
        try:
            if obj.perfil.solicita_lider:
                return "Sí" if not obj.groups.filter(name='Lider de Oficina').exists() else "✓ Aprobado"
            return "No"
        except PerfilUsuario.DoesNotExist:
            return "-"
    get_solicita_lider.short_description = 'Solicita Líder'
    
    def activar_usuarios(self, request, queryset):
        """Activa los usuarios seleccionados"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} usuario(s) activado(s) exitosamente.')
    activar_usuarios.short_description = "✓ Activar usuarios seleccionados"
    
    def desactivar_usuarios(self, request, queryset):
        """Desactiva los usuarios seleccionados"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} usuario(s) desactivado(s) exitosamente.')
    desactivar_usuarios.short_description = "✗ Desactivar usuarios seleccionados"
    
    def aprobar_como_lider(self, request, queryset):
        """Aprueba a los usuarios seleccionados como líderes de oficina"""
        from django.contrib.auth.models import Group
        grupo_lider, created = Group.objects.get_or_create(name='Lider de Oficina')
        count = 0
        for user in queryset:
            try:
                if user.perfil.solicita_lider and not user.groups.filter(name='Lider de Oficina').exists():
                    user.groups.add(grupo_lider)
                    user.is_active = True
                    user.save()
                    count += 1
            except PerfilUsuario.DoesNotExist:
                pass
        self.message_user(request, f'{count} usuario(s) aprobado(s) como líder de oficina.')
    aprobar_como_lider.short_description = "👤 Aprobar como Líder de Oficina"

# 4) Anular el registro default de User y registrar el nuevo
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)



@admin.register(SerieDocumental)
class SerieDocumentalAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'codigo_trd', 'contar_oficinas')
    search_fields = ('codigo', 'nombre', 'codigo_trd')
    filter_horizontal = ('oficinas_productoras',)  # Widget mejorado para ManyToManyField
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'codigo_trd')
        }),
        ('Relación con Oficinas Productoras (Subprocesos)', {
            'fields': ('oficinas_productoras',),
            'description': 'Seleccione las oficinas productoras que utilizan esta serie documental'
        }),
    )
    
    def contar_oficinas(self, obj):
        """Muestra el número de oficinas asociadas"""
        count = obj.oficinas_productoras.count()
        return f"{count} oficina(s)"
    contar_oficinas.short_description = 'Oficinas Asociadas'


@admin.register(SubserieDocumental)
class SubserieDocumentalAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'serie')
    list_filter = ('serie',)
    search_fields = ('codigo', 'nombre')


@admin.register(RegistroDeArchivo)
class RegistroDeArchivoAdmin(admin.ModelAdmin):
    list_display = (
        'numero_orden', 'unidad_documental', 'fecha_archivo', 
        'creado_por', 'ubicacion', 'soporte_fisico', 'soporte_electronico'
    )
    list_filter = ('soporte_fisico', 'soporte_electronico', 'fecha_archivo', 'creado_por')
    search_fields = ('numero_orden', 'unidad_documental', 'ubicacion', 'notas')
    readonly_fields = ('fecha_creacion', 'fecha_edicion')
    fieldsets = (
        ('Información General', {
            'fields': ('numero_orden', 'codigo_serie', 'codigo_subserie', 'unidad_documental','fecha_archivo', 
                        'fecha_inicial', 'fecha_final', 'notas', 'Estado_archivo')
        }),
        ('Soporte', {
            'fields': ('soporte_fisico', 'soporte_electronico', 'caja', 'carpeta', 
                       'tomo_legajo_libro', 'numero_folios', 'cantidad', 'ubicacion')
        }),
        ('Información Electrónica', {
            'fields': ('cantidad_documentos_electronicos', 'tamano_documentos_electronicos')
        }),
        ('Metadatos', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_edicion')
        }),
    )


@admin.register(PermisoUsuarioSerie)
class PermisoUsuarioSerieAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'serie', 'permiso_crear', 'permiso_editar', 'permiso_consultar', 'permiso_eliminar')
    list_filter = ('serie', 'usuario')


@admin.register(EntidadProductora)
class EntidadProductoraAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(MacroProceso)
class MacroProcesoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nombre')
    search_fields = ('nombre',)
    ordering = ('numero',)


@admin.register(Proceso)
class ProcesoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nombre', 'sigla', 'macroproceso')
    list_filter = ('macroproceso',)
    search_fields = ('nombre', 'sigla')
    ordering = ('macroproceso__numero', 'numero')


@admin.register(UnidadAdministrativa)
class UnidadAdministrativaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'entidad_productora')
    list_filter = ('entidad_productora',)
    search_fields = ('nombre', 'entidad_productora__nombre')


@admin.register(OficinaProductora)
class OficinaProductoraAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'codigo_sis', 'nombre', 'proceso', 'codigo_trd_comunicacion_interna', 'unidad_administrativa')
    list_filter = ('proceso__macroproceso', 'proceso', 'unidad_administrativa')
    search_fields = ('codigo', 'codigo_sis', 'nombre', 'codigo_trd_comunicacion_interna', 'proceso__nombre', 'proceso__sigla', 'unidad_administrativa__nombre')


@admin.register(Objeto)
class ObjetoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)


@admin.register(FUID)
class FUIDAdmin(admin.ModelAdmin):
    list_display = ('id', 'entidad_productora', 'unidad_administrativa', 'oficina_productora', 'objeto', 'creado_por', 'fecha_creacion')
    list_filter = ('entidad_productora', 'unidad_administrativa', 'oficina_productora', 'objeto', 'creado_por')
    search_fields = ('id', 'entidad_productora__nombre', 'unidad_administrativa__nombre', 'oficina_productora__nombre', 'objeto__nombre')
    filter_horizontal = ('registros',)  # Para administrar el ManyToManyField

@admin.register(FichaPaciente)
class FichaPacienteAdmin(admin.ModelAdmin):
    list_display = ('consecutivo', 'primer_nombre', 'primer_apellido', 'num_identificacion', 'Numero_historia_clinica', 'activo')
    list_filter = ('activo', 'sexo', 'tipo_identificacion')
    search_fields = ('primer_nombre', 'primer_apellido', 'num_identificacion', 'Numero_historia_clinica')




from django.contrib import admin
from django.utils.html import format_html

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        'registro', 
        'archivo', 
        'archivo_size',  
        'uploaded_at', 
        'creado_por',  
        'oficina',
    )
    search_fields = ('registro__numero_orden', 'registro__creado_por__username', 'registro__creado_por__first_name', 'registro__creado_por__last_name')
    list_filter = ('uploaded_at', 'registro__fuids__oficina_productora')

    def creado_por(self, obj):
        """ Devuelve el usuario que subió el archivo """
        return obj.registro.creado_por if hasattr(obj.registro, 'creado_por') else "Desconocido"
    creado_por.short_description = "Subido por"

    def oficina(self, obj):
        """ Devuelve la oficina a la que pertenece el registro """
        if hasattr(obj.registro, 'fuids') and obj.registro.fuids.exists():
            return obj.registro.fuids.first().oficina_productora.nombre
        return "Sin Oficina"
    oficina.short_description = "Oficina"

    def archivo_size(self, obj):
        """ Devuelve el tamaño del archivo en KB o MB """
        if obj.archivo and obj.archivo.size:
            size_kb = obj.archivo.size / 1024  # Convertir a KB
            if size_kb > 1024:
                return f"{size_kb / 1024:.2f} MB"
            return f"{size_kb:.2f} KB"
        return "Desconocido"
    archivo_size.short_description = "Tamaño"


# @admin.register(PerfilUsuario)
# class PerfilUsuarioAdmin(admin.ModelAdmin):
#     list_display = ('user', 'oficina')
#     search_fields = ('user__username', 'oficina__nombre')