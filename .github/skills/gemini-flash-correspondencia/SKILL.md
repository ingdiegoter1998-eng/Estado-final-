---
name: gemini-flash-correspondencia
description: 'Trabaja Gemini Flash dentro del asistente IA de correspondencia. Úsala cuando necesites ajustar prompts, retries, truncamiento, calidad de respuesta, tokens, benchmarking, comparación Flash vs Standard o preparar un posible tuning en Google AI Studio sin romper el flujo RAG existente.'
argument-hint: 'Describe si necesitas mejorar prompt, retries, contexto, tokens, truncamiento, benchmarking o comparar Gemini Flash frente a Gemini Standard'
user-invocable: true
disable-model-invocation: false
---

# Gemini Flash Correspondencia

## Qué Resuelve

Esta skill existe para trabajar específicamente el uso de Gemini Flash dentro del asistente IA del proyecto de correspondencia.

Su alcance incluye:

- ajustar prompts del asistente
- mejorar calidad de respuesta con Gemini Flash
- endurecer retries y manejo de errores transitorios
- reducir truncamiento por límite de salida
- optimizar consumo de tokens
- comparar Gemini Flash frente a Gemini Standard
- preparar benchmark para decidir si conviene tuning
- preparar al sistema para una futura versión ajustada desde Google AI Studio

No es una skill genérica para cualquier integración LLM. Está pensada para este chatbot RAG documental y su integración con Django.

## Cuándo Usarla

Actívala cuando el usuario pida cosas como:

- mejorar Gemini Flash
- ajustar el prompt del chatbot
- reducir errores 503 o inestabilidad del asistente
- mejorar calidad de respuestas con Gemini
- comparar Flash vs Standard
- revisar truncamiento por max tokens
- evaluar si conviene tuning en Google AI Studio
- medir tokens, retries o fallback del asistente

Palabras gatillo útiles:

- Gemini Flash
- Gemini Standard
- Google AI Studio
- tuning
- retries
- max tokens
- truncamiento
- prompt
- calidad de respuesta
- benchmark

## Contexto Real del Proyecto

Antes de tocar nada, asumir esta arquitectura:

- la integración real del LLM vive en `correspondencia/services_chatbot.py`
- la capa HTTP que entrega el chat vive en `correspondencia/views_chatbot.py`
- la entrada funcional del asistente sigue siendo el flujo RAG documental
- las conversaciones se exponen por las APIs `chatbot_create_conversation_api`, `chatbot_messages_api` y `chatbot_ask_api`
- el asistente opera sobre `AsistenteConversacion`, `AsistenteMensaje`, `AsistenteDocumento` y `AsistenteChunk`

## Regla Base de Trabajo

Siempre trabajar en este orden:

1. Confirmar si el problema es del modelo, del retrieval, del prompt o de disponibilidad.
2. Medir antes de cambiar: no asumir que un modelo mejor arregla un contexto malo.
3. Mantener la respuesta anclada a documentación real del proyecto.
4. No romper el contrato JSON que consume el frontend del chatbot.
5. Validar con tests del chatbot y, cuando sea posible, con interacción real vía API.

## Diagnóstico Rápido

### 1. Problema de calidad de respuesta

Sospechas típicas:

- prompt insuficiente
- demasiados chunks o chunks poco relevantes
- contexto demasiado largo
- historial excesivo
- falta de disciplina para reconocer que no hay suficiente contexto

### 2. Problema de disponibilidad

Sospechas típicas:

- errores 502, 503 o 504 del proveedor
- falta de retries con backoff
- mensaje de error crudo expuesto al frontend

### 3. Problema de truncamiento

Sospechas típicas:

- `finishReason = MAX_TOKENS`
- respuesta cortada a mitad de oración
- demasiado historial o demasiado contexto por consulta

### 4. Problema de benchmark o decisión de modelo

Sospechas típicas:

- se quiere decidir entre Flash y Standard sin dataset de prueba
- se atribuye al modelo un fallo que en realidad viene del retrieval
- se quiere hacer tuning sin ejemplos buenos ni métricas claras

## Flujo de Trabajo Recomendado

### Paso 1. Confirmar si el problema es del modelo o del sistema

Antes de culpar a Gemini Flash, revisar:

- chunks recuperados
- longitud del contexto enviado
- historial incluido
- `finish_reason`
- errores transitorios del proveedor

### Paso 2. Mantener a Gemini Flash dentro de su zona fuerte

Gemini Flash rinde mejor cuando:

- la pregunta es operativa y concreta
- el contexto está bien seleccionado
- el prompt es estricto y corto
- el número de tokens no se dispara innecesariamente

### Paso 3. Medir cambios con benchmark real

Usar preguntas reales del negocio, no solo casos técnicos. Idealmente incluir:

- saludo
- pregunta operativa simple
- pregunta operativa compleja
- pregunta sin suficiente contexto
- intento de obtener detalle técnico interno

## Reglas Específicas

### A. Si trabajas el prompt

- mantén lenguaje operativo y sencillo
- prohíbe alucinación y consejos no respaldados
- obliga a reconocer falta de contexto cuando corresponda
- evita prompts excesivamente largos

### B. Si trabajas retries o disponibilidad

- usa retries solo para errores transitorios
- añade backoff corto
- nunca expongas al frontend el error bruto del proveedor si puedes devolver un mensaje operativo mejor

### C. Si trabajas truncamiento

- reduce historia incluida
- limita el tamaño del contexto documental
- detecta `MAX_TOKENS` y sanea la salida para no dejar frases cortadas

### D. Si comparas Flash vs Standard

- no cambies retrieval entre una prueba y otra
- compara con el mismo set de preguntas
- mide exactitud, claridad, obediencia al contexto y estabilidad
- documenta costo, tiempo de respuesta y calidad percibida

### E. Si preparas tuning en Google AI Studio

- usa ejemplos reales del dominio de correspondencia
- incluye buenos ejemplos de rechazo por falta de contexto
- incluye preguntas ambiguas y preguntas técnicas que el asistente no debe responder con detalles internos
- no empieces tuning sin benchmark base contra Flash sin ajustar

## Validación Mínima Esperada

Después de tocar este frente, validar con:

- `python -m pytest correspondencia/tests/test_chatbot_mvp.py -v --tb=short`
- `python manage.py check`
- interacción real contra la API del chatbot si el entorno lo permite

## Criterio Estratégico del Proyecto

Para este asistente, Gemini Flash debe tratarse como una base rápida y suficientemente buena, pero dependiente de un RAG disciplinado. Si Gemini Standard se toma como 10/10 de referencia, Gemini Flash debe asumirse aproximadamente como 8/10 en este caso de uso, con fuerte dependencia de la calidad del retrieval.