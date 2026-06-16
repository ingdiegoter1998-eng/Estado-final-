from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_sync_control
from . import views_aprobar_masivo
from . import views_urgencias
from . import api_views
from . import views_chatbot
from . import views_seguimiento_entrega
from django.contrib.auth.views import LoginView, LogoutView
from .views import (
    # BandejaClasificadosView, BandejaRevisionManualView, DetalleCorreoClasificadoView, 
    radicar_correspondencia, lista_pendientes_distribuir, distribuir_correspondencia,
    listar_contactos, crear_contacto, editar_contacto, home_view, ver_perfil, bandeja_entrada, 
    detalle_correspondencia, #marcar_como_leido, 
    redistribuir_interna, compartir_correspondencia, redistribuir_oficinas,
    bandeja_personal, bandeja_oficina, bandeja_interoficina, bandeja_respuestas_salientes,
    bandeja_correos_pendientes_view, api_subseries, detalle_correo_entrante_view,
    marcar_correo_papelera_view, restaurar_correo_papelera_view,
    listar_entidades, crear_entidad, dashboard_ventanilla, dashboard_usuario,
    procesar_emails_imap_manual_view, procesar_emails_manual,
    crear_o_editar_respuesta, bandeja_respuestas_pendientes, revisar_respuesta,
    HistorialCorrespondenciaView, BandejaRadicacionRapidaView, BandejaRadicacionRapidaSalienteView,
    metricas_destinatarios, crear_contacto_ajax, crear_entidad_ajax, 
    responder_correspondencia_ajax, buscar_contactos_ajax, buscar_entidades_ajax, buscar_grupos_ajax, contactos_automaticos,
    crear_correspondencia_salida_ajax,
    crear_comunicacion_interna_ajax,
    oficinas_todas_interna_ajax,
    procesos_todos_ajax,
    grupos_agenda_index, grupo_agenda_crear, grupo_agenda_editar, grupo_agenda_eliminar,
    comunicaciones_list, comunicacion_masiva_crear, comunicacion_masiva_detalle, comunicacion_masiva_enviar,
    ComunicacionInternaListView, ComunicacionInternaDetailView, 
    ComunicacionInternaPDFView, ComunicacionInternaDescargarView, ComunicacionInternaPendientesView,
    ComunicacionInternaRecibidasView, ComunicacionInternaEnviadasView,
    ComunicacionInternaTrazabilidadView,
    ComunicacionInternaHistorialRespuestasView,
    InternaBienvenidaView, InternaConfigurarFirmaView, guardar_firma_interna,
    aprobar_comunicacion_interna
)
from django.http import JsonResponse
from .modelos_minimos_sla import SubserieTramite
from .utils_sla import get_cutoff_time, aplicar_corte, sumar_habiles
from .api_views import api_login, api_logout, api_me
from . import api_monitoreo
from . import views_postmark_webhook
from . import api_chat
from django.utils import timezone
import datetime

app_name = 'correspondencia'  # Definir el espacio de nombres de la aplicación

# Router para API REST
router = DefaultRouter()
router.register(r'api/calendario', api_views.CalendarioViewSet, basename='api-calendario')
router.register(r'api/informes', api_views.InformesViewSet, basename='api-informes')

urlpatterns = [
    path('', views.home_view, name='home'),
    path('welcome/', views.home_view, name='welcome'), 
    path('radicar/', views.radicar_correspondencia, name='radicar_manual'),
    path('radicar/desde-correo/<int:correo_id>/', views.radicar_correspondencia, name='radicar_desde_correo'),
    # path('bandeja/', views.bandeja_entrada, name='bandeja_entrada'), # <-- ELIMINADA/COMENTADA: Reemplazada por bandeja_personal
    path('correspondencia/<int:pk>/', views.detalle_correspondencia, name='detalle_correspondencia'),
    path('correspondencia/<int:pk>/sello.pdf', views.imprimir_sello_correspondencia, name='imprimir_sello'),
    # path('correspondencia/<int:pk>/marcar_leido/', views.marcar_como_leido, name='marcar_leido'), # <-- COMENTADA: Funcionalidad ahora en detalle_correspondencia
    # Añadir URL para redistribución si se implementa
    path('perfil/', views.ver_perfil, name='ver_perfil'),

    # URL para la nueva bandeja de correos clasificados
    # path('correos/clasificados/', views.BandejaClasificadosView.as_view(), name='bandeja_clasificados'),

    # Nueva URL para correos que requieren revisión manual
    # path('correos/revision-manual/', views.BandejaRevisionManualView.as_view(), name='bandeja_revision_manual'),

    # Descomentar URL para la vista de detalle del correo clasificado
    # path('correos/clasificados/<int:pk>/detalle/', views.DetalleCorreoClasificadoView.as_view(), name='detalle_correo_clasificado'),

    # --- Autenticación ---
    path('login/', LoginView.as_view(template_name='correspondencia/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='correspondencia:login'), name='logout_correspondencia'), # Redirigir a login al salir

    # Nueva URL para la lista de pendientes
    path('pendientes-distribuir/', views.lista_pendientes_distribuir, name='pendientes_distribuir'),
    # Nueva URL para la acción de distribuir
    path('<int:pk>/distribuir/', views.distribuir_correspondencia, name='distribuir_correspondencia'),
    # Aquí añadiremos más URLs de correspondencia más adelante
    # path('bandeja/oficina/', views.bandeja_oficina, name='bandeja_oficina'),

    # Rutas de Contactos
    path('contactos/', views.listar_contactos, name='listar_contactos'),
    path('contactos/agenda/', views.lista_contactos_usuario, name='contactos_usuario'),
    path('contactos/agenda/buscar-ajax/', views.contactos_agenda_modal_ajax, name='contactos_agenda_modal_ajax'),
    path('contactos/crear/', views.crear_contacto, name='crear_contacto'),
    path('contactos/<int:pk>/editar/', views.editar_contacto, name='editar_contacto'),
    path('contactos/<int:pk>/auditoria-ajax/', views.auditoria_contacto_ajax, name='auditoria_contacto_ajax'),
    path('contactos/<int:pk>/verificar-activo-ajax/', views.verificar_contacto_activo_ajax, name='verificar_contacto_activo_ajax'),
    # Aquí podríamos añadir URLs para eliminar contactos más adelante

    # --- URLs Entidades Externas (NUEVO) ---
    path('entidades/', views.listar_entidades, name='listar_entidades'),
    path('entidades/crear/', views.crear_entidad, name='crear_entidad'),
    path('entidades/<int:pk>/editar/', views.editar_entidad, name='editar_entidad'),

    path('compartir/<int:pk>/', views.compartir_correspondencia, name='compartir_correspondencia'),
    path('lider-compartir-oficina/<int:pk>/', views.lider_compartir_con_oficina, name='lider_compartir_con_oficina'),
    path('correspondencia/<int:pk>/redistribuir-oficinas/', views.redistribuir_oficinas, name='redistribuir_oficinas'),
    # path('marcar-leido/<int:pk>/', views.marcar_como_leido, name='marcar_leido'), # <-- COMENTADA TAMBIÉN AQUÍ

    # --- URLs USUARIO REGULAR ---
    path('bandeja/', views.bandeja_personal, name='bandeja_personal'), 
    path('bandeja-interoficina/', views.bandeja_interoficina, name='bandeja_interoficina'),
    path('bandeja-oficina/', views.bandeja_oficina, name='bandeja_oficina'),
    path('bandeja-salientes/', views.bandeja_respuestas_salientes, name='bandeja_respuestas_salientes'),
    path('dashboard/', views.dashboard_usuario, name='dashboard_usuario'),
    path('mis-rebotes/', views.mis_rebotes, name='mis_rebotes'),
    path('directorio/', views.directorio_usuarios, name='directorio_usuarios'),
    path('asistente/', views_chatbot.asistente_chatbot, name='asistente_chatbot'),
    # --- FIN URLs USUARIO REGULAR ---

    # AJAX: detalle de lectura para modal (bandeja personal)
    path('ajax/lectura-detalle/<int:correspondencia_id>/', views.lectura_detalle_ajax, name='lectura_detalle_ajax'),
    path('ajax/lectura-detalle-interoficina/<int:correspondencia_id>/', views.lectura_detalle_interoficina_ajax, name='lectura_detalle_interoficina_ajax'),

    # --- URLs VENTANILLA (NUEVO) ---
    path('ventanilla/dashboard/', views.dashboard_ventanilla, name='dashboard_ventanilla'),
    path('ventanilla/control-sincronizacion/', views_sync_control.control_sincronizacion_correos, name='control_sincronizacion_correos'),
    path('ventanilla/correos-pendientes/', views.bandeja_correos_pendientes_view, name='bandeja_correos_pendientes'),
    path('ventanilla/correos-problematicos/', views.bandeja_correos_problematicos_view, name='bandeja_correos_problematicos'),
    path('ventanilla/correo/<int:correo_id>/detalle/', views.detalle_correo_entrante_view, name='detalle_correo_entrante'),
    path('ventanilla/correo/<int:correo_id>/visor/', views.visor_correo_completo_view, name='visor_correo_completo'),
    path('ventanilla/correo-problematico/<int:problem_id>/detalle/', views.detalle_correo_problematico_view, name='detalle_correo_problematico'),
    path('ventanilla/correo-problematico/<int:problem_id>/forzar-ingreso/', views.forzar_ingreso_correo_problematico_view, name='forzar_ingreso_correo_problematico'),
    path('ventanilla/correo/<int:correo_id>/papelera/', views.marcar_correo_papelera_view, name='marcar_correo_papelera'),
    path('ventanilla/correo/<int:correo_id>/restaurar-papelera/', views.restaurar_correo_papelera_view, name='restaurar_correo_papelera'),
    path('ventanilla/correo/<int:correo_id>/generar-salida-rapida/', views.generar_radicado_salida_rapida, name='generar_radicado_salida_rapida'),
    path('ventanilla/salida/<int:salida_id>/enviar-radicado-email/', views.enviar_radicado_salida_email, name='enviar_radicado_salida_email'),
    path('ventanilla/procesar-emails-manual/', views.procesar_emails_manual, name='procesar_emails_manual'),
    path('ventanilla/procesar-emails-imap-manual/', views.procesar_emails_imap_manual_view, name='procesar_emails_imap_manual'),
    path('ventanilla/ajax/subseries/', views.api_subseries, name='ajax_subseries'),
    # API endpoints para búsqueda y filtrado
    path('buscar-contactos/', views.buscar_contactos, name='buscar_contactos'),
    path('buscar-entidades/', views.buscar_entidades, name='buscar_entidades'),
    path('buscar-oficinas/', views.buscar_oficinas, name='buscar_oficinas'),


    # path('ventanilla/correo/<int:correo_id>/radicar/', views.detalle_radicar_correo_view, name='detalle_radicar_correo'), # <-- ELIMINADA
    # --- FIN URLs VENTANILLA ---
    
    # === URLs PARA RESPUESTA DE CORRESPONDENCIA ===
    # Usuario Regular
    path('correspondencia/<int:correspondencia_entrada_id>/responder/', views.crear_o_editar_respuesta, name='crear_respuesta'),
    # Ventanilla
    path('ventanilla/respuestas-pendientes/', views.bandeja_respuestas_pendientes, name='bandeja_respuestas_pendientes'),
    path('ventanilla/respuesta/<int:respuesta_id>/revisar/', views.revisar_respuesta, name='revisar_respuesta'),
    path('ventanilla/aprobar-todas-respuestas/', views_aprobar_masivo.aprobar_todas_respuestas, name='aprobar_todas_respuestas'),
    # === FIN URLs RESPUESTA ===

    # --- Nueva URL para el Historial --- 
    path('historial/', HistorialCorrespondenciaView.as_view(), name='historial_correspondencia'),
    path('historial/informe-excel/', views.generar_informe_correspondencia_excel, name='informe_correspondencia_excel'),
    path('historial/informe-excel-mensual/', views.generar_informe_correspondencia_excel_mensual, name='informe_correspondencia_excel_mensual'),
    
    # --- Bandeja de Radicación Rápida ---
    path('radicacion-rapida/', BandejaRadicacionRapidaView.as_view(), name='bandeja_radicacion_rapida'),
    path('radicacion-rapida/salientes/', BandejaRadicacionRapidaSalienteView.as_view(), name='bandeja_radicacion_rapida_saliente'),
    path('radicacion-rapida/<int:pk>/editar/', views.editar_radicacion_rapida_entrante, name='editar_radicacion_rapida_entrante'),
    path('radicacion-rapida/<int:pk>/datos/', views.api_radicacion_rapida_entrante_data, name='api_radicacion_rapida_entrante_data'),
    path('radicacion-rapida/salientes/<int:pk>/editar/', views.editar_radicacion_rapida_saliente, name='editar_radicacion_rapida_saliente'),
    path('radicacion-rapida/salientes/<int:pk>/datos/', views.api_radicacion_rapida_saliente_data, name='api_radicacion_rapida_saliente_data'),
    path('api/tipos-tramite/', views.api_tipos_tramite, name='api_tipos_tramite'),
    
    # --- URLs para Calendario de Informes ---
    path('informes/calendario/', views.calendario_informes_view, name='calendario_informes'),
    path('informes/dia/<str:fecha_str>/', views.detalle_dia_informe, name='detalle_dia_informe'),
    path('informes/subir-firmado/', views.subir_informe_firmado, name='subir_informe_firmado'),
    path('informes/guardar-firma/', views.guardar_firma_correspondencia, name='guardar_firma_correspondencia'),
    
    # En urls.py
    path('respuesta/<int:respuesta_id>/detalle/', views.detalle_respuesta_salida, name='detalle_respuesta_salida'),
    path('respuesta/<int:respuesta_id>/detalle-errores/', views.detalle_respuesta_salida_errores, name='detalle_respuesta_salida_errores'),
    path('api/sla/calcular-plazo/', views.calcular_plazo_sla, name='calcular_plazo_sla'),
    
    # --- URLs para Métricas de Destinatarios ---
    path('ventanilla/metricas-destinatarios/', views.metricas_destinatarios, name='metricas_destinatarios'),
    path(
        'ventanilla/seguimiento-entrega/',
        views_seguimiento_entrega.panel_seguimiento_entrega,
        name='panel_seguimiento_entrega',
    ),
    path(
        'ventanilla/seguimiento-entrega/<int:salida_id>/',
        views_seguimiento_entrega.detalle_evidencia_envio,
        name='detalle_evidencia_envio',
    ),

    # --- URLs AJAX para Modales ---
    path('contactos/crear-ajax/', views.crear_contacto_ajax, name='crear_contacto_ajax'),
    path('entidades/crear-ajax/', views.crear_entidad_ajax, name='crear_entidad_ajax'),
    path('correspondencia/responder-ajax/', views.responder_correspondencia_ajax, name='responder_correspondencia_ajax'),
    path('correspondencia/salida/crear-ajax/', views.crear_correspondencia_salida_ajax, name='crear_correspondencia_salida_ajax'),
    path('buscar-contactos-ajax/', views.buscar_contactos_ajax, name='buscar_contactos_ajax'),
    path('buscar-entidades-ajax/', views.buscar_entidades_ajax, name='buscar_entidades_ajax'),
    path('buscar-grupos-ajax/', views.buscar_grupos_ajax, name='buscar_grupos_ajax'),
    # Categorías de contactos (para modal dentro de modal al responder)
    path('buscar-categorias-ajax/', views.buscar_categorias_ajax, name='buscar_categorias_ajax'),
    path('categorias/<int:pk>/detalle-ajax/', views.categoria_detalle_ajax, name='categoria_detalle_ajax'),
    path('categorias/<int:pk>/detalle/', views.categoria_detalle_view, name='categoria_detalle'),
    path('contactos-agenda/', views.contactos_automaticos, name='contactos_agenda'),
    path('salidas/<int:pk>/destinatarios-ajax/', views.destinatarios_salida_ajax, name='destinatarios_salida_ajax'),

    # --- Validación de email (MX y SMTP) ---
    path('contactos/validar-email-mx-ajax/', views.validar_email_mx_ajax, name='validar_email_mx_ajax'),
    path('contactos/validar-email-smtp-ajax/', views.validar_email_smtp_ajax, name='validar_email_smtp_ajax'),
    path('contactos/validar-email-api-ajax/', views.validar_email_api_ajax, name='validar_email_api_ajax'),
    path('contactos/test-api-config/', views.test_api_config, name='test_api_config'),
    path('contactos/simulate-timeout/', views.simulate_timeout_response, name='simulate_timeout_response'),

    # === Grupos de Agenda y Comunicaciones Masivas ===
    path('agenda/grupos/', grupos_agenda_index, name='grupos_agenda_index'),
    path('agenda/grupos/nuevo/', grupo_agenda_crear, name='grupo_agenda_crear'),
    path('agenda/grupos/<int:pk>/editar/', grupo_agenda_editar, name='grupo_agenda_editar'),
    path('agenda/grupos/<int:pk>/eliminar/', grupo_agenda_eliminar, name='grupo_agenda_eliminar'),
    # AJAX para modal de grupos (paginación y validación)
    path('agenda/grupos/contactos-ajax/', views.contactos_agenda_paginado_ajax, name='contactos_agenda_paginado_ajax'),
    path('agenda/grupos/validar-nombre-ajax/', views.validar_nombre_grupo_ajax, name='validar_nombre_grupo_ajax'),
    path('agenda/grupos/<int:pk>/detalle-ajax/', views.grupo_agenda_detalle_ajax, name='grupo_agenda_detalle_ajax'),
    path('agenda/comunicaciones/', comunicaciones_list, name='comunicaciones_list'),
    path('agenda/comunicaciones/nueva/', comunicacion_masiva_crear, name='comunicacion_masiva_crear'),
    path('agenda/comunicaciones/<int:pk>/', comunicacion_masiva_detalle, name='comunicacion_masiva_detalle'),
    path('agenda/comunicaciones/<int:pk>/enviar/', comunicacion_masiva_enviar, name='comunicacion_masiva_enviar'),

    # === Notificaciones ===
    path('notificaciones/obtener/', views.obtener_notificaciones, name='obtener_notificaciones'),
    path('notificaciones/<int:notificacion_id>/marcar-leida/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_notificaciones_leidas, name='marcar_todas_notificaciones_leidas'),

    # === Comunicaciones Internas (Oficios) ===
    path('interna/', ComunicacionInternaListView.as_view(), name='interna_lista'),
    path('interna/bienvenida/', InternaBienvenidaView.as_view(), name='interna_bienvenida'),
    path('interna/configurar-firma/', InternaConfigurarFirmaView.as_view(), name='interna_configurar_firma'),
    path('interna/guardar-firma/', guardar_firma_interna, name='interna_guardar_firma'),
    path('interna/recibidas/', ComunicacionInternaRecibidasView.as_view(), name='interna_recibidas'),
    path('interna/enviadas/', ComunicacionInternaEnviadasView.as_view(), name='interna_enviadas'),
    path('interna/pendientes/', ComunicacionInternaPendientesView.as_view(), name='interna_pendientes'),
    path('interna/<int:pk>/', ComunicacionInternaDetailView.as_view(), name='interna_detalle'),
    path('interna/<int:pk>/ver/', ComunicacionInternaPDFView.as_view(), name='interna_ver_pdf'),
    path('interna/<int:pk>/descargar/', ComunicacionInternaDescargarView.as_view(), name='interna_descargar'),
    path('interna/<int:pk>/aprobar/', aprobar_comunicacion_interna, name='interna_aprobar'),
    path('interna/<int:pk>/subir-firma/', views.subir_firma_interna, name='interna_subir_firma'),
    path('interna/<int:pk>/responder/', views.responder_comunicacion_interna, name='interna_responder'),
    path('interna/<int:pk>/responder-ajax/', views.responder_comunicacion_interna, name='interna_responder_ajax'),
    path('interna/<int:pk>/trazabilidad/', ComunicacionInternaTrazabilidadView.as_view(), name='interna_trazabilidad'),
    path('interna/<int:pk>/historial-respuestas/', ComunicacionInternaHistorialRespuestasView.as_view(), name='interna_historial_respuestas'),
    path('interna/<int:pk>/destinatarios-ajax/', views.destinatarios_interna_ajax, name='destinatarios_interna_ajax'),
    path('interna/usuarios-ajax/', views.usuarios_por_oficina_ajax, name='usuarios_por_oficina_ajax'),
    path('interna/crear-ajax/', views.crear_comunicacion_interna_ajax, name='crear_comunicacion_interna_ajax'),
    path('interna/<int:pk>/obtener-ajax/', views.obtener_comunicacion_interna_ajax, name='obtener_comunicacion_interna_ajax'),
    path('interna/<int:pk>/editar-ajax/', views.editar_comunicacion_interna_ajax, name='editar_comunicacion_interna_ajax'),
    path('interna/anexo/<int:pk>/eliminar/', views.eliminar_anexo_comunicacion_interna, name='interna_anexo_eliminar'),
    path('interna/oficinas-todas-ajax/', views.oficinas_todas_interna_ajax, name='oficinas_todas_interna_ajax'),
    path('interna/procesos-todos-ajax/', views.procesos_todos_ajax, name='procesos_todos_ajax'),
    path('interna/<int:pk>/aceptar-borrador-ajax/', views.aceptar_borrador_comunicacion_ajax, name='aceptar_borrador_ajax'),
    path('interna/<int:pk>/revertir-borrador-ajax/', views.revertir_borrador_comunicacion_ajax, name='revertir_borrador_ajax'),

    # === URGENCIAS ===
    path(
        'ventanilla/correo/<int:correo_id>/radicar-urgencia/',
        views_urgencias.radicar_urgencia_view,
        name='radicar_urgencia'
    ),
    path(
        'urgencias/',
        views_urgencias.buzon_urgencias,
        name='buzon_urgencias'
    ),
    path(
        'urgencias/<int:pk>/',
        views_urgencias.urgencia_detalle,
        name='urgencia_detalle'
    ),
    path(
        'urgencias/<int:pk>/tomar/',
        views_urgencias.tomar_urgencia,
        name='tomar_urgencia'
    ),
    path(
        'urgencias/<int:pk>/responder/',
        views_urgencias.responder_urgencia,
        name='responder_urgencia'
    ),
    
    # API Urgencias
    path(
        'api/urgencias/radicar/',
        views_urgencias.api_radicar_urgencia,
        name='api_radicar_urgencia'
    ),
    path(
        'api/urgencias/notificaciones/',
        views_urgencias.api_notificaciones_urgencias,
        name='api_notificaciones_urgencias'
    ),

    # API REST - Calendario e Informes
    path('api/firmas/guardar/', api_views.guardar_firma, name='api-guardar-firma'),
    path('api/firmas/guardar-auxiliar/', api_views.guardar_firma_auxiliar, name='api-guardar-firma-auxiliar'),

    # API Autenticación para Next.js
    path('api/auth/login/', api_login, name='api-auth-login'),
    path('api/auth/logout/', api_logout, name='api-auth-logout'),
    path('api/auth/me/', api_me, name='api-auth-me'),

    # API Asistente documental MVP
    path('api/chatbot/conversations/', views_chatbot.chatbot_conversations_api, name='chatbot_conversations_api'),
    path('api/chatbot/conversations/create/', views_chatbot.chatbot_create_conversation_api, name='chatbot_create_conversation_api'),
    path('api/chatbot/conversations/<int:conversation_id>/messages/', views_chatbot.chatbot_messages_api, name='chatbot_messages_api'),
    path('api/chatbot/conversations/<int:conversation_id>/ask/', views_chatbot.chatbot_ask_api, name='chatbot_ask_api'),

    # API Monitoreo Operativo (solo superusuarios)
    path('api/monitoreo/pulso/', api_monitoreo.api_monitoreo_pulso, name='api-monitoreo-pulso'),
    path('api/monitoreo/sla/', api_monitoreo.api_monitoreo_sla, name='api-monitoreo-sla'),
    path('api/monitoreo/envio/', api_monitoreo.api_monitoreo_envio, name='api-monitoreo-envio'),
    path('api/monitoreo/salidas-correo/', api_monitoreo.api_monitoreo_salidas_correo, name='api-monitoreo-salidas-correo'),
    path(
        'api/monitoreo/salidas-correo/<int:salida_id>/detalle/',
        api_monitoreo.api_monitoreo_salidas_correo_detalle,
        name='api-monitoreo-salidas-correo-detalle',
    ),
    path('api/monitoreo/entradas-correo/', api_monitoreo.api_monitoreo_entradas_correo, name='api-monitoreo-entradas-correo'),
    path(
        'api/monitoreo/entradas-correo/<int:correo_id>/detalle/',
        api_monitoreo.api_monitoreo_entradas_correo_detalle,
        name='api-monitoreo-entradas-correo-detalle',
    ),
    path('api/monitoreo/imap/', api_monitoreo.api_monitoreo_imap, name='api-monitoreo-imap'),
    path('api/monitoreo/email-sync/', api_monitoreo.api_monitoreo_imap, name='api-monitoreo-email-sync'),
    path(
        'api/monitoreo/email-sync/runs/<int:run_id>/',
        api_monitoreo.api_monitoreo_email_sync_run,
        name='api-monitoreo-email-sync-run',
    ),
    path('api/monitoreo/distribucion/', api_monitoreo.api_monitoreo_distribucion, name='api-monitoreo-distribucion'),
    path('api/monitoreo/internas/', api_monitoreo.api_monitoreo_internas, name='api-monitoreo-internas'),
    path('api/monitoreo/urgencias/', api_monitoreo.api_monitoreo_urgencias, name='api-monitoreo-urgencias'),
    path('api/monitoreo/tendencias/', api_monitoreo.api_monitoreo_tendencias, name='api-monitoreo-tendencias'),
    path('api/monitoreo/actividad/', api_monitoreo.api_monitoreo_actividad, name='api-monitoreo-actividad'),
    path('api/monitoreo/notificaciones/', api_monitoreo.api_monitoreo_notificaciones, name='api-monitoreo-notificaciones'),
    path('api/monitoreo/errores-sync/', api_monitoreo.api_monitoreo_errores_sync, name='api-monitoreo-errores-sync'),
    path('api/monitoreo/rebotes/', api_monitoreo.api_monitoreo_rebotes, name='api-monitoreo-rebotes'),
    path(
        'api/monitoreo/despliegue-oficinas/',
        api_monitoreo.api_monitoreo_despliegue_oficinas,
        name='api-monitoreo-despliegue-oficinas',
    ),
    path(
        'api/monitoreo/despliegue-oficinas/<int:oficina_id>/',
        api_monitoreo.api_monitoreo_despliegue_oficina_actualizar,
        name='api-monitoreo-despliegue-oficina-actualizar',
    ),

    # Webhooks Postmark (salida híbrida — sin autenticación de sesión)
    path('api/webhooks/postmark/', views_postmark_webhook.postmark_webhook, name='postmark-webhook'),

    # API Chat de soporte interno
    path('api/chat/conversaciones/', api_chat.api_chat_conversaciones, name='api-chat-conversaciones'),
    path('api/chat/conversaciones/crear/', api_chat.api_chat_crear_conversacion, name='api-chat-crear'),
    path('api/chat/conversaciones/<int:conversacion_id>/mensajes/', api_chat.api_chat_mensajes, name='api-chat-mensajes'),
    path('api/chat/conversaciones/<int:conversacion_id>/mensajes/enviar/', api_chat.api_chat_enviar_mensaje, name='api-chat-enviar'),
    path('api/chat/conversaciones/<int:conversacion_id>/estado/', api_chat.api_chat_cambiar_estado, name='api-chat-estado'),
    path('api/chat/resumen/', api_chat.api_chat_resumen, name='api-chat-resumen'),
    path('api/chat/resumen-tickets/', api_chat.api_chat_resumen_tickets, name='api-chat-resumen-tickets'),
    path('api/chat/directorio/', api_chat.api_chat_directorio, name='api-chat-directorio'),
    path('api/chat/usuarios/<int:user_id>/', api_chat.api_chat_usuario_detalle, name='api-chat-usuario-detalle'),
    path('api/chat/notificaciones/', api_chat.api_chat_notificaciones, name='api-chat-notificaciones'),

    # API Comunicaciones Internas (Visor de documentos)
    path('api/interna/<int:pk>/documento/', api_views.api_interna_documento_meta, name='api-interna-doc-meta'),
    path('api/interna/<int:pk>/documento/pdf/', api_views.api_interna_documento_pdf, name='api-interna-doc-pdf'),
    path('api/interna/<int:pk>/documento/anexo/<int:anexo_id>/', api_views.api_interna_anexo_pdf, name='api-interna-doc-anexo'),

    # Chat de soporte (vista usuario)
    path('chat/', views.chat_soporte_view, name='chat-soporte'),

] + router.urls 