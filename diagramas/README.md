# Diagramas de base de datos y modelos

## Estructura

| Carpeta / archivo | Uso |
|-------------------|-----|
| `generados/diagrama_comunicaciones_internas.dbml` | Oficios entre dependencias (~20 tablas) |
| `generados/diagrama_correspondencia_externa.dbml` | Radicación entrante/salida, contactos, correo (~46 tablas) |
| `generados/diagrama_prestamos_documentales.dbml` | Préstamos de expedientes (~25 tablas) |
| `generados/diagrama_completo.dbml` | Esquema total — **muy pesado para dbdiagram.io** |
| `legacy/` | Snapshots históricos manuales |
| `modelos/` | Mapas Mermaid en Markdown |
| `flujogramas/` | Flujos operativos |

## Visualizar en dbdiagram.io

Importar **un archivo modular** (no el completo) en [dbdiagram.io](https://dbdiagram.io/d):

1. **Comunicaciones internas** → `generados/diagrama_comunicaciones_internas.dbml`
2. **Correspondencia externa** → `generados/diagrama_correspondencia_externa.dbml`
3. **Préstamos documentales** → `generados/diagrama_prestamos_documentales.dbml`

## Regenerar (recomendado)

```bash
bash diagramas/generar_diagramas_modulares.sh
```

Incluye siempre `auth` y `contenttypes` (FK a `auth_user`) y las tablas `documentos` referenciadas por cada módulo.

## Esquema completo (solo referencia técnica)

```bash
venv/bin/python manage.py dbml auth contenttypes documentos correspondencia \
  --table_names --group_by_app \
  --add_project_name "Sistema Gestion Documental y Correspondencia" \
  --output_file diagramas/generados/diagrama_completo.dbml
```

No usar en dbdiagram.io si el navegador no termina de renderizar (~80 tablas).

Diccionario de datos: [`manual tecnico/DICCIONARIO_DATOS.md`](../manual%20tecnico/DICCIONARIO_DATOS.md)
