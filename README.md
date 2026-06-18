# Sistema de Gestión de Correspondencia - Hospital del Sarare

Sistema web para la gestión integral de correspondencia entrante, saliente, comunicaciones internas, urgencias y trazabilidad documental del Hospital del Sarare E.S.E.

El proyecto está construido sobre Django y Celery, con operación productiva en una VM Linux usando Gunicorn, Nginx, Redis y SQL Server. Para desarrollo local se recomienda usar SQLite mediante `settings_local.py`.

**Última revisión:** 2026-06-18

---

## Estado Actual del Proyecto

| Área | Estado actual |
|------|---------------|
| Backend principal | Django 5.0.14 con `hospital_document_management.settings` |
| Producción | Gunicorn + Nginx + SQL Server `GestionDocumental` |
| Desarrollo local | `hospital_document_management.settings_local` con `db_dev.sqlite3` |
| Tareas en segundo plano | Celery worker + Celery Beat + Redis |
| Correo entrante | IMAP o Gmail API, según `EMAIL_INGESTION_PROVIDER` |
| Correo saliente | SMTP, Gmail API o Postmark, según `EMAIL_PROVIDER` |
| Monitoreo operativo | App Next.js bajo `/monitoreo` |
| Calendario de planillas | App Next.js bajo `/calendario` |
| Tests | Pytest + Playwright E2E |

Fuentes de verdad:

- Producción y servicios: [`deploy/README.md`](deploy/README.md)
- Despliegue sin tumbar producción: [`deploy/DEPLOY_SEGURO.md`](deploy/DEPLOY_SEGURO.md)
- Variables de entorno base: [`deploy/env/.env.example`](deploy/env/.env.example)
- Índice de documentación técnica: [`documentacion/README_INDEX.md`](documentacion/README_INDEX.md)
- Índice maestro correspondencia: [`documentacion/indices/INDICE_MAESTRO_CORRESPONDENCIA.md`](documentacion/indices/INDICE_MAESTRO_CORRESPONDENCIA.md)
- Instrucciones para agentes IA: [`AGENTS.md`](AGENTS.md)

### Estructura del repositorio

| Carpeta | Propósito |
|---------|-----------|
| `correspondencia/`, `documentos/` | Apps Django |
| `deploy/` | Producción, systemd, scripts de despliegue |
| `scripts/` | Utilidades y mantenimiento ad hoc (no runtime) |
| `diagramas/`, `manual tecnico/` | Modelos, DBML y diccionario de datos |
| `documentacion/`, `guias/`, `reportes/`, `analisis/` | Documentación por tema |
| `documentacion/normativa/`, `documentacion/imap/` | Normativa legal e integración IMAP |
| `data/` | CSV y datos de referencia (`data/trd/`, `data/historias_clinicas/`) |
| `archivos afuera/` | Trabajo operativo local (gitignored) |
| `media/` | Adjuntos y uploads (gitignored) |

---

## Funcionalidades Principales

- Radicación automática con consecutivos únicos para correspondencia entrante y saliente.
- Bandejas de ventanilla, usuario, oficina, interoficina, urgencias y pendientes.
- Procesamiento de correos entrantes por IMAP o Gmail API.
- Flujo de respuestas con aprobación, envío, seguimiento y evidencia de entrega.
- Comunicaciones internas con aprobación, firma digital y trazabilidad.
- Cálculo automático de SLA con días hábiles, festivos y tipos de trámite.
- Seguimiento de rebotes, estados de entrega, Postmark webhooks y auditoría de destinatarios.
- Panel de monitoreo operativo en Next.js para métricas, salidas y entradas de correo.
- Asistente IA documental con RAG, Gemini y pruebas dedicadas.
- Historial completo de acciones para auditoría.

---

## Requisitos

| Requisito | Versión / nota |
|-----------|----------------|
| Python | 3.12 recomendado; 3.10+ mínimo |
| Redis | 6.0+ para Celery |
| SQL Server | Producción |
| SQLite | Desarrollo local |
| Node.js / npm | Apps Next.js y Playwright |
| Git | 2.0+ |

---

## Inicio Rápido en Desarrollo Local

Producción usa SQL Server con `hospital_document_management.settings`. Para no tocar datos productivos, usa `settings_local.py` y SQLite.

```bash
git clone https://github.com/Magicyasuo/Correspondencia-diciembre-1.0
cd Correspondencia-diciembre-1.0

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp hospital_document_management/settings_local.example.py hospital_document_management/settings_local.py
export DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local

python manage.py migrate
python manage.py poblar_vida_demo --confirm
python manage.py runserver 8001
```

La aplicación local queda disponible en `http://127.0.0.1:8001/`.

Guía completa: [`documentacion/POBLADO_DESARROLLO_SQLITE.md`](documentacion/POBLADO_DESARROLLO_SQLITE.md)

---

## Producción

La VM de producción corre con:

- Django/Gunicorn: `correspondencia.service`
- Nginx: proxy y archivos estáticos
- Celery worker: `correspondencia-celery-worker.service`
- Celery Beat: `correspondencia-celery-beat.service`
- Monitoreo Next.js: `correspondencia-monitoreo.service`
- Calendario Next.js: `correspondencia-nextjs.service`
- Base de datos: SQL Server `GestionDocumental`

Accesos principales:

| Ruta | Uso |
|------|-----|
| `http://192.168.3.230/` | Aplicación Django en intranet |
| `/registros/login/` | Login del sistema |
| `/monitoreo` | Monitoreo operativo Next.js |
| `/calendario` | Calendario de planillas |

### Despliegue Seguro

Para cambios de código Django/Celery/estáticos en la misma carpeta de producción:

```bash
cd /home/devdiego/Correspondencia-diciembre-1.0
./deploy/scripts/safe_deploy.sh
```

Este flujo hace respaldo, `manage.py check`, migraciones solo si `.env` tiene credenciales SQL, `collectstatic`, HUP a Gunicorn y reinicio controlado del pool de Celery cuando aplica.

Importante: si `.env` no tiene `DB_USER` y `DB_PASSWORD`, evita `systemctl restart correspondencia` hasta restaurar credenciales. Ver [`deploy/DEPLOY_SEGURO.md`](deploy/DEPLOY_SEGURO.md).

### Servicios y Logs

```bash
sudo systemctl status correspondencia
sudo systemctl status correspondencia-celery-worker correspondencia-celery-beat
sudo systemctl status correspondencia-monitoreo correspondencia-nextjs
sudo systemctl status nginx

sudo journalctl -u correspondencia -f
sudo journalctl -u correspondencia-celery-worker -f
sudo journalctl -u correspondencia-monitoreo -f
```

### Dimensionamiento Actual

El servicio Gunicorn versionado está configurado para una VM de 4 vCPU y ~8 GiB RAM:

```ini
--worker-class gthread --workers 6 --threads 3 --timeout 90
```

Esto da 18 slots HTTP concurrentes antes de colas en Gunicorn. Revisa [`deploy/systemd/correspondencia.service`](deploy/systemd/correspondencia.service) y [`deploy/README.md`](deploy/README.md) antes de cambiar workers o threads.

---

## Correo y Celery

El sistema soporta tres caminos de correo:

| Variable | Valores comunes | Uso |
|----------|-----------------|-----|
| `EMAIL_PROVIDER` | `smtp`, `gmail_api`, `postmark` | Envío saliente |
| `EMAIL_INGESTION_PROVIDER` | `imap`, `gmail_api` | Ingesta entrante |
| `EMAIL_HOST_*` | SMTP/IMAP Gmail | Fallback SMTP e IMAP manual |
| `GMAIL_API_*` | OAuth, Pub/Sub, history sync | Pipeline Gmail API |
| `POSTMARK_*` | token, stream, webhook | Envío y evidencia de entrega |

La plantilla operativa de `.env` está en [`deploy/env/.env.example`](deploy/env/.env.example).

### Tareas Programadas Base

Fuente: `CELERY_BEAT_SCHEDULE` en [`hospital_document_management/settings.py`](hospital_document_management/settings.py).

| Tarea | Intervalo por defecto | Descripción |
|-------|-----------------------|-------------|
| `procesar_emails_periodico` | `CELERY_EMAIL_CHECK_INTERVAL=300` | Procesa correo entrante por el pipeline configurado |
| `procesar_rebotes_periodico` | 600 s | Procesa rebotes DSN |
| `sincronizar_entregas_postmark_periodico` | 900 s | Sincroniza eventos de entrega de Postmark |
| `precalentar_cache_sla_periodico` | 240 s | Precalienta cache de SLA para evitar consultas lentas |
| `actualizar_urgencias_pendientes` | 1800 s | Actualiza vencimientos de urgencias |
| `escalar_urgencias_criticas` | 3600 s | Escala urgencias críticas |
| `aprobar_y_enviar_respuestas_pendientes_periodico` | `CELERY_APROBAR_RESPUESTAS_INTERVAL=180` | Aprueba y envía respuestas pendientes configuradas |
| `watchdog_inbox` | `CELERY_IMAP_WATCHDOG_INTERVAL=900` | Vigila INBOX por IMAP cuando aplica |

Si `EMAIL_INGESTION_PROVIDER=gmail_api`, se agregan:

| Tarea | Intervalo por defecto | Descripción |
|-------|-----------------------|-------------|
| `gmail_pubsub_pull_periodico` | `CELERY_GMAIL_PUBSUB_PULL_INTERVAL=90` | Consume mensajes Pub/Sub de Gmail |
| `gmail_watch_renew_periodico` | `CELERY_GMAIL_WATCH_RENEW_INTERVAL=21600` | Renueva Gmail Watch |
| `procesar_emails_periodico` | `CELERY_GMAIL_BACKUP_POLL_INTERVAL=1800` | Poll de respaldo |

Cuando `CELERY_DISABLE_WATCHDOG_WHEN_GMAIL_API=true`, el watchdog IMAP se desactiva para evitar duplicar presión sobre Gmail.

### Comandos Operativos de Correo

```bash
python manage.py gmail_operational_status
python manage.py procesar_emails_seguro
python manage.py procesar_emails_seguro --recovery --days 7
python manage.py procesar_rebotes
python manage.py gmail_history_sync
python manage.py gmail_pubsub_pull
python manage.py postmark_webhook_status
python manage.py postmark_sync_delivery_events
```

Si hay errores 429 de Gmail API, usa la skill/documentación de rate limit antes de reintentar en bucle. No ejecutes `gmail_operational_status` repetidamente durante cooldown.

---

## Estructura del Proyecto

```text
hospital_document_management/      # Configuración Django, Celery, URLs, WSGI/ASGI
correspondencia/                   # App principal de radicación, bandejas, correo y monitoreo
documentos/                        # Gestión documental base
monitoreo-nextjs/                  # Frontend Next.js para /monitoreo
calendario-informes-nextjs/        # Frontend Next.js para /calendario
deploy/                            # Systemd, Nginx, scripts, env examples y guías de despliegue
documentacion/                     # Documentación técnica y funcional
diagramas/                         # Diagramas DBML y flujogramas
manual tecnico/                    # Manuales técnicos históricos
correspondencia/tests/             # Pytest y Playwright E2E
```

---

## Modelo de Datos Principal

| Modelo | Descripción |
|--------|-------------|
| `Correspondencia` | Correspondencia entrante |
| `CorrespondenciaSalida` | Respuestas y comunicaciones salientes |
| `CorreoEntrante` | Correos pendientes de radicar |
| `Contacto` | Contactos externos |
| `EntidadExterna` | Empresas e instituciones externas |
| `ComunicacionInterna` | Oficios entre oficinas |
| `HistorialCorrespondencia` | Auditoría y trazabilidad |
| `Notificacion` | Alertas del sistema |
| `GrupoAgenda` | Grupos para envíos masivos |

Diagramas y flujogramas:

- [`diagramas/`](diagramas/)
- [`diagramas/flujogramas/flujograma_correspondencia_mejorado.md`](diagramas/flujogramas/flujograma_correspondencia_mejorado.md)

---

## Flujos Principales

### Correspondencia Entrante

```text
Documento físico o email -> Radicación -> Cálculo SLA -> Asignación -> Respuesta -> Envío -> Evidencia
```

### Correspondencia Saliente

```text
Borrador -> Adjuntos -> Aprobación -> Envío por proveedor configurado -> Seguimiento de entrega/rebote
```

### Comunicaciones Internas

```text
Oficio interno -> Revisión/Aprobación -> Firma digital si aplica -> Distribución -> Trazabilidad
```

### Urgencias

```text
Radicación de urgencia -> Seguimiento por tiempo transcurrido -> Vencimiento -> Escalamiento
```

---

## Comandos Útiles

### Django

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py verificar_sla
python manage.py indexar_asistente_docs
```

### Desarrollo Local

```bash
export DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local
python manage.py poblar_vida_demo --confirm
python manage.py runserver 8001
```

### Evitar Interferencia en Producción

En la VM productiva, antes de revisar problemas reales de correo o servicios, detén servidores de desarrollo que puedan interferir:

```bash
bash deploy/scripts/stop_dev_interference.sh
```

---

## Tests

Los tests Python usan `pytest` con `hospital_document_management.settings_test`, SQLite en memoria, cache local y Celery eager.

```bash
python -m pytest
python -m pytest --no-cov
python -m pytest correspondencia/tests/test_watchdog_inbox.py -v
python -m pytest correspondencia/tests/test_gmail_api_pubsub.py -v
python -m pytest correspondencia/tests/test_postmark_webhooks.py -v
```

Áreas cubiertas por tests:

- Gmail API, Pub/Sub, OAuth, history sync e INBOX.
- IMAP, watchdog, locks y procesamiento periódico.
- Postmark backend, webhooks, entregas y detalles de mensajes.
- Radicación rápida, bandejas, SLA, urgencias y aprobaciones.
- Chatbot/asistente IA.
- Monitoreo operativo de entradas y salidas de correo.

### Playwright E2E

La configuración está en [`playwright.config.ts`](playwright.config.ts) y usa `correspondencia/tests/e2e` con `E2E_BASE_URL` por defecto en `http://127.0.0.1:8001`.

```bash
npx playwright test
E2E_BASE_URL=http://127.0.0.1:8001 npx playwright test
```

Antes de modificar tests, consulta:

- [`.github/skills/testing-correspondencia/SKILL.md`](.github/skills/testing-correspondencia/SKILL.md)
- [`.claude/skills/playwright-best-practices/SKILL.md`](.claude/skills/playwright-best-practices/SKILL.md)

---

## Variables de Entorno

No documentes secretos reales en el README. Usa [`deploy/env/.env.example`](deploy/env/.env.example) como plantilla.

| Grupo | Variables principales |
|-------|-----------------------|
| Django | `SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS` |
| SQL Server | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| Celery/Redis | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| SMTP/IMAP | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `IMAP_*` |
| Proveedores | `EMAIL_PROVIDER`, `EMAIL_INGESTION_PROVIDER` |
| Gmail API | `GMAIL_API_CLIENT_ID`, `GMAIL_API_REFRESH_TOKEN`, `GMAIL_API_PUBSUB_*` |
| Postmark | `POSTMARK_SERVER_TOKEN`, `POSTMARK_MESSAGE_STREAM`, `POSTMARK_WEBHOOK_*` |
| Identidad saliente | `OUTBOUND_EMAIL_ADDRESS`, `OUTBOUND_EMAIL_NAME`, `EMAIL_MESSAGE_ID_DOMAIN` |
| Rate limit | `CELERY_PAUSE_GMAIL_API_TASKS`, `GMAIL_API_RATE_LIMIT_COOLDOWN_BUFFER_SECONDS` |

---

## Documentación

| Documento | Uso |
|-----------|-----|
| [`documentacion/README_INDEX.md`](documentacion/README_INDEX.md) | Índice general de documentación técnica |
| [`documentacion/RESUMEN_APLICATIVO_CORRESPONDENCIA.md`](documentacion/RESUMEN_APLICATIVO_CORRESPONDENCIA.md) | Resumen funcional y técnico |
| [`documentacion/GUIA_SEGURIDAD_CIBERNETICA.md`](documentacion/GUIA_SEGURIDAD_CIBERNETICA.md) | Guía de seguridad |
| [`documentacion/POBLADO_DESARROLLO_SQLITE.md`](documentacion/POBLADO_DESARROLLO_SQLITE.md) | Desarrollo local con SQLite |
| [`documentacion/ASISTENTE_IA_CAMBIOS_RESPUESTAS_Y_TESTS_2026-03-28_164033.md`](documentacion/ASISTENTE_IA_CAMBIOS_RESPUESTAS_Y_TESTS_2026-03-28_164033.md) | Cambios y validación del asistente IA |
| [`deploy/README.md`](deploy/README.md) | Operación y servicios de producción |
| [`deploy/DEPLOY_SEGURO.md`](deploy/DEPLOY_SEGURO.md) | Despliegue sin restart completo |
| [`deploy/scripts/USER_ACTION_GMAIL_PUBSUB.md`](deploy/scripts/USER_ACTION_GMAIL_PUBSUB.md) | Acciones manuales Gmail Pub/Sub |
| [`deploy/scripts/USER_ACTION_POSTMARK.md`](deploy/scripts/USER_ACTION_POSTMARK.md) | Acciones manuales Postmark |

---

## Trabajo con Agentes IA

Antes de implementar o diagnosticar en este repositorio:

1. Lee [`AGENTS.md`](AGENTS.md).
2. Consulta [`.github/skills/indice-skills/SKILL.md`](.github/skills/indice-skills/SKILL.md).
3. Carga la skill que corresponda: correos, rebotes, UI, tests, Playwright, asistente IA, etc.

No improvises flujos operativos de Gmail, Postmark, Celery o producción si ya existe una skill o guía.

---

## Tecnologías

- Backend: Django 5.0.14, Python, Django REST Framework.
- Frontend Django: Bootstrap 5, AdminLTE 3, HTMX.
- Frontend separado: Next.js para monitoreo y calendario.
- Base de datos: SQL Server en producción, SQLite en desarrollo local y tests.
- Tareas: Celery + Redis.
- Correo: SMTP/IMAP Gmail, Gmail API, Pub/Sub y Postmark.
- Seguridad: django-allauth, django-axes, restricciones Nginx de intranet.
- Testing: pytest, pytest-django, Playwright.

---

## Licencia y Contacto

Desarrollado para el Hospital del Sarare E.S.E.

Todos los derechos reservados © 2026.

Para soporte técnico o consultas, contactar al equipo de desarrollo.
