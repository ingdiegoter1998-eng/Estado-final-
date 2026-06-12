# Respuesta discrecional para correspondencia marcada como no requiere respuesta

Fecha de registro: 2026-03-28 19:20:10 -05

## Alcance

Este documento registra el cambio implementado para permitir respuestas discrecionales sobre correspondencia de entrada que fue clasificada como no requiere respuesta, sin alterar el significado original de esa clasificacion y sin abrir el flujo a todos los usuarios.

El alcance cubre:

- separacion entre la clasificacion requiere respuesta y la decision operativa de responder
- control de acceso por permiso Django asignable por usuario
- motivo obligatorio para toda respuesta discrecional
- trazabilidad en modelo, historial y mensajes de interfaz
- actualizacion del flujo modal AJAX y del formulario clasico
- migracion para persistencia de campos, permiso y grupo semilla
- pruebas focalizadas del nuevo comportamiento

## Problema de negocio

El sistema trataba la marca no requiere respuesta como una clasificacion documental y, al mismo tiempo, como un bloqueo absoluto para responder. Ese comportamiento era consistente tecnicamente, pero no representaba bien la necesidad operativa de algunas areas donde ciertos usuarios deben poder contestar por criterio profesional o funcional aunque la comunicacion no haya sido radicada como un requerimiento formal de respuesta.

El problema real no era de SLA ni de plazos. El problema era de autonomia operativa y trazabilidad.

## Decision funcional adoptada

Se decidio no convertir artificialmente una correspondencia de no requiere respuesta en una correspondencia que si requiere respuesta solo para permitir el envio de una salida.

En lugar de eso, se implemento una segunda via controlada:

- la correspondencia sigue conservando su clasificacion original
- un conjunto restringido de usuarios puede responder de forma discrecional
- toda respuesta discrecional exige motivo obligatorio
- el sistema deja evidencia explicita de que la respuesta fue discrecional y no obligatoria

## Criterios de diseno aplicados

### 1. No alterar la semantica de requiere_respuesta

El campo sigue representando la necesidad formal de respuesta dentro del flujo documental. No se reutilizo como bandera de conveniencia para habilitar acciones excepcionales.

### 2. Permiso por usuario, no por oficina

No se creo una configuracion nueva por oficina. La habilitacion se resolvio con permiso Django asignable a usuarios concretos, coherente con el modelo de acceso ya existente en el proyecto.

### 3. Trazabilidad obligatoria

Toda respuesta discrecional exige un motivo escrito. La intencion fue evitar un bypass silencioso del flujo y dejar respaldo funcional y de auditoria.

### 4. Compatibilidad con el flujo existente

Se mantuvo el comportamiento normal para correspondencia que si requiere respuesta. El cambio solo agrega una excepcion controlada para el caso de no requiere respuesta.

## Implementacion realizada

### 1. Permiso funcional nuevo

Se agrego un permiso Django en el modelo de correspondencia:

- `responder_correspondencia_discrecional`

Este permiso es la llave funcional para habilitar la nueva capacidad sin crear un rol nuevo ni alterar la estructura de perfiles.

Archivo relevante:

- `correspondencia/models.py`

### 2. Trazabilidad en respuestas salientes

Se ampliaron los datos de `CorrespondenciaSalida` para registrar expresamente el tipo de respuesta:

- `tipo_respuesta`
- `motivo_respuesta_discrecional`

Tambien se agrego un evento especifico en `HistorialSalida` para identificar respuestas discrecionales.

Resultado esperado:

- distinguir entre respuestas obligatorias y discrecionales
- conservar el motivo que justifico la excepcion
- permitir auditoria posterior sobre la decision tomada

### 3. Validacion de formulario

El formulario de respuesta fue extendido para soportar un modo discrecional.

Comportamiento agregado:

- si la respuesta es normal, el motivo no se exige
- si la respuesta es discrecional, el motivo se vuelve obligatorio
- la validacion se aplica tambien del lado servidor

Archivo relevante:

- `correspondencia/forms.py`

### 4. Reglas backend de autorizacion

Se ajusto la logica de vistas para separar dos preguntas distintas:

- si la correspondencia requiere respuesta
- si el usuario tiene permiso para responder discrecionalmente cuando no la requiere

Cambios relevantes:

- se agregaron helpers de permiso en `correspondencia/views.py`
- `crear_o_editar_respuesta` ya no bloquea ciegamente las correspondencias no requiere respuesta
- `responder_correspondencia_ajax` ahora valida el permiso discrecional y el motivo obligatorio
- se persiste `tipo_respuesta` y `motivo_respuesta_discrecional`
- el historial y los mensajes de exito reflejan cuando la respuesta fue discrecional

Esto corrige ademas un vacio importante: el endpoint AJAX no tenia el mismo endurecimiento de negocio que el flujo clasico.

### 5. Ajustes de interfaz

Se actualizaron las plantillas para que la interfaz comunique correctamente el nuevo estado funcional.

Cambios visibles:

- el detalle de correspondencia muestra el CTA aunque la comunicacion no requiera respuesta, pero solo cuando aplica el permiso discrecional
- el boton cambia su etiqueta a `Responder discrecionalmente`
- el modal muestra advertencia contextual
- el modal incorpora el campo de motivo obligatorio en modo discrecional
- el formulario clasico tambien soporta el nuevo campo
- el JavaScript del modal valida el motivo antes del envio

Archivos relevantes:

- `correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html`
- `correspondencia/templates/correspondencia/partials/modals/modal_responder_correspondencia.html`
- `correspondencia/templates/correspondencia/usuario/respuesta_form.html`
- `correspondencia/static/correspondencia/js/modals/responder-correspondencia.js`

### 6. Migracion y despliegue inicial

Se creo la migracion:

- `correspondencia/migrations/0071_respuesta_discrecional_permiso_y_trazabilidad.py`

La migracion hace lo siguiente:

- agrega los nuevos campos a `CorrespondenciaSalida`
- actualiza los permisos del modelo de correspondencia
- crea el grupo `Respuesta discrecional correspondencia`
- asigna inicialmente al grupo a usuarios actuales de Planeacion y Facturacion, contemplando variantes comunes del nombre de oficina

La idea operativa es dejar un punto de partida para el despliegue inicial y mantener luego la administracion de acceso por asignacion manual de usuarios o grupos.

## Archivos principales modificados

### Backend Django

- `correspondencia/models.py`
- `correspondencia/forms.py`
- `correspondencia/views.py`
- `correspondencia/migrations/0071_respuesta_discrecional_permiso_y_trazabilidad.py`
- `correspondencia/tests.py`

### Templates y frontend del flujo de respuesta

- `correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html`
- `correspondencia/templates/correspondencia/partials/modals/modal_responder_correspondencia.html`
- `correspondencia/templates/correspondencia/usuario/respuesta_form.html`
- `correspondencia/static/correspondencia/js/modals/responder-correspondencia.js`

## Comportamiento final esperado

### Caso 1. Correspondencia que si requiere respuesta

El flujo permanece igual al comportamiento previo. Los usuarios autorizados pueden responder normalmente y la respuesta se registra como obligatoria.

### Caso 2. Correspondencia que no requiere respuesta y usuario sin permiso discrecional

El sistema mantiene el bloqueo. No se habilita el CTA funcional y el backend rechaza el intento si se fuerza la llamada.

### Caso 3. Correspondencia que no requiere respuesta y usuario con permiso discrecional

El sistema habilita la accion de respuesta discrecional.

Condiciones:

- debe existir permiso para responder en ese contexto
- debe diligenciarse un motivo obligatorio
- la respuesta queda marcada como discrecional
- el historial deja evidencia especifica de ese tipo de respuesta

## Validacion realizada

Se ejecutaron validaciones estaticas sobre los archivos modificados y no quedaron errores reportados en editor para los cambios introducidos.

Tambien se agregaron pruebas focalizadas para estos escenarios:

- visualizacion del caso discrecional en detalle
- bloqueo AJAX sin permiso discrecional
- creacion correcta de respuesta discrecional con motivo

## Limitacion encontrada al cierre

No fue posible ejecutar la prueba Django desde la terminal activa porque el entorno no tenia Django disponible en el `python3` invocado en ese momento.

El ultimo intento observado fue:

- `python3 manage.py test correspondencia.tests.RespuestaDiscrecionalTests`

Resultado:

- fallo por ausencia del entorno Django activo, no por una evidencia confirmada de error de logica del cambio

Por tanto, la validacion funcional completa queda pendiente de correr en el entorno correcto del proyecto.

## Riesgos y consideraciones

### 1. Asignacion de acceso

La capacidad discrecional ya no depende de la oficina por si sola, sino de la asignacion concreta del permiso o del grupo al usuario. Operativamente esto da mas control, pero exige administracion consciente.

### 2. Semilla inicial vs operacion futura

La migracion siembra usuarios actuales de Planeacion y Facturacion como punto de partida. Cualquier cambio posterior de personal o ampliacion a otras areas debe administrarse desde permisos o grupos.

### 3. Lectura de reportes y auditoria

Como ahora existen respuestas obligatorias y discrecionales, cualquier futuro reporte o tablero que analice salidas deberia considerar esa diferencia si necesita precision funcional.

## Recomendaciones operativas siguientes

1. Activar el entorno Python correcto del proyecto.
2. Ejecutar `python manage.py migrate`.
3. Ejecutar `python manage.py test correspondencia.tests.RespuestaDiscrecionalTests`.
4. Hacer prueba manual con un usuario sin permiso y otro con permiso discrecional.
5. Verificar en administracion de usuarios o grupos quienes conservaran el acceso inicial en Planeacion y Facturacion.

## Resumen ejecutivo final

El cambio deja de tratar no requiere respuesta como una prohibicion absoluta y lo convierte en una clasificacion documental compatible con una excepcion controlada. La excepcion no es abierta: depende de permiso por usuario, exige motivo obligatorio y deja trazabilidad en datos, historial y UI.

Con esto el sistema conserva rigor documental y al mismo tiempo gana flexibilidad operativa para equipos que necesitan responder por criterio funcional sin distorsionar la clasificacion original de la comunicacion.