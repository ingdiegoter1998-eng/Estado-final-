from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import FUIDCreateView, FUIDUpdateView, lista_fuids
from django.urls import path
from .views import detalle_fuid
from .views import crear_ficha_paciente
from .views import lista_fichas_paciente
from .views import EditarFichaPaciente, detalle_ficha_paciente
from .views import ListaFichasAPIView
from .views import export_fuid_to_excel
from .views import estadisticas_fuids, estadisticas_registros, estadisticas_pacientes,  pagina_estadisticas, obtener_usuarios
from django.views.generic import TemplateView
from .views import registros_api
from .views import registros_api_con_id
from .views import registros_api, ver_documento
from .views import soporte_view, panel_view, registros_fuid_json
from .views import (
    solicitar_prestamo,
    mis_prestamos,
    gestion_prestamos,
    procesar_prestamo,
    detalle_prestamo,
    confirmar_recepcion,
    reintegrar_prestamo,
    eliminar_documento_prestamo,
    enviar_notificacion_aviso,
    solicitar_devolucion,
    exportar_prestamos_excel_mensual,
)

# from .views import export_fuids_to_excel
from .views import mi_error_403
handler403 = 'documentos.views.mi_error_403'

urlpatterns = [
    path('', views.lista_registros, name='lista_registros'),  # Página principal de registros
    path('nuevo/', views.crear_registro, name='crear_registro'),
    path('<int:pk>/editar/', views.editar_registro, name='editar_registro'),
    path('<int:pk>/eliminar/', views.eliminar_registro, name='eliminar_registro'),
    path('cargar_subseries/', views.cargar_subseries, name='cargar_subseries'),
    path('cargar_series/', views.cargar_series, name='cargar_series'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('registro/', views.registro_usuario, name='registro'),
    path('registros/completo/', views.lista_completa_registros, name='lista_completa_registros'),
    path('fuids/', views.lista_fuids, name='lista_fuids'),
    path('documento/<int:registro_id>/', ver_documento, name='ver_documento'),  # <-- Agregar esta línea
    #fuids y registros
    path('fuids/<int:fuid_id>/form_registro/', views.form_registro_fuid_ajax, name='form_registro_fuid_ajax'),
    path('fuids/<int:fuid_id>/crear_registro/', views.crear_registro_fuid_ajax, name='crear_registro_fuid_ajax'),
    path('fuids/', lista_fuids, name='lista_fuids'),
    path('soporte/', soporte_view, name='soporte'),
    path('fuids/<int:fuid_id>/registros/', registros_fuid_json, name='registros_fuid_json'),

    path('fuids/create/', FUIDCreateView.as_view(), name='crear_fuid'),
    path('fuids/edit/<int:pk>/', FUIDUpdateView.as_view(), name='editar_fuid'),
    path('fuids/detalle/<int:pk>/', detalle_fuid, name='detalle_fuid'),
    path('welcome/', views.welcome_view, name='welcome'),
    path('panel/', views.panel_view, name='panel'),

    # Rutas de fichas de pacientes
    path('fichas/', views.bienvenida_fichas, name='bienvenida_fichas'),
    path('fichas/preparar/', views.preparar_fichas1, name='preparar_fichas'),
    path('fichas/buscar/', views.buscar_ficha1, name='buscar_ficha1'),
    path('fichas/lista/', views.lista_fichas1, name='lista_fichas1'),
    path('fichas/crear/', views.crear_ficha1, name='crear_ficha1'),
    path('fichas/editar/<int:consecutivo>/', views.editar_ficha1, name='editar_ficha1'),
    path('fichas/detalle/<int:consecutivo>/', views.detalle_ficha1, name='detalle_ficha1'),

    # Rutas antiguas de fichas (compatibilidad)
    path('crear-ficha/', crear_ficha_paciente, name='crear_ficha'),
    path('lista-fichas/', lista_fichas_paciente, name='lista_fichas'),
    path('editar-ficha/<int:consecutivo>/', EditarFichaPaciente.as_view(), name='editar_ficha'),
    path('detalle-ficha/<int:consecutivo>/', detalle_ficha_paciente, name='detalle_ficha'),
    path('api/lista-fichas/', ListaFichasAPIView.as_view(), name='api_lista_fichas'),
    path('fuid/<int:pk>/export-excel/', export_fuid_to_excel, name='export_fuid_to_excel'),
    path('fuids/<int:fuid_id>/agregar_registro/', views.agregar_registro_a_fuid, name='agregar_registro_a_fuid'),
    path('fuids/<int:fuid_id>/agregar_registro_ajax/', views.agregar_registro_modal_ajax, name='agregar_registro_modal_ajax'),
      # Otras rutas de tu app...
    path('estadisticas/pacientes/', views.estadisticas_pacientes, name='estadisticas_pacientes'),
    path('estadisticas/registros/', views.estadisticas_pacientes, name='estadisticas_pacientes'),
    path('estadisticas/fuids/', estadisticas_fuids, name='estadisticas_fuids'),
    path('estadisticas/', pagina_estadisticas, name='pagina_estadisticas'),
    path('api/usuarios/', obtener_usuarios, name='obtener_usuarios'),
    # path('adminlte/', TemplateView.as_view(template_name="admin-lte/index.html"), name="adminlte_index"),
    path('', TemplateView.as_view(template_name="adminlte/base.html"), name="home"),
    path('api/registros/', registros_api, name='registros_api'),
    path('api/registros_api_completo/', views.registros_api_completo, name='registros_api_completo'),
    path('registros_api_con_id/', registros_api_con_id, name='registros_api_con_id'),
    path('fuids/<int:fuid_id>/editar_registro/<int:registro_id>/', views.editar_registro_de_fuid, name='editar_registro_de_fuid'),
    
    # Importar Excel para Archivos
    path('importar-excel/', views.importar_excel_archivo, name='importar_excel_archivo'),
    path('importar-excel/progreso/<str:task_id>/', views.progreso_importacion_excel, name='progreso_importacion_excel'),
    
    # Aliases para compatibilidad con templates
    path('fuids/nuevo/', FUIDCreateView.as_view(), name='fuid_form'),  # Alias de crear_fuid
    path('fuids/todos/', lista_fuids, name='fuid_list'),  # Alias de lista_fuids

    # Rutas de Préstamos Documentales
    path('prestamos/solicitar/', solicitar_prestamo, name='solicitar_prestamo'),
    path('prestamos/mis-prestamos/', mis_prestamos, name='mis_prestamos'),
    path('prestamos/gestion/', gestion_prestamos, name='gestion_prestamos'),
    path('prestamos/detalle/<int:pk>/', detalle_prestamo, name='detalle_prestamo'),
    path('prestamos/procesar/<int:pk>/', procesar_prestamo, name='procesar_prestamo'),
    path('prestamos/confirmar/<int:pk>/', confirmar_recepcion, name='confirmar_recepcion'),
    path('prestamos/reintegrar/<int:pk>/', reintegrar_prestamo, name='reintegrar_prestamo'),
    path('prestamos/solicitar-devolucion/<int:pk>/', solicitar_devolucion, name='solicitar_devolucion'),
    path('prestamos/documento/eliminar/<int:pk>/', eliminar_documento_prestamo, name='eliminar_documento_prestamo'),
    path('prestamos/notificar/<int:pk>/', enviar_notificacion_aviso, name='enviar_notificacion_aviso'),
    path('prestamos/reporte-mensual/', exportar_prestamos_excel_mensual, name='exportar_prestamos_excel_mensual'),
    
    # API para búsqueda de registros (para AJAX, optimizado para 1M+ de registros)
    path('api/buscar-registros/', views.buscar_registros_ajax, name='buscar_registros_ajax'),]