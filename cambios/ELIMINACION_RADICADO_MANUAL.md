# Eliminación de  Campo Número de Radicado Manual

**Fecha:** 9 de marzo de 2026  
**Categoría:** Simplificación de Formularios  
**Prioridad:** Media  
**Estado:** ✅ Completado

---

## 📋 Resumen

Se eliminó la funcionalidad de ingresar manualmente un número de radicado en el formulario de radicación de correspondencia. Ahora el sistema siempre genera el número de radicado automáticamente.

---

## 🎯 Motivación

- **Simplificación**: Reducir campos opcionales que pueden causar confusión
- **Consistencia**: Garantizar que todos los radicados sigan el formato estándar automático
- **Prevención de errores**: Evitar duplicados o números incorrectos por entrada manual

---

## 🔧 Cambios Realizados

### 1. **Formulario de Radicación** (`correspondencia/forms.py`)

#### Campo Eliminado:
```python
numero_radicado_manual = forms.CharField(
    max_length=5,
    required=False,
    label="Consecutivo manual (opcional)",
    widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ej: 00042 (solo 5 dígitos)',
        'maxlength': '5',
        'pattern': '[0-9]*',
        'inputmode': 'numeric',
    }),
    help_text="Deje vacío para radicado automático. Si indica el consecutivo (1 a 99999), se usará ENTRANTE-{año}-xxxxx."
)
```

#### Layout Actualizado:
- **Eliminado:** `Field('numero_radicado_manual', css_class='mb-3')`
- El campo ya no aparece en el formulario renderizado

#### Validaciones Eliminadas (Método `clean`):
```python
# ELIMINADO: Validación de consecutivo manual
raw_consecutivo = (cleaned_data.get('numero_radicado_manual') or '').strip()
if raw_consecutivo:
    if not raw_consecutivo.isdigit():
        self.add_error('numero_radicado_manual', 'Solo se permiten números...')
    else:
        # Validación de rango 1-99999
        # Validación de duplicados
        # Construcción de ENTRANTE-{año}-{consecutivo:05d}
```

---

### 2. **Vistas** (`correspondencia/views.py`)

#### Ubicaciones Modificadas:

##### ✅ Vista `dashboard_ventanilla` (línea ~1690)
**Antes:**
```python
if radicacion_form.is_valid():
    correspondencia = radicacion_form.save(commit=False)
    correspondencia.tipo_radicado = 'ENTRANTE'
    correspondencia.usuario_radicador = request.user
    if radicacion_form.cleaned_data.get('numero_radicado_manual'):
        correspondencia.numero_radicado = radicacion_form.cleaned_data['numero_radicado_manual']
    correspondencia.save()
```

**Después:**
```python
if radicacion_form.is_valid():
    correspondencia = radicacion_form.save(commit=False)
    correspondencia.tipo_radicado = 'ENTRANTE'
    correspondencia.usuario_radicador = request.user
    correspondencia.save()  # Genera número automáticamente
```

##### ✅ Vista `dashboard_ventanilla_legacy` (línea ~4760)
- Se aplicó el mismo cambio que en `dashboard_ventanilla`

##### ✅ Vista `detalle_correo_entrante_view` (línea ~5260)
**Antes:**
```python
correspondencia.usuario_radicador = request.user
correspondencia.origen_radicacion = 'CORREO'
if form_radicacion.cleaned_data.get('numero_radicado_manual'):
    correspondencia.numero_radicado = form_radicacion.cleaned_data['numero_radicado_manual']
correspondencia.save()
```

**Después:**
```python
correspondencia.usuario_radicador = request.user
correspondencia.origen_radicacion = 'CORREO'
correspondencia.save()  # Genera número automáticamente
```

---

## 🧪 Validación

### ✅ Sin Errores de Sintaxis
```bash
# Verificado en:
- correspondencia/forms.py
- correspondencia/views.py
```

### ✅ Búsqueda de Referencias
```bash
grep -r "numero_radicado_manual" correspondencia/
# Resultado: Sin coincidencias
```

---

## 📁 Archivos Modificados

| Archivo | Cambios | Líneas Afectadas |
|---------|---------|------------------|
| `correspondencia/forms.py` | Campo eliminado + Layout + Validación | ~469-479, ~590, ~698-716 |
| `correspondencia/views.py` | Procesamiento eliminado (3 ubicaciones) | ~1694-1695, ~4760-4761, ~5261-5262 |

---

## 🔄 Comportamiento Actual

### Generación Automática de Radicado

El sistema sigue utilizando el método `save()` del modelo `Correspondencia`, que **automáticamente** genera el número de radicado con el formato:

```
ENTRANTE-{año}-{consecutivo:05d}
```

**Ejemplo:**
- `ENTRANTE-2026-00001`
- `ENTRANTE-2026-00042`
- `ENTRANTE-2026-12345`

El consecutivo es **autoincremental** y se obtiene del último radicado del año actual, garantizando unicidad.

---

## 🎨 Impacto en la Interfaz

### Modal de Radicación (`modal_radicacion.html`)

#### Antes:
```
┌─────────────────────────────────┐
│  Remitente                      │
│  Medio de Recepción / Oficina   │
│  Consecutivo manual (opcional)  │ ← ELIMINADO
│  Asunto                         │
│  Serie / Subserie               │
└─────────────────────────────────┘
```

#### Después:
```
┌─────────────────────────────────┐
│  Remitente                      │
│  Medio de Recepción / Oficina   │
│  Asunto                         │
│  Serie / Subserie               │
└─────────────────────────────────┘
```

---

## 🚀 Próximos Pasos Recomendados

1. **Testing Manual:**
   - Radicar correspondencia desde ventanilla
   - Verificar que el número se genera correctamente
   - Probar en dashboard y detalle de correo

2. **Documentación de Usuario:**
   - Actualizar manual de usuario
   - Comunicar cambio a equipo de ventanilla

3. **Monitoreo:**
   - Verificar que no haya errores en logs
   - Confirmar que consecutivos siguen siendo únicos

---

## 📝 Notas Adicionales

- **Sin breaking changes:** El cambio es transparente para el usuario
- **Modelo sin cambios:** No requiere migración de base de datos
- **Backward compatible:** Radicados existentes no se ven afectados
- **Simplificación exitosa:** Menos campos = menos errores potenciales

---

## ✅ Checklist de Validación

- [x] Campo eliminado del formulario
- [x] Validaciones eliminadas
- [x] Layout actualizado
- [x] 3 ubicaciones en vistas modificadas
- [x] Sin errores de sintaxis
- [x] Sin referencias huérfanas
- [x] Documentación actualizada

---

**Documentado por:** GitHub Copilot  
**Revisado por:** DevDiego  
**Ticket relacionado:** N/A
