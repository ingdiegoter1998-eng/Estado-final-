# Envios y radicados

Este documento describe el flujo de radicacion rapida entrante y el envio automatico de notificaciones por correo, incluyendo el threading (In-Reply-To / References) y el registro en historial.

## Objetivo

- Radicar rapidamente una correspondencia entrante desde el detalle del correo.
- Enviar una notificacion automatica al funcionario responsable del tramite.
- Mantener el hilo de conversacion en Gmail usando el Message-ID original.
- Registrar el resultado del envio en el historial de la correspondencia.

## Flujo general

1. Usuario abre el detalle del correo entrante.
2. En el modal de radicacion rapida, diligencia los campos y el correo del funcionario responsable.
3. Al guardar:
   - Se crea la correspondencia entrante.
   - Se asocia el correo entrante al radicado.
   - Se copian adjuntos del correo al radicado.
4. Fuera de la transaccion:
   - Se envia un email al funcionario responsable.
   - Se inyectan headers de threading.
   - Se adjuntan los archivos del correo original.
   - Se registra el resultado en historial.

## Modelo de datos

Se agrego un nuevo campo para persistir el email del funcionario responsable:

- [correspondencia/models.py](correspondencia/models.py#L438-L447)
  - `email_funcionario_responsable`: `EmailField`, opcional.

Migracion:

- [correspondencia/migrations/0053_add_email_funcionario_responsable.py](correspondencia/migrations/0053_add_email_funcionario_responsable.py#L1-L18)

## Formulario de radicacion rapida

El formulario ahora incluye el email del funcionario responsable:

- [correspondencia/forms.py](correspondencia/forms.py#L1452-L1635)
  - Campo `email_funcionario_responsable` agregado a `fields`, `widgets` y `labels`.
  - El campo se marca como opcional en el `__init__`.

## Modal de radicacion rapida (UI)

Se agrego el campo en el modal con aviso de envio automatico:

- [correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_entrante.html](correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_entrante.html#L110-L138)

## Envio automatico de correo

La logica se implemento en la vista del detalle del correo entrante, en el flujo de `rapida_entrante`.

- [correspondencia/views.py](correspondencia/views.py#L7382-L7545)

### Pasos del envio

1. Se prepara un contexto con datos del radicado:
   - `numero_radicado`, `fecha_radicacion`, `remitente`, `oficina_destino`, `medio_recepcion`.
   - `tipo_tramite`, `fecha_limite_respuesta_manual`, `asunto`.
   - `usuario_radicador`.
2. Se renderiza el HTML del correo.
3. Se calculan headers de threading:
   - `In-Reply-To` y `References` con el `Message-ID` del correo original.
4. Se fuerza el asunto con prefijo `Re:` si no esta presente.
5. Se adjuntan archivos del correo entrante original.
6. Se envia el correo.
7. Se registra en historial:
   - `NOTIFICACION` si se envia con exito.
   - `ERROR` si falla el envio.

## Template de notificacion

El correo de notificacion se genera con el template:

- [correspondencia/templates/correspondencia/email/notificacion_asignacion_entrante.html](correspondencia/templates/correspondencia/email/notificacion_asignacion_entrante.html#L1-L120)

Incluye:

- Encabezado institucional.
- Datos del radicado en tabla.
- Asunto del radicado.
- Cuerpo del correo original (si existe).
- Aviso de confidencialidad.

## Threading con Gmail

Para que Gmail agrupe en el mismo hilo:

- `In-Reply-To`: debe contener el `Message-ID` del correo original entre `< >`.
- `References`: debe contener el mismo `Message-ID`.
- El `Subject` mantiene el prefijo `Re:`.

Esto se aplica en la vista antes de enviar.

## Registro en historial

Se registran eventos en `HistorialCorrespondencia`:

- Evento `NOTIFICACION` con descripcion del envio y el email destino.
- Evento `ERROR` si el envio falla.

## Consideraciones y fallos tolerados

- Si el envio de correo falla, la radicacion no se revierte.
- Se muestra un warning al usuario, pero el radicado queda guardado.
- Los adjuntos se intentan adjuntar uno por uno; si falla alguno, no bloquea el envio.

## Validacion previa (correccion adicional)

Se corrigio un error de template en firma cuando `usuario_destino_inicial` es `None`:

- [correspondencia/templates/correspondencia/admin/detalle_dia_informe.html](correspondencia/templates/correspondencia/admin/detalle_dia_informe.html#L330-L337)

## Pruebas sugeridas

1. Abrir un correo entrante y radicar con email del funcionario.
2. Verificar que llegue el correo con asunto `Re:`.
3. Confirmar que el correo quede en el mismo hilo (Gmail).
4. Validar adjuntos en la notificacion.
5. Revisar historial en la correspondencia.

## Posibles mejoras futuras

- Guardar Message-ID del correo enviado para threading de respuestas posteriores.
- Convertir funcionario responsable a un selector de usuarios del sistema.
- Configurar reintento automatico en caso de fallos SMTP.
