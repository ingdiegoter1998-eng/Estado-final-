# Sesión Chat Monitoreo - 2026-03-28 16:40:30 -05

## Alcance

Documento de registro técnico de los cambios aplicados sobre el sistema de tickets/chat, el monitoreo administrativo y los accesos de Ventanilla durante la sesión del 28 de marzo de 2026.

## Resumen Ejecutivo

Durante esta sesión se consolidó el módulo de chat/tickets en dos frentes:

- experiencia administrativa en Monitoreo Next.js
- acceso operativo desde vistas de Ventanilla en Django

Además, se corrigió un problema real de carga de imágenes adjuntas en Monitoreo causado por URLs absolutas generadas detrás de un proxy entre Next.js y Django.

## Cambios Implementados

### 1. Ampliación del chat administrativo en Monitoreo

Se amplió la vista administrativa de Monitoreo en la ruta /monitoreo/chat con estos componentes:

- resumen KPI de tickets
- panel de notificaciones de actividad reciente
- directorio de usuarios agrupado por oficinas
- modal de detalle de usuario
- creación de ticket desde el directorio
- separación funcional entre conversaciones y directorio

### 2. Nuevos endpoints backend para el chat

Se agregaron endpoints en correspondencia/api_chat.py para soportar la nueva experiencia administrativa:

- resumen extendido de tickets
- directorio por oficina
- detalle de usuario
- feed de notificaciones recientes

También se registraron sus rutas en correspondencia/urls.py.

### 3. Nuevos hooks y actualización de la vista Next.js

En Monitoreo se incorporó el archivo hooks/use-directorio.ts y se reestructuró la pantalla principal del chat administrativo para consumir los nuevos endpoints y renderizar la nueva interfaz.

### 4. Accesos desde Ventanilla

Se agregaron accesos visibles para usuarios de Ventanilla hacia el sistema de tickets:

- botón Tickets / Soporte en la portada operativa de pendientes por distribuir
- enlace Tickets y Soporte en el sidebar compartido de Ventanilla apuntando a /monitoreo/chat

### 5. Corrección de imágenes adjuntas en Monitoreo

Se corrigió el problema por el cual las imágenes adjuntas del chat no cargaban en la interfaz administrativa de Monitoreo.

#### Causa raíz

La API del chat estaba serializando los adjuntos con request.build_absolute_uri(...). Como Monitoreo consume el backend a través de un proxy de Next.js, Django podía construir URLs con el host interno del backend en lugar del host público.

#### Corrección aplicada

Se centralizó la serialización del adjunto en correspondencia/api_chat.py y ahora el API devuelve la ruta pública relativa del archivo en media, por ejemplo:

- /media/chat_adjuntos/...

Con esto, el navegador resuelve el recurso contra el mismo host público desde el cual se carga Monitoreo.

## Decisiones Técnicas Tomadas

### 1. Notificaciones como panel deslizable

Se descartó una barra lateral fija siempre visible para notificaciones dentro del chat administrativo.

Razón:

- una columna fija reduce demasiado el espacio útil de lectura y respuesta
- el panel deslizable mantiene acceso rápido sin degradar la conversación principal

### 2. Conversaciones y directorio en tabs separados

Se decidió no mezclar el directorio organizacional con la lista de conversaciones activas.

Razón:

- evita mezclar navegación operativa con consulta de estructura organizacional
- mejora foco visual y reduce ruido cognitivo

### 3. KPIs en la cabecera del módulo

Se decidió presentar los indicadores de tickets en la parte superior de la pantalla.

Razón:

- permite lectura rápida del estado operativo antes de entrar al detalle
- da contexto administrativo sin ocultar las acciones principales

### 4. URLs relativas para adjuntos del chat

Se decidió corregir el problema en el backend y no en el render del frontend.

Razón:

- soluciona la causa raíz del contrato de datos
- evita hardcodear dominios o acoplar el frontend a hosts específicos
- mantiene consistencia entre el chat Django y el chat en Monitoreo

### 5. Acceso a Monitoreo desde sidebar de Ventanilla

Se decidió agregar el acceso al chat administrativo en la base compartida de navegación y no solamente en una pantalla puntual.

Razón:

- mejora descubribilidad
- evita depender de una única bandeja para entrar al módulo

## Archivos Relevantes Tocadas en la Sesión

### Backend Django

- correspondencia/api_chat.py
- correspondencia/urls.py
- correspondencia/templates/correspondencia/admin/lista_pendientes.html
- correspondencia/templates/correspondencia/bases/base_correspondencia.html

### Frontend Monitoreo

- monitoreo-nextjs/app/chat/page.tsx
- monitoreo-nextjs/hooks/use-chat.ts
- monitoreo-nextjs/hooks/use-directorio.ts
- monitoreo-nextjs/app/page.tsx
- monitoreo-nextjs/app/api/chat/[...path]/route.ts

### Infraestructura relevante para el diagnóstico

- monitoreo-nextjs/next.config.mjs
- hospital_document_management/settings.py
- deploy/nginx/correspondencia.conf

## Validaciones Ejecutadas

Se validaron estos puntos durante la sesión:

- python manage.py check sin errores
- compilación de Monitoreo Next.js exitosa
- revisión de rutas y proxy entre Monitoreo y Django

## Riesgos y Consideraciones

### 1. Aplicación del fix en producción

La corrección de adjuntos en correspondencia/api_chat.py requiere que el servicio Django desplegado cargue el cambio actualizado.

### 2. Dependencia del reverse proxy

El problema original confirmó que cualquier serialización de URL absoluta generada desde Django detrás del proxy debe revisarse con cuidado cuando el consumidor final sea Monitoreo.

## Recomendaciones de Continuidad

1. Verificar manualmente en /monitoreo/chat que un ticket nuevo con imagen adjunta cargue miniatura y lightbox.
2. Revisar si otros endpoints del proyecto están devolviendo URLs absolutas innecesarias detrás del proxy.
3. Mantener el acceso a tickets en la navegación de Ventanilla como punto fijo del flujo operativo.

## Fecha de Registro

- Fecha y hora del registro: 2026-03-28 16:40:30 -05
- Ubicación del registro: documentacion/SESION_CHAT_MONITOREO_2026-03-28_164030.md