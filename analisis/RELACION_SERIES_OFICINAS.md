# Relación Muchos a Muchos: Series Documentales y Oficinas Productoras

## Implementación

Se ha establecido una relación muchos a muchos entre `SerieDocumental` y `OficinaProductora` (subprocesos) para permitir que:
- Una **Serie Documental** pueda ser utilizada por **múltiples Oficinas Productoras**
- Una **Oficina Productora** pueda tener **múltiples Series Documentales**

## Cambios Realizados

### 1. Modelo `SerieDocumental` (documentos/models.py)

```python
class SerieDocumental(models.Model):
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    codigo_trd = models.CharField(max_length=255, blank=True, null=True)
    oficinas_productoras = models.ManyToManyField(
        'OficinaProductora',
        related_name='series_documentales',
        blank=True,
        help_text="Oficinas productoras (subprocesos) que utilizan esta serie documental"
    )
```

### 2. Admin de Django (documentos/admin.py)

Se actualizó el admin para gestionar la relación con un widget mejorado:

```python
@admin.register(SerieDocumental)
class SerieDocumentalAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'codigo_trd', 'contar_oficinas')
    filter_horizontal = ('oficinas_productoras',)  # Widget de selección dual
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'codigo_trd')
        }),
        ('Relación con Oficinas Productoras (Subprocesos)', {
            'fields': ('oficinas_productoras',),
        }),
    )
```

### 3. Migración

- Archivo: `documentos/migrations/0019_agregar_relacion_series_oficinas.py`
- Crea tabla intermedia: `documentos_seriedocumental_oficinas_productoras`

## Uso en Código

### Asignar oficinas a una serie:

```python
from documentos.models import SerieDocumental, OficinaProductora

# Obtener una serie
serie = SerieDocumental.objects.get(codigo='01')

# Obtener oficinas
oficina1 = OficinaProductora.objects.get(codigo='300')
oficina2 = OficinaProductora.objects.get(codigo='301')

# Asignar oficinas a la serie
serie.oficinas_productoras.add(oficina1, oficina2)

# O usar set() para reemplazar todas
serie.oficinas_productoras.set([oficina1, oficina2])
```

### Consultar oficinas de una serie:

```python
# Obtener todas las oficinas que usan una serie
serie = SerieDocumental.objects.get(codigo='01')
oficinas = serie.oficinas_productoras.all()

for oficina in oficinas:
    print(f"Oficina: {oficina.nombre} - TRD: {oficina.codigo_trd}")
```

### Consultar series de una oficina:

```python
# Obtener todas las series que usa una oficina
oficina = OficinaProductora.objects.get(codigo='300')
series = oficina.series_documentales.all()

for serie in series:
    print(f"Serie: {serie.nombre} - Código: {serie.codigo}")
```

### Filtrar series por oficina:

```python
# Series que usa una oficina específica
oficina_id = 1
series = SerieDocumental.objects.filter(oficinas_productoras__id=oficina_id)

# Series que NO tienen oficinas asignadas
series_sin_oficina = SerieDocumental.objects.filter(oficinas_productoras__isnull=True)

# Series con al menos una oficina asignada
series_con_oficina = SerieDocumental.objects.filter(oficinas_productoras__isnull=False).distinct()
```

### Verificar si una serie está asignada a una oficina:

```python
serie = SerieDocumental.objects.get(codigo='01')
oficina = OficinaProductora.objects.get(codigo='300')

if oficina in serie.oficinas_productoras.all():
    print("La oficina usa esta serie")
    
# O más eficiente:
if serie.oficinas_productoras.filter(id=oficina.id).exists():
    print("La oficina usa esta serie")
```

## Casos de Uso

### 1. Filtrar series disponibles para un usuario según su oficina

```python
def get_series_for_user(user):
    """Devuelve las series documentales disponibles para la oficina del usuario"""
    if not hasattr(user, 'perfil') or not user.perfil.oficina:
        return SerieDocumental.objects.none()
    
    return user.perfil.oficina.series_documentales.all()
```

### 2. Validar que una serie puede ser usada por una oficina

```python
def puede_usar_serie(oficina, serie):
    """Verifica si una oficina puede usar una serie específica"""
    # Si la serie no tiene oficinas asignadas, está disponible para todos
    if not serie.oficinas_productoras.exists():
        return True
    
    # Si tiene oficinas asignadas, verificar si esta oficina está incluida
    return serie.oficinas_productoras.filter(id=oficina.id).exists()
```

### 3. Pre-cargar series en un formulario según la oficina del usuario

```python
class MiFormulario(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'perfil') and user.perfil.oficina:
            # Filtrar series por la oficina del usuario
            self.fields['serie'].queryset = user.perfil.oficina.series_documentales.all()
```

## Administración desde Django Admin

1. Ve al panel de administración: `/admin/`
2. Navega a **Documentos → Series Documentales**
3. Selecciona o crea una serie
4. En la sección "Relación con Oficinas Productoras":
   - Usa el widget dual para seleccionar las oficinas
   - Las oficinas disponibles aparecen a la izquierda
   - Las oficinas asignadas aparecen a la derecha
   - Usa las flechas o doble clic para mover entre listas

## Consultas Optimizadas

Para evitar el problema N+1, usa `prefetch_related`:

```python
# Cargar series con sus oficinas
series = SerieDocumental.objects.prefetch_related('oficinas_productoras')

for serie in series:
    print(f"Serie: {serie.nombre}")
    for oficina in serie.oficinas_productoras.all():
        print(f"  - {oficina.nombre}")
```

## Notas Importantes

1. **Blank=True**: El campo es opcional, una serie puede no tener oficinas asignadas
2. **Tabla intermedia automática**: Django crea automáticamente `documentos_seriedocumental_oficinas_productoras`
3. **Related name**: Desde `OficinaProductora` se accede con `.series_documentales.all()`
4. **Desde Series**: Desde `SerieDocumental` se accede con `.oficinas_productoras.all()`

## Migración Aplicada

✅ Migración: `0019_agregar_relacion_series_oficinas.py`
✅ Estado: Aplicada exitosamente
✅ Tabla creada: `documentos_seriedocumental_oficinas_productoras`
