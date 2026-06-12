# Plan: Modal de Radicación Saliente Rápida

## Análisis de viabilidad

### Estado actual
- **Modal existe:** `modal_radicacion_rapida_saliente.html` (modal-lg, campos actuales: asunto, cuerpo, destinatario_contacto, destinatario_texto, oficina_emisora).
- **Formulario existe:** `RadicacionRapidaSalienteForm` en `forms.py`.
- **Modelo base:** `CorrespondenciaSalida` con `numero_radicado_salida`, `fecha_creacion`, `asunto`, `cuerpo`, `destinatario_contacto`, `destinatario_email`, `oficina_emisora`, `usuario_redactor`.

### Mapeo de campos solicitados vs. modelo actual

| Campo solicitado | Modelo actual | Acción |
|------------------|---------------|--------|
| NUMERO DE RADICACION | `numero_radicado_salida` (auto) | Mantener auto o añadir override manual opcional |
| FECHA | `fecha_creacion` (auto) | Usar fecha_creacion o añadir `fecha_documento` opcional |
| NOMBRE PERSONA/ENTIDAD DESTINATARIA | `destinatario_contacto` + `destinatario_texto` (form) | Ya existe |
| ASUNTO | `asunto` | Ya existe |
| ANEXOS | No existe en CorrespondenciaSalida | **Añadir** `anexos` CharField (opcional) |
| MEDIO DE ENVIO | No existe | **Añadir** `medio_envio` CharField (opcional, choices) |
| DIRECCION O CORREO DE ENVIO | `destinatario_email` (editable=False) | **Añadir** `direccion_correo_envio` CharField o permitir llenar destinatario_email desde form |
| NOMBRE FUNCIONARIO RESPONSABLE | `redactor_nombre` (editable=False) | **Añadir** `funcionario_responsable_envio` CharField (opcional) |
| SUBPROCESO RESPONSABLE | `oficina_emisora` → OficinaProductora.proceso | Ya implícito: al elegir oficina se tiene el subproceso. Mostrar como informativo. |

---

## Plan menos disruptivo

### Fase 1: Modelo (migración única)

Añadir a `CorrespondenciaSalida` campos opcionales (todos `null=True, blank=True`):

```python
# Campos temporales para radicación rápida saliente
anexos = models.CharField(max_length=500, null=True, blank=True)
medio_envio = models.CharField(max_length=50, null=True, blank=True, choices=MEDIO_ENVIO_CHOICES)
direccion_correo_envio = models.CharField(max_length=254, null=True, blank=True)  # Email o dirección física
funcionario_responsable_envio = models.CharField(max_length=255, null=True, blank=True)
fecha_documento = models.DateField(null=True, blank=True)  # Fecha del documento (opcional, si difiere de creación)
```

`MEDIO_ENVIO_CHOICES` similar a `MEDIO_RECIBIDO_CHOICES`: EMAIL, CORREO_CERTIFICADO, FISICO, PERSONAL, etc.

El subproceso se obtiene de `oficina_emisora.proceso`; no requiere campo nuevo.

### Fase 2: Formulario (`forms.py`)

- Extender `RadicacionRapidaSalienteForm` con los nuevos campos.
- Hacer `cuerpo` opcional con valor por defecto para radicación rápida (ej. `"Registro de constancia - radicación rápida"`).
- Añadir `numero_radicado_manual` opcional (como en Correspondencia) si se desea override.
- Mantener `destinatario_contacto` y `destinatario_texto`; usar `direccion_correo_envio` cuando no haya contacto.

### Fase 3: Modal (`modal_radicacion_rapida_saliente.html`)

- Alinear con `modal_radicacion_rapida_entrante`: `modal-xl`, `max-width: 1370px`, layout en 4 columnas.
- Orden sugerido de campos:
  - Fila 1: Número radicación (readonly/info), Fecha, Nombre destinatario, Asunto
  - Fila 2: Anexos, Medio de envío, Dirección/correo envío, Funcionario responsable
  - Fila 3: Subproceso (derivado de oficina, readonly), Oficina emisora
- Mantener lógica de Select2 para selects.

### Fase 4: Vista

- En el manejo de `rapida_saliente`:
  - Asignar `salida.direccion_correo_envio` o `salida.destinatario_email` desde `direccion_correo_envio` cuando no hay contacto.
  - Asignar `salida.funcionario_responsable_envio`, `salida.anexos`, `salida.medio_envio`, `salida.fecha_documento`.
  - Si se implementa `numero_radicado_manual`, usarlo como override.

---

## Consideraciones

1. **Cuerpo obligatorio:** El modelo exige `cuerpo`. Para radicación rápida se puede usar un texto por defecto cuando no se ingrese nada.
2. **oficina_emisora editable:** Actualmente tiene `editable=False` en el modelo, pero se asigna en el `save()` o desde el form. Revisar que el form pueda pasarla correctamente (ya se hace en la vista con `salida.oficina_emisora = rapida_saliente_form.cleaned_data.get('oficina_emisora')`).
3. **Subproceso:** Se puede mostrar en el modal como texto informativo: "Subproceso: {oficina.proceso.nombre}" una vez seleccionada la oficina, o dejarlo implícito.

---

## Orden de implementación sugerido

1. Crear `MEDIO_ENVIO_CHOICES` y migración con los nuevos campos.
2. Actualizar `RadicacionRapidaSalienteForm` con los campos nuevos.
3. Actualizar el modal con el nuevo layout y campos.
4. Ajustar la vista para guardar los nuevos campos.
5. Probar el flujo completo.

---

## Impacto

- **Bajo:** Solo se añaden campos opcionales al modelo.
- **Formulario:** Se amplía el form existente, sin romper el actual.
- **Modal:** Se reemplaza el contenido manteniendo el mismo ID y flujo de apertura.
- **Vista:** Cambios locales en el bloque `rapida_saliente`.
