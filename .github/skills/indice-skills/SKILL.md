---
name: indice-skills
description: 'Indice maestro de todas las skills del proyecto de correspondencia. Consultar SIEMPRE como primer paso para identificar que skill especializada cargar segun la tarea del usuario. Activar con cualquier peticion que no encaje claramente en una skill existente, o cuando se necesite orientacion sobre que skill usar. Palabras gatillo: que skill, cual skill, como trabajo esto, donde esta, orientame, no se por donde empezar.'
argument-hint: 'Describe la tarea o problema para que el indice te dirija a la skill correcta'
user-invocable: true
disable-model-invocation: false
---

# Indice Maestro de Skills

## Para que Existe

Este archivo es el punto de entrada para descubrir, seleccionar y combinar las skills
especializadas del proyecto de correspondencia del Hospital E.S.E. Sarare.

Regla principal: **antes de actuar, consultar este indice para identificar si ya existe
una skill que cubre la tarea**. Si existe, cargarla y seguir sus instrucciones.
Si no existe, trabajar normalmente y considerar si el trabajo amerita crear una skill nueva.

## Catalogo de Skills

### 1. correos-tareas-operativas

**Ruta:** `.github/skills/correos-tareas-operativas/SKILL.md`

**Usar cuando:**
- un correo no llega a la BD
- Celery no ejecuta tareas o Beat no despacha
- el watchdog no rescata faltantes
- hay locks pegados o timeouts
- el panel de sincronizacion muestra estado incorrecto
- hay duplicados o faltantes entre Gmail y BD
- se necesita correr recovery de correos
- se necesita reiniciar workers de Celery

**Palabras clave:** correo, IMAP, sincronizacion, watchdog, Celery, Beat, lock, timeout, recovery, faltantes, duplicados

**Archivos principales:**
- `correspondencia/tasks.py`
- `correspondencia/management/commands/procesar_emails_seguro.py`
- `correspondencia/email_sync_control.py`
- `hospital_document_management/settings.py`

---

### 1b. gmail-api-rate-limit

**Ruta:** `.github/skills/gmail-api-rate-limit/SKILL.md`

**Usar cuando:**
- aparece `HttpError 429` / `User-rate limit exceeded` en envios o sync
- la cuota parece arrastrarse hacia adelante (`Retry after` que se mueve)
- hay que pausar Celery Gmail API y operar por SMTP/IMAP
- reactivacion segura tras cooldown

**Palabras clave:** 429, rate limit, rateLimitExceeded, Retry after, cuota Gmail API, CELERY_PAUSE_GMAIL_API_TASKS, SMTP, IMAP manual

**Archivos principales:**
- `correspondencia/utils/gmail_rate_limit.py`
- `correspondencia/tasks.py`
- `.env`

---

### 2. rebotes-dsn-depuracion

**Ruta:** `.github/skills/rebotes-dsn-depuracion/SKILL.md`

**Usar cuando:**
- un radicado saliente aparece como REBOTE sin justificacion
- hay falsos positivos de rebote
- se necesita verificar DSN reales en Gmail via IMAP
- se debe corregir registros marcados incorrectamente
- se necesita auditar o mejorar el procesador de rebotes

**Palabras clave:** rebote, bounce, DSN, falso positivo, REBOTE incorrecto, SalidaDestinatario, procesar_rebotes, smtp_code, dsn_status, ENVIADO, Undeliverable, postmaster, mailer-daemon

**Archivos principales:**
- `correspondencia/management/commands/procesar_rebotes.py`
- `correspondencia/models.py` (CorrespondenciaSalida, SalidaDestinatario, HistorialSalida)

---

### 3. asistente-ia-correspondencia

**Ruta:** `.github/skills/asistente-ia-correspondencia/SKILL.md`

**Usar cuando:**
- se trabaja el chatbot RAG del dashboard
- se necesita ajustar indexacion documental o retrieval
- se modifica la experiencia modal del asistente
- se trabajan APIs del chat, conversaciones o historial
- se ajustan tests del asistente

**Palabras clave:** chatbot, asistente, IA, RAG, indexacion, retrieval, conversacion, modal, Gemini, chat API

**Archivos principales:**
- `correspondencia/api_chat.py`
- `correspondencia/rag/`
- Templates del modal de chat

---

### 4. gemini-flash-correspondencia

**Ruta:** `.github/skills/gemini-flash-correspondencia/SKILL.md`

**Usar cuando:**
- se ajustan prompts del asistente IA
- se trabaja retries, truncamiento o calidad de respuesta
- se necesita benchmarking Flash vs Standard
- se explora tuning en Google AI Studio
- se trabajan tokens o limites de contexto

**Palabras clave:** Gemini, Flash, prompt, tokens, truncamiento, retries, calidad, tuning, Google AI Studio

**Archivos principales:**
- Los mismos del asistente IA + configuracion de Gemini

**Nota:** Esta skill complementa a `asistente-ia-correspondencia`. Cargar ambas si el trabajo toca tanto el flujo RAG como el modelo Gemini.

---

### 5. correspondencia-ui-line

**Ruta:** `.github/skills/correspondencia-ui-line/SKILL.md`

**Usar cuando:**
- se redisena una interfaz de la unidad de correspondencia
- se moderniza un template Django (bandeja, dashboard, modal, sidebar, tabla)
- se necesita homologar estilo visual entre vistas
- se trabaja paginacion, filtros o layout
- se ajusta la experiencia responsiva

**Palabras clave:** redisenar, UI, modal, bandeja, dashboard, tabla, paginacion, sidebar, layout, estilo, template, responsivo

**Archivos principales:**
- Templates en `correspondencia/templates/`
- Archivos estaticos en `static/`

---

### 6. testing-correspondencia

**Ruta:** `.github/skills/testing-correspondencia/SKILL.md`

**Usar cuando:**
- se necesita escribir tests nuevos para cualquier feature
- se diagnostican o arreglan tests rotos
- se corre la suite de tests o se genera cobertura
- se agregan fixtures o datos de prueba
- se configura o depura la infraestructura de testing
- se necesita saber como mockear componentes (IMAP, Celery, Gemini)

**Palabras clave:** test, pytest, fixture, cobertura, coverage, assert, mock, TestCase, conftest, TDD, prueba, pruebas, testing

**Archivos principales:**
- `pytest.ini`
- `conftest.py` (raiz)
- `correspondencia/tests/conftest.py`
- `correspondencia/tests/` (directorio de tests)
- `hospital_document_management/settings_test.py`

---

## Como Elegir la Skill Correcta

| Si el usuario dice... | Cargar esta skill |
|---|---|
| no llega un correo / faltante / sincronizacion | correos-tareas-operativas |
| rebote falso / REBOTE incorrecto / DSN | rebotes-dsn-depuracion |
| chatbot / asistente / RAG / pregunta al sistema | asistente-ia-correspondencia |
| prompt / Gemini / tokens / calidad respuesta | gemini-flash-correspondencia |
| redisenar / UI / modal / tabla / bandeja / estilo | correspondencia-ui-line |
| test / pytest / fixture / cobertura / pruebas | testing-correspondencia |
| no se por donde empezar / que skill uso | **este indice** |

## Combinaciones Frecuentes

- **Correo no llega + aparece como REBOTE:** cargar `correos-tareas-operativas` + `rebotes-dsn-depuracion`
- **Chatbot con respuesta mala:** cargar `asistente-ia-correspondencia` + `gemini-flash-correspondencia`
- **Redisenar panel de sincronizacion:** cargar `correspondencia-ui-line` + `correos-tareas-operativas`
- **Agregar tests a feature nueva:** cargar `testing-correspondencia` + la skill del dominio

## Cuando Crear una Skill Nueva

Crear skill nueva solo si:

1. El dominio no lo cubre ninguna skill existente
2. Se han acumulado al menos 3-4 lecciones aprendidas sobre el tema
3. El trabajo es recurrente (no un one-off)
4. La skill tendria al menos: contexto, procedimiento, archivos clave y checklist

Ruta para crearla: `.github/skills/<nombre-kebab>/SKILL.md`

## Contexto General del Proyecto

- **Stack:** Django 5.0.14 + Celery + Redis + MSSQL, Python 3.12
- **Entorno:** Ubuntu en VirtualBox VM, 4 cores, 8.7 GB RAM
- **Email:** Gmail IMAP/SMTP con App Password
- **Proyecto:** `/home/devdiego/Correspondencia-diciembre-1.0/`
- **Venv:** `venv/`
- **Servidor:** Gunicorn (4 workers) + Nginx
- **Tareas:** Celery worker (concurrency=2) + Beat
