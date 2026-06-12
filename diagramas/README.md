# 📊 Generador de Diagramas DBML

Script modularizado para generar diagramas de base de datos en formato DBML desde los modelos Django.

## 📁 Estructura

```
diagramas/
├── generar_dbml_modular.py    # Script principal
├── generados/                   # Carpeta de salida
│   ├── diagrama_correspondencia.dbml
│   ├── diagrama_documentos.dbml
│   └── diagrama_general.dbml
└── README.md                   # Este archivo
```

## 🚀 Uso

### Generar todos los diagramas (recomendado)

```bash
cd C:\Users\ingdi\Downloads\correspondencia\07-04\diagramas
python generar_dbml_modular.py
```

Esto generará 3 archivos en la carpeta `generados/`:
- **diagrama_correspondencia.dbml** - Todos los modelos del módulo de correspondencia (449 líneas)
- **diagrama_documentos.dbml** - Todos los modelos del módulo de documentos (325 líneas)
- **diagrama_general.dbml** - Vista simplificada con modelos clave y relaciones principales (147 líneas)

### Generar solo un módulo específico

```bash
# Solo correspondencia
python generar_dbml_modular.py correspondencia

# Solo documentos
python generar_dbml_modular.py documentos

# Solo diagrama general
python generar_dbml_modular.py general
```

## 📋 Próximos Pasos

1. **Abrir los archivos generados** desde la carpeta `generados/`
2. **Copiar el contenido completo** de cada archivo `.dbml`
3. **Ir a https://dbdiagram.io/**
4. **Pegar el código** en el editor izquierdo
5. **Exportar** el diagrama:
   - Menú → Export → PNG (para presentaciones)
   - Menú → Export → PDF (para documentación)
   - Menú → Export → SVG (para edición vectorial)

## 📊 Descripción de los Diagramas

### diagrama_correspondencia.dbml
- **Contenido:** Todos los modelos del módulo de correspondencia
- **Incluye:** Correspondencia, Comunicaciones Internas, Contactos, Entidades Externas, Historiales, etc.
- **Relaciones:** Todas las relaciones ForeignKey y ManyToMany dentro del módulo
- **Tamaño:** ~449 líneas

### diagrama_documentos.dbml
- **Contenido:** Todos los modelos del módulo de documentos
- **Incluye:** FUIDs, Registros de Archivo, Préstamos, Series, Subseries, Oficinas, etc.
- **Relaciones:** Todas las relaciones ForeignKey y ManyToMany dentro del módulo
- **Tamaño:** ~325 líneas

### diagrama_general.dbml
- **Contenido:** Modelos clave y relaciones principales entre módulos
- **Incluye:** Solo los modelos más importantes de cada módulo
- **Relaciones:** Relaciones principales entre correspondencia y documentos
- **Uso:** Ideal para presentaciones y documentación de alto nivel
- **Tamaño:** ~147 líneas

## 🔧 Requisitos

- Python 3.x
- Django configurado con el proyecto
- Módulos `correspondencia` y `documentos` instalados

## 📝 Notas

- Los archivos se generan en formato UTF-8
- Compatible con dbdiagram.io
- Los diagramas incluyen TableGroups para organización visual
- Las relaciones muestran el tipo de `on_delete` cuando aplica

## 🎨 Personalización

Para modificar qué modelos se incluyen en el diagrama general, edita la función `generate_general_dbml()` en el script y ajusta el diccionario `key_models`.




