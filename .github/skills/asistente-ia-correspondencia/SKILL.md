---
name: asistente-ia-correspondencia
description: 'Mejora, mantiene y evoluciona el asistente IA de correspondencia de este proyecto. Úsala para trabajar el chatbot RAG, su indexación documental, retrieval, prompts, Gemini Flash, APIs, conversaciones, tests y su experiencia modal dentro del dashboard sin romper hooks, rutas ni flujos existentes.'
argument-hint: 'Describe si necesitas mejorar respuestas, retrieval, indexación, prompts, UI modal, historial, rendimiento, pruebas o mantenimiento del asistente'
user-invocable: true
disable-model-invocation: false
---

# Asistente IA Correspondencia

## Qué Resuelve

Esta skill existe para trabajar específicamente sobre el asistente IA del proyecto de correspondencia.

Su alcance incluye:

- mejorar respuestas del chatbot
- ajustar retrieval y scoring del RAG
- ampliar o corregir indexación documental
- cambiar prompts o comportamiento de Gemini Flash
- mantener el historial de conversaciones por usuario
- evolucionar APIs del asistente
- mejorar el modal expandible y contraíble del asistente
- depurar errores funcionales del chat
- reforzar pruebas y validación del asistente

No es una skill genérica para cualquier agente o cualquier integración LLM. Está pensada para esta implementación concreta del repo.

## Cuándo Usarla

Actívala cuando el usuario pida cosas como:

- mejorar el asistente documental
- ajustar cómo responde el chatbot
- hacer mantenimiento al asistente IA
- corregir el retrieval o la indexación
- cambiar el prompt de Gemini
- modernizar el modal del asistente
- agregar funcionalidades al historial de conversaciones
- hacer que el asistente entienda mejor la documentación
- arreglar errores de las APIs del chatbot

Palabras gatillo útiles:

- asistente
- chatbot
- IA
- RAG
- Gemini
- indexación
- embeddings
- retrieval
- chunks
- conversaciones
- prompt
- modal del asistente

## Contexto Real del Proyecto

Antes de tocar nada, asumir esta arquitectura actual:

- el asistente se expone en la ruta `correspondencia:asistente_chatbot`
- las APIs activas son:
  - `chatbot_conversations_api`
  - `chatbot_create_conversation_api`
  - `chatbot_messages_api`
  - `chatbot_ask_api`
- la lógica principal del chatbot vive en `correspondencia/services_chatbot.py`
- las vistas HTTP viven en `correspondencia/views_chatbot.py`
- la indexación documental corre con `manage.py indexar_asistente_docs`
- los modelos base del asistente son:
  - `AsistenteDocumento`
  - `AsistenteChunk`
  - `AsistenteConversacion`
  - `AsistenteMensaje`
- la UI actual del asistente usa una experiencia modal reutilizable integrada en dashboard

Archivos clave del frente:

- `correspondencia/services_chatbot.py`
- `correspondencia/views_chatbot.py`
- `correspondencia/management/commands/indexar_asistente_docs.py`
- `correspondencia/templates/correspondencia/usuario/asistente_chatbot.html`
- `correspondencia/templates/correspondencia/partials/modals/modal_asistente_chatbot.html`
- `correspondencia/static/correspondencia/js/chatbot-mvp.js`
- `correspondencia/static/correspondencia/css/chatbot-mvp.css`
- `correspondencia/tests/test_chatbot_mvp.py`
- `correspondencia/urls.py`

## Regla Base de Trabajo

Siempre trabajar en este orden:

1. Confirmar si el problema es de datos, retrieval, prompt, API, UI o pruebas.
2. Leer la implementación real antes de proponer cambios.
3. Mantener consistencia entre servicio, vista, template y JS.
4. Corregir la causa raíz y no solo el síntoma visible.
5. Validar con pruebas puntuales del chatbot y `manage.py check`.

## Clasificación Rápida del Trabajo

### 1. Problema de respuestas

Sospechas típicas:

- prompt insuficiente
- contexto documental poco relevante
- scoring débil en retrieval
- demasiados o muy pocos chunks
- detección de intención incompleta

### 2. Problema de indexación

Sospechas típicas:

- rutas de documentos mal configuradas
- chunks mal segmentados
- archivos fuera de `ALLOWED_EXTENSIONS`
- checksum no regenerado como se espera
- documentos no marcados como activos

### 3. Problema de API o historial

Sospechas típicas:

- serialización incompleta
- títulos de conversación no actualizados
- creación o carga de conversaciones rota
- errores de autenticación o permisos
- errores de integración entre frontend y endpoints

### 4. Problema de UI modal

Sospechas típicas:

- rompimiento de `data-*` hooks
- modal no expande o no contrae bien
- sidebar de sesiones no colapsa bien
- scroll interno deficiente
- integración rota en dashboard o vista dedicada

## Flujo de Trabajo Recomendado

### Paso 1. Ubicar el frente exacto

Separar el caso primero en una de estas categorías:

- retrieval o scoring
- prompt o generación
- indexación documental
- APIs de conversación
- modal o experiencia visual
- pruebas y validación

No mezclar todos los frentes desde el inicio si no hace falta.

### Paso 2. Revisar el contrato actual

Antes de editar, confirmar:

- qué rutas usa el frontend
- qué `data-*` consume `chatbot-mvp.js`
- qué espera la vista en contexto
- qué estructura devuelve cada API
- qué cubren ya los tests en `test_chatbot_mvp.py`

### Paso 3. Proteger compatibilidad funcional

Por defecto, preservar:

- nombres de rutas Django
- nombres de modelos del asistente
- forma del JSON devuelto por las APIs existentes
- `data-chatbot-root` y demás `data-*` usados por JS
- estructura principal del modal si el cambio no exige rediseño fuerte

## Reglas Específicas por Frente

### A. Retrieval y scoring

Si trabajas el RAG:

- revisa `tokenize`, `expand_query_tokens`, `build_search_text`
- revisa el límite y selección de chunks en `DocumentRetrievalService`
- evita sobrecomplicar el scoring si una mejora simple resuelve el problema
- mantén trazabilidad suficiente para entender por qué un chunk fue usado

Evitar:

- introducir lógica opaca sin pruebas
- devolver demasiados chunks irrelevantes
- cambiar el retrieval sin validar consultas reales del proyecto

### B. Prompt y generación

Si ajustas Gemini Flash:

- mantén respuestas operativas y orientadas a documentación real
- evita prompts demasiado literarios o vagos
- conserva la instrucción de no inventar políticas ni datos
- si agregas comportamiento nuevo, documenta el criterio dentro de la skill o del código

### C. Indexación documental

Si tocas indexación:

- respeta `DEFAULT_DOC_PATHS` salvo cambio intencional
- no indexes binarios o fuentes irrelevantes
- valida que `split_document` no rompa contexto útil
- verifica que el comando `indexar_asistente_docs` siga siendo la entrada oficial

### D. APIs y conversaciones

Si cambias vistas o endpoints:

- conserva autenticación con `login_required`
- no cambies la firma pública del JSON sin necesidad real
- mantén el vínculo por usuario en conversaciones
- protege los errores con mensajes útiles para frontend

### E. Modal y experiencia visual

Si el cambio es UI:

- preservar `data-chatbot-root`
- preservar `data-conversation-list`, `data-chat-form`, `data-question-input`, `data-submit-button`, `data-chat-title`
- conservar accesibilidad básica del modal
- asegurar que expandir, contraer y colapsar sesiones siga funcionando en desktop y mobile
- mantener consistencia visual con `dashboard_usuario`

## Comandos de Validación

Usar siempre el entorno del repo:

- `venv/bin/python manage.py check`
- `venv/bin/python -m pytest correspondencia/tests/test_chatbot_mvp.py`
- `venv/bin/python manage.py indexar_asistente_docs --clear --path <ruta>`

Si el trabajo cambia indexación, prompt o flujo de preguntas, la validación mínima debe incluir al menos:

1. `manage.py check`
2. la suite `test_chatbot_mvp.py`

## Criterios de Calidad

La tarea se considera bien resuelta si:

1. el asistente sigue respondiendo con contexto documental útil
2. no se rompieron las APIs existentes
3. el modal sigue funcionando en la vista dedicada y en el dashboard
4. la indexación continúa operativa
5. los tests del chatbot siguen pasando o se actualizan de forma justificada
6. el cambio no introduce complejidad innecesaria

## Qué Evitar

- reemplazar la arquitectura existente sin necesidad clara
- tocar rutas o nombres públicos del asistente por estética
- romper los `data-*` que usa el JS del modal
- mezclar mejoras del asistente con refactors no relacionados del módulo de correspondencia
- cambiar retrieval, prompt y UI a la vez sin una razón sólida
- dejar el asistente visualmente mejor pero funcionalmente peor

## Prompts de Ejemplo

- `/asistente-ia-correspondencia mejora el retrieval del asistente para preguntas sobre radicación desde correo`
- `/asistente-ia-correspondencia revisa el prompt de Gemini para que responda más corto y más operativo`
- `/asistente-ia-correspondencia corrige el modal del asistente porque no expande bien dentro del dashboard`
- `/asistente-ia-correspondencia mejora la indexación de documentos para que tome mejor los markdown largos`
- `/asistente-ia-correspondencia agrega pruebas para una nueva intención del chatbot`

## Nota Final

Si existe ambigüedad entre mantenimiento funcional y retoque visual, prioriza primero la estabilidad funcional del asistente. La UI del asistente puede evolucionar, pero no a costa de romper el flujo de preguntas, conversaciones, indexación o APIs.