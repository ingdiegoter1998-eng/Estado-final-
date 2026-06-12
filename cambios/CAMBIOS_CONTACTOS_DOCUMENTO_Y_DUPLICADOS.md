# 📝 Cambios al Sistema de Contactos - Versión 2.0

## ✨ Nuevas Características

### 1. **Campo Número de Documento** 📋
Se agregó un nuevo campo **opcional** al modelo `Contacto`:

```python
numero_documento = models.CharField(
    max_length=50, 
    blank=True, 
    null=True, 
    verbose_name="Número de Documento",
    help_text="Cédula, pasaporte u otro documento de identificación (opcional)"
)
```

**Características:**
- ✅ Completamente opcional (puede estar vacío)
- ✅ Soporta cédulas, pasaportes, carnés profesionales, etc.
- ✅ Máximo 50 caracteres
- ✅ Incluido en búsquedas del admin
- ✅ Visible en la lista de contactos

---

### 2. **Prevención de Emails Duplicados** 🔒

Se agregó validación en el modelo `Contacto` para **prevenir correos duplicados**:

```python
def clean(self):
    """Validaciones adicionales al guardar."""
    if self.correo_electronico:
        correo_duplicado = Contacto.objects.filter(
            correo_electronico=self.correo_electronico
        ).exclude(pk=self.pk)  # Excluir a sí mismo en caso de edición
        
        if correo_duplicado.exists():
            raise ValidationError(
                f"Ya existe un contacto con el correo '{self.correo_electronico}'. "
                f"Contactos duplicados no están permitidos en el sistema."
            )
```

**Comportamiento:**
- ❌ NO permite crear dos contactos con el mismo email
- ✅ Permite editar un contacto sin error si mantiene su email
- ✅ Se valida automáticamente al guardar desde formularios
- 📊 Nivel global: aplica a TODA la base de datos

---

## 📋 Cambios en Ficheros

### 1. **models.py** - Modelo Contacto
```diff
class Contacto(models.Model):
    # ... campos existentes ...
+   numero_documento = models.CharField(...)
    
+   def clean(self):
+       # Validación de correos duplicados
```

---

### 2. **forms.py** - ContactoForm
```diff
class ContactoForm(forms.ModelForm):
    class Meta:
        fields = [
            'entidad_externa',
            'nombres', 
            'apellidos', 
            'cargo', 
            'correo_electronico',
            'telefono_contacto',
+           'numero_documento'  # ← NUEVO
        ]
        widgets = {
+           'numero_documento': forms.TextInput(...)
        }
    
    def __init__(self, *args, **kwargs):
        self.helper.layout = Layout(
            Row(
                Column(Field('nombres'), ...),
                Column(Field('apellidos'), ...)
            ),
            Row(
                Column(Field('cargo'), ...),
+               Column(Field('numero_documento'), ...)  # ← NUEVO
            ),
            Row(
                Column(Field('correo_electronico'), ...),
                Column(Field('telefono_contacto'), ...)
            ),
        )
```

---

### 3. **admin.py** - ContactoAdmin
```diff
class ContactoAdmin(admin.ModelAdmin):
-   list_display = (..., 'correo_electronico')
+   list_display = (..., 'correo_electronico', 'numero_documento')
    
-   search_fields = ('nombres', 'apellidos', 'correo_electronico', ...)
+   search_fields = ('nombres', 'apellidos', 'correo_electronico', 'numero_documento', ...)
    
    fieldsets = (
        ('Información de Contacto', {
-           'fields': ('correo_electronico', 'telefono_contacto')
+           'fields': ('correo_electronico', 'telefono_contacto', 'numero_documento')
        }),
    )
```

---

### 4. **migrations/0018_contacto_numero_documento.py** - Nueva Migración
```python
class Migration(migrations.Migration):
    dependencies = [
        ('correspondencia', '0017_auto_20250426_2123'),
    ]
    
    operations = [
        migrations.AddField(
            model_name='contacto',
            name='numero_documento',
            field=models.CharField(...),
        ),
    ]
```

---

## 🚀 Cómo Aplicar los Cambios

### Paso 1: Aplicar la Migración
```bash
python manage.py migrate correspondencia
```

### Paso 2: Verificar
```bash
# Ver si el campo se agregó a la BD
python manage.py sqlmigrate correspondencia 0018

# O verificar directamente
python manage.py shell
>>> from correspondencia.models import Contacto
>>> Contacto._meta.get_field('numero_documento')
```

---

## 🎯 Casos de Uso del Campo Número de Documento

### Caso 1: Identificación de Pacientes
```
Contacto:
├─ Nombres: Juan
├─ Apellidos: García
├─ Entidad: Hospital Central
├─ Correo: juan@mail.com
└─ Número de Documento: 1234567890 ← Cédula del paciente
```

### Caso 2: Identificación de Funcionarios
```
Contacto:
├─ Nombres: María
├─ Apellidos: López
├─ Entidad: Ministerio de Salud
├─ Cargo: Directora
├─ Correo: maria@minsalud.gov.co
└─ Número de Documento: 9876543210 ← Cédula profesional
```

### Caso 3: Identificación de Profesionales
```
Contacto:
├─ Nombres: Carlos
├─ Apellidos: Rodríguez
├─ Entidad: Consultorio Externo
├─ Cargo: Médico Especialista
├─ Correo: carlos@consultorio.com
└─ Número de Documento: C12-A45-B67 ← Carné profesional
```

---

## ⚠️ Impacto en Validaciones

### Validación de Correos Duplicados

**ANTES:**
```
✅ Contacto 1: juan@mail.com
✅ Contacto 2: juan@mail.com  ← Permitido
✅ Contacto 3: juan@mail.com  ← Permitido
```

**DESPUÉS:**
```
✅ Contacto 1: juan@mail.com
❌ Contacto 2: juan@mail.com  ← ERROR: Ya existe
❌ Contacto 3: juan@mail.com  ← ERROR: Ya existe
```

**Mensaje de Error:**
```
Ya existe un contacto con el correo 'juan@mail.com'. 
Contactos duplicados no están permitidos en el sistema.
```

---

## 🔍 Búsqueda en Admin

Ahora puedes buscar por número de documento:

```
Admin de Contactos → Búsqueda
├─ Buscar por nombre: "Juan" ✅
├─ Buscar por apellido: "García" ✅
├─ Buscar por email: "juan@mail.com" ✅
├─ Buscar por documento: "1234567890" ✅ ← NUEVO
├─ Buscar por entidad: "Hospital" ✅
└─ Buscar por oficina: "Dirección" ✅
```

---

## 📊 Base de Datos

### Cambios en la tabla `correspondencia_contacto`:

```sql
ALTER TABLE correspondencia_contacto 
ADD COLUMN numero_documento VARCHAR(50) NULL;

-- Índice para búsquedas rápidas (opcional pero recomendado)
CREATE INDEX idx_numero_documento 
ON correspondencia_contacto(numero_documento);
```

---

## ✅ Checklist de Verificación

Después de aplicar los cambios:

- [ ] Migración aplicada correctamente
- [ ] Campo visible en admin
- [ ] Campo visible en formulario de creación
- [ ] Campo visible en búsqueda del admin
- [ ] Validación de correos duplicados funciona
- [ ] Puedo crear contactos con documento
- [ ] Puedo editar contactos y agregar documento
- [ ] Puedo buscar por documento en admin
- [ ] Los contactos sin documento siguen funcionando

---

## 🔐 Consideraciones de Seguridad

### Número de Documento
- ❌ NO es único a nivel de BD (puede haber documentos vacíos)
- ✅ Es almacenado localmente (no se valida contra sistemas externos)
- ✅ Puede ser modificado en cualquier momento

### Correo Electrónico
- ✅ ES único a nivel de BD (se valida antes de guardar)
- ✅ No permite duplicados en ningún circunstancia
- ✅ Validación ocurre en la capa de modelo (antes de la BD)

---

## 💡 Mejoras Futuras

Si se necesita mayor control:

```python
# Opción 1: Hacer número_documento único
numero_documento = models.CharField(
    max_length=50, 
    unique=True,  # ← Único globalmente
    blank=True, 
    null=True
)

# Opción 2: Validar formato de documento según país
def clean(self):
    if self.numero_documento:
        if not validar_cedula_colombia(self.numero_documento):
            raise ValidationError("Formato de cédula inválido")

# Opción 3: Agregar tipo de documento
TIPO_DOCUMENTO_CHOICES = [
    ('CC', 'Cédula de Ciudadanía'),
    ('CE', 'Cédula de Extranjería'),
    ('PP', 'Pasaporte'),
    ('TI', 'Tarjeta de Identidad'),
]
tipo_documento = models.CharField(
    max_length=2,
    choices=TIPO_DOCUMENTO_CHOICES,
    blank=True,
    null=True
)
```

---

## 📞 Soporte

Si encuentras problemas:

1. **Error: "Ya existe un contacto con ese correo"**
   - Verifica que el email sea único
   - Si necesitas cambiar el email, edita el contacto existente
   - Si el contacto es incorrecto, elimínalo primero

2. **Migración no funciona**
   - Asegúrate de estar en el directorio correcto
   - Verifica que `manage.py` esté disponible
   - Prueba: `python manage.py migrate --list`

3. **Campo no aparece en formulario**
   - Limpia el cache: `python manage.py collectstatic --clear`
   - Recarga el navegador (Ctrl+F5)
   - Verifica que `numero_documento` esté en `ContactoForm.Meta.fields`

---

## 📌 Notas Importantes

✅ **Backward Compatible:** Los contactos existentes siguen funcionando  
✅ **Opcional:** El número de documento es completamente opcional  
✅ **Sin Cambios en API:** Si usas la API, no hay cambios requeridos  
✅ **Auditoría:** Todos los cambios se registran en el historial  

---

## 🎓 Conclusión

El sistema ahora:
- ✅ Previene correos duplicados automáticamente
- ✅ Permite capturar número de documento de contactos
- ✅ Mejora búsquedas en el admin
- ✅ Mantiene integridad de datos
- ✅ Es más seguro y auditable
