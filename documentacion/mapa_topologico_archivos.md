# Mapa topologico de archivos clave del flujo

Version depurada: solo archivos realmente relevantes para entender y operar el aplicativo.
Se excluyeron dependencias, migraciones, tests y artefactos de build.

Total archivos clave: 229

## 01. Nucleo del Proyecto Django
Total: 9

- hospital_document_management/__init__.py — Archivo clave del aplicativo
- hospital_document_management/asgi.py — Punto de integracion con servidor de despliegue
- hospital_document_management/celery.py — Archivo clave del aplicativo
- hospital_document_management/settings.py — Configuracion central (DB, apps, correo, static, seguridad)
- hospital_document_management/settings_test.py — Archivo clave del aplicativo
- hospital_document_management/test_settings.py — Archivo clave del aplicativo
- hospital_document_management/urls.py — Mapa de rutas HTTP del modulo
- hospital_document_management/wsgi.py — Punto de integracion con servidor de despliegue
- manage.py — Entry point de Django (comandos, runserver, migraciones)

## 02. Backend de Correspondencia (Flujo Principal)
Total: 21

- correspondencia/__init__.py — Modulo de soporte del dominio correspondencia
- correspondencia/admin.py — Configuracion de administracion interna
- correspondencia/apps.py — Modulo de soporte del dominio correspondencia
- correspondencia/aprobacion_envio.py — Modulo de soporte del dominio correspondencia
- correspondencia/context_processors.py — Modulo de soporte del dominio correspondencia
- correspondencia/forms.py — Formularios y validaciones de captura/edicion
- correspondencia/management/__init__.py — Modulo de soporte del dominio correspondencia
- correspondencia/modelos_minimos_sla.py — Modulo de soporte del dominio correspondencia
- correspondencia/models.py — Modelo de datos y reglas del dominio de correspondencia
- correspondencia/settings/email_config.py — Modulo de soporte del dominio correspondencia
- correspondencia/signals.py — Eventos automáticos al guardar/eliminar modelos
- correspondencia/tasks.py — Procesos asincronos y tareas programadas
- correspondencia/templatetags/__init__.py — Modulo de soporte del dominio correspondencia
- correspondencia/templatetags/auth_extras.py — Modulo de soporte del dominio correspondencia
- correspondencia/urls.py — Mapa de rutas HTTP del modulo
- correspondencia/utils/email_attachment_validator.py — Modulo de soporte del dominio correspondencia
- correspondencia/utils/email_processor_example.py — Modulo de soporte del dominio correspondencia
- correspondencia/utils_sla.py — Modulo de soporte del dominio correspondencia
- correspondencia/views.py — Flujo principal de bandejas, radicacion y operaciones
- correspondencia/views_aprobar_masivo.py — Modulo de soporte del dominio correspondencia
- correspondencia/views_urgencias.py — Flujo especifico de correspondencia urgente

## 03. Comandos Operativos de Correo
Total: 5

- correspondencia/management/commands/actualizar_fechas_lectura.py — Comando operativo del flujo de correos/radicacion
- correspondencia/management/commands/clasificar_emails_ia.py — Comando operativo del flujo de correos/radicacion
- correspondencia/management/commands/procesar_emails.py — Comando operativo del flujo de correos/radicacion
- correspondencia/management/commands/procesar_emails_seguro.py — Comando operativo del flujo de correos/radicacion
- correspondencia/management/commands/procesar_rebotes.py — Comando operativo del flujo de correos/radicacion

## 04. Templates de Interfaz y Correos
Total: 89

- correspondencia/templates/correspondencia/admin/bandeja_clasificados.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/bandeja_correos_pendientes.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/bandeja_entrada.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/bandeja_radicacion_rapida.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/bandeja_radicacion_rapida_saliente.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/bandeja_respuestas.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/calendario_informes.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/contacto_form.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/contactos_automaticos.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/dashboard_moderno.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/dashboard_ventanilla.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/detalle_correo_clasificado.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/detalle_correo_entrante.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/detalle_dia_informe.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/detalle_respuesta_salida.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/detalle_respuesta_salida_errores.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/distribuir_correspondencia.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/entidad_form.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/historial_correspondencia.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/lista_contactos.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/lista_entidades.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/lista_pendientes.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/metricas_destinatarios.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/radicar_form.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/redistribuir_interna.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/admin/revisar_respuesta.html — Pantalla principal del usuario en el flujo operativo
- correspondencia/templates/correspondencia/agenda/comunicacion_detalle.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/agenda/comunicacion_form.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/agenda/comunicaciones_list.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/agenda/grupo_confirm_delete.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/agenda/grupo_form.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/agenda/grupos_index.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/base_correspondencia.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/base_correspondencia_usuario.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/bases/base_correspondencia.html — Layout base compartido de interfaz
- correspondencia/templates/correspondencia/bases/base_correspondencia_usuario.html — Layout base compartido de interfaz
- correspondencia/templates/correspondencia/categoria_detalle.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/email/notificacion_asignacion_entrante.html — Plantilla de notificacion/correo saliente
- correspondencia/templates/correspondencia/email/respuesta_salida_base.html — Plantilla de notificacion/correo saliente
- correspondencia/templates/correspondencia/includes/mass_actions_toolbar.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/includes/tabla_correspondencia.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/includes/tabla_fila_correspondencia.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/aprobar.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/bienvenida.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/configurar_firma.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/confirmar_firma.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/detalle.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/enviadas.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/historial_respuestas.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/lista.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/pendientes_aprobacion.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/recibidas.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/responder.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/subir_firma.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/interna/trazabilidad.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/partials/correos_pendientes_table.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/header_usuario.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/messages.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modal_radicar_urgencia.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_agenda_contactos.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_compartir.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_comunicacion_interna.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_comunicacion_interna_v2.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_contacto.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_contacto_dashboard.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_correspondencia_salida.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_editar_comunicacion_interna.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_entidad.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_estadisticas_oficinas.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_grupo_agenda.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_radicacion.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_entrante.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_saliente.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_redistribuir_oficinas.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/modals/modal_responder_correspondencia.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/sidebar_usuario.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/partials/sidebar_usuario_BACKUP.html — Fragmento reusable (modales/componentes del flujo)
- correspondencia/templates/correspondencia/urgencias/buzon_urgencias.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/urgencias/detalle_urgencia.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/bandeja_interoficina.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/bandeja_oficina.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/bandeja_personal.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/bandeja_respuestas_salientes.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/compartir_form.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/contactos_globales.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/dashboard_usuario.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/redistribuir_oficinas.html — Template del modulo correspondencia
- correspondencia/templates/correspondencia/usuario/respuesta_form.html — Template del modulo correspondencia

## 05. Frontend Propio (JS/CSS)
Total: 24

- correspondencia/static/correspondencia/css/base_correspondencia.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/base_correspondencia_usuario.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/dashboard-modern.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/datatables-modern.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/datatables-responsive.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/lista_pendientes.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/modal-comunicacion-interna.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/modern-layout.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/navbar-fixes.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/css/notificaciones.css — Estilos visuales de pantallas del flujo
- correspondencia/static/correspondencia/js/cleanup-overflow.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/datatables-modern.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/datatables-responsive.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/comunicacion-interna.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/core-modals.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/correspondencia-salida.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/modal-minimizable.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/radicacion-rapida-entrante.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/radicacion.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modals/responder-correspondencia.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/modern-layout.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/notificaciones-toast.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/notificaciones.js — Logica frontend (interacciones, AJAX, validaciones en cliente)
- correspondencia/static/correspondencia/js/sla-calculator.js — Logica frontend (interacciones, AJAX, validaciones en cliente)

## 06. Modulo Documental (TRD)
Total: 78

- documentos/__init__.py — Modulo de apoyo documental (TRD)
- documentos/admin.py — Admin del modulo documental
- documentos/apps.py — Modulo de apoyo documental (TRD)
- documentos/forms.py — Formularios de configuracion documental
- documentos/management/commands/__init__.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/corregir_oficinas.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/corregir_oficinas_faltantes.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/corregir_ultimas_oficinas.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/crear_oficinas_series_faltantes.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/import_data.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/import_fichas.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/import_trd_oficinas.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/import_trd_series_subseries.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/importar_csv.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/listar_oficinas.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/poblar_procesos.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/poblar_series_oficinas.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/populate_db.py — Modulo de apoyo documental (TRD)
- documentos/management/commands/update_subseries_trd.py — Modulo de apoyo documental (TRD)
- documentos/models.py — Modelos TRD/series/subseries documentales
- documentos/services.py — Modulo de apoyo documental (TRD)
- documentos/tasks.py — Modulo de apoyo documental (TRD)
- documentos/templates/403.html — Modulo de apoyo documental (TRD)
- documentos/templates/404.html — Modulo de apoyo documental (TRD)
- documentos/templates/500.html — Modulo de apoyo documental (TRD)
- documentos/templates/_form_registro.html — Modulo de apoyo documental (TRD)
- documentos/templates/agregar_registro_a_fuid.html — Modulo de apoyo documental (TRD)
- documentos/templates/agregar_registro_form.html — Modulo de apoyo documental (TRD)
- documentos/templates/base.html — Modulo de apoyo documental (TRD)
- documentos/templates/basefichas.html — Modulo de apoyo documental (TRD)
- documentos/templates/detalle_ficha_paciente.html — Modulo de apoyo documental (TRD)
- documentos/templates/documento_detalle.html — Modulo de apoyo documental (TRD)
- documentos/templates/editar_registro_de_fuid.html — Modulo de apoyo documental (TRD)
- documentos/templates/ficha_paciente_form.html — Modulo de apoyo documental (TRD)
- documentos/templates/files.html — Modulo de apoyo documental (TRD)
- documentos/templates/fuid_complete_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/fuid_form.html — Modulo de apoyo documental (TRD)
- documentos/templates/fuid_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/lista_fichas_paciente.html — Modulo de apoyo documental (TRD)
- documentos/templates/pagina_estadisticas.html — Modulo de apoyo documental (TRD)
- documentos/templates/panel_de_control.html — Modulo de apoyo documental (TRD)
- documentos/templates/partials/sidebar_nav.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/confirmacion.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/detalle.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/gestion_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/mis_prestamos_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/partials/sidebar_prestamos.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/procesar_form.html — Modulo de apoyo documental (TRD)
- documentos/templates/prestamos/solicitud_form.html — Modulo de apoyo documental (TRD)
- documentos/templates/registration/login.html — Modulo de apoyo documental (TRD)
- documentos/templates/registration/registro.html — Modulo de apoyo documental (TRD)
- documentos/templates/registro_completo.html — Modulo de apoyo documental (TRD)
- documentos/templates/registro_form.html — Modulo de apoyo documental (TRD)
- documentos/templates/registro_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/soporte.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/bienvenida.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/buscar.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/ficha_paciente_detail.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/ficha_paciente_form1.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/fichas_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/importar_excel.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/preparar.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas.html/resultado_importacion.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/bienvenida.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/buscar.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/ficha_paciente_detail.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/ficha_paciente_form1.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/fichas_list.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/importar_excel.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/preparar.html — Modulo de apoyo documental (TRD)
- documentos/templates/templatesfichas/resultado_importacion.html — Modulo de apoyo documental (TRD)
- documentos/templates/welcome.html — Modulo de apoyo documental (TRD)
- documentos/templatetags/__init__.py — Modulo de apoyo documental (TRD)
- documentos/templatetags/custom_filters.py — Modulo de apoyo documental (TRD)
- documentos/transformacion_datos.py — Modulo de apoyo documental (TRD)
- documentos/urls.py — Mapa de rutas HTTP del modulo
- documentos/views.py — Vistas de administracion documental
- documentos/views_errors.py — Modulo de apoyo documental (TRD)

## 07. Modulo DataUnidad
Total: 1

- dataUnidad/import_data.py — Modulo de datos de apoyo del sistema

## 09. Otros Archivos Clave
Total: 2

- correspondencia/templates/detalle_respuesta_salida.html — Template del modulo correspondencia
- correspondencia/templates/includes/paginacion.html — Template del modulo correspondencia
