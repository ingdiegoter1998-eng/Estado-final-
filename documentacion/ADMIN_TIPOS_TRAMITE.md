# Implementación - Tipos de Trámite Editables desde Admin

**Fecha:** 10 de febrero de 2026  
**Objetivo:** Permitir administrar los tipos de trámite y sus días de respuesta desde el panel de administración de Django

---

## 🎯 Cambios Implementados

### 1. Nuevo Modelo: `TipoTramite`

**Ubicación:** [correspondencia/models.py](correspondencia/models.py)

Se creó un modelo completo para gestionar tipos de trámite:

```python
class TipoTramite(models.Model):
    codigo = CharField(max_length=20, unique=True)
    nombre = CharField(max_length=100)
    descripcion = TextField(blank=True)
    dias_respuesta = PositiveIntegerField(null=True, blank=True)
    activo = BooleanField(default=True)
    orden = PositiveIntegerField(default=0)
    fecha_creacion = DateTimeField(auto_now_add=True)
    fecha_modificacion = DateTimeField(auto_now=True)
```

**Campos:**
- `codigo`: Código único (PT, PTA, DM, etc.)
- `nombre`: Nombre descriptivo
- `descripcion`: Descripción detallada (opcional)
- `dias_respuesta`: Días hábiles de respuesta (null = sin plazo)
- `activo`: Solo tipos activos aparecen en formularios
- `orden`: Orden en listas desplegables
- Campos de auditoría (fecha_creacion, fecha_modificacion)

### 2. Panel de Administración

**Ubicación:** [correspondencia/admin.py](correspondencia/admin.py)

Se registró el modelo con una interfaz completa:

```python
@admin.register(TipoTramite)
class TipoTramiteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'dias_respuesta_display', 'activo', 'orden', 'fecha_modificacion')
    list_filter = ('activo', 'dias_respuesta')
    search_fields = ('codigo', 'nombre', 'descripcion')
    list_editable = ('activo', 'orden')
```

**Funcionalidades del Admin:**
- ✅ Lista ordenada por orden y código
- ✅ Edición rápida de activo y orden desde la lista
- ✅ Filtros por activo y días de respuesta
- ✅ Búsqueda por código, nombre y descripción
- ✅ Display amigable de días de respuesta
- ✅ Campos de auditoría en vista de solo lectura
- ✅ Mensaje de confirmación al guardar cambios

### 3. Vistas Actualizadas

**Ubicación:** [correspondencia/views.py](correspondencia/views.py)

Las vistas ahora consultan el modelo en lugar de constantes:

```python
# Antes (constantes estáticas)
if tipo_tramite in DIAS_RESPUESTA_POR_TIPO_TRAMITE:
    dias_respuesta = DIAS_RESPUESTA_POR_TIPO_TRAMITE[tipo_tramite]

# Ahora (consulta dinámica)
tipo_tramite_obj = TipoTramite.objects.get(codigo=tipo_tramite_codigo, activo=True)
if tipo_tramite_obj.dias_respuesta is not None:
    fecha_limite = calcular_dias_habiles(fecha_radicacion, tipo_tramite_obj.dias_respuesta)
```

**Vistas modificadas:**
- `dashboard_ventanilla()` - Creación de radicación rápida
- `editar_radicacion_rapida_entrante()` - Edición de radicación rápida

### 4. Nueva API para JavaScript

**Ubicación:** [correspondencia/views.py](correspondencia/views.py)
**URL:** `/correspondencia/api/tipos-tramite/`

Nueva vista que expone los tipos de trámite activos:

```python
@login_required
@require_GET
def api_tipos_tramite(request):
    tipos = TipoTramite.objects.filter(activo=True).order_by('orden', 'codigo')
    data = {}
    for tipo in tipos:
        data[tipo.codigo] = {
            'nombre': tipo.nombre,
            'dias_respuesta': tipo.dias_respuesta,
            'descripcion': tipo.descripcion
        }
    return JsonResponse(data)
```

**Respuesta de ejemplo:**
```json
{
  "PT": {
    "nombre": "Petición",
    "dias_respuesta": 15,
    "descripcion": "Petición general de información..."
  },
  "PTA": {
    "nombre": "Petición Anticipada",
    "dias_respuesta": 4,
    "descripcion": "Petición que requiere respuesta prioritaria..."
  }
}
```

### 5. Formulario Dinámico

**Ubicación:** [correspondencia/forms.py](correspondencia/forms.py)

El formulario ahora carga opciones dinámicamente:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Cargar tipos de trámite dinámicamente desde la base de datos
    if 'tipo_tramite' in self.fields:
        tipos_activos = TipoTramite.objects.filter(activo=True).order_by('orden', 'codigo')
        choices = [('', '---------')]
        for tipo in tipos_activos:
            choices.append((tipo.codigo, tipo.get_choice_display()))
        self.fields['tipo_tramite'].choices = choices
```

### 6. JavaScript Actualizado

**Ubicación:** [correspondencia/static/.../radicacion-rapida-entrante.js](correspondencia/static/correspondencia/js/modals/radicacion-rapida-entrante.js)

El JavaScript ahora carga tipos desde la API:

**Antes:**
```javascript
const DIAS_RESPUESTA_POR_TIPO_TRAMITE = {
    'PT': 15,
    'PTA': 4,
    // ... hardcoded
};
```

**Ahora:**
```javascript
async function cargarTiposTramite() {
    const response = await fetch('/correspondencia/api/tipos-tramite/');
    TIPOS_TRAMITE_CACHE = await response.json();
    return TIPOS_TRAMITE_CACHE;
}

async function initTipoTramiteListener(prefix) {
    const tiposTramite = await cargarTiposTramite();
    // Usa tiposTramite dinámicamente
}
```

### 7. Migración con Datos Iniciales

**Ubicación:** [correspondencia/migrations/0051_crear_modelo_tipo_tramite.py](correspondencia/migrations/0051_crear_modelo_tipo_tramite.py)

La migración crea la tabla y pobla los 10 tipos iniciales:

```python
def crear_tipos_tramite_iniciales(apps, schema_editor):
    TipoTramite = apps.get_model('correspondencia', 'TipoTramite')
    
    tipos_iniciales = [
        {
            'codigo': 'PT',
            'nombre': 'Petición',
            'descripcion': 'Petición general de información...',
            'dias_respuesta': 15,
            'orden': 10
        },
        # ... 9 tipos más
    ]
    
    for tipo_data in tipos_iniciales:
        TipoTramite.objects.create(**tipo_data)
```

**Tipos creados:**
1. PT - Petición (15 días)
2. PTA - Petición Anticipada (4 días)
3. DM - Documento Médico (5 días)
4. HC - Historia Clínica (3 días)
5. CMC - Cita Médica/Consulta (2 días)
6. PQRSF - PQRSF (15 días)
7. GLA - Queja/Reclamo (15 días)
8. SD - Solicitud de Documentos (10 días)
9. AT - Asunto Técnico (8 días)
10. NA - No Aplica (sin plazo)

---

## 📋 Cómo Usar el Panel de Administración

### Acceso

1. Ir a: **http://tu-servidor/admin/**
2. Iniciar sesión como superusuario
3. Buscar sección: **Correspondencia**
4. Hacer clic en: **Tipos de Trámite**

### Editar un Tipo Existente

1. En la lista, hacer clic en el tipo de trámite deseado
2. Modificar los campos:
   - **Código**: Solo lectura (no se puede cambiar)
   - **Nombre**: Actualizar descripción corta
   - **Descripción**: Actualizar descripción detallada
   - **Días de Respuesta**: Cambiar número de días hábiles (dejar vacío = sin plazo)
   - **Activo**: Marcar/desmarcar para mostrar/ocultar en formularios
   - **Orden**: Cambiar posición en lista desplegable
3. Hacer clic en **Guardar**

### Agregar un Nuevo Tipo

1. Hacer clic en **Agregar Tipo de Trámite** (botón superior derecho)
2. Completar campos:
   - **Código** ⚠️: Único, corto, sin espacios (ej: `REC`)
   - **Nombre**: Descriptivo (ej: `Reclamo`)
   - **Descripción**: Detallada (opcional)
   - **Días de Respuesta**: Número de días hábiles (ej: `10`)
   - **Activo**: Marcar ✓
   - **Orden**: Número (menor = primero, ej: `85`)
3. Hacer clic en **Guardar**

### Edición Rápida desde la Lista

Para cambios rápidos de **Activo** y **Orden**:
1. En la lista de tipos de trámite
2. Modificar directamente los valores en las columnas editables
3. Hacer clic en **Guardar** (botón inferior)

### Desactivar un Tipo (sin eliminarlo)

1. Editar el tipo de trámite
2. Desmarcar **Activo**
3. Guardar
   - El tipo desaparecerá de los formularios
   - Los registros existentes conservan el tipo

### Cambiar Orden de Aparición

Los tipos se ordenan por:
1. Campo **Orden** (ascendente - menor número primero)
2. **Código** (alfabético)

**Ejemplo:**
- Orden 10 → PT (aparece primero)
- Orden 20 → PTA (aparece segundo)
- Orden 100 → NA (aparece último)

---

## 🔍 Flujo Completo

### 1. Administrador edita tipo en Admin

```
Admin Panel → Tipos de Trámite → PTA (editar)
Cambiar días_respuesta de 4 a 3
Guardar
```

### 2. Cambio se refleja en la base de datos

```sql
UPDATE correspondencia_tipotramite 
SET dias_respuesta = 3, fecha_modificacion = NOW()
WHERE codigo = 'PTA';
```

### 3. Formulario carga dinámicamente desde DB

```python
# En RadicacionRapidaEntranteForm.__init__()
tipos_activos = TipoTramite.objects.filter(activo=True)
# Resultado: incluye PTA con 3 días (valor actualizado)
```

### 4. JavaScript obtiene tipos desde API

```javascript
fetch('/correspondencia/api/tipos-tramite/')
// Respuesta: {"PTA": {"dias_respuesta": 3, ...}}
```

### 5. Usuario selecciona PTA en formulario

```
Frontend: Calcula fecha límite (3 días desde hoy)
Backend: Al guardar, calcula fecha límite (3 días desde radicación)
```

---

## ✅ Ventajas de esta Implementación

### Para Administradores

- ✅ **Sin código**: Cambios desde interfaz web
- ✅ **Inmediato**: Cambios se reflejan automáticamente
- ✅ **Auditoría**: Fecha de modificación registrada
- ✅ **Reversible**: Desactivar sin eliminar
- ✅ **Ordenable**: Control total del orden de aparición

### Para el Sistema

- ✅ **Dinámico**: No requiere despliegue para cambios
- ✅ **Consistente**: Una sola fuente de verdad (DB)
- ✅ **Escalable**: Agregar nuevos tipos fácilmente
- ✅ **Performante**: API cacheada en frontend
- ✅ **Mantenible**: Código más limpio sin constantes hardcoded

### Para Usuarios Finales

- ✅ **Actualizado**: Ven siempre opciones actuales
- ✅ **Preciso**: Cálculos con valores correctos
- ✅ **Rápido**: JavaScript calcula preview instantáneo
- ✅ **Confiable**: Backend valida nuevamente al guardar

---

## 🔧 Archivos Modificados/Creados

```
✏️  correspondencia/models.py            (+ TipoTramite model)
✏️  correspondencia/admin.py             (+ TipoTramiteAdmin)
✏️  correspondencia/views.py             (consultas dinámicas, + api_tipos_tramite)
✏️  correspondencia/urls.py              (+ ruta api/tipos-tramite/)
✏️  correspondencia/forms.py             (choices dinámicos en __init__)
✏️  ...js/modals/radicacion-rapida-entrante.js  (carga desde API)
🆕 correspondencia/migrations/0051_crear_modelo_tipo_tramite.py
🆕 documentacion/ADMIN_TIPOS_TRAMITE.md (este documento)
```

---

## 🚀 Testing Manual

### 1. Verificar Panel Admin

```bash
# Acceder a http://localhost:8000/admin/
# Login → Correspondencia → Tipos de Trámite
# Verificar que aparecen los 10 tipos iniciales
```

### 2. Editar un Tipo

```bash
# En Admin: Editar PTA
# Cambiar días_respuesta de 4 a 6
# Guardar
```

### 3. Verificar API

```bash
curl http://localhost:8000/correspondencia/api/tipos-tramite/
# Verificar que PTA muestra "dias_respuesta": 6
```

### 4. Probar en Formulario

```bash
# Abrir Dashboard Ventanilla
# Abrir modal "Radicación Rápida Entrante"
# Seleccionar tipo "PTA"
# Verificar que fecha límite se calcula con 6 días (nuevo valor)
```

### 5. Desactivar un Tipo

```bash
# En Admin: Editar AT (Asunto Técnico)
# Desmarcar "Activo"
# Guardar
# Verificar que AT ya no aparece en formulario
```

---

## 📝 Notas Importantes

### Constantes Legacy

Las constantes `TIPO_TRAMITE_CHOICES` y `DIAS_RESPUESTA_POR_TIPO_TRAMITE` en [correspondencia/models.py](correspondencia/models.py) se mantienen como **respaldo** por compatibilidad, pero **NO se usan** en producción. El sistema obtiene todo desde la base de datos.

### Cache en JavaScript

El JavaScript cachea los tipos de trámite en `TIPOS_TRAMITE_CACHE` durante la sesión. Si un administrador hace cambios mientras un usuario tiene el formulario abierto, el usuario verá los valores antiguos hasta que recargue la página.

**Solución:** Los cambios son validados nuevamente en el backend al guardar, así que la fecha límite siempre se calcula con el valor actualizado en la base de datos.

### Validación de Código Único

El campo `codigo` tiene constraint `unique=True`. Si intentas crear dos tipos con el mismo código, Django lanzará error de integridad.

### Eliminar vs Desactivar

**Recomendación:** Siempre **desactivar** (`activo=False`) en lugar de eliminar tipos de trámite. Esto preserva los registros históricos que referencian ese código.

---

## 🎓 Capacitación para Administradores

### Conceptos Clave

**Días Hábiles:** Excluyen sábados y domingos. El sistema calcula automáticamente.

**Orden:** Número que determina la posición. Menores van primero.
- Orden 10 = Primera posición
- Orden 100 = Última posición

**Activo:** Solo tipos activos aparecen en formularios nuevos. Los registros antiguos conservan su tipo.

**Código:** Identificador único del tipo (PT, PTA, etc.). No se puede cambiar después de crear.

### Ejemplos Prácticos

#### Cambiar tiempo de respuesta de PQRSF de 15 a 20 días

1. Admin → Tipos de Trámite → PQRSF
2. Cambiar **Días Hábiles de Respuesta**: `15` → `20`
3. Guardar
4. ✅ Listo. Nuevas radicaciones PQRSF tendrán 20 días.

#### Agregar nuevo tipo: Renovación de Contrato (5 días)

1. Admin → Tipos de Trámite → **Agregar**
2. Código: `RC`
3. Nombre: `Renovación de Contrato`
4. Días: `5`
5. Activo: ✓
6. Orden: `75` (entre SD=80 y GLA=70)
7. Guardar
8. ✅ Aparece en formularios inmediatamente.

#### Reordenar: Poner CMC antes que HC

1. Admin → Tipos de Trámite
2. Cambiar **Orden** de CMC: `50` → `35`
3. Cambiar **Orden** de HC: `40` → `40` (sin cambios)
4. Guardar
5. ✅ CMC ahora aparece antes.

---

**Fecha de implementación:** 10 de febrero de 2026  
**Estado:** ✅ Completa y funcional  
**Migración aplicada:** ✅ 0051_crear_modelo_tipo_tramite.py  
**Archivos estáticos:** ✅ Recopilados con collectstatic
