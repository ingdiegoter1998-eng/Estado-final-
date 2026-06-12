# Informe de Actividades — Marzo 2026

**Proyecto:** Sistema de Gestión de Correspondencia  
**Período:** 1 al 31 de marzo de 2026  
**Generado:** 31 de marzo de 2026

---

## Resumen Ejecutivo

Durante marzo de 2026 se trabajó de forma continua en la evolución del aplicativo de correspondencia, abordando progresivamente once frentes: refuerzo de la infraestructura de recepción y supervisión de correos (pipeline IMAP, locks, watchdog, panel de control operativo), políticas de seguridad para adjuntos entrantes, procesamiento y detección de rebotes SMTP, rediseño integral de interfaces de usuario, construcción de un visor documental en Next.js, consolidación del sistema de chat/tickets y monitoreo, desarrollo y evaluación del asistente IA documental con Gemini Flash, simplificación de formularios de radicación, implementación de respuesta discrecional sobre correspondencia, automatización de aprobación y envío de respuestas pendientes, y unificación visual completa del sistema (sidebar, paleta, tipografía).

---

## Actividades Realizadas

### 1. Infraestructura de Recepción y Supervisión de Correos (Pipeline IMAP)

**Fecha:** 1 al 4 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Durante los primeros días de marzo se abordó la consolidación del pipeline completo de recepción de correos. Se refactorizó la tarea principal de Celery (`procesar_emails_periodico`), se implementó un mecanismo de lock compartido en Redis para evitar colisiones entre tareas concurrentes, se construyó la tarea watchdog (`watchdog_inbox`) para detectar correos faltantes en INBOX, y se diseñó el panel de control de sincronización accesible desde Ventanilla.

**Componentes construidos/reforzados:**

- **Tarea `procesar_emails_periodico`:** ejecución periódica cada 5 min (configurable vía `CELERY_EMAIL_CHECK_INTERVAL`), con lock Redis, manejo de `SoftTimeLimitExceeded`, cierre limpio de conexiones y actualización automática del modelo `EstadoSincronizacionCorreos` en cada rama (success, fail, timeout).
- **Lock Redis anti-colisión:** clave `correspondencia:email_processing_lock` con timeout de seguridad (240s principal, 120s watchdog), liberación garantizada en bloque `finally`, fallback a cache de Django si Redis no está disponible.
- **Tarea `watchdog_inbox`:** vigila INBOX cada 15 min (configurable vía `CELERY_IMAP_WATCHDOG_INTERVAL`), descarga solo headers para comparar `message_id` contra BD, incluye correos problemáticos no resueltos en la deduplicación, procesa máximo 20 faltantes por ciclo.
- **Comando `procesar_emails_seguro`:** modo normal (INBOX, 1 día), modo recovery (INBOX + AllMail, 7 días), flags `--dry-run`, `--days`, `--since`/`--until` con rango ISO 8601, deduplicación cruzada entre carpetas, procesamiento en lotes de 50.
- **Panel de control operativo** en `/registros/correspondencia/ventanilla/control-sincronizacion/` con 6 operaciones: VERIFY (cobertura Gmail vs BD), RECOVER (recuperación de faltantes), DUPLICATES (detección de duplicados reales y sospechosos), DIAGNOSE (estado de Celery, lock, workers), IMAP_TEST (conectividad IMAP), SYNC_NOW (sincronización inmediata).
- **Modelos operativos:** `EstadoSincronizacionCorreos` (estado resumido de la última sincronización), `EjecucionControlCorreos` (bitácora de operaciones con métricas: encontrados, nuevos, guardados, rechazados, adjuntos, duplicados, sospechosos, errores) y `CorreoProblematico` (bandeja de correos que no pasaron validación).
- **Saneamiento automático:** ejecuciones atascadas en PENDING o RUNNING por más de 20 minutos se marcan automáticamente como FAIL. Posibilidad de cancelar o eliminar ejecuciones desde el panel.

**Archivos principales:** `correspondencia/tasks.py`, `correspondencia/email_sync_control.py`, `correspondencia/views_sync_control.py`, `correspondencia/management/commands/procesar_emails_seguro.py`, `correspondencia/models.py`

**Validación:** suite de tests dedicada con 649 líneas de prueba (ver actividad 13).

---

### 2. Política de Seguridad para Adjuntos Entrantes

**Fecha:** 4 al 5 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Se diseñó e implementó una política de seguridad centralizada para validar todos los adjuntos que ingresan al sistema vía correo electrónico. La política funciona como punto de control antes de persistir cualquier archivo, y se aplica tanto en el flujo normal como en el watchdog y recovery.

**Componentes:**

- **Configuración centralizada** en `correspondencia/settings/email_config.py`:
  - Whitelist de extensiones permitidas: PDF, Office, imágenes, comprimidos controlados (25 tipos).
  - Blacklist explícita de extensiones bloqueadas: ejecutables, scripts, macros peligrosos (30+ tipos).
  - Límites de tamaño: 20 MB por archivo, 40 MB total por correo, máximo 20 archivos por correo.
- **Validador `EmailAttachmentValidator`:** validación de extensión (whitelist/blacklist), validación de tamaño individual, validación de peso total y cantidad por email.
- **Pipeline de ingestion unificado** en `correspondencia/utils/email_ingestion.py`: normalización de `message_id`, normalización de fechas con timezone, extracción de metadata de adjuntos, despacho a `CorreoProblematico` cuando un adjunto falla validación con motivo clasificado (ADJUNTO_EXCEDE_LIMITE, TOTAL_EXCEDE_LIMITE, TIPO_BLOQUEADO, TIPO_NO_PERMITIDO, VALIDACION_ADJUNTO).
- **Modelo `CorreoProblematico`:** almacena correos que no pasaron validación con motivo, detalle, resumen de adjuntos JSON, y bandera de resolución para seguimiento operativo.

**Archivos principales:** `correspondencia/settings/email_config.py`, `correspondencia/utils/email_attachment_validator.py`, `correspondencia/utils/email_ingestion.py`, `correspondencia/models.py`

---

### 3. Procesamiento de Rebotes SMTP y Aprobación Automática de Respuestas

**Fecha:** 6 al 7 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Se construyeron dos subsistemas complementarios para cerrar el ciclo completo de correspondencia saliente: detección de rebotes SMTP y aprobación automática de respuestas pendientes.

**Rebotes SMTP (`procesar_rebotes`):**
- Comando `manage.py procesar_rebotes` que escanea IMAP buscando correos DSN (Delivery Status Notification).
- Parseo completo de mensajes multipart/report: extracción de `Final-Recipient`, `Status`, `Diagnostic-Code`, código SMTP.
- Actualización automática de `SalidaDestinatario` y `HistorialSalida` con el estado del rebote.
- Tarea periódica `procesar_rebotes_periodico` ejecutada cada 10 minutos por Celery Beat.

**Aprobación automática de respuestas:**
- Tarea `aprobar_y_enviar_respuestas_pendientes_periodico` que procesa respuestas en estados PENDIENTE_APROBACION y ERROR_ENVIO.
- Usuario de aprobación configurable vía variable de entorno `CELERY_APROBACION_USER`.
- Ejecución cada minuto (configurable vía `CELERY_APROBAR_RESPUESTAS_INTERVAL`).

**Archivos principales:** `correspondencia/management/commands/procesar_rebotes.py`, `correspondencia/tasks.py`, `correspondencia/aprobacion_envio.py`

---

### 4. Rediseño Visual de Bandejas y Dashboard de Usuario

**Fecha:** 7 al 9 de marzo de 2026  
**Estado:** Completado e integrado en `main`

**Descripción:**  
Se inició el mes con la homologación visual de las bandejas de correspondencia y el dashboard del usuario. El trabajo se distribuyó en tres días: primero la bandeja de oficina, luego la interoficina, y al cierre el dashboard principal.

**Entregables:**
- Rediseño completo de `bandeja_oficina.html`: nueva estructura con contenedores amplios, tarjetas con bordes redondeados, sombras suaves, badges/pills para estados, panel de filtros colapsable y paginación estilizada.
- Rediseño completo de `bandeja_interoficina.html`: homologación de layout con la nueva línea visual, badges para origen/visibilidad, modal de historial de lectura mejorado.
- Retoque visual del `dashboard_usuario.html`: ajuste de ancho útil, mejora de cards con sombras y cabeceras, refinamiento del hero principal, mejor contraste y legibilidad.

**Validación:** `python manage.py check` sin errores. Commit `70c88b0`, integrado en `main`.

---

### 5. Visor Documental de Comunicaciones Internas (Next.js)

**Fecha:** 9 al 11 de marzo de 2026  
**Estado:** Completado y en producción

**Descripción:**  
Aprovechando el impulso del rediseño visual, se construyó un visor documental embebido en el aplicativo calendario Next.js para comunicaciones internas. El objetivo principal fue evitar la descarga directa de PDFs, ofreciendo una previsualización en línea con metadata completa. El desarrollo tomó varios días por la necesidad de integrar con el backend Django, implementar previsualización de múltiples formatos y resolver restricciones de seguridad.

**Ruta funcional:** `/calendario/documento/<id>`

**Características:**
- Visualización de metadata: radicado, estado, asunto, remitente, destinatario, tipo de distribución, historial.
- Pestañas: Documento principal, Documento firmado, Adjuntos.
- Previsualización inline para PDF e imágenes; descarga/apertura externa para otros formatos.
- Solo un archivo activo a la vez para optimizar rendimiento.
- **Ajuste de seguridad:** se habilitó `X-Frame-Options: SAMEORIGIN` solo en endpoints del visor, manteniendo `DENY` global para protección de clickjacking.

---

### 6. Sistema de Chat/Tickets y Monitoreo Administrativo

**Fecha:** 11 al 14 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Se consolidó el módulo de chat/tickets tanto en la experiencia administrativa (Monitoreo Next.js) como en el acceso operativo (Ventanilla Django). Este fue un bloque de trabajo intenso que incluyó nuevos endpoints, hooks, componentes de interfaz y corrección de un problema crítico con imágenes adjuntas.

**Entregables:**
- Ampliación del chat administrativo en `/monitoreo/chat`: resumen KPI de tickets, panel de notificaciones, directorio de usuarios por oficinas, modal de detalle, creación de tickets desde directorio.
- Nuevos endpoints backend en `correspondencia/api_chat.py`: resumen extendido, directorio por oficina, detalle de usuario, feed de notificaciones.
- Nuevos hooks y reestructuración de pantalla Next.js (`use-directorio.ts`, `use-chat.ts`).
- Accesos desde Ventanilla: botón en portada de pendientes y enlace en sidebar.
- **Corrección de imágenes adjuntas:** se solucionó error donde las imágenes no cargaban por URLs absolutas generadas detrás del proxy. Se centralizó serialización a rutas públicas relativas.

---

### 7. Mejoras al Asistente IA Documental (Chatbot RAG)

**Fecha:** 14 al 17 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Con la infraestructura de chat estabilizada, se dedicó un bloque de cuatro días a la mejora integral del asistente IA documental. Se trabajó en tres ejes: ampliación de la base de conocimiento indexada, refinamiento del pipeline de retrieval/scoring, y expansión de la suite de pruebas.

**Día a día del avance:**
- **14 mar:** Auditoría del corpus documental. Se identificaron documentos no indexados y chunks basura. Se amplió la indexación de 7 a 42 documentos activos (de 187 a 596 chunks).
- **15 mar:** Limpieza de chunks menores a 40 caracteres. Introducción de `CODE_FENCE_RE` para limpiar bloques de código antes de segmentar.
- **16 mar:** Mejora de scoring con `length_factor` y `coverage_bonus` para privilegiar fragmentos sustantivos. Refuerzo del prompt para respuestas más concretas, operativas y ancladas al contexto.
- **17 mar:** Corrección de `is_greeting()` que fallaba por colisión con stopwords. Ampliación de la suite de tests a 90 pruebas pasando.

**Archivos principales:** `correspondencia/services_chatbot.py`, `correspondencia/tests/test_chatbot_mvp.py`

---

### 8. Simplificación del Formulario de Radicación — Eliminación del Radicado Manual

**Fecha:** 18 al 19 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Se abordó una tarea de simplificación: eliminar la posibilidad de ingresar manualmente un número de radicado en el formulario de radicación. Tras analizar el uso del campo y confirmar que generaba errores por duplicados y formatos inconsistentes, se procedió a removerlo por completo. El sistema ahora genera siempre el número automáticamente bajo el formato estándar.

**Archivos modificados:**
- `correspondencia/forms.py` — eliminación del campo `numero_radicado_manual` y sus validaciones asociadas.
- `correspondencia/views.py` — eliminación de la lógica condicional en vistas `dashboard_ventanilla`, `dashboard_ventanilla_legacy` y `detalle_correo_entrante_view`.

**Resultado:** Formularios más limpios, menor superficie de error y consistencia total en la numeración de radicados.

---

### 9. Implementación de Respuesta Discrecional sobre Correspondencia

**Fecha:** 20 al 25 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Se diseñó e implementó la funcionalidad de respuesta discrecional, que permite a usuarios autorizados responder correspondencia previamente clasificada como "no requiere respuesta", de forma controlada y con trazabilidad completa. El desarrollo abarcó modelo de datos, permisos, validación servidor/cliente y migración.

**Cambios funcionales:**
- Nuevo permiso Django: `responder_correspondencia_discrecional`.
- Nuevos campos en `CorrespondenciaSalida`: `tipo_respuesta` y `motivo_respuesta_discrecional`.
- Motivo obligatorio para toda respuesta discrecional.
- Evento específico en `HistorialSalida` para trazabilidad.
- Validación del lado servidor y cliente (modal AJAX y formulario clásico).
- Migración `0071_respuesta_discrecional_permiso_y_trazabilidad.py` con grupo semilla para Planeación y Facturación.

**Archivos modificados:** `models.py`, `forms.py`, `views.py`, `detalle_correspondencia.html`, `modal_responder_correspondencia.html`, `respuesta_form.html`, `responder-correspondencia.js`.

---

### 10. Evaluación del Asistente IA en Chat en Vivo

**Fecha:** 26 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Una vez estabilizado el chatbot, se realizó una evaluación completa contra la API real con preguntas operativas, saludos, consultas ambiguas y solicitudes de datos técnicos internos.

**Calificación obtenida:**
| Criterio | Nota |
|----------|------|
| Utilidad operativa | 7/10 |
| Claridad de redacción | 8/10 |
| Fidelidad al contexto | 6/10 |
| Manejo de límites y seguridad | 8.5/10 |
| Confiabilidad del servicio | 4/10 |
| **Calidad general percibida** | **6.5/10** |

**Hallazgos:**
- Errores 503 transitorios del proveedor Gemini afectan percepción de calidad.
- Respuestas truncadas por `MAX_TOKENS` en preguntas relevantes.
- Buena restricción de datos técnicos internos al usuario final.

**Plan técnico derivado:** reintentos con backoff para 502/503/504, manejo de truncamiento, reducción de contexto cuando crece el historial.

---

### 11. Evaluación Gemini Flash vs Standard y Definición de Estrategia

**Fecha:** 26 al 27 de marzo de 2026  
**Estado:** Completado (decisión documentada)

**Descripción:**  
Complementando la evaluación funcional, se documentó la decisión técnica sobre el uso de Gemini Flash frente a Gemini Standard, comparando calidad de respuesta, costo y latencia.

**Conclusión técnica:**
- Gemini 3 Standard: 10/10 (referencia).
- Gemini 3 Flash: ~8/10 para este asistente, con variación según calidad del retrieval.
- Decisión: mantener Gemini Flash como base operativa por costo y velocidad.
- La mejora más rentable sigue estando en el sistema RAG y en la disciplina de respuesta.
- Se creó skill específica para trabajar Gemini Flash dentro del proyecto.

---

### 12. Modal Chatbot Dual-Tab (Asistente IA + Soporte TI)

**Fecha:** 27 al 28 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
Con los resultados de la evaluación, se procedió a integrar el asistente IA y el chat de Soporte TI en un único modal con pestañas, resolviendo varias correcciones de UX detectadas durante las pruebas de los días previos.

**Cambios realizados:**
- Rediseño del modal con dos pestañas: "Asistente IA" (chatbot RAG) y "Soporte TI" (tickets/reportes).
- Fix de CSS grid para acomodar barra de pestañas (de 2 a 3 filas).
- Fix de salto de altura al cambiar pestañas (migración de `display: none` a `visibility: hidden` con celdas superpuestas).
- Sidebar toggle independiente por pestaña.
- Botón inline "Crear nuevo reporte" en estado vacío de Soporte.
- **94 tests del chatbot pasando** tras los ajustes finales.

---

### 13. Suite de Tests para Pipeline de Correos y Watchdog

**Fecha:** Desarrollo continuo (1–28 de marzo)
**Estado:** Completado

**Descripción:**  
A lo largo del mes se construyó y amplió una suite de pruebas unitarias dedicada al pipeline de correos, cubriendo los mecanismos de lock, la tarea principal, el watchdog y las operaciones del panel de control. Las pruebas se desarrollaron en paralelo con cada componente para validar comportamiento ante escenarios reales: lock activo, timeout, errores IMAP, correos faltantes, duplicados, y correos problemáticos.

**Cobertura:**

- **`test_watchdog_inbox.py`** (439 líneas): tests de lock (adquirir, rechazar, liberar), test de procesar_emails_periodico con lock, test de watchdog sin correos, con todos los correos ya en BD, con faltante que se rescata, con lock activo que omite, con correos problemáticos, y coordinación entre tareas.
- **`test_procesar_emails_celery.py`** (210 líneas): tests del comando seguro, modo dry-run, modo recovery, validación de adjuntos, deduplicación por message_id.

**Total:** 649 líneas de prueba dedicadas exclusivamente al frente de correos.

---

### 14. Unificación Visual del Sistema (Welcome + Sidebar + Paleta)

**Fecha:** 29 al 31 de marzo de 2026  
**Estado:** Completado

**Descripción:**  
El cierre del mes se dedicó a la unificación visual del sistema completo: consolidar sidebars, limpiar páginas legacy, migrar la paleta de colores y estandarizar la tipografía. Este bloque le dio coherencia visual a todo el trabajo acumulado durante marzo.

**Cambios realizados:**
- **Correos salientes:** eliminación de `TO_DEFAULT` que copiaba automáticamente a correo innecesario.
- **Unificación de sidebars:** la página `/registros/welcome/` ahora usa el mismo sidebar moderno del dashboard (`sidebar_usuario.html`).
- **Restauración de accesos faltantes:** se agregaron secciones de Préstamos Documentales, FUID, Tarjetero Índice y Recursos al sidebar unificado.
- **Subcategorización de "Mi Correspondencia":** reorganización en 3 subgrupos (Vista general, Bandejas, Directorio y apoyo) para mejorar escaneo visual.
- **Limpieza de HTML muerto:** eliminación de sección Tarjetero y basura de Contactos obsoleta.
- **Iconos coloreados por sección:** asignación de colores diferenciados para cada sección del sidebar.
- **Reemplazo de navbar en welcome:** navbar custom reemplazado por `header_usuario.html` estándar con chip de estado, botón de Asistente IA y dropdown de notificaciones completo.
- **Migración de paleta teal → azul:** toda la paleta visual migrada de teal (#0f6077) al azul del sistema (#003366, #0b4f97, #0e63b9). Fuente migrada a IBM Plex Sans.
- **Fix z-index notificaciones:** corrección de dropdown renderizado detrás del hero.

---

## Resumen Cronológico

| Semana | Fechas | Actividad |
|--------|--------|-----------|
| **Semana 1** | 1 – 4 mar | Infraestructura de recepción y supervisión de correos (pipeline IMAP, locks, watchdog, panel de control) |
| | 4 – 5 mar | Política de seguridad para adjuntos entrantes |
| | 6 – 7 mar | Procesamiento de rebotes SMTP y aprobación automática de respuestas |
| | 7 – 9 mar | Rediseño visual de bandejas y dashboard de usuario |
| **Semana 2** | 9 – 11 mar | Visor documental de comunicaciones internas (Next.js) |
| | 11 – 14 mar | Sistema de chat/tickets y monitoreo administrativo |
| | 14 – 17 mar | Mejoras al asistente IA (indexación, retrieval, prompt, 90 tests) |
| **Semana 3** | 18 – 19 mar | Eliminación del campo de radicado manual |
| | 20 – 25 mar | Implementación de respuesta discrecional |
| **Semana 4** | 26 mar | Evaluación del asistente IA en chat en vivo |
| | 26 – 27 mar | Evaluación y decisión Gemini Flash vs Standard |
| | 27 – 28 mar | Modal chatbot dual-tab (Asistente IA + Soporte TI) |
| | 29 – 31 mar | Unificación visual del sistema (welcome, sidebar, paleta) |
| **Transversal** | 1 – 28 mar | Suite de tests para pipeline de correos y watchdog (649 líneas) |

---

## Tecnologías Involucradas

- **Backend:** Django, Python, Celery, PostgreSQL
- **Frontend:** HTML/CSS/JS (Bootstrap 5), Next.js, React, Tailwind CSS
- **IA:** Google Gemini Flash (chatbot RAG)
- **Infraestructura:** Nginx (reverse proxy), IMAP, Redis (locks)
- **Automatización:** Celery Beat (6 tareas periódicas programadas)

---

## Métricas Relevantes

- Tests del chatbot: **94 pasando** (al cierre del mes)
- Tests del pipeline de correos: **649 líneas** en 2 suites dedicadas
- Documentos indexados: **42** (antes: 7)
- Chunks indexados: **596** (antes: 187)
- Calidad percibida del asistente IA: **6.5/10**
- Gemini Flash evaluado como: **8/10** vs Standard como referencia
- Tareas Celery Beat configuradas: **6** (correos, rebotes, watchdog, urgencias ×2, aprobación automática)
- Operaciones del panel de control: **6** (VERIFY, RECOVER, DUPLICATES, DIAGNOSE, IMAP_TEST, SYNC_NOW)
- Extensiones de adjuntos permitidas: **25 tipos** / bloqueadas: **30+ tipos**
- Límites de adjuntos: **20 MB** por archivo, **40 MB** por correo, máximo **20** archivos
