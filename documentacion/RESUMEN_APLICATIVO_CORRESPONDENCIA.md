# RESUMEN DEL APLICATIVO DE GESTIÓN DE CORRESPONDENCIA
## Sistema de Gestión Documental Hospitalaria

**Fecha:** Enero 2026  
**Versión:** 1.0  
**Tipo de Documento:** Documentación Técnica y Funcional

---

## 📋 ÍNDICE

1. [Misión e Intención](#misión-e-intención)
2. [Descripción General](#descripción-general)
3. [Flujograma del Sistema](#flujograma-del-sistema)
4. [Componentes Principales](#componentes-principales)
5. [Tecnologías Utilizadas](#tecnologías-utilizadas)

---

## MISIÓN E INTENCIÓN

### 🎯 MISIÓN

El Sistema de Gestión de Correspondencia Hospitalaria tiene como misión **automatizar, digitalizar y optimizar el ciclo completo de gestión de correspondencia entrante y saliente** en instituciones de salud, garantizando:

1. **Cumplimiento Normativo**: Asegurar el cumplimiento de todas las normativas colombianas aplicables (Ley 1755/2015, Ley 1437/2011, Ley 594/2000, Decreto 2609/2012, entre otras).

2. **Trazabilidad Completa**: Registrar cada acción, cambio de estado y movimiento de la correspondencia con metadatos inmutables (usuario, fecha, hora, IP).

3. **Control de Plazos (SLA)**: Calcular automáticamente fechas límite de respuesta considerando días hábiles, festivos y normativas específicas por tipo de trámite.

4. **Eficiencia Operacional**: Reducir tiempos de procesamiento, eliminar reprocesos y facilitar la colaboración entre oficinas.

5. **Transparencia**: Proporcionar visibilidad completa del estado de cada trámite tanto para funcionarios internos como para ciudadanos.

### 🎯 INTENCIÓN

El sistema fue diseñado con la intención de:

- **Eliminar el procesamiento manual** de correspondencia física y electrónica mediante automatización inteligente.

- **Centralizar la gestión** de toda la correspondencia en un único sistema integrado, desde la recepción hasta la respuesta final.

- **Prevenir incumplimientos legales** mediante alertas automáticas de vencimiento de plazos y cálculo preciso de fechas límite.

- **Facilitar la toma de decisiones** mediante dashboards y reportes en tiempo real sobre el estado de la correspondencia.

- **Garantizar la integridad documental** mediante digitalización obligatoria, snapshots históricos y conservación según Tablas de Retención Documental (TRD).

- **Mejorar la experiencia del ciudadano** mediante notificaciones automáticas, seguimiento de estado y respuestas oportunas.

---

## DESCRIPCIÓN GENERAL

### ¿Qué es el Sistema?

El Sistema de Gestión de Correspondencia es una **plataforma web desarrollada en Django** que gestiona el ciclo completo de correspondencia en instituciones de salud, desde la recepción (física o electrónica) hasta la respuesta final al ciudadano.

### ¿Qué Problemas Resuelve?

1. **Problema de Radicación Manual**: Antes, cada documento debía ser radicado manualmente con riesgo de errores. Ahora, el sistema genera automáticamente números de radicado únicos e irrepetibles.

2. **Problema de Cálculo de Plazos**: Antes, calcular fechas límite considerando días hábiles y festivos era propenso a errores. Ahora, el sistema calcula automáticamente considerando calendario laboral y normativas específicas.

3. **Problema de Trazabilidad**: Antes, era difícil rastrear quién hizo qué y cuándo. Ahora, cada acción queda registrada en un historial inmutable.

4. **Problema de Correspondencia Electrónica**: Antes, los correos electrónicos debían procesarse manualmente. Ahora, el sistema lee automáticamente la bandeja de correo y radica los mensajes.

5. **Problema de Control de Rebotes**: Antes, no había forma de saber si un correo fue entregado. Ahora, el sistema monitorea rebotes y reintenta automáticamente.

6. **Problema de Distribución**: Antes, distribuir correspondencia entre oficinas era manual y propenso a errores. Ahora, el sistema permite asignación automática o manual con notificaciones instantáneas.

### Características Principales

- ✅ **Radicación Automática** con numeración consecutiva única
- ✅ **Procesamiento Automático de Correos** mediante IMAP
- ✅ **Cálculo Automático de SLA** con calendario laboral
- ✅ **Digitalización Obligatoria** de documentos físicos
- ✅ **Sello con QR** para verificación de autenticidad
- ✅ **Flujo de Aprobación** multinivel para respuestas
- ✅ **Validación de Emails** antes de envío
- ✅ **Seguimiento DSN** de entrega de correos
- ✅ **Historial Completo** de todas las acciones
- ✅ **Dashboards y Reportes** en tiempo real
- ✅ **Gestión de Contactos** por oficina
- ✅ **Comunicaciones Masivas** controladas

---

## FLUJOGRAMA DEL SISTEMA

### FLUJO 1: RECEPCIÓN Y RADICACIÓN DE CORRESPONDENCIA ENTRANTE

#### 1.1. Entrada de Documentos

**Punto de Inicio**: Un documento llega a la institución por dos medios posibles:

**A) Documento Físico:**
- El ciudadano entrega físicamente un documento en ventanilla
- El funcionario de ventanilla recibe el documento
- Se realiza inspección visual para verificar integridad
- Si el documento no cumple requisitos, se rechaza y se devuelve al ciudadano
- Si cumple requisitos, se procede a digitalización

**B) Correo Electrónico:**
- Un correo electrónico llega a la bandeja institucional
- El sistema ejecuta automáticamente el comando `procesar_emails_seguro.py` (cada 5 minutos vía Celery)
- El comando se conecta al servidor IMAP (Gmail)
- Lee correos no leídos desde el 1 de enero de 2026
- Descarga el correo y sus adjuntos
- Crea un registro en la tabla `CorreoEntrante`
- Marca el correo como leído en el servidor

#### 1.2. Digitalización (Solo Físico)

- El funcionario escanea el documento físico
- Sube el archivo digital al sistema (PDF, JPG, PNG)
- El sistema valida formato y tamaño (máx 10 archivos, 15MB total)
- Los archivos se almacenan en la carpeta `media/`
- Se genera un hash de integridad para cada archivo

#### 1.3. Radicación

**Proceso Automático:**
- El sistema genera automáticamente un número de radicado único
- Formato: `ENTRANTE-2026-00001` (tipo-año-consecutivo)
- El consecutivo se incrementa automáticamente por año
- La fecha de radicación se registra automáticamente
- El usuario radicador queda registrado

**Datos Capturados:**
- Remitente (Contacto externo)
- Asunto de la correspondencia
- Medio de recepción (Físico/Electrónico)
- Oficina destino (Oficina Productora)
- Serie y Subserie documental
- Tipo de trámite (si aplica)
- Requiere respuesta (Sí/No)
- Tiempo de respuesta (Normal/Urgente/Muy Urgente)

#### 1.4. Impresión de Sello (Solo Físico)

- Si el documento es físico, se imprime un sello con QR
- El sello contiene:
  - Número de radicado
  - Fecha y hora de radicación
  - Código QR con URL de verificación
  - Logo institucional
- Se entrega comprobante al ciudadano
- El ciudadano puede escanear el QR para verificar estado

#### 1.5. Clasificación Documental

- El funcionario asigna manualmente:
  - **Serie Documental**: Categoría principal del documento
  - **Subserie Documental**: Subcategoría específica
  - **Tipo de Trámite**: Petición, Queja, Reclamo, Sugerencia, Información
- Esta clasificación determina el plazo legal de respuesta según normativa

#### 1.6. Cálculo Automático de SLA

**Proceso:**
1. El sistema verifica si la Subserie tiene un mapeo TRD (Tabla de Retención Documental)
2. Si existe mapeo TRD, usa el plazo legal específico del trámite (ej: 15 días hábiles para peticiones)
3. Si no existe mapeo, usa el tiempo de respuesta configurado (Normal: 15 días, Urgente: 5 días, Muy Urgente: 3 días)
4. Aplica la hora de corte (ej: 4:00 PM) - si se radica después del corte, cuenta desde el siguiente día hábil
5. Suma los días hábiles excluyendo:
   - Sábados y domingos
   - Días festivos nacionales (según archivo `feriados.csv`)
6. Calcula la fecha límite de respuesta
7. Persiste el cálculo en la base de datos para reportes históricos

**Ejemplo:**
- Radicación: 15 de enero de 2026 a las 3:00 PM
- Plazo: 15 días hábiles
- Hora de corte: 4:00 PM
- Fecha límite calculada: 5 de febrero de 2026 (excluyendo sábados, domingos y festivos)

#### 1.7. Asignación a Oficina y Usuario

- El sistema asigna la correspondencia a una **Oficina Productora** (responsable del trámite)
- Opcionalmente, se puede asignar a un **usuario específico** dentro de la oficina
- Si no se asigna usuario, queda en la bandeja compartida de la oficina
- Se registra en el historial: "ASIGNADA_USUARIO" o "ASIGNADA_OFICINA"

#### 1.8. Notificación Automática

- El sistema envía notificación automática por email al usuario/oficina asignada
- La notificación incluye:
  - Número de radicado
  - Remitente y asunto
  - Fecha límite de respuesta
  - Días restantes
  - Enlace directo a la correspondencia
- También se crea una notificación en la bandeja interna del sistema

---

### FLUJO 2: PROCESAMIENTO Y RESPUESTA

#### 2.1. Recepción en Bandeja

**Bandejas Disponibles:**
- **Bandeja Personal**: Correspondencia asignada directamente al usuario
- **Bandeja de Oficina**: Correspondencia asignada a la oficina (cualquier funcionario puede atender)
- **Bandeja de Clasificados**: Correos electrónicos pendientes de clasificación manual

#### 2.2. Lectura de Correspondencia

- El usuario abre la correspondencia desde su bandeja
- Puede ver:
  - Detalles completos del remitente
  - Documentos adjuntos (escaneados o descargados del correo)
  - Historial completo de acciones
  - Estado actual y fecha límite
- Al abrir, se registra en el historial: "LEIDA" con usuario, fecha, hora e IP

#### 2.3. Acciones Disponibles

El usuario puede realizar las siguientes acciones:

**A) Compartir con Otra Oficina:**
- Comparte la correspondencia con otra oficina para colaboración
- La oficina compartida puede ver y comentar, pero no modificar
- Se registra: "COMPARTIDA_OFICINA"

**B) Redistribuir Internamente:**
- Reasigna la correspondencia a otro usuario dentro de la misma oficina
- Debe indicar motivo de redistribución
- Se registra: "REDISTRIBUIDA_INTERNA"
- Se notifica al nuevo usuario asignado

**C) Marcar como Leída (Sin Respuesta):**
- Si la correspondencia no requiere respuesta, se marca como leída
- Se registra: "LEIDA" (estado final)
- La correspondencia queda archivada

**D) Responder:**
- Inicia el proceso de creación de respuesta (ver Flujo 3)

#### 2.4. Alertas de SLA

- El sistema monitorea constantemente las fechas límite
- Genera alertas automáticas:
  - **75% del tiempo transcurrido**: Recordatorio suave
  - **90% del tiempo transcurrido**: Alerta importante
  - **95% del tiempo transcurrido**: Alerta crítica
  - **100% del tiempo transcurrido**: VENCIDO (estado automático)
- Las alertas se muestran en dashboards y se envían por email

---

### FLUJO 3: CREACIÓN Y ENVÍO DE RESPUESTA

#### 3.1. Creación de Borrador

- El usuario hace clic en "Responder"
- Se abre el formulario de respuesta
- Campos requeridos:
  - **Asunto**: Título de la respuesta
  - **Cuerpo**: Contenido de la respuesta (editor de texto enriquecido)
  - **Destinatarios**: Contactos externos que recibirán la respuesta
  - **Adjuntos**: Archivos adicionales (opcional)
  - **Requiere Aprobación**: Si necesita revisión de supervisor

#### 3.2. Gestión de Contactos

- El sistema permite:
  - **Seleccionar contactos existentes** de la agenda de la oficina
  - **Crear nuevos contactos** asociados a entidades externas
  - **Usar grupos de contactos** predefinidos (para comunicaciones masivas)
- Cada contacto debe tener:
  - Email (validado antes de guardar)
  - Nombre completo
  - Cargo (opcional)
  - Entidad externa asociada

#### 3.3. Validación de Emails

**Antes de guardar el borrador:**
- El sistema valida el formato de cada email (RFC 5322)
- Verifica la existencia del dominio (MX Record DNS)
- Intenta conexión SMTP al servidor destino (opcional)
- Si algún email es inválido, muestra error y no permite guardar

#### 3.4. Aprobación (Si Requiere)

**Si requiere aprobación:**
- El borrador se guarda con estado "PENDIENTE_APROBACION"
- Se notifica automáticamente al supervisor
- El supervisor puede:
  - **Aprobar**: La respuesta pasa a estado "APROBADA" y queda lista para envío
  - **Rechazar**: Debe indicar motivo de rechazo, la respuesta vuelve a borrador para correcciones

**Si no requiere aprobación:**
- El borrador se guarda con estado "APROBADA" automáticamente
- Queda lista para envío inmediato

#### 3.5. Generación de Radicado Saliente

- Al aprobar, se genera automáticamente número de radicado saliente
- Formato: `SALIENTE-2026-00001`
- Se registra fecha de aprobación y usuario aprobador

#### 3.6. Snapshots Automáticos

**Al aprobar, el sistema congela (snapshot) los siguientes datos:**
- Nombre de la oficina emisora (por si cambia después)
- Nombre del redactor (por si cambia después)
- Cargo del redactor (por si cambia después)
- Email del destinatario (por si cambia después)
- Nombre del destinatario (por si cambia después)

**Propósito**: Garantizar que los datos históricos no cambien, manteniendo integridad para reportes y auditorías.

#### 3.7. Envío de Correo Electrónico

**Proceso Automático:**
1. El sistema genera el mensaje de correo con:
   - Asunto y cuerpo (HTML y texto plano)
   - Adjuntos incluidos
   - Message-ID único para seguimiento
2. Se conecta al servidor SMTP (Gmail)
3. Envía el correo a cada destinatario
4. Para comunicaciones masivas, usa BCC (copia oculta)
5. Registra en la base de datos:
   - Estado: "ENVIADA"
   - Fecha y hora de envío
   - Message-ID para seguimiento
   - Lista de destinatarios con sus emails

#### 3.8. Seguimiento DSN (Delivery Status Notification)

**Proceso Automático (cada 10 minutos vía Celery):**
1. El comando `procesar_rebotes.py` se conecta a IMAP
2. Lee la carpeta de rebotes (bounces)
3. Busca mensajes de rebote relacionados con los Message-ID enviados
4. Extrae información del DSN:
   - Código SMTP de error (5xx, 4xx)
   - Mensaje de error
   - Email del destinatario que falló
5. Actualiza el estado del destinatario a "REBOTE"
6. Registra el error en la base de datos

**Política de Reintentos:**
- 1er intento: Inmediato
- 2do intento: +15 minutos
- 3er intento: +1 hora
- 4to intento: +4 horas
- Después: Notificar al usuario para canal alternativo

#### 3.9. Actualización de Estado

- Si el envío es exitoso:
  - Estado de correspondencia entrante: "RESPONDIDA"
  - Estado de correspondencia saliente: "ENVIADA"
  - Se registra en historial: "RESPONDIDA" y "ENVIADA"
- Si hay rebotes:
  - Estado de destinatarios rebotados: "REBOTE"
  - Se notifica al usuario para acción correctiva

---

### FLUJO 4: COMUNICACIONES MASIVAS

#### 4.1. Creación de Comunicación Masiva

- El usuario crea una comunicación masiva desde el menú
- Selecciona un **grupo de contactos** predefinido
- O selecciona múltiples contactos manualmente
- Escribe el asunto y cuerpo del mensaje
- Adjunta archivos si es necesario

#### 4.2. Validación Masiva

- El sistema valida todos los emails del grupo
- Muestra estadísticas:
  - Total de destinatarios
  - Emails válidos
  - Emails inválidos (con detalles)
- Permite corregir emails inválidos antes de enviar

#### 4.3. Envío Masivo

- El sistema envía el correo usando BCC (copia oculta)
- Cada destinatario recibe el correo individualmente
- Se crea un registro `SalidaDestinatario` por cada destinatario
- Se monitorea el estado de entrega de cada uno

---

### FLUJO 5: HISTORIAL Y TRAZABILIDAD

#### 5.1. Registro Automático de Eventos

**Cada acción importante se registra automáticamente en `HistorialCorrespondencia`:**

- **RADICADA**: Cuando se radica la correspondencia
- **ASIGNADA_USUARIO**: Cuando se asigna a un usuario
- **ASIGNADA_OFICINA**: Cuando se asigna solo a oficina
- **LEIDA**: Cuando un usuario lee la correspondencia
- **COMPARTIDA_OFICINA**: Cuando se comparte con otra oficina
- **REDISTRIBUIDA_INTERNA**: Cuando se reasigna a otro usuario
- **RESPONDIDA**: Cuando se crea una respuesta
- **ENVIADA**: Cuando se envía la respuesta
- **SELLO_IMPRESO**: Cuando se imprime el sello (físico)

#### 5.2. Metadatos de Cada Evento

Cada registro de historial contiene:
- **Evento**: Tipo de acción realizada
- **Usuario**: Usuario que realizó la acción
- **Fecha y Hora**: Timestamp exacto
- **IP de Origen**: Dirección IP desde donde se realizó
- **Descripción**: Texto descriptivo del cambio
- **Inmutable**: No se puede modificar ni eliminar

#### 5.3. Consulta de Historial

- Cualquier usuario autorizado puede ver el historial completo
- Filtros disponibles:
  - Por correspondencia específica
  - Por usuario
  - Por rango de fechas
  - Por tipo de evento
- El historial se muestra en orden cronológico

---

## COMPONENTES PRINCIPALES

### Modelos de Datos (Base de Datos)

1. **Correspondencia**: Modelo principal que almacena toda la información de correspondencia entrante
2. **CorrespondenciaSalida**: Almacena respuestas y comunicaciones salientes
3. **Contacto**: Contactos externos (personas) asociados a entidades
4. **EntidadExterna**: Empresas o instituciones externas
5. **CorreoEntrante**: Correos electrónicos leídos de IMAP antes de radicar
6. **HistorialCorrespondencia**: Registro inmutable de todos los eventos
7. **SalidaDestinatario**: Destinatarios individuales de comunicaciones salientes
8. **Notificacion**: Notificaciones internas del sistema
9. **AdjuntoCorreoEntrante**: Archivos adjuntos de correos entrantes
10. **AdjuntoSalida**: Archivos adjuntos de respuestas salientes

### Comandos de Gestión (Django Management Commands)

1. **procesar_emails_seguro.py**: Lee correos de IMAP con validación de adjuntos y los guarda en `CorreoEntrante`
2. **procesar_rebotes.py**: Lee rebotes de IMAP y actualiza estados de destinatarios
3. **clasificar_emails_ia.py**: (Futuro) Clasifica automáticamente correos usando IA

### Tareas Automáticas (Celery)

1. **procesar_emails_periodico**: Se ejecuta cada 5 minutos para leer nuevos correos
2. **procesar_rebotes_periodico**: Se ejecuta cada 10 minutos para procesar rebotes

### Utilidades

1. **utils_sla.py**: Funciones para cálculo de días hábiles y fechas límite
2. **modelos_minimos_sla.py**: Modelos para mapeo TRD (Subserie → Trámite → Plazo)

---

## TECNOLOGÍAS UTILIZADAS

### Backend
- **Django 5.1.3**: Framework web principal
- **Python 3.x**: Lenguaje de programación
- **SQLite/PostgreSQL**: Base de datos

### Frontend
- **HTML5 + CSS3**: Estructura y estilos
- **Bootstrap 5**: Framework CSS responsivo
- **JavaScript/jQuery**: Interactividad
- **AdminLTE 3**: Tema administrativo

### Servicios Externos
- **Gmail SMTP/IMAP**: Servicio de correo electrónico
- **Celery**: Procesamiento de tareas asíncronas
- **Redis**: Broker para Celery (opcional)

### Bibliotecas Python
- **imap-tools**: Lectura de correos IMAP
- **django-axes**: Bloqueo de intentos de login fallidos
- **django-guardian**: Permisos por objeto
- **python-dotenv**: Gestión de variables de entorno
- **django-cors-headers**: CORS para APIs

---

## CONCLUSIÓN

El Sistema de Gestión de Correspondencia es una **solución integral** que automatiza y optimiza todo el ciclo de vida de la correspondencia en instituciones de salud, desde la recepción hasta la respuesta final, garantizando cumplimiento normativo, trazabilidad completa y eficiencia operacional.

**Última actualización:** Enero 2026  
**Mantenido por:** Equipo de Desarrollo

