# Diagramas de base de datos y modelos

## Estructura

- `generados/` — DBML canónico (regenerable con `manage.py dbml`)
- `legacy/` — snapshots históricos
- `modelos/` — mapas Mermaid en Markdown
- `flujogramas/` — flujos operativos

Regenerar:

```bash
venv/bin/python manage.py dbml documentos correspondencia --table_names --group_by_app \
  --output_file diagramas/generados/diagrama_completo.dbml
```

Visualizar en [dbdiagram.io](https://dbdiagram.io/).

Diccionario de datos: [`manual tecnico/DICCIONARIO_DATOS.md`](../manual%20tecnico/DICCIONARIO_DATOS.md)
