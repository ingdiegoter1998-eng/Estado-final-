# Tickets - 27 de febrero de 2026

Reportado por: Coordinación (vía Dayana)

---

## TICKET #1 — Términos legales: contar desde la hora real de llegada del correo

**Prioridad:** 🔴 Crítica  
**Tipo:** Bug / Regla de negocio  
**Área solicitante:** Jurídica  

**Descripción:**  
Cuando un correo (ej. tutela) llega fuera de horario laboral, los términos legales deben contarse desde la fecha/hora en que el correo fue recibido, **no** desde la fecha/hora en que se radica.

**Caso reportado:**  
Una tutela llegó a las **11:43 p.m.** del día 25. Dayana la radicó al día siguiente (26) a las **7:40 a.m.** Los términos se empezaron a contar desde el día 25, no desde el 26. Esto generó inconformidad del área jurídica (Cristian).

**Comportamiento esperado:**  
- La fecha de inicio de términos debe ser la fecha/hora de recepción real del correo, independientemente de cuándo se radique.
- Si un correo llega a las 4:00 p.m., debe radicarse con esa hora y los términos cuentan desde ese momento.

**Acción requerida:**  
Revisar la lógica de cálculo de términos para que tome como referencia la fecha de recepción del correo electrónico, no la fecha de radicación manual.

---

## TICKET #2 — Correos se demoran más de 2 horas en reflejarse en el sistema

**Prioridad:** 🔴 Crítica  
**Tipo:** Bug / Rendimiento  

**Descripción:**  
A fecha de hoy (27 de febrero), los correos entrantes se demoran **más de 2 horas** en aparecer reflejados en el software.

**Impacto:**  
Esto es crítico para documentos con plazos legales (tutelas, requerimientos de la Supersalud, etc.). Si una tutela llega a las 4:00–4:30 p.m., esos son términos que deben contarse desde hoy, pero si el correo no se refleja a tiempo, se pierde tiempo valioso de respuesta.

**Comportamiento esperado:**  
Los correos deben reflejarse en el sistema en un tiempo razonable (idealmente menos de 15 minutos).

**Acción requerida:**  
Investigar y corregir la causa de la demora en la sincronización de correos. Revisar la frecuencia del polling IMAP / tarea Celery.

---

## TICKET #3 — Permitir eliminar todos los correos (incluidos los de papelera)

**Prioridad:** 🟠 Alta  
**Tipo:** Mejora funcional  

**Descripción:**  
Actualmente hay correos que **no se pueden eliminar**, incluyendo:
- Correos que están en papelera.
- Correos basura (spam).
- Correos que fueron radicados inicialmente pero luego llegaron duplicados y no se pudieron eliminar.
- Correos que no ameritan radicación.

**Problema que genera:**  
El contador de correos entrantes sin radicar en la vista de "Comunicaciones Externas" siempre muestra un número inflado (ej. "más de 10"). Dayana **nunca sabe realmente cuántos correos pendientes tiene** porque el número incluye correos que no requieren acción.

**Comportamiento esperado:**  
- **Todo** correo debe tener la opción de ser eliminado o enviado a papelera.
- Si es basura → se puede eliminar.
- Si no amerita radicación → se puede enviar a papelera.
- El contador de correos entrantes debe reflejar solo los correos realmente pendientes de radicar.

---

## TICKET #4 — Paginación configurable en correos entrantes e historial de radicación rápida

**Prioridad:** 🟡 Media  
**Tipo:** Mejora funcional / UX  

**Descripción:**  
Se requiere agregar un selector de cantidad de registros por página en:
1. **Lista de correos entrantes**
2. **Historial de radicación rápida**

Similar a como funciona en el formato FIT, donde se puede elegir ver: **10, 50, 100 o 150** registros.

**Justificación:**  
Dayana necesita poder ver el historial de 100 correos, o solo 50, o solo 10, según la necesidad del momento.

**Comportamiento esperado:**  
Agregar un dropdown/selector con opciones de paginación (10, 50, 100, 150) en ambas vistas.

---

## TICKET #5 — Correos movidos de SPAM en Gmail no se reflejan en el software

**Prioridad:** 🔴 Crítica  
**Tipo:** Bug  

**Descripción:**  
Correos importantes que llegan a la carpeta **SPAM** de Gmail (cuenta de correspondencia) **no se reflejan en el software**, incluso cuando Dayana los mueve manualmente del SPAM a la bandeja de recibidos.

**Ejemplos de correos afectados:**
- Facturas
- Correos de la **Supersalud**
- Otra correspondencia importante

**Impacto:**  
Dayana debe revisar el SPAM de Gmail **todos los días** manualmente y radicar esos correos de forma manual, lo cual anula parcialmente el propósito del sistema automatizado.

**Comportamiento esperado:**  
- El sistema debe detectar correos que han sido movidos del SPAM a la bandeja de recibidos en Gmail.
- Alternativa: incluir la carpeta SPAM en el monitoreo IMAP para capturar todos los correos relevantes.

**Acción requerida:**  
Revisar la sincronización IMAP para que detecte correos movidos de SPAM a recibidos, o configurar el monitoreo de la carpeta SPAM directamente.

---

## TICKET #6 — Tableta no abre al iniciar la jornada

**Prioridad:** 🟠 Alta  
**Tipo:** Bug / Soporte  

**Descripción:**  
La tableta usada para recepción de correspondencia **no abre correctamente** al iniciar la jornada laboral. El problema es recurrente y no hay instrucciones claras de qué hacer cuando ocurre.

**Contexto adicional:**  
- A veces se arregla solo, a veces lo arregla Diego remotamente.
- Los usuarios no saben qué pasos seguir para solucionarlo.
- El lunes 2 de marzo llega **Mirtic** (nueva persona) y necesita poder usar la tableta.

**Acción requerida:**  
1. Diagnosticar la causa raíz del problema.
2. **Documentar paso a paso** qué debe hacer el usuario cuando la tableta no abre (guía clara para personal no técnico).
3. Si es posible, implementar una solución permanente.

---

## TICKET #7 — Soporte prioritario el lunes 2 de marzo

**Prioridad:** 🟠 Alta  
**Tipo:** Soporte / Coordinación  

**Descripción:**  
El lunes 2 de marzo el coordinador no estará disponible (tiene permiso). Se requiere que Diego esté disponible **desde temprano** para:

- Brindar soporte a **Dayana** con cualquier observación o incidente.
- Apoyar a **Mirtic** (nueva integrante) en su primer día usando el sistema.
- Atender el tema de la tableta (Ticket #6).
- Notificar a Dayana sobre cualquier corrección implementada durante el fin de semana.

---

## Resumen de tickets

| #  | Título                                              | Prioridad | Tipo              |
|----|-----------------------------------------------------|-----------|-------------------|
| 1  | Términos legales desde hora real de llegada          | 🔴 Crítica | Bug / Regla negocio |
| 2  | Correos demoran +2 horas en reflejarse               | 🔴 Crítica | Bug / Rendimiento  |
| 3  | Permitir eliminar todos los correos                  | 🟠 Alta    | Mejora funcional   |
| 4  | Paginación configurable en listas                    | 🟡 Media   | Mejora UX          |
| 5  | Correos de SPAM no se reflejan tras mover a recibidos | 🔴 Crítica | Bug               |
| 6  | Tableta no abre al iniciar jornada                   | 🟠 Alta    | Bug / Soporte      |
| 7  | Soporte prioritario lunes 2 de marzo                 | 🟠 Alta    | Soporte            |
