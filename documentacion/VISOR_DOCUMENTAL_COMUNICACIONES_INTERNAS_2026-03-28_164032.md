# Visor documental de comunicaciones internas en calendario Next.js

## Fecha de registro

- 2026-03-28 16:40:32 -05

## Alcance del cambio

Durante esta sesión se implementó y publicó en producción la visualización de documentos de comunicaciones internas dentro del aplicativo React/Next.js de calendario, evitando la salida directa al visor o descarga del lado Django para el flujo principal de consulta.

La ruta funcional resultante es:

- /calendario/documento/<id>

Ejemplo probado durante la sesión:

- /calendario/documento/118

## Objetivo funcional

Se buscó que el usuario pudiera abrir una comunicación interna generada desde una interfaz propia del aplicativo Next.js, con contexto adicional del documento y sin depender de abrir el PDF como descarga directa desde Django.

Posteriormente se amplió el objetivo para permitir también la visualización de adjuntos en la misma pantalla, usando pestañas y manteniendo una sola previsualización activa para controlar el costo de carga.

## Cambios implementados

### 1. Endpoints Django para el visor

Se añadieron endpoints API específicos para comunicaciones internas:

- metadata del documento
- PDF principal inline
- anexos inline

Estos endpoints quedaron orientados a consumo desde el frontend Next.js y no como descarga forzada.

## 2. Integración del frontend Next.js

En el servicio calendario Next.js se creó la ruta protegida de visor documental para mostrar:

- radicado
- estado
- asunto
- remitente
- destinatario
- tipo de distribución
- historial reciente
- documento principal
- documento firmado cuando exista
- anexos

La pantalla quedó montada como visor embebido con sidebar informativo.

## 3. Pestañas para documentos y adjuntos

La vista fue extendida para soportar pestañas dentro del mismo visor:

- Documento principal
- Documento firmado
- Adjuntos

Comportamiento definido:

- Si el archivo es PDF o imagen, se previsualiza dentro del visor.
- Si el archivo no es previsualizable de forma segura o nativa en navegador, se mantiene la pestaña visible pero se ofrecen acciones para abrir en otra pestaña o descargar.
- Solo se renderiza un archivo activo a la vez.

## 4. Cambio de enlaces desde templates Django

Las vistas Django que antes abrían o descargaban el PDF directamente fueron ajustadas para apuntar al visor Next.js.

## 5. Ajuste de seguridad para iframe

Se detectó un bloqueo real en navegador con el error ERR_BLOCKED_BY_RESPONSE.

Causa raíz encontrada:

- Django tenía X_FRAME_OPTIONS = DENY a nivel global.
- El endpoint del PDF heredaba ese header y el navegador rechazaba el iframe.

Decisión implementada:

- No se cambió la política global del proyecto.
- Solo se habilitó SAMEORIGIN en los endpoints concretos del visor documental y anexos.

Esto permitió mantener la protección de clickjacking del resto del sistema y abrir únicamente la superficie necesaria para el visor propio alojado en el mismo dominio.

## Decisiones técnicas tomadas

### 1. Reutilizar el servicio Next.js existente

No se creó un nuevo servicio React para este visor.

Motivo:

- ya existía el servicio calendario en producción
- el flujo de autenticación por sesión ya estaba resuelto
- evita nuevos puertos, nuevos units y complejidad operativa adicional

### 2. Mantener autenticación basada en sesión Django

La integración se dejó sobre el mismo dominio y con la misma sesión autenticada.

Motivo:

- evita duplicar esquemas de autenticación
- reduce el riesgo de inconsistencias entre backend Django y frontend Next.js
- simplifica el consumo de los endpoints protegidos

### 3. Permitir embebido solo same-origin

No se abrió el visor para orígenes externos.

Motivo:

- la necesidad era embeber dentro del mismo aplicativo
- SAMEORIGIN resuelve el caso de uso sin ampliar innecesariamente la superficie de exposición

### 4. Cargar un solo archivo a la vez

No se montan varios iframes ni varias previsualizaciones simultáneas.

Motivo:

- reduce consumo de memoria en navegador
- reduce tráfico concurrente al servidor
- evita una experiencia lenta en documentos con múltiples adjuntos pesados

### 5. Previsualización selectiva de anexos

La previsualización inline quedó restringida a tipos razonables para navegador:

- application/pdf
- image/*

Motivo:

- no todos los formatos se renderizan de forma fiable en iframe
- algunos archivos tienen mejor comportamiento como apertura externa o descarga directa

## Impacto esperado en rendimiento

La solución no debería sobrecargar de forma significativa el sistema bajo el diseño actual.

Razones:

- la metadata del documento es liviana
- la vista mantiene una sola pestaña activa
- el costo fuerte ocurre cuando el usuario abre un archivo específico, lo cual ya existía como consumo cuando antes descargaba el archivo
- el impacto principal está más asociado al peso de PDFs o imágenes que a CPU del servidor

Riesgos normales a vigilar:

- adjuntos muy pesados
- múltiples usuarios abriendo varios PDFs grandes al mismo tiempo
- formatos no previsualizables que requieran salida externa

## Archivos tocados durante la implementación

Backend Django:

- correspondencia/api_views.py
- correspondencia/urls.py
- correspondencia/admin.py
- templates/correspondencia/interna/enviadas.html
- templates/correspondencia/interna/recibidas.html
- templates/correspondencia/interna/lista.html
- templates/correspondencia/interna/detalle.html

Frontend Next.js calendario:

- calendario-informes-nextjs/next.config.mjs
- calendario-informes-nextjs/types/documento.ts
- calendario-informes-nextjs/lib/api/documento.ts
- calendario-informes-nextjs/hooks/useDocumento.ts
- calendario-informes-nextjs/app/(protected)/documento/[id]/page.tsx
- calendario-informes-nextjs/app/(protected)/documento/[id]/VisorDocumentoClient.tsx

## Validaciones realizadas

Durante la sesión se validó lo siguiente:

- Django check sin errores
- build de Next.js exitoso
- reinicio de servicios correspondencia y correspondencia-nextjs
- verificación del header X-Frame-Options con salida SAMEORIGIN en endpoints del visor

## Estado final

El visor documental quedó publicado en producción con estas capacidades:

- abrir documento principal dentro del aplicativo
- abrir documento firmado dentro del aplicativo
- consultar metadatos e historial en sidebar
- navegar adjuntos desde pestañas en la misma vista
- abrir o descargar archivos no previsualizables

## Observaciones operativas

- Si el navegador conserva una respuesta anterior bloqueada, puede requerirse recarga fuerte.
- Si en el futuro se agregan nuevos tipos de adjunto que deban previsualizarse inline, la lógica de content_type puede ampliarse.
- Si la cantidad de adjuntos crece mucho por documento, podría agregarse paginación o agrupación visual, pero no fue necesario en esta implementación.

## Resultado de la decisión principal

Se priorizó una solución integrada, segura y de bajo impacto operativo:

- integrada al servicio Next.js ya existente
- compatible con sesión Django
- segura mediante SAMEORIGIN selectivo
- moderada en consumo al cargar un solo archivo por vez
