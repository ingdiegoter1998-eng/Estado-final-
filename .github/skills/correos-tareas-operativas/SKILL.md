---
name: correos-tareas-operativas
description: 'Diagnostica y corrige fallas de recepcion de correos, sincronizacion IMAP, watchdog, Celery Beat, tareas periodicas, locks, panel de control de correos y ejecucion de tareas en este proyecto. Usar cuando un correo no entra, el dashboard no refleja sincronizacion, Celery no corre, watchdog no rescata faltantes, hay duplicados, timeouts, locks pegados o tareas que no ejecutan.'
argument-hint: 'Describe el sintoma: correo no llega, watchdog no corre, Celery no ejecuta, tarea pegada, duplicados, timeout, lock, panel inconsistente'
user-invocable: true
disable-model-invocation: false
---

# Correos y Tareas Operativas

## Que Resuelve

Esta skill existe para trabajar incidentes operativos de este proyecto relacionados con:

- recepcion fallida de correos entrantes
- sincronizacion IMAP inconsistente
- watchdog que no rescata faltantes
- Celery Beat o workers que no ejecutan tareas
- locks de procesamiento pegados
- panel de control de sincronizacion con estado incorrecto
- duplicados o faltantes entre Gmail y base de datos
- timeouts, fallos de recovery y tareas periodicas que dejan de correr

No es una skill generica de correo. Esta pensada para la implementacion real de este repo.

## Cuando Usarla

Activa esta skill cuando el usuario pida cosas como:

- revisar por que no estan entrando correos
- depurar la recepcion IMAP
- validar por que Celery no esta ejecutando tareas
- arreglar watchdog o recovery
- revisar por que no se actualiza el estado de sincronizacion
- verificar faltantes o duplicados entre Gmail y BD
- investigar una tarea pegada o un timeout
- crear o corregir herramientas de control operativo para correos

Palabras gatillo utiles para discovery:

- correo no llega
- recepcion de correos
- sincronizacion
- IMAP
- watchdog
- Celery
- Beat
- tarea periodica
- lock
- timeout
- duplicados
- recovery
- faltantes

## Contexto Real del Proyecto

Antes de proponer cambios, asume esta arquitectura actual:

- la tarea principal de recepcion es `correspondencia.tasks.procesar_emails_periodico`
- la recepcion segura corre el comando `procesar_emails_seguro`
- existe un lock `_EMAIL_LOCK_KEY` para `procesar_emails_periodico`
- existe un lock separado `_WATCHDOG_LOCK_KEY` para `watchdog_inbox` (no colisionan entre si)
- existe una tarea `correspondencia.tasks.watchdog_inbox` para rescatar correos faltantes en INBOX (cubre ayer + hoy)
- existe un panel operativo de control de sincronizacion
- el estado resumido se guarda en `EstadoSincronizacionCorreos`
- la bitacora de operaciones manuales se guarda en `EjecucionControlCorreos`

Archivos clave de referencia:

- `correspondencia/tasks.py`
- `correspondencia/management/commands/procesar_emails_seguro.py`
- `correspondencia/email_sync_control.py`
- `correspondencia/views_sync_control.py`
- `correspondencia/models.py`
- `hospital_document_management/settings.py`
- `correspondencia/tests/test_procesar_emails_celery.py`
- `correspondencia/tests/test_watchdog_inbox.py`

Ruta operativa ya existente:

- `/registros/correspondencia/ventanilla/control-sincronizacion/`

Referencia adicional para ejecucion rapida por tipo de incidente:

- [Playbook de comandos rapidos](./references/playbook-comandos-rapidos.md)

## Regla Base de Trabajo

Siempre trabajar en este orden:

1. Confirmar el sintoma exacto.
2. Diferenciar si es problema de recepcion, ejecucion, estado, duplicados o UI de control.
3. Recolectar evidencia real del sistema antes de editar.
4. Intentar solucion no destructiva primero.
5. Corregir la causa raiz, no solo el sintoma visual.
6. Validar con prueba puntual o reproduccion controlada.

## Clasificacion Rapida del Incidente

### 1. Correo no entra a la BD

Sospechas principales:

- `procesar_emails_periodico` no corrio
- Celery Beat no despacho la tarea
- worker no estaba vivo
- lock quedo pegado (raro: ambas tareas tienen `finally` que libera lock)
- `procesar_emails_seguro` filtro o descarto el correo
- el correo esta en Gmail pero fuera del rango de busqueda (normal = 2 dias, watchdog = ayer+hoy)
- un lote IMAP fallo y el retry+reconexion no pudo recuperar (el lote se salta pero los demas continuan)
- el watchdog no rescato el faltante

IMPORTANTE: el sistema ya NO depende de UNSEEN. Escanea TODOS los headers y deduplica por `message_id`. Que alguien lea el correo en Gmail web NO impide la captura.

### 2. El panel muestra estado raro pero los correos si entran

Sospechas principales:

- `EstadoSincronizacionCorreos` no se actualiza en una rama de error
- una tarea quedo marcada como `RUNNING`
- hubo timeout o excepcion sin cierre limpio
- la vista del panel o la ejecucion de control no esta serializando bien la salida

### 3. Celery o tareas periodicas no ejecutan

Sospechas principales:

- Beat no esta levantado
- worker no esta consumiendo cola
- schedule mal configurado en settings
- el task name cambio y Beat sigue apuntando al anterior
- el proceso corre pero la tarea se omite por lock o guard clause

### 4. Hay duplicados o correos faltantes

Sospechas principales:

- deduplicacion por `message_id` inconsistente
- recovery revisa un rango equivocado
- watchdog rescata solo lotes parciales
- el correo cambia headers o llega sin `message-id`
- correos DSN/rebote de cendoj que no son correos entrantes reales (los maneja `procesar_rebotes`)
- workers Celery duplicados acumulados de dias anteriores (verificar con `ps aux | grep celery`)

## Procedimiento Recomendado

### Paso 1. Confirmar el frente afectado

Separar el caso en uno de estos grupos:

- recepcion IMAP
- ejecucion Celery
- estado del panel
- duplicados o faltantes
- problema mixto

No mezclar todos los frentes desde el inicio.

### Paso 2. Recolectar evidencia minima obligatoria

Verificar:

- si el correo existe en Gmail
- si existe en `CorreoEntrante`
- si `EstadoSincronizacionCorreos` tiene `RUNNING`, `SUCCESS` o `FAIL`
- si hay registros recientes en `EjecucionControlCorreos`
- si la tarea de Celery se despacho realmente
- si el lock `_EMAIL_LOCK_KEY` sigue activo

Usar primero mecanismos ya existentes del proyecto antes de inventar scripts nuevos.

## Orden Correcto de Diagnostico

### A. Revisar primero el panel operativo si aplica

Si el incidente es de sincronizacion o faltantes, partir por:

- `/registros/correspondencia/ventanilla/control-sincronizacion/`

Operaciones disponibles y su uso:

- `VERIFY`: comparar cobertura Gmail vs BD
- `RECOVER`: recuperar faltantes
- `DUPLICATES`: detectar duplicados reales y sospechosos
- `DIAGNOSE`: revisar estado operativo de Celery, lock y sincronizacion
- `IMAP_TEST`: probar conectividad IMAP
- `SYNC_NOW`: encolar sincronizacion inmediata

Regla:

- si existe una herramienta interna que ya responde la pregunta, usarla primero
- solo modificar codigo si la herramienta muestra una falla real o una carencia funcional

### B. Revisar despues las tareas y el schedule

Puntos concretos a revisar:

- `correspondencia.tasks.procesar_emails_periodico`
- `correspondencia.tasks.watchdog_inbox`
- `correspondencia.tasks.ejecutar_operacion_control_correos`
- `CELERY_EMAIL_CHECK_INTERVAL`
- `CELERY_IMAP_WATCHDOG_INTERVAL`
- `CELERY_BEAT_SCHEDULE`

Buscar especialmente:

- nombres de task incorrectos
- timeout demasiado corto
- lock no liberado en `finally` (verificar: `_EMAIL_LOCK_KEY` y `_WATCHDOG_LOCK_KEY` son independientes)
- ruta de error que no actualiza estado
- fetch IMAP demasiado restrictivo
- workers zombi acumulados de dias anteriores consumiendo RAM (ver seccion Workers Duplicados)

### C. Revisar luego el comando seguro de procesamiento

`procesar_emails_seguro` es la fuente principal de verdad para recovery y recepcion controlada.

Validar:

- rango de fechas (`--days`, `--since`, `--until`)
- modo `--recovery`
- deduplicacion por `message_id`
- reglas de adjuntos y filtros de seguridad
- comportamiento cuando el correo ya existe

## Acciones Seguras Preferidas

Antes de tocar logica sensible, priorizar:

1. correr diagnostico operativo
2. probar IMAP
3. verificar cobertura Gmail vs BD
4. encolar sincronizacion inmediata
5. usar recovery en el rango exacto del incidente

Si el usuario pide ir directo a comandos por tipo de falla, cargar y seguir el
[Playbook de comandos rapidos](./references/playbook-comandos-rapidos.md).

Evitar como primera respuesta:

- limpiar datos manualmente en masa
- borrar registros para forzar reprocesamiento sin entender causa
- tocar schedule sin confirmar que el problema esta ahi
- duplicar logica ya existente en tareas, comandos y panel

## Reglas de Implementacion

Si hace falta corregir codigo:

### 1. Centralizar la logica operativa

Si la misma verificacion o recovery aparece repetida en varias vistas o tareas:

- extraer helper comun
- no copiar y pegar logica de IMAP, serializacion o metricas

### 2. Mantener trazabilidad operativa

Si una operacion manual o automatica falla, debe dejar:

- estado claro
- error claro
- timestamps de inicio y fin si aplica
- salida o resumen util para diagnostico posterior

### 3. No romper el panel de control

Si agregas una nueva operacion operativa:

- definir tipo en `EjecucionControlCorreos`
- implementar su ejecucion en `execute_control_operation`
- conectarla a la tarea `ejecutar_operacion_control_correos`
- exponerla en la vista o template de control si el usuario lo necesita

### 4. No exponer soluciones destructivas por defecto

Si una posible solucion implica borrar o reprocesar datos:

- primero presentar una ruta segura
- luego una ruta correctiva controlada
- solo despues una ruta destructiva, y con evidencia fuerte

## Checklist de Validacion

Despues de cualquier cambio, validar segun el frente afectado.

### Si fue recepcion de correos

- el correo de prueba aparece en BD
- no se duplica
- el estado de sincronizacion cierra correctamente
- el panel muestra resultado coherente

### Si fue Celery o Beat

- la tarea puede encolarse
- el worker la ejecuta
- no queda lock colgado
- el estado final queda en `SUCCESS`, `WARN` o `FAIL` con mensaje claro

### Si fue watchdog o recovery

- rescata faltantes reales
- no trae ya procesados
- respeta el rango exacto del incidente
- deja metricas coherentes

### Si fue duplicados

- la deduplicacion por `message_id` sigue vigente
- no se rompe la recepcion de correos sin `message-id`
- existe prueba puntual para el caso cubierto

## Pruebas que Deben Revisarse

Cuando toques este frente, revisar o ampliar al menos una de estas suites:

- `correspondencia/tests/test_procesar_emails_celery.py`
- `correspondencia/tests/test_watchdog_inbox.py`

Si el cambio agrega una nueva operacion del panel o una rama de recovery, crear prueba especifica.

## Comandos Utiles del Proyecto

Usar Python del entorno virtual del repo.

Para ejecucion orientada por incidente, ver tambien el
[Playbook de comandos rapidos](./references/playbook-comandos-rapidos.md).

Comandos frecuentes:

- `venv/bin/python manage.py check`
- `venv/bin/python manage.py procesar_emails_seguro --show-config`
- `venv/bin/python manage.py procesar_emails_seguro --dry-run --days 1`
- `venv/bin/python manage.py procesar_emails_seguro --recovery --since 2026-03-12T16:44:00-05:00 --until 2026-03-12T18:00:00-05:00`
- `venv/bin/python -m pytest correspondencia/tests/test_procesar_emails_celery.py`
- `venv/bin/python -m pytest correspondencia/tests/test_watchdog_inbox.py`

## Lecciones Aprendidas (Abril 2026)

### Error IMAP en lote ya no aborta todo

Antes un error IMAP en un lote de 15 correos abortaba todo el procesamiento restante
(patron `break` + `else: continue` / `break`). Ahora el sistema reintenta 1 vez
con reconexion IMAP y si falla salta ese lote y continua con el siguiente.

### Locks separados

`procesar_emails_periodico` y `watchdog_inbox` ya no compiten por el mismo lock.
Cada uno tiene su propia key Redis. Esto elimina la colision que causaba que el
watchdog retornara sin hacer nada cuando la tarea principal tenia el lock.

### Ventana de busqueda ampliada

- Modo normal: 2 dias (antes 1 dia). Captura correos de ayer que no se procesaron.
- Watchdog: ayer + hoy (antes solo hoy). Rescata correos nocturnos perdidos.
- Recovery: 7 dias por defecto, configurable con `--days`.

### Workers duplicados: problema recurrente

Si no se mata Celery antes de iniciar uno nuevo, se acumulan workers zombi que
consumen RAM sin utilidad. Verificar periodicamente:

```bash
ps aux | grep celery | grep -v grep | awk '{print $2, $9, $11}'
```

Para reiniciar limpio:

```bash
pkill -f "celery -A hospital_document_management"
sleep 2
rm -f celerybeat-schedule celerybeat-schedule.dir celerybeat-schedule.bak celerybeat-schedule.dat
celery -A hospital_document_management worker --concurrency=2 -l info &
celery -A hospital_document_management beat -l info &
```

### Faltantes que NO son fallas del sistema

Algunos correos en Gmail AllMail que no estan en BD son normales:

- DSN/bounces de cendoj que maneja `procesar_rebotes` (no van a CorreoEntrante)
- correos enviados por la propia cuenta (filtrados en AllMail scan)
- notificaciones internas de Gmail

## Señales de Mala Solucion

Desconfia de una solucion si hace cualquiera de estas cosas:

- arregla solo el template o el panel pero no la tarea real
- mete otro command o script cuando ya existe una ruta operativa suficiente
- cambia tiempos de Celery sin explicar por que
- desactiva el lock en lugar de corregir su manejo
- elimina deduplicacion para esconder un faltante
- hace recovery masivo sin acotar rango ni riesgo

## Resultado Esperado de Esta Skill

Cuando esta skill se use bien, el agente debe:

1. aislar el frente real del incidente
2. usar primero el panel y helpers operativos existentes
3. ubicar si el fallo esta en IMAP, Celery, lock, recovery, deduplicacion o estado
4. corregir la causa raiz con el menor cambio seguro posible
5. dejar validacion puntual y, cuando aplique, prueba automatizada

## Nota Final

Esta skill es para incidentes operativos reales de correo y tareas periodicas en este proyecto.

No usarla para problemas generales de frontend, formularios o modales salvo que el incidente este conectado con sincronizacion de correos, ejecucion de tareas o control operativo.