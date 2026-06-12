# Asistente IA: cambios, decisiones y validación

Fecha de documentación: 2026-03-28 16:40:33 -05

## Alcance

Este documento registra los cambios aplicados al asistente IA documental del módulo de correspondencia, las decisiones técnicas tomadas durante la sesión y la validación ejecutada al cierre.

El alcance cubre:

- mejora de calidad de respuestas del asistente
- revisión de consumo de tokens por interacción
- correcciones en indexación documental
- ajuste del retrieval y scoring del RAG
- refinamiento del prompt de Gemini Flash
- ampliación y corrección de la suite de pruebas del asistente

## Resumen ejecutivo

Se priorizó mejorar la calidad de las respuestas antes que reducir agresivamente el historial conversacional. La razón fue preservar continuidad y contexto entre preguntas del usuario. La mejora principal no estuvo en recortar tokens, sino en elevar la calidad del contexto que llega al modelo y en reducir ruido documental.

Los cambios produjeron estos resultados operativos:

- la indexación pasó de 7 a 42 documentos activos
- los chunks pasaron de 187 a 596
- se eliminó la presencia de chunks basura menores a 40 caracteres
- se reforzó el prompt para que la respuesta sea más concreta, operativa y anclada al contexto
- la suite del chatbot quedó en 90 pruebas pasando

## Diagnóstico inicial

### 1. Consumo de tokens

Se evaluó el tamaño de una interacción completa con Gemini Flash y se concluyó que el volumen era razonable para el caso de uso actual. El peor caso estimado rondaba aproximadamente 9600 tokens por interacción, pero el problema principal no era el costo del historial sino la calidad del contexto recuperado.

### 2. Problemas detectados en indexación

Se detectaron tres fallas de fondo:

- muy pocos documentos indexados para el universo documental real del proyecto
- chunks basura o demasiado pequeños que contaminaban el retrieval
- contaminación de encabezados y fragmentos por bloques de código Markdown

Adicionalmente, un único documento dominaba los resultados con demasiados fragmentos candidatos, reduciendo diversidad de contexto.

## Decisiones técnicas tomadas

### 1. No reducir el historial como primera medida

Se decidió no recortar de entrada el historial conversacional porque eso podía degradar la continuidad del chat. La estrategia elegida fue mantener el historial reciente y mejorar la relevancia de los chunks entregados al modelo.

### 2. Corregir la causa raíz en la indexación

Se priorizó corregir la segmentación documental para evitar que el modelo reciba ruido. El razonamiento fue que un prompt más estricto no compensa un contexto mal indexado.

### 3. Premiar cobertura y sustancia, no solo coincidencia puntual

El scoring dejó de depender principalmente del overlap bruto. Se introdujo una ponderación adicional para privilegiar fragmentos con buena cobertura de la pregunta y suficiente contenido útil.

### 4. Mantener las respuestas cortas y operativas

Se reforzó el prompt para que el asistente responda en español claro, sin exponer detalles técnicos internos, con un máximo de 4 a 6 oraciones o pasos cuando sea posible.

### 5. Corregir pruebas según el contrato real del orquestador

Durante la validación aparecieron pruebas fallidas no por un error del modelo, sino por una colisión entre reglas de intención y los textos usados por los tests. Se ajustaron las pruebas para validar el flujo correcto.

## Cambios implementados

### A. Indexación documental

Archivo principal afectado: correspondencia/services_chatbot.py

Cambios:

- se agregó `guias` a `DEFAULT_DOC_PATHS`
- se introdujo `CODE_FENCE_RE` para eliminar bloques de código antes de partir documentos
- se definió `MIN_CHUNK_CHARS = 40`
- `split_document()` ahora descarta separadores puros como `---` o `===`
- `split_document()` ignora fragmentos demasiado cortos y evita indexar ruido

Efecto esperado:

- menos fragmentos vacíos o irrelevantes
- encabezados más limpios
- mejor relación señal/ruido en retrieval

### B. Retrieval y scoring

Archivo principal afectado: correspondencia/services_chatbot.py

Cambios:

- se agregó `length_factor` para penalizar chunks demasiado cortos y favorecer fragmentos sustantivos
- se agregó `coverage_bonus` para premiar chunks que cubren una mayor fracción de tokens de la pregunta
- se mantuvo el límite de 2 chunks por documento para evitar dominancia de una sola fuente
- se filtran candidatos con contenido por debajo de `MIN_CHUNK_CHARS`

Efecto esperado:

- contexto más útil para el LLM
- menor sesgo hacia fragmentos cortos o casualmente coincidentes
- mayor diversidad documental en la respuesta final

### C. Prompt y generación con Gemini Flash

Archivo principal afectado: correspondencia/services_chatbot.py

Cambios:

- el prompt del usuario ahora obliga a responder solo con lo respaldado por el contexto
- se pide transformar información técnica en instrucciones operativas para usuarios finales
- se reforzó la prohibición de mostrar rutas, archivos, detalles de código o formato Markdown
- la instrucción de sistema se reorganizó en bloques de "CÓMO RESPONDER" y "REGLAS ESTRICTAS"
- se mantuvo `temperature = 0.2` y `maxOutputTokens = 2048`

Efecto esperado:

- respuestas más breves y accionables
- menor alucinación
- menor fuga de detalles técnicos internos al usuario final

### D. Detección de saludo

Archivo principal afectado: correspondencia/services_chatbot.py

Problema:

- `is_greeting()` usaba `tokenize()`
- `tokenize()` elimina stopwords
- `hola` y `buenas` estaban dentro de `STOPWORDS`
- como consecuencia, un saludo simple como "hola" podía no ser detectado

Corrección aplicada:

- `is_greeting()` dejó de depender de `tokenize()`
- ahora extrae tokens crudos con `TOKEN_RE.findall()` y compara directamente contra `GREETING_TOKENS`

Efecto esperado:

- los saludos reales se detectan correctamente aunque coincidan con stopwords filtradas para retrieval

### E. Suite de pruebas del asistente

Archivo principal afectado: correspondencia/tests/test_chatbot_mvp.py

Cambios:

- la suite fue ampliada y reorganizada para documentar pipelines completos del asistente
- se pasó de una cobertura reducida a una suite de 90 pruebas
- se cubrieron indexación, retrieval, intents, generación, estructura de respuesta, APIs, autenticación y aislamiento de conversaciones

Correcciones finales sobre la suite:

- se corrigió el caso de saludo simple mediante el fix de `is_greeting()`
- se ajustaron preguntas de pruebas LLM para no disparar el flujo hardcoded de `is_send_correspondence_intent()`
- en lugar de preguntar por "cómo radicar correspondencia", los tests usan formulaciones que sí obligan a recorrer el flujo LLM

## Validación ejecutada

Se validó el resultado con pruebas del chatbot y revisión del flujo completo.

Resultado final:

- 90 pruebas aprobadas en `correspondencia/tests/test_chatbot_mvp.py`

Comando de validación relevante:

- `python -m pytest correspondencia/tests/test_chatbot_mvp.py -v --tb=short`

Estado final observado:

- `90 passed in 126.20s`

## Impacto funcional

Impacto esperado para usuarios del asistente:

- mejores respuestas para preguntas documentales reales
- menos respuestas influenciadas por ruido de documentación
- mejor reconocimiento de saludos
- mayor consistencia entre contexto recuperado y respuesta generada

Impacto esperado para mantenimiento:

- mejor trazabilidad de regresiones gracias a la suite ampliada
- documentación más completa del comportamiento del asistente
- base más segura para futuros cambios de retrieval, prompt o UI del modal

## Riesgos y límites vigentes

- el asistente sigue siendo dependiente de retrieval léxico; no usa embeddings
- si la documentación fuente está incompleta o desactualizada, el modelo seguirá limitado por ese contexto
- el flujo especial de intención de envío de correspondencia sigue teniendo precedencia sobre preguntas que contengan esa combinación semántica
- la cobertura total del repositorio sigue siendo baja; la mejora fuerte se concentró en el chatbot

## Recomendaciones siguientes

1. Añadir pruebas con fixtures documentales más cercanos a casos reales de operación del hospital.
2. Incorporar métricas de calidad de retrieval para preguntas frecuentes del usuario final.
3. Documentar ejemplos de preguntas buenas y malas para el asistente dentro de guías funcionales.
4. Evaluar una segunda fase con reranking o embeddings solo si el retrieval léxico vuelve a mostrar límites reales en producción.