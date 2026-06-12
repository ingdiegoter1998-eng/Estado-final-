# Tipos de Trámite - Radicación Rápida Entrante

Este documento describe los tipos de trámite disponibles para la radicación rápida de correspondencia entrante y sus tiempos de respuesta asociados.

## Tipos de Trámite Disponibles

La siguiente tabla muestra los códigos de trámite, sus descripciones y los días hábiles de respuesta:

| Código | Descripción | Días Hábiles de Respuesta |
|--------|-------------|---------------------------|
| **PT** | Petición | 15 días |
| **PTA** | Petición Anticipada | 4 días |
| **DM** | Documento Médico | 5 días |
| **HC** | Historia Clínica | 3 días |
| **CMC** | Cita Médica/Consulta | 2 días |
| **PQRSF** | PQRSF (Peticiones, Quejas, Reclamos, Sugerencias, Felicitaciones) | 15 días |
| **GLA** | Queja/Reclamo | 15 días |
| **SD** | Solicitud de Documentos | 10 días |
| **AT** | Asunto Técnico | 8 días |
| **NA** | No Aplica | Sin plazo definido |

## Cálculo Automático de Fecha Límite

Cuando se selecciona un tipo de trámite durante la radicación rápida entrante, el sistema calcula automáticamente la **fecha límite de respuesta** de las siguientes formas:

### En el Backend (Python)

El cálculo se realiza en el servidor al momento de guardar la radicación. Los días hábiles se calculan excluyendo sábados y domingos:

```python
# En correspondencia/views.py - dashboard_ventanilla()
tipo_tramite = correspondencia.tipo_tramite
if tipo_tramite and tipo_tramite in DIAS_RESPUESTA_POR_TIPO_TRAMITE:
    dias_respuesta = DIAS_RESPUESTA_POR_TIPO_TRAMITE[tipo_tramite]
    if dias_respuesta is not None:
        fecha_limite = calcular_dias_habiles(correspondencia.fecha_radicacion, dias_respuesta)
        correspondencia.fecha_limite_respuesta_manual = fecha_limite
```

### En el Frontend (JavaScript)

También se proporciona un cálculo dinámico en tiempo real que actualiza el campo de fecha límite cuando el usuario selecciona un tipo de trámite en el formulario:

```javascript
// En correspondencia/static/correspondencia/js/modals/radicacion-rapida-entrante.js
tipoTramiteField.addEventListener('change', function() {
    const tipoSeleccionado = this.value;
    if (tipoSeleccionado) {
        actualizarFechaLimite(tipoSeleccionado, fechaLimiteField);
    }
});
```

## Días Hábiles

**Días hábiles** son aquellos que **NO** son sábado ni domingo. El sistema automáticamente excluye los fines de semana al calcular la fecha límite.

### Ejemplo de Cálculo

Si se radica una correspondencia con tipo **PTA (Petición Anticipada)** el **martes 10 de febrero de 2026**:

- **Días hábiles a sumar:** 4
- **Conteo:**
  1. Miércoles 11 de febrero
  2. Jueves 12 de febrero
  3. Viernes 13 de febrero
  4. Lunes 16 de febrero (se excluyen sábado 14 y domingo 15)
- **Fecha límite:** Lunes 16 de febrero de 2026

## Configuración de Nuevos Tipos de Trámite

Para agregar o modificar tipos de trámite, editar las siguientes constantes en `correspondencia/models.py`:

### 1. Agregar el choice:

```python
TIPO_TRAMITE_CHOICES = [
    ('', '---------'),
    ('PT', 'Petición (PT)'),
    ('PTA', 'Petición Anticipada (PTA)'),
    # ... agregar nueva opción aquí
    ('NUEVO', 'Descripción del Nuevo Tipo (NUEVO)'),
]
```

### 2. Definir los días de respuesta:

```python
DIAS_RESPUESTA_POR_TIPO_TRAMITE = {
    'PT': 15,
    'PTA': 4,
    # ... agregar mapeo aquí
    'NUEVO': 5,  # número de días hábiles
}
```

### 3. Actualizar JavaScript (opcional):

Si se desea cálculo en tiempo real en el frontend, actualizar el diccionario en `radicacion-rapida-entrante.js`:

```javascript
const DIAS_RESPUESTA_POR_TIPO_TRAMITE = {
    'PT': 15,
    'PTA': 4,
    // ... agregar mapeo aquí
    'NUEVO': 5
};
```

### 4. Generar y aplicar migración:

```bash
python manage.py makemigrations correspondencia
python manage.py migrate
```

## Uso en el Formulario

1. **Abrir el modal de Radicación Rápida Entrante** desde el Dashboard de Ventanilla
2. **Completar los campos obligatorios:** Asunto y Oficina Destino
3. **Seleccionar Tipo de Trámite** en la sección de datos adicionales
4. El sistema automáticamente:
   - Calcula la fecha límite en el backend al guardar
   - Muestra una vista previa en el frontend (si JavaScript está habilitado)
5. **Radicar** para guardar la correspondencia entrante

## Validación

El campo `tipo_tramite` es **opcional** pero si se proporciona debe ser uno de los códigos definidos en `TIPO_TRAMITE_CHOICES`.

El formulario valida que:
- El código sea válido
- Si se calcula una fecha límite, sea posterior a la fecha de radicación

## Consideraciones Especiales

### Tipo NA (No Aplica)

El tipo **NA** no tiene días de respuesta definidos (`null`). Cuando se selecciona:
- No se calcula ninguna fecha límite automáticamente
- El usuario puede ingresar manualmente una fecha límite si lo desea

### Festivos

**Nota:** La versión actual del cálculo de días hábiles **NO** considera festivos nacionales o regionales. Solo excluye sábados y domingos.

Si se requiere considerar festivos, se debe:
1. Crear una tabla/modelo de festivos en la base de datos
2. Modificar la función `calcular_dias_habiles()` en `correspondencia/models.py`
3. Actualizar el JavaScript correspondiente

## Archivos Relacionados

- **Modelo:** `correspondencia/models.py` - Definiciones de choices y función de cálculo
- **Formulario:** `correspondencia/forms.py` - Configuración del campo tipo_tramite
- **Vista:** `correspondencia/views.py` - Lógica de guardado y cálculo backend
- **Template:** `correspondencia/templates/correspondencia/partials/modals/modal_radicacion_rapida_entrante.html`
- **JavaScript:** `correspondencia/static/correspondencia/js/modals/radicacion-rapida-entrante.js`
- **Tests:** `correspondencia/tests.py` - Pruebas unitarias

## Migración de Base de Datos

La migración `0050_alter_correspondencia_tipo_tramite.py` actualiza el campo `tipo_tramite` de texto libre a choices con los códigos definidos.

**Datos existentes:** Si hay registros con valores de texto libre anteriores, se mantendrán, pero el formulario solo permitirá los nuevos códigos para registros futuros.

---

*Última actualización: 10 de febrero de 2026*
