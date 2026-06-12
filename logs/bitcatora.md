"comando de peticion: Instrucciones de Ejecución:

Análisis de Contexto: Sintetiza todas las modificaciones, correcciones y acuerdos alcanzados durante la sesión actual de chat.

Inmutabilidad Histórica: Bajo ninguna circunstancia edites, elimines o alteres el texto existente en el archivo. Tu escritura debe comenzar estrictamente en una nueva línea al final del documento.

Detección Temporal: Registra la entrada con la fecha actual del sistema. Si no tienes acceso a la fecha exacta, utiliza el formato [FECHA_ACTUAL].

Estructura de Salida Requerida (Markdown): Genera el reporte siguiendo rigurosamente esta jerarquía:

[Fecha: DD/MM/AAAA] - Sesión de Trabajo
1. Cambios Atómicos (Lo Táctico)
Listar de forma granular los archivos creados, modificados o eliminados.

Describir brevemente la funcionalidad técnica implementada.

2. Decisiones Arquitectónicas (Lo Estratégico)
Decisión: [Nombre de la decisión de alto nivel]

Fundamentación: Explicar el porqué estratégico (causa raíz, optimización de costos, seguridad, deuda técnica).

Ejecuta la actualización ahora

# Bitácora de Cambios – Sesión de Desarrollo"

**Período:** 30 de enero, 1 y 2 de febrero de 2026

---

## 1. Formularios de Radicación Rápida (Entrante y Saliente)

### Cambios realizados
- Creación de formularios simplificados para radicación rápida: `RadicacionRapidaEntranteForm` y `RadicacionRapidaSalienteForm`.
- Ubicación: botones en el dashboard de ventanilla (`/registros/correspondencia/ventanilla/dashboard/`).
- Modales `modal_radicacion_rapida_entrante.html` y `modal_radicacion_rapida_saliente.html`.
- Campos mínimos: asunto, oficina destino, remitente (opcional) para entrante; destinatario y oficina emisora para saliente.

### Decisión de alto nivel
Implementar un formulario de radicación rápida para el período de transición durante el despliegue por oficinas. **Por qué:** durante la fase de implementación, las oficinas que se suman necesitan registrar correspondencia de forma ágil sin depender de los flujos completos (radicado automático, Excel externo, etc.). La radicación rápida permite capturar lo esencial y asignar consecutivo.

---

## 2. Corrección de selectores vacíos en modales de Radicación Rápida

### Cambios realizados
- Los selectores de remitente, oficina destino, medio de recepción (entrante) y destinatario/contacto, oficina emisora (saliente) aparecían vacíos.
- Desactivación de Crispy Forms (`self.helper = None`) para renderizado manual de campos.
- Clase `select2` en los widgets para usar Select2 con `dropdownParent` apuntando al modal.
- Campo `medio_recepcion`: definido explícitamente como `forms.ChoiceField` con `MEDIO_RECEPCION_CHOICES` y widget con clase `select2`.

### Decisión de alto nivel
Tomar los mismos endpoints y configuración que usan los modales ya funcionales. **Por qué:** los selectores se alimentan de APIs/querysets; al desactivar Crispy y alinear el HTML con el modal de referencia, Select2 pudo inicializarse correctamente dentro del modal.

---

## 3. Nuevos campos opcionales en el modelo Correspondencia

### Cambios realizados
- 16 campos adicionales (todos `null=True, blank=True`) para correspondencia externa entrante:
  - `entidad_persona_remitente`, `funcionario_responsable_tramite`, `clasificacion_comunicacion`
  - `numero_folios`, `anexos`, `medio_recibido`, `direccion_correo_remitente`
  - `empresa_transportadora`, `numero_guia`, `fecha_limite_respuesta_manual`
  - `fecha_primer_seguimiento`, `fecha_segundo_seguimiento`, `fecha_notificacion_vencimiento`
  - `fecha_respuesta`, `estado_respuesta`, `radicado_enviado_respuesta`
- Migraciones: `0045_campos_temporales_radicacion_rapida`, `0046_add_origen_radicacion`.

### Decisión de alto nivel
Incluir campos temporales opcionales sin alterar el flujo principal. **Por qué:** se requieren datos extra para seguimiento y control, pero aún no están definidos en el proceso formal. Hacerlos opcionales permite usarlos cuando aplique sin bloquear radicaciones básicas.

---

## 4. Campo origen_radicacion

### Cambios realizados
- Nuevo campo `origen_radicacion` en el modelo `Correspondencia`.
- Valores: `NORMAL`, `RAPIDA`, `CORREO`.
- Se asigna según el flujo: `RAPIDA` al usar radicación rápida, `CORREO` al radicar desde correo electrónico.

### Decisión de alto nivel
Identificar el origen de cada radicado para evitar confusión durante el despliegue. **Por qué:** se mezclan radicados automáticos, manuales, rápidos y desde correo; sin un indicador explícito sería difícil rastrear su procedencia.

---

## 5. Ajustes visuales del modal de Radicación Rápida entrante

### Cambios realizados
- `modal-content` más ancho (~20 % más): `max-width: 1370px`.
- Layout de 2 a 4 columnas (`col-md-3`).
- Integración de los 16 campos opcionales en la sección "Datos adicionales (opcionales)".

### Decisión de alto nivel
Ampliar el modal y pasar a 4 columnas para facilitar la lectura y el llenado de los campos adicionales sin saturar la pantalla.

---

## 6. Nueva bandeja "Historial de Radicación Rápida"

### Cambios realizados
- Vista `BandejaRadicacionRapidaView` con filtro `origen_radicacion='RAPIDA'`.
- Template `bandeja_radicacion_rapida.html` con filtros para todos los campos.
- URL: `/registros/correspondencia/radicacion-rapida/`.
- Enlace en el menú lateral tras "Historial General".

### Decisión de alto nivel
Ofrecer una bandeja exclusiva para radicados rápidos. **Por qué:** concentrar el seguimiento de la radicación rápida y permitir filtros específicos sin mezclar con otros flujos.

---

## 7. Cambios en la página Historial General

### Cambios realizados
- Asunto truncado a 40 caracteres con "..." y más espacio en la columna.
- Oficina truncada a 40 caracteres y columna más estrecha.
- Nueva columna "Origen" con badge de rayo para radicación rápida.
- Estilos para evitar saltos de línea en la columna Asunto.

### Decisión de alto nivel
Priorizar legibilidad sin perder información. **Por qué:** asuntos largos desordenan la tabla; truncar y mostrar el origen mejora la lectura y la identificación del tipo de radicado.

---

## 8. Corrección de saltos de línea en el campo Asunto

### Cambios realizados
- Nuevo filtro `oneline` en `auth_extras.py`: elimina `\n`, `\r` y colapsa espacios múltiples.
- Uso en `historial_correspondencia.html`: `{{ item.asunto|oneline|truncatechars:40 }}` con `white-space: nowrap`.
- Uso en `bandeja_correos_pendientes.html`: `{{ correo.asunto|oneline|truncatechars:80 }}`.

### Decisión de alto nivel
Limpiar los datos en origen en lugar de confiar solo en CSS. **Por qué:** `white-space: nowrap` no elimina saltos de línea embebidos; los correos traían `\n`/`\r` en el asunto. El filtro `oneline` corrige el problema en la fuente.

---

## 9. Modal de Radicación Rápida desde el detalle del correo

### Cambios realizados
- Botón "Radicación Rápida" en `detalle_correo_entrante.html`.
- Inclusión del modal con formulario pre-llenado (asunto, remitente, medio ELECTRÓNICO).
- En la vista: manejo del POST `rapida_entrante` con asociación `correo.radicado_asociado = correspondencia` y copia de adjuntos.
- Redirección al detalle del correo tras radicar.

### Decisión de alto nivel
Permitir radicación rápida desde la pantalla de detalle del correo. **Por qué:** el usuario revisa el correo ahí y quiere radicarlo sin ir al dashboard. El correo debe quedar marcado como radicado para no duplicar procesos.

---

## 10. Unificación visual de botones en la card de Acciones

### Cambios realizados
- Estilo unificado: botones rellenos (`btn-primary`, `btn-success`, `btn-danger`, etc.) en lugar de outline.
- Colores: Radicar Manualmente (primary), Radicación Rápida (degradado eléctrico), URGENCIA (danger), Papelera/Volver (secondary), Crear Contacto (success), Crear Entidad (info).
- Eliminación del texto "Para correos que no son correspondencia (notificaciones, spam, invitaciones, etc.)" debajo de Enviar a papelera.
- Clase `btn-rapida-electrico` con degradado amarillo–ámbar–naranja para el botón Radicación Rápida.

### Decisión de alto nivel
Usar botones rellenos para mejorar contraste y legibilidad. **Por qué:** los botones outline tenían fondo blanco y solo se rellenaban al hacer hover; el usuario solicitó fondos de color visibles siempre.

---

## 11. Icono de fuego (Radicar como URGENCIA)

### Cambios realizados
- Sustitución de `fas fa-fire` (Font Awesome) por `bi bi-fire` (Bootstrap Icons).

### Decisión de alto nivel
Unificar en Bootstrap Icons. **Por qué:** Font Awesome no se cargaba correctamente; Bootstrap Icons ya está integrado en el proyecto.

---

## 12. Nombre del enlace en el menú de navegación

### Cambios realizados
- En `base_correspondencia.html`: texto del enlace cambiado de "Radicación Rápida" a "Historial de Radicación Rápida".

### Decisión de alto nivel
Aclarar que el enlace lleva al listado/historial, no al formulario. **Por qué:** evitar confusión entre el formulario de radicación rápida (en dashboard/detalle) y la bandeja de radicados rápidos.

---

## Resumen de archivos modificados/creados

| Archivo | Tipo de cambio |
|---------|----------------|
| `correspondencia/models.py` | Campos opcionales, `origen_radicacion` |
| `correspondencia/forms.py` | `RadicacionRapidaEntranteForm`, `RadicacionRapidaSalienteForm` |
| `correspondencia/views.py` | `BandejaRadicacionRapidaView`, radicación rápida desde detalle |
| `correspondencia/urls.py` | Ruta `radicacion-rapida/` |
| `correspondencia/templatetags/auth_extras.py` | Filtro `oneline` |
| `correspondencia/templates/.../historial_correspondencia.html` | Truncado, columna Origen, `oneline` |
| `correspondencia/templates/.../bandeja_correos_pendientes.html` | `oneline` |
| `correspondencia/templates/.../bandeja_radicacion_rapida.html` | **Nuevo** bandeja con filtros |
| `correspondencia/templates/.../detalle_correo_entrante.html` | Botones, modal, estilos |
| `correspondencia/templates/.../modal_radicacion_rapida_entrante.html` | Modal ampliado, 4 columnas |
| `correspondencia/templates/bases/base_correspondencia.html` | Enlace "Historial de Radicación Rápida" |
| `correspondencia/migrations/0045_*.py`, `0046_*.py` | Migraciones de nuevos campos |

---

## [Fecha: 04/02/2025] - Sesión de Trabajo

### 1. Cambios Atómicos (Lo Táctico)

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `documentos/templates/welcome.html` | Modificado | Eliminado el div "Aviso: Transición Contractual" (módulos Préstamos Documentales y Comunicaciones Internas bajo transición contractual). La entidad formalizó soporte, el aviso ya no aplica. |
| `correspondencia/templates/correspondencia/partials/modals/modal_responder_correspondencia.html` | Modificado | (a) Buscador de destinatarios oculto con `d-none` por fallas intermitentes. (b) Botón "+" junto al Remitente Original para agregarlo como destinatario. (c) Script inline que define `window.agregarRemitenteOriginalDesdeBoton` como fallback si el JS externo no carga. |
| `correspondencia/static/correspondencia/js/modals/responder-correspondencia.js` | Modificado | Función global `agregarRemitenteOriginalDesdeBoton` y handler de click para el botón de remitente original. Agrega el contacto al Map de destinatarios y actualiza chips. |
| `deploy/systemd/correspondencia-celery-worker.service` | **Creado** | Servicio systemd para Celery worker. Ejecuta tareas en segundo plano (procesar correos, enviar respuestas). Depende de `redis-server.service`. |
| `deploy/systemd/correspondencia-celery-beat.service` | **Creado** | Servicio systemd para Celery beat. Programa tareas periódicas (correos cada 5 min, rebotes, urgencias, aprobaciones automáticas). Depende de `redis-server.service`. |
| `deploy/README.md` | Modificado | Estructura actualizada con los dos servicios Celery. Nueva sección "Celery y Redis" con: instalación de Redis vía apt, comandos para copiar/habilitar/iniciar servicios, verificación con `systemctl status`, logs vía `journalctl`, reinicio tras cambios. Inclusión de Celery en "Después de cambios en el código", "Detener servicios" y "Habilitar/Deshabilitar arranque automático". |

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Fallback inline para el botón "Agregar remitente original como destinatario"

**Fundamentación:** El botón llamaba a `window.agregarRemitenteOriginalDesdeBoton`, definida en `responder-correspondencia.js`. En algunas páginas (p. ej. urgencias u otras que incluyen el modal sin cargar ese script), la función no existía y el click fallaba con "is not a function". Se añadió un script inline en el propio modal que define la función solo si no existe, y que actualiza chips e inputs ocultos directamente. Así el botón funciona sin depender del orden o disponibilidad del script externo, garantizando operación en todos los contextos donde se usa el modal.

---

**Decisión:** Servicios systemd para Celery worker y beat (operación sin terminales)

**Fundamentación:** El usuario no usa Docker y necesita que Redis, Celery worker y Celery beat se ejecuten permanentemente y se reinicien tras un apagado. Los comandos `celery worker` y `celery beat` requieren terminales abiertas. Con servicios systemd, los procesos arrancan con el sistema (`enable`), se reinician si fallan (`Restart=always`) y los logs se consultan con `journalctl`. Se mantiene la misma estructura de usuario, rutas y virtualenv que `correspondencia.service` (Gunicorn) para consistencia del despliegue.

---

## [Fecha: 04/02/2026] - Sesión de Trabajo

### 1. Cambios Atómicos (Lo Táctico)

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `PLAN_RADICACION_SALIENTE_RAPIDA.md` | **Creado** | Documento de análisis y plan para el modal de radicación saliente rápida. Mapeo de campos solicitados vs. modelo `CorrespondenciaSalida`, plan por fases (modelo, formulario, modal, vista) y consideraciones de menor impacto. |
| `correspondencia/templates/correspondencia/admin/dashboard_ventanilla.html` | Modificado | Texto del botón cambiado de "Saliente Rápida" a "Radicación Saliente Rápida" en la categoría Radicación Rápida. El botón abre el modal `#modalRadicacionRapidaSaliente`. |

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Documentar plan antes de implementar radicación saliente rápida

**Fundamentación:** Se definió un plan explícito (`PLAN_RADICACION_SALIENTE_RAPIDA.md`) para extender el modal de radicación saliente con los campos: número radicación, fecha, destinatario, asunto, anexos, medio envío, dirección/correo, funcionario responsable, subproceso. El plan prioriza la menor perturbación: solo nuevos campos opcionales en el modelo, extensión del formulario existente y actualización del modal alineado con el entrante. Esto evita deuda técnica y reduce riesgos en flujos ya operativos.

---

## [Fecha: 07/02/2026] - Sesión de Trabajo

### 1. Cambios Atómicos (Lo Táctico)

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `correspondencia/templates/correspondencia/admin/editar_radicacion_rapida_saliente.html` | **Eliminado** | Página standalone de edición; se reutiliza el modal de creación. |
| `correspondencia/templates/correspondencia/admin/editar_radicacion_rapida_entrante.html` | **Eliminado** | Página standalone de edición; se reutiliza el modal de creación. |
| `correspondencia/views.py` | Modificado | `editar_radicacion_rapida_saliente` y `editar_radicacion_rapida_entrante` convertidas en endpoints AJAX (`@require_POST`), retornan `JsonResponse` (éxito o errores). Nuevos endpoints `api_radicacion_rapida_entrante_data` y `api_radicacion_rapida_saliente_data` (GET) que devuelven JSON para pre-poblar el modal. Formularios en edición usan prefix `rapida_ent` / `rapida_sal`. |
| `correspondencia/urls.py` | Modificado | Añadidas rutas `radicacion-rapida/<int:pk>/datos/` y `radicacion-rapida/salientes/<int:pk>/datos/` para las APIs de datos. |
| `correspondencia/views.py` (bandejas) | Modificado | `BandejaRadicacionRapidaView` y `BandejaRadicacionRapidaSalienteView` pasan en contexto `form_rapida_entrante` y `form_rapida_saliente` (vacíos, con prefix) para incluir los modales. |
| `correspondencia/templates/correspondencia/admin/bandeja_radicacion_rapida.html` | Modificado | Inclusión del modal entrante **dentro** de `{% block content %}` para que se renderice. Botón "Editar" cambiado a `<button class="btn-editar-entrante">` con `data-pk`, `data-url-datos`, `data-url-editar`. JS: al hacer clic se obtienen datos por AJAX, se rellenan los campos del modal, se cambia título/alerta/botón a modo edición y se envía el formulario por AJAX al endpoint de edición; al cerrar se restaura el modal a modo creación. |
| `correspondencia/templates/correspondencia/admin/bandeja_radicacion_rapida_saliente.html` | Modificado | Igual que la bandeja entrante: modal incluido dentro del block, botón "Editar" como `btn-editar-saliente`, JS para cargar datos, poblar formulario y enviar por AJAX. |
| `correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_entrante.html` | Modificado | Añadidos `id="alert-rapida-entrante"` e `id="btn-submit-rapida-entrante"` para que el JS pueda cambiar título/alerta/botón en modo edición. |
| `correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_saliente.html` | Modificado | Añadidos `id="alert-rapida-saliente"` e `id="btn-submit-rapida-saliente"` con el mismo fin. |
| `correspondencia/models.py` | Modificado | Nueva constante `ESTADO_RESPUESTA_RAPIDA_CHOICES`: `('', '---------'), ('PENDIENTE', 'Pendiente'), ('RESPONDIDA', 'Respondida'), ('VENCIDA', 'Vencida')`. Campo `estado_respuesta` pasa a `CharField(max_length=20, choices=ESTADO_RESPUESTA_RAPIDA_CHOICES, null=True, blank=True)` con `help_text` indicando que es solo para radicación rápida. |
| `correspondencia/forms.py` | Modificado | Import de `ESTADO_RESPUESTA_RAPIDA_CHOICES`. En `RadicacionRapidaEntranteForm`: `estado_respuesta` con widget `Select` y choices restringidos a los tres valores. En `clean()`: si `fecha_respuesta` y `fecha_limite_respuesta_manual` y `fecha_respuesta <= fecha_limite_respuesta_manual` → `estado_respuesta = 'RESPONDIDA'`; si hay fecha límite y no hay fecha respuesta y hoy > fecha límite → `'VENCIDA'`; si no hay fecha respuesta → `'PENDIENTE'` (o valor elegido). |
| `correspondencia/views.py` (bandeja + API) | Modificado | Import de `ESTADO_RESPUESTA_RAPIDA_CHOICES`. Filtro por `estado_respuesta` pasa de `icontains` a igualdad exacta. Contexto de bandeja incluye `estado_respuesta_choices` y en filtros activos se muestra la etiqueta del choice. API `api_radicacion_rapida_entrante_data` devuelve `estado_respuesta` solo si es uno de PENDIENTE/RESPONDIDA/VENCIDA. |
| `correspondencia/templates/correspondencia/admin/bandeja_radicacion_rapida.html` (filtro y tabla) | Modificado | Filtro "Estado Respuesta" de input texto a `<select>` con los tres estados. En la tabla, estado mostrado con badge (verde=Respondida, rojo=Vencida, gris=Pendiente) usando `get_estado_respuesta_display`. |
| `correspondencia/migrations/0049_estado_respuesta_rapida_choices.py` | **Creado** | Alteración de `estado_respuesta` en `Correspondencia` con choices; incluye alter de `comunicacion_origen` en `ComunicacionInterna` (pendiente previo). |

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Reutilizar el mismo modal de creación para editar radicación rápida (entrante y saliente)

**Fundamentación:** Inicialmente se habían creado páginas completas (`editar_radicacion_rapida_entrante.html`, `editar_radicacion_rapida_saliente.html`) para editar, duplicando UI y mantenimiento. El usuario indicó que debía ser el mismo modal con lógica reutilizable. Se eliminaron esas páginas, se convirtieron las vistas de edición en endpoints POST que devuelven JSON y se añadieron endpoints GET que devuelven los datos de la radicación para pre-poblar el formulario. En las bandejas se incluye el mismo modal de creación; al hacer clic en "Editar" el JS obtiene los datos, rellena el formulario, cambia título y botón a "Guardar Cambios" y envía por AJAX. Así se mantiene una única fuente de verdad para el formulario (el modal) y se evita duplicar pantallas.

---

**Decisión:** Incluir el partial del modal dentro de `{% block content %}` en las bandejas

**Fundamentación:** El botón "Editar" no abría el modal porque el `{% include %}` del modal estaba entre `{% endblock content %}` y `{% block extra_scripts %}`. En la herencia de templates de Django, el contenido fuera de cualquier bloque no se renderiza. Al mover el include dentro de `{% block content %}`, el HTML del modal pasa a formar parte de la página y el JS puede encontrar el elemento y mostrarlo.

---

**Decisión:** Estado de la respuesta con tres valores fijos y asignación automática según fechas (solo radicación rápida)

**Fundamentación:** El campo `estado_respuesta` debía tener exactamente tres estados (Pendiente, Respondida, Vencida) y, si la fecha de respuesta es menor o igual a la fecha límite de respuesta, marcarse como Respondida. Se introdujo `ESTADO_RESPUESTA_RAPIDA_CHOICES` en el modelo y se restringió el campo a esos valores para no mezclar con los estados del flujo de correspondencia entrante normal (Radicada, Asignada, Leída, etc.). La lógica en `RadicacionRapidaEntranteForm.clean()` asigna automáticamente RESPONDIDA cuando hay fecha de respuesta y es ≤ fecha límite; VENCIDA cuando hay fecha límite pasada y no hay fecha de respuesta; PENDIENTE en caso contrario cuando no hay respuesta. El filtro de la bandeja y la tabla usan los mismos choices para consistencia.


---

## [Fecha: 26/02/2026] - Sesión de Trabajo: Correos Faltantes, Watchdog y Optimización de Rendimiento

### 1. Cambios Atómicos (Lo Táctico)

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `correspondencia/management/commands/procesar_emails_seguro.py` | Modificado | Escaneo multi-carpeta: INBOX primero, luego `[Gmail]/Todos` con deduplicación por `message-id`. Modo normal usa filtro `UNSEEN` server-side y solo INBOX (1 día). Modo `--recovery` mantiene ambas carpetas y 7 días. Default de `--days` cambiado de 7 a 1. |
| `correspondencia/tasks.py` | Modificado | Añadidos `_acquire_email_lock(timeout)` y `_release_email_lock()` con Redis (fallback Django cache). `procesar_emails_periodico` usa lock con `finally`. Nueva tarea `watchdog_inbox`: escanea INBOX cada 1 min con `UNSEEN` filter, compara headers con BD, descarga y guarda faltantes (máx 20/ciclo). |
| `hospital_document_management/settings.py` | Modificado | `CELERY_EMAIL_CHECK_INTERVAL` de 300s a 120s (2 min). Watchdog añadido al beat schedule (60s). |
| `hospital_document_management/settings_test.py` | Sin cambios | Ya existía con SQLite para tests. |
| `correspondencia/tests/test_watchdog_inbox.py` | **Creado** | 18 tests unitarios: `EmailLockTests` (4), `ProcesarEmailsPeriodicoLockTests` (3), `WatchdogInboxTests` (8), `WatchdogCoordinationTests` (2). Cubre lock, watchdog, adjuntos, filtro fecha, anti-duplicación, coordinación entre tareas. |
| `pytest.ini` | Modificado | `DJANGO_SETTINGS_MODULE` cambiado a `settings_test` para usar SQLite en tests (evita permisos SQL Server). |
| `README.md` | Modificado | Sección Celery expandida: tabla de 6 tareas, documentación de lock, watchdog, escaneo multi-carpeta, sección de tests, servicios systemd. |

**Correos rescatados manualmente durante la sesión:**
- ID 1553: MC-008-2026
- ID 1554: CITOLOGIAS (solicitud bases de datos)
- ID 1556: DENGUE VACUNACIÓN
- ID 1568: COMUNICA ACTUACION PROCESAL RAD 2020-00162-01 (5 adjuntos)

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Escanear INBOX además de AllMail para capturar correos con retraso de sincronización Gmail

**Fundamentación:** Gmail no sincroniza inmediatamente los correos de INBOX a `[Gmail]/Todos` (AllMail). Durante horas pico se detectaron 4 correos que habían llegado a INBOX pero no aparecían en AllMail, causando que el sistema no los procesara. La solución dual (INBOX + AllMail con deduplicación por `message-id`) garantiza captura inmediata sin duplicados.

---

**Decisión:** Lock Redis compartido entre `procesar_emails_periodico` y `watchdog_inbox`

**Fundamentación:** Con dos tareas accediendo a IMAP y escribiendo en BD simultáneamente, existía riesgo de duplicados y conflictos de conexión IMAP. El lock Redis con clave `correspondencia:email_processing_lock` garantiza exclusión mutua. Se implementó con fallback a `django.core.cache` para entornos sin `django-redis`. El bloque `finally` asegura liberación incluso ante errores.

---

**Decisión:** Filtro `UNSEEN` server-side y reducción de alcance temporal a 1 día

**Fundamentación:** El escaneo anterior descargaba headers de 7 días en 2 carpetas (~cientos de headers) solo para comparar con BD. Con el filtro `UNSEEN` de IMAP, el servidor filtra antes de transmitir datos, reduciendo la carga de red y tiempo de ~5-15s a <1s cuando no hay correos nuevos. El alcance de 1 día es suficiente para ejecución periódica; el modo `--recovery` conserva 7 días y ambas carpetas para recuperación masiva.

---

**Decisión:** Intervalos reducidos (2 min principal, 1 min watchdog)

**Fundamentación:** Con las optimizaciones de rendimiento (UNSEEN filter, solo INBOX, 1 día), cada ejecución sin correos nuevos tarda <1 segundo. Esto permite intervalos más agresivos sin impacto en CPU/RAM. Un correo nuevo ahora llega al sistema en ~1 minuto (antes hasta 5 min).

---

**Decisión:** Tests con SQLite en memoria (`settings_test.py`) vía pytest

**Fundamentación:** El usuario SQL Server de producción no tiene permisos `CREATE DATABASE`, impidiendo crear BD de test. Se reutilizó `settings_test.py` (SQLite `:memory:`) y se apuntó `pytest.ini` a ese settings, permitiendo correr los 18 tests en ~3 segundos sin depender de infraestructura externa.

---

19 de febrero de 2026 - Integración Tailscale y URLs relativas para Next.js/Django
Cambios realizados
.env.local (Next.js)

Se cambiaron las variables NEXT_PUBLIC_API_URL y NEXT_PUBLIC_DJANGO_URL para usar rutas relativas (/registros/correspondencia y vacío respectivamente) en vez de IPs fijas. Así la app funciona desde LAN, Tailscale o localhost sin modificar la IP.
axios.ts (Next.js)

Se ajustó el baseURL de axios para que use la variable de entorno relativa.
Se cambió el redirect automático de error 401 para que apunte a /calendario/login (relativo), evitando hardcodear la IP.
page.tsx (Next.js)

Se cambió la URL de login para que use la variable relativa y funcione desde cualquier IP.
Se mejoró el mensaje de error para no mencionar un puerto específico.
nginx (sites-available/correspondencia)

Se añadió el bloque location /login para que las rutas de login de Next.js funcionen correctamente desde cualquier IP, incluyendo Tailscale.
settings.py (Django)

Se agregó la IP de Tailscale (100.104.246.117) a CORS_ALLOWED_ORIGINS y CSRF_TRUSTED_ORIGINS para permitir cookies y autenticación desde la red Tailscale.
base_correspondencia.html (Django)

Se cambió el link del sidebar de http://localhost:3000/calendario a /calendario (relativo), para que funcione desde cualquier IP o proxy.
Limpieza de puertos

Se mataron procesos de Django en los puertos 8000 y 8001, ya que nginx usa el socket de gunicorn y no es necesario tener runserver en esos puertos.
Reinicio de Next.js

Se intentó reiniciar Next.js en el puerto 3000 para que tome las nuevas variables y rutas relativas.
Justificación técnica
El uso de URLs relativas y la inclusión de la IP de Tailscale en CORS/CSRF permite que la aplicación funcione correctamente desde cualquier red (LAN, Tailscale, localhost) sin modificar código ni variables cada vez que cambia la IP de acceso.
El ajuste en nginx y el sidebar asegura que los usuarios puedan acceder al calendario Next.js desde cualquier entorno.
La limpieza de puertos evita conflictos y asegura que solo gunicorn maneje el backend Django.

---

## [Fecha: 26/02/2026] - Sesión de Trabajo: Aplicativo React — Calendario de Planillas (Next.js)

### Descripción del Aplicativo

El **Calendario de Planillas** es una aplicación web separada construida con **Next.js 14 (App Router)**, React 18, Tailwind CSS, shadcn/ui y SWR, desplegada bajo la ruta `/calendario` del mismo servidor. Su propósito es gestionar los **informes diarios de correspondencia hospitalaria**: visualizar en un calendario mensual cuáles días tienen correspondencias registradas, si el informe de ese día está firmado o pendiente, permitir subir archivos firmados, capturar firmas digitales via canvas, descargar Excel y consultar historial de descargas. Funciona como PWA con soporte offline (Service Worker + IndexedDB) para captura de firmas sin conexión y sincronización automática.

**Stack técnico:**
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui (Radix), SWR, Axios, Lucide Icons, date-fns, react-dropzone
- Autenticación: Cookie de sesión Django (`sessionid`) — el middleware Next.js verifica la cookie y redirige a `/calendario/login` si no existe; el login envía credenciales a la API Django
- Proxy: Nginx reversa `/calendario → localhost:3000` (Next.js), todo lo demás va a Gunicorn (Django)
- Servicio: `correspondencia-nextjs.service` (systemd) ejecuta `next start -p 3000`
- Offline: Service Worker (`sw.js`) con estrategias cache-first (assets) y network-first (API); IndexedDB para cola de firmas pendientes; Background Sync

**Estructura de archivos principal:**

| Directorio/Archivo | Función |
|---|---|
| `app/layout.tsx` | Layout raíz con Toaster y ServiceWorkerProvider |
| `app/global-error.tsx` | Error boundary global con botón "Limpiar caché y recargar" |
| `app/login/page.tsx` | Página de login contra API Django |
| `app/(protected)/layout.tsx` | Layout protegido: verifica sesión contra `/api/auth/me/`, navbar con estado online/offline, botón sync manual |
| `app/(protected)/page.tsx` | Página principal del calendario mensual |
| `app/(protected)/[fecha]/page.tsx` | Página de detalle del día (server component que extrae `fecha` de params) |
| `app/(protected)/[fecha]/DetalleDiaClient.tsx` | Client component: estadísticas, tabla de correspondencias, firmas, subida de archivo, historial |
| `components/calendario/CalendarioMensual.tsx` | Calendario mensual con navegación, grid 7 columnas, leyenda |
| `components/calendario/DiaCelda.tsx` | Celda individual del día: color según estado, badge de cantidad, indicador "Hoy" |
| `components/firma/ModalFirma.tsx` | Modal para captura de firma digital vía canvas |
| `components/firma/CanvasFirma.tsx` | Canvas de dibujo de firma con soporte táctil |
| `components/firma/ModalVerFirma.tsx` | Modal para visualizar firma existente |
| `components/informes/TablaCorrespondencias.tsx` | Tabla con todas las correspondencias del día, botones firmar/ver firma/detalle |
| `components/informes/CardEstadisticas.tsx` | Cards con stats: total, firmadas, pendientes, porcentaje |
| `components/informes/SubirArchivo.tsx` | Dropzone para subir archivo firmado (PDF/imagen) |
| `components/informes/SeccionHistorial.tsx` | Historial de descargas del informe |
| `components/ServiceWorkerProvider.tsx` | Registra SW, escucha evento online, sincroniza firmas pendientes |
| `lib/axios.ts` | Cliente Axios con baseURL relativa, interceptor CSRF, redirect 401 |
| `lib/api/calendario.ts` | Llamada API: `getCalendarioInformes(year, month)` |
| `lib/api/informes.ts` | Llamadas API: detalle día, descarga Excel, subida archivo |
| `lib/api/firmas.ts` | Llamada API: `guardarFirma()` |
| `lib/hooks/useCalendario.ts` | Hook SWR para datos del calendario mensual |
| `lib/hooks/useInformeDia.ts` | Hook SWR para detalle de un día |
| `lib/hooks/useFirmaCanvas.ts` | Hook para lógica del canvas de firma |
| `lib/offlineDb.ts` | Wrapper IndexedDB: cola de firmas pendientes offline |
| `lib/syncManager.ts` | Sincronización de firmas offline → servidor con Background Sync |
| `hooks/useOnlineStatus.ts` | Hook para detectar estado online/offline con polling de pendientes |
| `middleware.ts` | Middleware Next.js: verifica cookie `sessionid`, redirige a login |
| `public/sw.js` | Service Worker: cache-first assets, network-first API, sync firmas |
| `types/informes.ts` | Tipos TypeScript: CalendarioData, DiaCalendario, InformeDiario, Correspondencia, etc. |
| `next.config.mjs` | basePath `/calendario` en producción |

### 1. Cambios Atómicos (Lo Táctico)

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `components/calendario/CalendarioMensual.tsx` | Modificado | Se añadió `useMemo` para calcular `todayStr` (fecha de hoy en formato `YYYY-MM-DD`) en el **cliente**, independiente del API. En el map de días se sobreescriben `es_hoy` y `es_futuro` comparando `dia.fecha === todayStr` en vez de depender del valor cacheado del servidor. |
| `components/calendario/DiaCelda.tsx` | Modificado | Se corrigió el bug de timezone UTC: antes usaba `new Date(fecha).getDate()` para mostrar el número del día, pero `new Date('2026-02-26')` se parsea como UTC medianoche y al convertir a UTC-5 (Colombia) retrocedía un día (mostraba 25 en vez de 26). Ahora el número se extrae directamente del string con `fecha.split('-')[2]`. El `aria-label` también se corrigió usando `new Date(fecha + 'T12:00:00')`. |
| `app/(protected)/[fecha]/DetalleDiaClient.tsx` | Modificado | Misma corrección de timezone: `new Date(fecha)` → `new Date(fecha + 'T12:00:00')` para que `toLocaleDateString` muestre la fecha correcta en zona horaria Colombia. |
| `app/global-error.tsx` | **Creado** | Error boundary global que captura errores de cliente no manejados. Muestra botón "Reintentar" (llama `reset()`) y botón "Limpiar caché y recargar" (borra caches del SW, desregistra SW, recarga). Previene que el usuario vea el error genérico de Next.js "Application error: a client-side exception has occurred". |
| `public/sw.js` | Modificado | Versión de cache incrementada de `calendario-v1` a `calendario-v2` para invalidar caches del SW anterior tras el deploy. Al activarse, el SW nuevo limpia automáticamente los caches de la versión anterior. |
| Servicio `correspondencia-nextjs` | Reiniciado | El servidor Next.js estaba ejecutando un build anterior (`fnnU3HmC8GNgK2ilLbvM9`) mientras los archivos en disco ya tenían un build nuevo (`btK9eP2HrkDtcPhCU89j7`). Los chunks JS que el HTML viejo referenciaba ya no existían, causando el crash "Application error". Se reinició el servicio para alinear el servidor con el build actual. |

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Calcular `es_hoy` y `es_futuro` en el cliente, no depender del valor del API

**Fundamentación:** El Service Worker cachea las respuestas de la API con estrategia network-first, pero si el usuario abre la app offline o con cache stale, los campos `es_hoy`/`es_futuro` calculados por Django reflejan el momento del request original (ayer). Al calcularlo en el cliente con `new Date()`, el indicador "Hoy" siempre es correcto sin importar la edad del cache.

---

**Decisión:** Extraer el día del string ISO en vez de parsear con `new Date()`

**Fundamentación:** Este es un bug clásico de JavaScript: `new Date('YYYY-MM-DD')` (sin componente de hora) se parsea como **UTC medianoche** según el estándar ECMAScript. En zonas horarias negativas (como UTC-5 Colombia), esto resulta en el día anterior al convertir a hora local. La solución idiomática es: (a) para números, extraer del string directamente (`split('-')[2]`), y (b) para formateo con `toLocaleDateString`, agregar `T12:00:00` que se interpreta como hora local y nunca retrocede un día.

---

**Decisión:** Agregar `global-error.tsx` como error boundary

**Fundamentación:** Next.js 14 App Router no tiene un error boundary global por defecto. Cuando el build cambia o hay un error de hidratación, el usuario ve un mensaje críptico "Application error: a client-side exception has occurred" sin opción de recuperarse. El `global-error.tsx` captura estos errores y ofrece dos opciones: reintentar el render o limpiar todo el cache (SW + caches API) y recargar, lo cual resuelve la mayoría de problemas de despliegue sin intervención técnica.

---

**Decisión:** Siempre reiniciar `correspondencia-nextjs` después de `next build`

**Fundamentación:** Next.js en modo producción (`next start`) carga el `BUILD_ID` y los manifests en memoria al arrancar. Si se ejecuta `next build` sin reiniciar el servicio, el servidor sirve HTML con referencias al buildId nuevo, pero los manifests en memoria aún apuntan al viejo. Los chunks con hash distinto causan 404 y el cliente falla al hidratar. La regla operativa es: **todo `next build` debe ir seguido de `systemctl restart correspondencia-nextjs`**.

---

## [Fecha: 25/02/2026] - Sesión de Trabajo: Envío de email en radicación rápida entrante (física)

### 1. Cambios Atómicos (Lo Táctico)

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `correspondencia/views.py` (~línea 2493) | **Modificado** | Se agregó bloque completo de envío de correo electrónico al funcionario responsable dentro del flujo de radicación rápida entrante (`form_prefix == 'rapida_entrante'`). Anteriormente, tras guardar la correspondencia y los adjuntos, solo se mostraba un `messages.success` y se redirigía sin enviar notificación. Ahora, si `email_funcionario_responsable` tiene valor, se construye el contexto, se renderiza la plantilla `notificacion_asignacion_entrante.html`, se adjuntan los escaneos cargados (`adjuntos_rapidos`) y se envía el email. Se registra historial `NOTIFICACION` o `ERROR` según el resultado. |
| `correspondencia/views.py` (~línea 2508) | **Corregido** | Se eliminó referencia a `correspondencia.remitente_texto` (campo inexistente en el modelo) en el contexto del email. El formulario `RadicacionRapidaEntranteForm` mapea `remitente_texto` → `entidad_persona_remitente` en su método `save()`, por lo que el contexto ahora usa solo `correspondencia.entidad_persona_remitente or 'No especificado'`. |
| `correspondencia/tests.py` (final del archivo) | **Modificado** | Se agregó clase `RadicacionRapidaEntranteEmailTests` con 7 tests unitarios usando `django.core.mail.backends.locmem.EmailBackend` para verificar el envío de email sin conexión SMTP real. |
| `correspondencia/tests/__init__.py` | **Modificado** | Se registró `RadicacionRapidaEntranteEmailTests` en las exportaciones del paquete `tests` para que Django pueda descubrir la clase al ejecutar `python manage.py test correspondencia.tests.RadicacionRapidaEntranteEmailTests`. |

#### Tests agregados (7/7 pasando)

| Test | Qué verifica |
|------|-------------|
| `test_envia_email_cuando_tiene_email_funcionario` | Se envía 1 email al destinatario correcto, asunto contiene radicado, cuerpo HTML incluye nombre del funcionario, historial NOTIFICACION creado |
| `test_no_envia_email_sin_email_funcionario` | Sin `email_funcionario_responsable` → 0 emails enviados, sin historial NOTIFICACION |
| `test_email_falla_no_impide_radicacion` | Si `send()` lanza excepción, la correspondencia se crea igual, se registra historial ERROR |
| `test_email_usa_plantilla_correcta` | El cuerpo contiene "Hospital del Sarare", nombre del funcionario y asunto |
| `test_email_con_remitente_no_especificado` | Sin `entidad_persona_remitente` → el cuerpo contiene "No especificado" |
| `test_email_asunto_contiene_radicado` | El subject del email contiene "Correspondencia asignada" y el número de radicado |
| `test_email_no_tiene_cuerpo_correo_original` | No aparece "Contenido del correo original" (porque es correspondencia física, no email) |

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Enviar notificación por email también en radicación rápida entrante (correspondencia física)

**Fundamentación:** El envío de correo de notificación al funcionario responsable solo existía en el flujo de radicación desde correos electrónicos (`CorreoEntrante`, ~línea 7505 de `views.py`), donde hay un objeto `correo` con `message_id`, `cuerpo_html`, etc. En el flujo de radicación rápida entrante (~línea 2448), usado para correspondencia física, el código guardaba la correspondencia, procesaba adjuntos, mostraba un mensaje de éxito y redirigía **sin enviar ningún email**. Los usuarios reportaron que necesitaban la notificación también para correspondencia física, ya que los funcionarios responsables no se enteraban de la asignación hasta revisar el sistema manualmente.

---

**Decisión:** Reutilizar la misma plantilla `notificacion_asignacion_entrante.html` con `cuerpo_correo` vacío

**Fundamentación:** La plantilla ya tiene un `{% if cuerpo_correo %}` que oculta la sección "Contenido del correo original" cuando está vacía. Esto permite reutilizar la misma plantilla para ambos flujos (email y físico) sin crear una plantilla duplicada. El email de notificación para correspondencia física incluye toda la información relevante (radicado, remitente, oficina destino, tipo trámite, fecha límite) omitiendo solo el cuerpo del correo original que no existe en este caso.

---

**Decisión:** No revertir la radicación si falla el envío de email

**Fundamentación:** El envío de correo es una operación secundaria. Si el SMTP falla, la correspondencia ya fue guardada y registrada correctamente en base de datos. Se muestra un warning al usuario indicando que la radicación fue exitosa pero el email no se envió, y se registra un historial de tipo `ERROR` para trazabilidad. Esto sigue el mismo patrón que ya usa el flujo de radicación desde correo electrónico.

---

## 7. TICKET #1 — Términos legales: contar desde hora real de llegada del correo

**Fecha:** 27 de febrero de 2026  
**Responsable:** Diego (Implementación) / Cristian (Jurídica - feedback)  
**Estado:** ✅ COMPLETADO  

### 1. Cambios Atómicos

#### 1.1 Archivo: `correspondencia/models.py`

- **Nuevo método `_fecha_inicio_terminos()`** (línea ~673–705):
  - Determina la fecha de inicio para contar términos legales.
  - **Lógica:** Si la correspondencia está vinculada a un correo electrónico (`CorreoEntrante`), usa la fecha de recepción del correo (prioridad: `fecha_recepcion_original` → `fecha_recibida_gmail` → `fecha_lectura_imap`).
  - Si no hay correo origen, usa `fecha_radicacion` (comportamiento anterior).
  - Consulta explícita a BD con `.only()` para evitar problemas de caché cuando el objeto está recién guardado.

- **Método `_recalcular_sla_persistido()`** (línea ~710–774):
  - Modificado para usar `_fecha_inicio_terminos()` en vez de `self.fecha_radicacion`.
  - Calcula fecha límite de respuesta a partir de la **fecha real de llegada del correo**, no de la radicación manual.

- **Propiedad `fecha_limite_respuesta`** (línea ~507–559):
  - Modificada para usar `_fecha_inicio_terminos()` en el cálculo dinámico (fallback cuando `fecha_limite_respuesta_persist` no está disponible).

#### 1.2 Archivo: `correspondencia/utils_sla.py`

- **Función `aplicar_corte()`** (línea ~67–95):
  - **Bug corregido:** Ahora convierte a hora **local** (America/Bogota) antes de comparar con el cutoff (16:00).
  - Antes: comparaba `datetime.time()` (UTC) directamente, lo que hacía que el corte efectivo fuera a las 11 AM Bogota en lugar de 4 PM.
  - Ahora: `timezone.localtime(fecha_dt).time()` asegura que el cutoff sea en hora local.
  - Ajusta hábiles usando fecha local también.

- **Función `sumar_habiles()`** (línea ~100–118):
  - Modificada para usar fecha local al evaluar `_es_habil()`.
  - Evita errores cuando un datetime UTC cercano a medianoche se evalúa en fecha incorrecta.

#### 1.3 Archivo: `correspondencia/tests/test_ticket1_terminos_legales.py` (NUEVO)

- **15 tests** completamente nuevos (456 líneas):
  - 5 tests para `_fecha_inicio_terminos()`: prioridad de fechas, fallbacks, sin correo.
  - 7 tests para SLA persistido con correo origen: caso tutela 11pm, antes/después de cutoff, viernes noche, manual vs email, diferencias de vencimiento.
  - 2 tests para SLA con fallback (URGENTE, MUY_URGENTE) sin TRD.
  - 1 test para `requiere_respuesta=False` con correo.

### 2. Decisiones Arquitectónicas

**Decisión:** Usar fecha de recepción del correo (no de radicación) para términos legales

**Fundamentación:** Los plazos legales (tutelas, requerimientos) son **perentorios** y corren desde la notificación (recepción del correo), no desde el trámite administrativo interno. 
- **Caso reportado:** Tutela llega 25-feb 23:43, se radica 26-feb 7:40. Jurídica reportó que términos deben contar desde el 25.
- **Impacto regulatorio:** Incumplimiento de términos por demora operativa interna genera responsabilidad civil/disciplinaria.
- **Requisito:** Independientemente de cuándo se radique manualmente, el sistema debe honrar la fecha real de llegada para cálculos de SLA.

---

**Decisión:** Usar hora **local** (Bogota) en `aplicar_corte()` y `sumar_habiles()`

**Fundamentación:** Django almacena todos los datetimes en UTC. El cutoff de 16:00 debe ser 16:00 **Bogota** (UTC-5), no UTC.
- **Bug preexistente:** Sin conversión a local, un correo llegado a 14:00 Bogota (19:00 UTC) se evaluaba como llegado después del cutoff (16:00 UTC), desplazando el inicio de términos al día siguiente.
- **Solución:** Conversión explícita con `timezone.localtime()` antes de comparar `.time()`.
- **Cobertura:** Afecta tanto al código nuevo como a cálculos SLA existentes (beneficio transversal).

---

**Decisión:** Tests con comparación en hora local (`_local_date()`)

**Fundamentación:** Los tests crean datetimes naïve y Django los convierte a UTC al guardar. Las aserciones comparan `.date()` UTC vs esperadas (local).
- **Solución:** Helper `_local_date(dt)` que extrae la fecha en hora local antes de comparar.
- **Garantía:** Tests validan el comportamiento correcto **en la zona horaria del negocio**, no en UTC.

### 3. Resultados

| Métrica | Valor |
|---------|-------|
| **Tests nuevos** | 15/15 ✅ PASSED |
| **Errores de lint** | 0 |
| **Imports funcionales** | ✅ |
| **Archivos modificados** | 3 |
| **Líneas agregadas** | ~550 |
| **Compatibilidad hacia atrás** | ✅ (correspondencia sin correo origen usa `fecha_radicacion`) |

### 4. Verificación

- ✅ Todos los 15 tests del Ticket #1 pasan.
- ✅ Tests existentes no se rompieron (64 passed, errores preexistentes de setup no relacionados).
- ✅ Modelo Correspondencia importa sin errores.
- ✅ Métodos accesibles y funcionales.

### 5. Next Steps / Notas

- **Inmediato:** Desplegar cambios en producción (requiere reinicio de Gunicorn + Celery).
- **Documentación:** Actualizar manuales de jurídica sobre el comportamiento correcto de cálculo de términos.
- **Monitoreo:** Validar que nuevos radicados desde correo calcula correctamente el SLA.

---

## [Fecha: 27/02/2026] - Sesión de Trabajo — TICKET #2: Correos demoran +2 horas en reflejarse

### 1. Cambios Atómicos (Lo Táctico)

**Archivos modificados:**

| Archivo | Cambio |
|---------|--------|
| `correspondencia/tasks.py` | Función `watchdog_inbox()`: eliminado filtro `seen=False` del fetch IMAP. Ahora escanea **todos** los correos de hoy (leídos y no leídos) y compara contra BD para detectar faltantes. |
| `hospital_document_management/settings.py` | `CELERY_EMAIL_CHECK_INTERVAL`: reducido de `120` (2 min) a `60` (1 min). Watchdog: renombrado de `watchdog-inbox-cada-1-minuto` a `watchdog-inbox-cada-45-segundos`, intervalo de `60.0` a `45.0`. |
| `celerybeat-schedule` | Eliminado (archivo cacheado de Celery Beat) para forzar recarga de la nueva configuración. |

**Servicios reiniciados:**
- `correspondencia-celery-beat` — reiniciado para aplicar nuevos intervalos.
- `correspondencia-celery-worker` — reiniciado para cargar el nuevo código de `watchdog_inbox`.

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Eliminar dependencia del flag UNSEEN en el watchdog IMAP

**Fundamentación:**
- **Causa raíz identificada:** El sistema filtraba solo correos `UNSEEN` (no leídos) en Gmail. Si Dayana abría Gmail en el navegador web y los correos se marcaban automáticamente como leídos, el sistema **nunca los importaba** — ni la tarea `procesar_emails_periodico` ni el `watchdog_inbox` los veían.
- **Evidencia en logs:** En la mañana (06:00-12:00), las tareas tardaban ~31-41 segundos por ejecución (había correos acumulados de la noche). En la noche (19:00+), tardaban ~1.5 segundos (sin cola). Ambas tareas usaban lock compartido, causando contención adicional.
- **Solución aplicada:** El watchdog ahora usa `AND(date_gte=hoy)` sin `seen=False`, descarga solo headers (ultraligero) y compara `message_id` contra la BD. Solo descarga completos los correos que faltan (máximo 20 por ciclo).
- **Impacto:** Los correos ahora se detectan en <1 minuto sin importar si fueron leídos en Gmail.

**Decisión:** Reducir intervalos de polling

**Fundamentación:**
- El filtro IMAP server-side por fecha hace que cada ejecución sin correos nuevos tome <1 segundo, por lo que intervalos más cortos no generan carga significativa.
- `procesar_emails_periodico`: 120s → 60s (más oportunidades de captura).
- `watchdog_inbox`: 60s → 45s (red de seguridad más agresiva, ya que es la tarea que NO depende de UNSEEN).

### 3. Resultados

| Métrica | Valor |
|---------|-------|
| **Tests unitarios** | 21/21 ✅ PASSED (`test_watchdog_inbox.py` + `test_procesar_emails_celery.py`) |
| **Errores en producción** | 0 (17 tareas exitosas en 5 min post-deploy) |
| **Tiempo de sincronización** | De **+2 horas** a **<1 minuto** |
| **Archivos modificados** | 2 (`tasks.py`, `settings.py`) |
| **Servicios reiniciados** | 2 (`celery-beat`, `celery-worker`) |

### 4. Verificación

- ✅ Celery Beat despachando watchdog cada 45s y procesar_emails cada 60s (confirmado en journalctl).
- ✅ Worker ejecutando ambas tareas en ~1.5-2.1 segundos (sin errores).
- ✅ Lock Redis limpio (`nil`) — sin contención residual.
- ✅ 21 tests unitarios pasando con 100% cobertura en los módulos afectados.
- ✅ Correos leídos en Gmail ahora son capturados por el watchdog (compara contra BD, no depende de UNSEEN).

---

## [Fecha: 12/03/2026] - Sesión de Trabajo

### 1. Cambios Atómicos (Lo Táctico)

**Archivos modificados:**

| Archivo | Cambio |
|---------|--------|
| `correspondencia/templates/correspondencia/usuario/bandeja_oficina.html` | Rediseño completo de la bandeja de oficina con layout tipo card, cabecera con métricas, filtros colapsables, tabla más legible, badges visuales para acceso/lectura/plazo, paginación estilizada y modal AJAX para trazabilidad de lectura. |
| `correspondencia/templates/correspondencia/usuario/bandeja_interoficina.html` | Rediseño completo de la bandeja interoficina con la misma familia visual, énfasis en origen/visibilidad/estado, modal de historial de lectura agrupado por oficina y consistencia visual con las demás bandejas del usuario. |
| `correspondencia/templates/correspondencia/usuario/dashboard_usuario.html` | Retoque visual ligero del dashboard del usuario: shell más ancho, cards con mejor jerarquía visual, hero refinado, métricas y accesos rápidos con mejor contraste, bordes más suaves y espaciado más limpio, sin alterar la lógica funcional. |

**Archivos revisados como referencia técnica durante la sesión:**

| Archivo | Uso |
|---------|-----|
| `correspondencia/templates/correspondencia/usuario/bandeja_personal.html` | Tomado como referencia visual y estructural para alinear el lenguaje de diseño de las nuevas bandejas. |
| `correspondencia/views.py` | Revisado para confirmar contexto de datos, columnas, paginación y endpoints AJAX usados por cada plantilla. |

**Validaciones y cierre operativo:**

- Se ejecutó `python manage.py check` después de los cambios y no se reportaron errores del sistema.
- Todos los cambios del branch `desarrollo-3` fueron consolidados en el commit `70c88b0`.
- Posteriormente se integraron en `main` mediante merge fast-forward, dejando producción local alineada con el trabajo de la sesión.

### 2. Decisiones Arquitectónicas (Lo Estratégico)

**Decisión:** Reutilizar el lenguaje visual de `bandeja_personal` como patrón para las demás bandejas del usuario

**Fundamentación:** Ya existía una dirección visual aprobada y funcional. Reaprovecharla evitó divergencias de interfaz, redujo deuda de mantenimiento y mantuvo coherencia entre bandejas personales, de oficina e interoficina.

---

**Decisión:** Aplicar un retoque moderado al dashboard de usuario en lugar de un rediseño agresivo

**Fundamentación:** El requerimiento explícito fue “no algo hardcore”. Se mejoró legibilidad, jerarquía y presentación sin mover flujos, acciones ni estructura mental del usuario, minimizando riesgo de regresión UX.

---

**Decisión:** Mantener intacta la lógica de backend y concentrar el trabajo en capa de presentación

**Fundamentación:** El objetivo de la sesión fue visual. Se preservaron vistas, endpoints AJAX y reglas de negocio existentes para reducir riesgo funcional y acelerar despliegue.

### 3. Resultados

| Métrica | Valor |
|---------|-------|
| **Pantallas rediseñadas en esta sesión** | 3 |
| **Rediseños completos** | 2 (`bandeja_oficina`, `bandeja_interoficina`) |
| **Retoques visuales ligeros** | 1 (`dashboard_usuario`) |
| **Cambios de backend para este frente** | 0 |
| **Validación Django** | `python manage.py check` ✅ |
| **Integración a `main`** | ✅ Fast-forward |

### 4. Verificación

- ✅ Las bandejas de oficina e interoficina quedaron homologadas con el estilo moderno ya aplicado en la experiencia de usuario.
- ✅ El dashboard de usuario recibió una mejora visual controlada, sin cambio de comportamiento funcional.
- ✅ El trabajo quedó versionado e integrado en `main` durante esta misma sesión.

### 5. Nota de alcance

- Este bloque documenta específicamente la parte de rediseño web trabajada y cerrada durante la sesión del 12/03/2026 para la unidad de correspondencia.
- **Ticket #5 relacionado:** Bug de SPAM también afecta visibilidad de correos, recomendado revisar después de desplegar Ticket #1.