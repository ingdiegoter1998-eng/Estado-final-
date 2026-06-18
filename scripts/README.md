# Scripts auxiliares

Scripts puntuales de mantenimiento y utilidades. No forman parte del runtime de Gunicorn/Celery.

Ejecutar desde la raíz: `venv/bin/python scripts/mantenimiento/check_faltantes.py`

| Carpeta | Contenido |
|---------|-----------|
| `mantenimiento/` | Oficinas, duplicados, IMAP ad hoc |
| `utilidades/` | Parches puntuales de templates/UI |
| `sql/` | Consultas SQL sueltas |
| `legacy/` | `.bat` / `.ps1` históricos |

Despliegue operativo: preferir `deploy/scripts/`.
