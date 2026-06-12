# Instrucciones para agentes (Cursor / Claude)

Antes de improvisar en este repositorio, **elige y lee la skill del proyecto** que corresponda a la tarea.

## Punto de entrada (obligatorio)

1. Abre [`.github/skills/indice-skills/SKILL.md`](.github/skills/indice-skills/SKILL.md) — índice maestro con palabras clave y rutas.
2. Carga la skill indicada y síguela de principio a fin.

## Dónde están las skills

| Ubicación | Contenido |
|-----------|-----------|
| [`.github/skills/`](.github/skills/) | Skills del dominio correspondencia (correos, rebotes, UI, tests, asistente IA) |
| [`.claude/skills/`](.claude/skills/) | Skills genéricas (Playwright, pytest, accesibilidad, SEO, frontend) |
| [`CLAUDE.md`](CLAUDE.md) | Resumen autoskills para Claude Code |

## Producción vs desarrollo (correo y BD)

| Entorno | URL | Django | Base de datos |
|---------|-----|--------|---------------|
| **Producción** | `http://<vm>/` y `/monitoreo` | `hospital_document_management.settings` (Gunicorn systemd) | SQL Server `GestionDocumental` |
| Dev SQLite | `:8001` o `settings_local` | `settings_dev_sqlite` / `settings_local` | `db_dev.sqlite3` — no usar en VM prod |

Comando de verificación: `python manage.py gmail_operational_status`

Detener servidores dev que interfieren: `bash deploy/scripts/stop_dev_interference.sh`

## Frases que activan skills

- Correos / sincronización / Celery → `correos-tareas-operativas`
- Rebotes / DSN → `rebotes-dsn-depuracion`
- Tests / pytest → `testing-correspondencia` o `.claude/skills/python-testing-patterns/`
- Playwright E2E → `.claude/skills/playwright-best-practices/`
- UI / templates → `correspondencia-ui-line`
