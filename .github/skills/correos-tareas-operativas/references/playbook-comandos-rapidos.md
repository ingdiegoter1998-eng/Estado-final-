# Playbook de Comandos Rapidos

Usar siempre el Python del entorno virtual del repo.

Base comun:

- `venv/bin/python manage.py check`

## 1. Incidente: correo no entro a la BD

Secuencia recomendada:

1. validar configuracion de seguridad y comando base
2. correr simulacion rapida
3. correr recovery acotado si ya se conoce la ventana del incidente

Comandos:

- `venv/bin/python manage.py procesar_emails_seguro --show-config`
- `venv/bin/python manage.py procesar_emails_seguro --dry-run --days 1`
- `venv/bin/python manage.py procesar_emails_seguro --recovery --days 1`
- `venv/bin/python manage.py procesar_emails_seguro --recovery --since 2026-03-12T16:44:00-05:00 --until 2026-03-12T18:00:00-05:00`

Objetivo:

- confirmar si el correo faltante aparece en el barrido
- evitar recovery masivo innecesario

## 2. Incidente: watchdog no rescata faltantes

Secuencia recomendada:

1. correr suite puntual del watchdog
2. revisar que el lock no impida la tarea
3. contrastar con un recovery acotado

Comandos:

- `venv/bin/python -m pytest correspondencia/tests/test_watchdog_inbox.py`
- `venv/bin/python manage.py procesar_emails_seguro --recovery --days 1`

Objetivo:

- separar si falla el watchdog o si el correo nunca fue visible para IMAP en ese rango

## 3. Incidente: Celery no esta ejecutando la recepcion

Secuencia recomendada:

1. validar integridad Django
2. correr pruebas de tarea periodica
3. usar el panel para diagnostico y sincronizacion inmediata

Comandos:

- `venv/bin/python manage.py check`
- `venv/bin/python -m pytest correspondencia/tests/test_procesar_emails_celery.py`

Apoyo desde la UI operativa:

- ejecutar `DIAGNOSE`
- ejecutar `SYNC_NOW`

Objetivo:

- aislar si falla Beat, worker, task name, guard clause o lock

## 4. Incidente: estado de sincronizacion queda en RUNNING o no refleja la realidad

Secuencia recomendada:

1. correr diagnostico operativo desde el panel
2. revisar si una corrida reciente quedo sin `finalizado_en`
3. validar ramas de error y timeout en tareas

Comandos de apoyo:

- `venv/bin/python manage.py check`
- `venv/bin/python -m pytest correspondencia/tests/test_procesar_emails_celery.py`

Apoyo desde la UI operativa:

- ejecutar `DIAGNOSE`
- revisar ejecuciones `RUNNING` en el historial del panel

Objetivo:

- confirmar si el problema es de estado persistido o de ejecucion real

## 5. Incidente: hay duplicados

Secuencia recomendada:

1. usar verificacion de duplicados del panel
2. validar pruebas de watchdog y task principal
3. revisar tratamiento de `message_id` y correos sin identificador

Comandos:

- `venv/bin/python -m pytest correspondencia/tests/test_watchdog_inbox.py`
- `venv/bin/python -m pytest correspondencia/tests/test_procesar_emails_celery.py`

Apoyo desde la UI operativa:

- ejecutar `DUPLICATES`

Objetivo:

- determinar si son duplicados reales por persistencia o sospechosos por mismos metadatos

## 6. Incidente: timeout o tarea pegada

Secuencia recomendada:

1. revisar task involucrada y su `soft_time_limit`
2. validar si el lock quedo activo
3. correr diagnostico operativo
4. reproducir con rango corto y no con recovery amplio

Comandos:

- `venv/bin/python manage.py procesar_emails_seguro --dry-run --days 1`
- `venv/bin/python -m pytest correspondencia/tests/test_procesar_emails_celery.py`
- `venv/bin/python -m pytest correspondencia/tests/test_watchdog_inbox.py`

Apoyo desde la UI operativa:

- ejecutar `DIAGNOSE`
- ejecutar `IMAP_TEST`

Objetivo:

- no tapar el timeout bajando controles; ubicar si el cuello esta en IMAP, lote, lock o serializacion

## 7. Orden de uso recomendado en incidentes mixtos

Si el caso mezcla varios sintomas, usar este orden:

1. `check`
2. `DIAGNOSE`
3. `IMAP_TEST`
4. `VERIFY`
5. `SYNC_NOW`
6. `RECOVER` acotado por rango
7. pruebas puntuales

## 8. Lo que no se debe hacer primero

- recovery de 30 o 60 dias sin evidencia
- borrar registros para reprocesar a ciegas
- tocar intervalos de Celery sin aislar la causa
- quitar el lock solo para que “parezca” que corre
- corregir solo el template del panel