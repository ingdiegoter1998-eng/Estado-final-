---
name: rebotes-dsn-depuracion
description: "Investiga, depura y corrige problemas de rebotes (DSN/bounce) en correspondencia saliente. Usar cuando un radicado saliente aparece como REBOTE sin justificacion, cuando hay falsos positivos de rebote, cuando se necesita verificar DSN reales en Gmail via IMAP, cuando se debe corregir registros marcados incorrectamente, o cuando se necesita auditar o mejorar el procesador de rebotes. Palabras clave: rebote, bounce, DSN, falso positivo, REBOTE incorrecto, SalidaDestinatario, procesar_rebotes, smtp_code, dsn_status, ENVIADO, Undeliverable, postmaster, mailer-daemon."
argument-hint: "Describe el caso: radicado con rebote sospechoso, falso positivo, depuracion masiva, mejora del procesador, verificacion de DSN en Gmail"
user-invocable: true
disable-model-invocation: false
---

# Rebotes DSN - Depuracion y Correccion

## Que Resuelve

Esta skill sirve para investigar, diagnosticar y corregir todo lo relacionado con rebotes (DSN / bounce) de correspondencia saliente en este proyecto:

- radicados salientes marcados como REBOTE que en realidad se entregaron bien
- falsos positivos causados por el fallback del procesador de rebotes
- verificacion cruzada de DSN reales en Gmail (via IMAP) vs lo que marca la BD
- correccion individual o masiva de registros SalidaDestinatario
- auditoria del procesador `procesar_rebotes.py`
- mejoras al matching de DSN para evitar falsos positivos futuros

No cubre recepcion de correos entrantes ni tareas de Celery (eso es skill `correos-tareas-operativas`).

## Cuando Usarla

Activa esta skill cuando el usuario pida cosas como:

- por que tal radicado saliente marca rebote si no hay bounce en Gmail
- revisar si un rebote es real o falso positivo
- depurar todos los rebotes de un destinatario o dominio especifico
- corregir un radicado que fue marcado como REBOTE incorrectamente
- auditar cuantos rebotes son reales vs falsos positivos
- mejorar la logica de matching del procesador de rebotes
- investigar DSN de un dominio especifico (ej: cendoj, gmail, etc)
- listar todos los envios a una direccion y su estado

Palabras gatillo:

- rebote
- bounce
- DSN
- falso positivo
- REBOTE incorrecto
- Undeliverable
- postmaster
- mailer-daemon
- smtp_code
- dsn_status
- corregir rebote
- revertir rebote

## Arquitectura del Sistema de Rebotes

### Flujo de envio

1. `correspondencia/aprobacion_envio.py` envia el email via SMTP (Gmail)
2. Genera un `Message-ID` con `make_msgid(domain=EMAIL_MESSAGE_ID_DOMAIN)`
3. Guarda el `id_mensaje_enviado` en `CorrespondenciaSalida` y `SalidaDestinatario`
4. El estado inicial del destinatario queda `ENVIADO`

### Flujo de deteccion de rebotes

1. La tarea `procesar_rebotes_periodico` corre cada 10 minutos via Celery Beat
2. Ejecuta el comando `procesar_rebotes`
3. Se conecta via IMAP a Gmail
4. Busca DSN en INBOX (no-vistos primero, luego vistos recientes con ventana de 3 dias)
5. Para cada DSN encontrado:
   - extrae `Message-ID` original, destinatario, status y diagnostico via `_parse_dsn()`
   - intenta match PRIMARIO: `id_mensaje_enviado` + `email_snapshot`
   - si no encuentra: FALLBACK por `email_snapshot` solo (acotado a 7 dias y estado ENVIADO)
   - si no encuentra: FALLBACK por `id_mensaje_enviado` solo
6. Marca los registros encontrados como `REBOTE` con smtp_code, dsn_status y detalle_error
7. Crea entrada en `HistorialSalida` tipo `ENVIO_FALLIDO`
8. Crea `Notificacion` tipo `rebote` para el redactor

### Archivos clave

- `correspondencia/management/commands/procesar_rebotes.py` — procesador principal
- `correspondencia/aprobacion_envio.py` — pipeline de envio SMTP
- `correspondencia/tasks.py` — tarea periodica `procesar_rebotes_periodico`
- `correspondencia/models.py` — `SalidaDestinatario`, `HistorialSalida`, `Notificacion`
- `hospital_document_management/settings.py` — schedule de Celery Beat, config IMAP/SMTP

### Modelos relevantes

**SalidaDestinatario** — un registro por cada destinatario de cada envio:
- `email_snapshot`: email del destinatario
- `id_mensaje_enviado`: Message-ID del email enviado
- `estado`: `PENDIENTE`, `ENVIADO`, `REBOTE`, `FALLO`
- `smtp_code`: codigo SMTP del rebote (ej: 550)
- `dsn_status`: codigo DSN (ej: 5.7.1)
- `detalle_error`: texto del diagnostico DSN
- `ultimo_evento_at`: timestamp del ultimo cambio de estado
- `fecha_envio`: cuando se envio el email

**HistorialSalida** — auditoria de eventos por correspondencia saliente:
- `tipo_evento`: `ENVIO_EXITOSO`, `ENVIO_FALLIDO`, `CORRECCION`, etc
- `descripcion`: texto descriptivo del evento

## Bug Conocido: Falso Positivo por Fallback

### Descripcion

Cuando un DSN llega a Gmail pero su `Message-ID` original no coincide con ningun envio del sistema (porque fue un reenvio manual, un forward, o un correo enviado por otro medio), el procesador cae al fallback que busca por `email_snapshot` solamente.

Esto provoca que TODOS los envios historicos a esa misma direccion que esten en estado ENVIADO se marquen como REBOTE, aunque no hayan rebotado.

### Mitigacion actual

El fallback por email_snapshot esta acotado a:
- solo registros en estado `ENVIADO`
- solo con `fecha_envio` dentro de los ultimos 7 dias

Esto reduce drasticamente los falsos positivos pero no los elimina al 100% si hay envios recientes al mismo destinatario.

### Caso real documentado

Los 12 rebotes de `@cendoj.ramajudicial.gov.co` de marzo-abril 2026 fueron causados por vacancia judicial de Semana Santa. Envios de dias antes de la vacancia fueron marcados como REBOTE por el fallback cuando llego un DSN de un forward posterior.

## Procedimiento de Investigacion

Cuando el usuario reporte un rebote sospechoso, seguir estos pasos EN ORDEN:

### Paso 1. Consultar estado en BD

```python
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','hospital_document_management.settings')
django.setup()
from correspondencia.models import CorrespondenciaSalida, SalidaDestinatario, HistorialSalida

rad = 'SALIENTE-2026-XXXXX'
s = CorrespondenciaSalida.objects.get(numero_radicado_salida=rad)
print(f'Asunto: {s.asunto}')
print(f'Estado: {s.estado}')
print(f'Fecha envio: {s.fecha_envio}')
print(f'Message-ID: {s.id_mensaje_enviado}')

for d in s.destinatarios.all():
    print(f'  {d.email_snapshot} | estado={d.estado} | smtp={d.smtp_code} | dsn={d.dsn_status}')
    print(f'  detalle: {d.detalle_error}')
    print(f'  ultimo_evento: {d.ultimo_evento_at}')

for h in HistorialSalida.objects.filter(correspondencia_salida=s).order_by('fecha_hora'):
    print(f'  {h.fecha_hora} | {h.tipo_evento} | {h.descripcion}')
```

Datos a extraer:
- fecha de envio SMTP exitoso
- fecha en que se marco REBOTE (ultimo_evento_at)
- Message-ID del envio
- email del destinatario

### Paso 2. Listar todos los envios al mismo destinatario

```python
email = 'destinatario@dominio.com'
for d in SalidaDestinatario.objects.filter(email_snapshot=email).select_related('correspondencia_salida').order_by('fecha_envio'):
    s = d.correspondencia_salida
    print(f'{s.numero_radicado_salida} | envio={d.fecha_envio} | estado={d.estado} | msgid={d.id_mensaje_enviado} | marcado={d.ultimo_evento_at}')
```

Buscar patron: varios registros marcados REBOTE en la misma fecha/hora = probable falso positivo por fallback.

### Paso 3. Buscar DSN real en Gmail via IMAP

```python
import imaplib, email

imap = imaplib.IMAP4_SSL('imap.gmail.com', 993)
imap.login('Correspondenciaesesarare@gmail.com', 'kheb oroj oosc cfli')

for folder in ['INBOX', '"[Gmail]/Todos"']:
    imap.select(folder, readonly=True)
    for sender in ['mailer-daemon', 'postmaster']:
        _, nums = imap.search(None, f'(FROM "{sender}" BODY "destinatario@dominio.com")')
        if nums[0]:
            ids = nums[0].split()
            print(f'{folder} | {sender} | {len(ids)} DSN encontrados')
            for uid in ids:
                _, data = imap.fetch(uid, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
                if data[0]:
                    msg = email.message_from_bytes(data[0][1])
                    print(f'  Date={msg["Date"]} | Subject={msg["Subject"]}')

imap.logout()
```

Buscar: existe un DSN cuyo Subject mencione el asunto EXACTO del radicado investigado?

### Paso 4. Cruzar Message-ID del DSN vs BD

Si hay DSN, descargar su contenido completo y extraer el Message-ID original del correo que reboto:

```python
# Dentro del DSN buscar la parte message/rfc822 o message/delivery-status
# Comparar ese Message-ID con el id_mensaje_enviado del radicado investigado
# Si NO coincide -> el DSN NO es para este radicado -> FALSO POSITIVO
```

### Paso 5. Diagnosticar

Clasificar el caso:

| Situacion | Diagnostico | Accion |
|-----------|------------|--------|
| DSN existe en Gmail Y su Message-ID coincide con el radicado | Rebote REAL | Mantener REBOTE |
| DSN existe en Gmail pero su Message-ID es de OTRO correo | FALSO POSITIVO por fallback | Revertir a ENVIADO |
| NO existe ningun DSN en Gmail para ese destinatario | FALSO POSITIVO | Revertir a ENVIADO |
| DSN existe pero es de un reenvio manual (Subject con "Fwd:") | FALSO POSITIVO por forward ajeno | Revertir a ENVIADO |

### Paso 6. Corregir registros (si falso positivo)

```python
from django.utils import timezone
from correspondencia.models import CorrespondenciaSalida, SalidaDestinatario, HistorialSalida

rad = 'SALIENTE-2026-XXXXX'
salida = CorrespondenciaSalida.objects.get(numero_radicado_salida=rad)

for sd in salida.destinatarios.filter(estado='REBOTE'):
    old_smtp = sd.smtp_code
    old_dsn = sd.dsn_status
    old_detalle = sd.detalle_error

    sd.estado = 'ENVIADO'
    sd.smtp_code = None
    sd.dsn_status = None
    sd.detalle_error = None
    sd.ultimo_evento_at = sd.fecha_envio
    sd.save(update_fields=['estado', 'smtp_code', 'dsn_status', 'detalle_error', 'ultimo_evento_at'])

    HistorialSalida.objects.create(
        correspondencia_salida=salida,
        tipo_evento='CORRECCION',
        descripcion=(
            f'Falso positivo REBOTE corregido a ENVIADO para {sd.email_snapshot}. '
            f'Datos borrados: smtp={old_smtp}, dsn={old_dsn}, detalle={old_detalle}'
        )
    )
    print(f'CORREGIDO: {rad} | {sd.email_snapshot}')
```

SIEMPRE:
- dejar registro en HistorialSalida tipo CORRECCION
- restaurar `ultimo_evento_at` a la fecha de envio original
- limpiar smtp_code, dsn_status, detalle_error
- verificar estado final despues de corregir

## Depuracion Masiva

Cuando el usuario pida auditar todos los rebotes o un lote grande:

### Listar todos los rebotes con contexto

```python
from correspondencia.models import SalidaDestinatario
rebotes = SalidaDestinatario.objects.filter(estado='REBOTE').select_related('correspondencia_salida').order_by('ultimo_evento_at')
for d in rebotes:
    s = d.correspondencia_salida
    print(f'{s.numero_radicado_salida} | {d.email_snapshot} | envio={d.fecha_envio} | marcado={d.ultimo_evento_at} | smtp={d.smtp_code} | dsn={d.dsn_status}')
```

### Agrupar por ultimo_evento_at para detectar lotes de fallback

Si multiples destinatarios distintos tienen exactamente el mismo `ultimo_evento_at`, fueron marcados en la misma corrida del procesador. Investigar si todos corresponden a un mismo DSN.

### Agrupar por email para detectar rebotes repetidos

```python
from django.db.models import Count
SalidaDestinatario.objects.filter(estado='REBOTE').values('email_snapshot').annotate(total=Count('id')).order_by('-total')
```

Si un email tiene muchos rebotes, es probable que algunos sean falsos positivos del fallback.

## Mejoras al Procesador

Si el usuario pide mejorar `procesar_rebotes.py`, considerar:

### Reglas de seguridad

1. **NUNCA eliminar el match primario por Message-ID** — es la unica forma confiable
2. **El fallback por email solo DEBE tener restricciones** — ventana de tiempo + solo ENVIADO
3. **No marcar como REBOTE si el DSN viene de un forward** (Subject con "Fwd:" o "Re: Undeliverable")
4. **Logging** — agregar self.stdout.write para cada match fallback para poder auditar

### Estructura del matching (actual)

```
1. Match primario: id_mensaje_enviado + email_snapshot (interseccion)
2. Fallback 1: email_snapshot solo, acotado a 7 dias y estado ENVIADO
3. Fallback 2: id_mensaje_enviado solo
```

### Mejoras potenciales

- Agregar un campo `dsn_message_uid` en SalidaDestinatario para trackear exactamente que DSN causo el marcado
- Filtrar DSN cuyo Subject contenga "Fwd:" o "Re: Undeliverable" (reenvios manuales, no del sistema)
- Agregar ventana de tiempo tambien al match primario para no matchear envios muy viejos
- Log detallado cuando se usa fallback para auditoria posterior

## Credenciales IMAP/SMTP

Para acceso directo a Gmail en scripts de depuracion:

- **IMAP**: `imap.gmail.com:993`, SSL
- **SMTP**: `smtp.gmail.com:587`, TLS
- **Usuario**: `Correspondenciaesesarare@gmail.com`
- **App Password**: definida en `.env` como `EMAIL_HOST_PASSWORD`
- **FROM**: `"Correspondencia - Hospital E.S.E. Sarare" <Correspondenciaesesarare@gmail.com>`

## Reglas de Trabajo

1. **Siempre activar el venv** antes de ejecutar scripts: `source venv/bin/activate`
2. **Siempre usar readonly=True** en IMAP cuando solo se investiga
3. **Nunca borrar DSN de Gmail** — son evidencia
4. **Siempre dejar HistorialSalida para correcciones** — trazabilidad obligatoria
5. **Verificar estado final** despues de cualquier correccion
6. **No modificar el procesador sin entender los 3 niveles de matching**
7. **Confirmar con el usuario** antes de correcciones masivas (>5 registros)
8. **django.setup()** y DJANGO_SETTINGS_MODULE siempre antes de importar modelos

## Checklist de Validacion

Despues de cualquier correccion o mejora:

- [ ] Los registros corregidos muestran estado=ENVIADO, smtp=None, dsn=None
- [ ] Existe entrada HistorialSalida tipo CORRECCION para cada registro revertido
- [ ] `python manage.py check` pasa sin errores
- [ ] El procesador de rebotes sigue matcheando rebotes REALES correctamente
- [ ] No se crearon duplicados en HistorialSalida o Notificacion
