# 🗺️ GUÍA: Generar Diagrama Visual de Base de Datos

## 🎯 OBJETIVO
Crear un diagrama visual tipo SQL con tablas, campos y relaciones desde tus modelos Django.

---

## ✅ OPCIÓN 1: django-extensions + Graphviz (RECOMENDADO)

### **Paso 1: Instalar Graphviz en Windows**

**Opción A: Descarga directa**
1. Ve a: https://graphviz.org/download/
2. Descarga: "Windows install packages" → `stable_windows_10_cmake_Release_x64_graphviz-install-*.exe`
3. Ejecuta el instalador
4. **IMPORTANTE:** Durante instalación marca "Add Graphviz to system PATH"

**Opción B: Con Chocolatey (si lo tienes)**
```bash
choco install graphviz
```

**Opción C: Con winget**
```bash
winget install graphviz
```

### **Paso 2: Verificar instalación**

Abre PowerShell y ejecuta:
```bash
dot -V
```

Debería mostrar: `dot - graphviz version X.X.X`

Si no funciona, agrega manualmente a PATH:
1. Busca la carpeta de instalación (ej: `C:\Program Files\Graphviz\bin`)
2. Sistema → Configuración avanzada → Variables de entorno
3. PATH → Editar → Agregar la ruta

### **Paso 3: Generar el diagrama**

Abre terminal en tu proyecto y ejecuta:

**Diagrama COMPLETO (todos los modelos):**
```bash
python manage.py graph_models -a -g -o diagrama_completo.png
```

**Diagrama solo CORRESPONDENCIA:**
```bash
python manage.py graph_models correspondencia -g -o diagrama_correspondencia.png
```

**Diagrama solo DOCUMENTOS:**
```bash
python manage.py graph_models documentos -g -o diagrama_documentos.png
```

**Diagrama AMBOS módulos:**
```bash
python manage.py graph_models correspondencia documentos -g -o diagrama_sistema.png
```

**Diagrama en formato DOT (editable):**
```bash
python manage.py graph_models -a -o diagrama.dot
```

### **Paso 4: Opciones adicionales útiles**

**Con colores por app:**
```bash
python manage.py graph_models -a -g --color-code-deletions -o diagrama_colores.png
```

**Sin modelos de Django Admin:**
```bash
python manage.py graph_models -a -g -X ContentType,Permission,Group,Session -o diagrama_limpio.png
```

**Alta resolución (para presentaciones):**
```bash
python manage.py graph_models -a -g --output diagrama_hd.png --settings=hospital_document_management.settings
```

**Formato SVG (escalable):**
```bash
python manage.py graph_models -a -g -o diagrama.svg
```

**Formato PDF:**
```bash
python manage.py graph_models -a -g -o diagrama.pdf
```

### **Opciones del comando:**

| Opción | Descripción |
|--------|-------------|
| `-a` | Todas las apps |
| `-g` | Agrupa por app |
| `--color-code-deletions` | Colorea según on_delete |
| `--arrow-shape normal` | Estilo de flechas |
| `--theme django2018` | Tema visual |
| `-X Model1,Model2` | Excluye modelos |
| `-I Model1,Model2` | Incluye solo estos modelos |
| `--hide-edge-labels` | Oculta labels de relaciones |

---

## 🎨 OPCIÓN 2: ERAlchemy (Alternativa)

Si Graphviz da problemas, usa esta alternativa.

### **Instalación:**
```bash
pip install eralchemy
```

### **Generar diagrama:**
```bash
# Desde settings de Django
eralchemy -i "django://hospital_document_management.settings" -o diagrama_er.png
```

---

## 🖼️ OPCIÓN 3: django-schema-graph

Genera diagramas interactivos HTML.

### **Instalación:**
```bash
pip install django-schema-graph
```

### **Configuración en settings.py:**
```python
INSTALLED_APPS = [
    # ... otras apps
    'schema_graph',
]
```

### **Generar diagrama:**
```bash
python manage.py graph_schema
```

Abre: `http://127.0.0.1:8000/schema/`

---

## 🎯 OPCIÓN 4: Online con dbdiagram.io

Si todo lo demás falla, genera el código para dbdiagram.io

### **Script para generar código DBML:**

Crea archivo `generate_dbml.py`:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_document_management.settings')
django.setup()

from django.apps import apps

def generate_dbml():
    output = []
    
    for model in apps.get_models():
        if model._meta.app_label in ['correspondencia', 'documentos']:
            output.append(f"\nTable {model._meta.db_table} {{")
            
            for field in model._meta.fields:
                field_type = field.get_internal_type()
                field_name = field.name
                
                # Mapear tipos Django a DBML
                type_map = {
                    'AutoField': 'int',
                    'BigAutoField': 'bigint',
                    'CharField': 'varchar',
                    'TextField': 'text',
                    'IntegerField': 'int',
                    'BooleanField': 'boolean',
                    'DateField': 'date',
                    'DateTimeField': 'datetime',
                    'ForeignKey': 'int',
                    'EmailField': 'varchar',
                    'FileField': 'varchar',
                }
                
                dbml_type = type_map.get(field_type, 'varchar')
                
                # Primary Key
                if field.primary_key:
                    output.append(f"  {field_name} {dbml_type} [pk]")
                # Foreign Key
                elif field.many_to_one:
                    output.append(f"  {field_name} {dbml_type} [ref: > {field.related_model._meta.db_table}.id]")
                else:
                    output.append(f"  {field_name} {dbml_type}")
            
            output.append("}")
    
    return '\n'.join(output)

if __name__ == '__main__':
    dbml = generate_dbml()
    with open('database_schema.dbml', 'w', encoding='utf-8') as f:
        f.write(dbml)
    print("✅ Archivo database_schema.dbml generado!")
    print("📋 Copia el contenido en https://dbdiagram.io/")
```

### **Ejecutar:**
```bash
python generate_dbml.py
```

Luego:
1. Abre el archivo `database_schema.dbml`
2. Copia todo el contenido
3. Ve a https://dbdiagram.io/
4. Pega el código
5. Exporta como imagen

---

## 🚀 DIAGRAMA RECOMENDADO PARA PRESENTACIÓN

### **Comando sugerido:**

```bash
python manage.py graph_models correspondencia documentos -g --color-code-deletions --theme django2018 -o diagrama_presentacion.png
```

**Esto genera:**
- ✅ Solo tus módulos (sin Django admin)
- ✅ Agrupado por app
- ✅ Con colores por tipo de relación
- ✅ Tema moderno
- ✅ Alta calidad

---

## 🎨 PERSONALIZACIÓN DEL DIAGRAMA

### **Crear archivo `graph_settings.py`:**

```python
GRAPH_MODELS = {
    'all_applications': False,
    'group_models': True,
    'app_labels': ['correspondencia', 'documentos'],
    'exclude_models': ['ContentType', 'Permission', 'Group', 'Session', 'LogEntry'],
    'output': 'diagrama_custom.png',
    'layout': 'dot',  # dot, neato, fdp, sfdp, circo, twopi
    'theme': 'django2018',
    'verbose_names': True,
    'color_code_deletions': True,
    'arrow_shape': 'normal',
}
```

### **Usar:**
```bash
python manage.py graph_models --pydot --settings=graph_settings.py
```

---

## 📊 EJEMPLO DE SALIDA

El diagrama mostrará:

```
┌─────────────────────────────┐
│   Correspondencia           │
├─────────────────────────────┤
│ id (PK)                     │
│ numero_radicado (UK)        │
│ fecha_radicacion            │
│ asunto                      │
│ remitente_id (FK) ────────┐ │
│ oficina_destino_id (FK) ──┼─┼──> OficinaProductora
│ serie_id (FK) ────────────┼─┼──> SerieDocumental
└───────────────────────────┼─┘
                            │
                            ▼
                ┌───────────────────┐
                │   Contacto        │
                ├───────────────────┤
                │ id (PK)           │
                │ nombres           │
                │ correo_electronico│
                └───────────────────┘
```

---

## 🎯 TROUBLESHOOTING

### **Error: "dot not found in PATH"**
**Solución:** Instala Graphviz y agrégalo al PATH

### **Error: "No module named 'pydot'"**
**Solución:**
```bash
pip install pydotplus
```

### **El diagrama es muy grande**
**Solución:** Genera por módulo separado:
```bash
python manage.py graph_models correspondencia -o corresp.png
python manage.py graph_models documentos -o docs.png
```

### **Imagen muy pequeña/borrosa**
**Solución:** Usa SVG o PDF:
```bash
python manage.py graph_models -a -g -o diagrama.svg
```

---

## ✨ RESULTADO FINAL

Después de ejecutar el comando, tendrás:

📁 `diagrama_presentacion.png` - Imagen visual de alta calidad con:
- Tablas con todos los campos
- Relaciones con flechas
- Colores por tipo
- Agrupado por módulo
- Listo para insertar en PowerPoint/Google Slides

---

## 🎬 SIGUIENTE PASO

1. **Instala Graphviz** (si no lo tienes)
2. **Ejecuta el comando recomendado**
3. **Abre la imagen** generada
4. **Inserta en tu presentación**

**¿Listo para generar tu diagrama?** 🚀

