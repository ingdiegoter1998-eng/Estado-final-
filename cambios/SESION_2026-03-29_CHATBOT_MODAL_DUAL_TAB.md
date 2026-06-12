# Sesión 29 de marzo de 2026 — Modal Chatbot Dual-Tab + Mejoras UX

## Resumen general

Se integró el asistente IA y el chat de Soporte TI en un único modal con pestañas, se corrigieron múltiples bugs de layout y se agregaron mejoras de UX (sidebar independiente por pestaña, botón inline para crear reportes).

---

## Cambios realizados (orden cronológico)

### 1. Integración dual-tab: Asistente IA + Soporte TI
**Hora estimada:** Inicio de sesión  
**Archivos modificados:**
- `correspondencia/templates/correspondencia/components/modal_asistente_chatbot.html`
- `correspondencia/static/correspondencia/js/chatbot-mvp.js`
- `correspondencia/static/correspondencia/css/chatbot-mvp.css`

**Descripción:**  
Se rediseñó el modal del chatbot para incluir dos pestañas:
- **Asistente IA** — chatbot RAG con Gemini Flash
- **Soporte TI** — sistema de tickets/reportes con chat en tiempo real

Se agregó una barra de pestañas (`[data-chatbot-tab]`) entre el header y el contenido. Cada pestaña tiene su propio contenido (`[data-chatbot-tab-content]`), sidebar de sesiones/reportes, y área de chat independiente.

El tab de Soporte TI incluye: listado de reportes, creación de nuevos reportes (overlay), chat con polling cada 3-5s, subida de imágenes y lightbox.

---

### 2. Fix: Pestaña "Soporte TI" no cambiaba al hacer clic
**Hora estimada:** Durante integración  
**Archivos modificados:**
- `correspondencia/static/correspondencia/css/chatbot-mvp.css`

**Causa raíz:**  
El CSS grid tenía `grid-template-rows: auto 1fr` (2 filas) pero el modal tiene 3 elementos: header, tab bar y contenido. El tab bar no tenía fila asignada.

**Solución:**  
Cambiar a `grid-template-rows: auto auto 1fr` para acomodar las 3 filas correctamente.

---

### 3. Fix: Altura del modal saltaba al cambiar pestañas
**Hora estimada:** Post fix #2  
**Archivos modificados:**
- `correspondencia/static/correspondencia/css/chatbot-mvp.css`
- `correspondencia/static/correspondencia/js/chatbot-mvp.js`

**Causa raíz:**  
Se usaba `display: none` / `display: block` para ocultar/mostrar pestañas. Esto removía la pestaña inactiva del flujo del layout, causando que el grid recalculara la altura.

**Solución:**  
Cambiar a `visibility: hidden` / `visibility: visible` con celdas de grid superpuestas:
```css
.chatbot-tab-content {
    grid-row: 3;
    grid-column: 1;
    visibility: hidden;
}
.chatbot-tab-content.is-active {
    visibility: visible;
}
```
Ambas pestañas siempre ocupan el mismo espacio en la fila 3, evitando saltos de altura.

---

### 4. Sidebar toggle independiente por pestaña
**Hora estimada:** Post fix #3  
**Archivos modificados:**
- `correspondencia/static/correspondencia/js/chatbot-mvp.js`
- `correspondencia/static/correspondencia/css/chatbot-mvp.css`

**Descripción:**  
Antes, el botón "Sesiones" colapsaba/expandía el sidebar de ambas pestañas simultáneamente (clase `is-sidebar-collapsed` en el elemento raíz).

**Solución:**  
- Se movió la clase `is-sidebar-collapsed` al nivel de cada `chatbot-tab-content` individual.
- Se creó helper `getActiveTabContent()` para obtener la pestaña activa.
- El botón toggle ahora opera solo sobre la pestaña visible.
- Al cambiar de pestaña, el icono/label del botón toggle se sincroniza con el estado de la pestaña destino.

---

### 5. Botón inline "Crear nuevo reporte" en estado vacío de Soporte
**Hora estimada:** ~Final de sesión  
**Archivos modificados:**
- `correspondencia/templates/correspondencia/components/modal_asistente_chatbot.html`
- `correspondencia/static/correspondencia/js/chatbot-mvp.js`

**Descripción:**  
Cuando no hay un reporte seleccionado en el tab de Soporte TI, se muestra un estado vacío. Se agregó un botón visible en esa zona para crear un nuevo reporte sin necesidad de abrir el sidebar.

**HTML agregado** (en el empty state de soporte):
```html
<button type="button"
        class="chatbot-suggestion chatbot-suggestion--support"
        data-action="new-support-conversation-inline">
    <i class="bi bi-plus-circle"></i> Crear nuevo reporte
</button>
```

**JS agregado** — Se refactorizó el handler existente a función compartida:
```javascript
function openNewReportOverlay() {
    if (supportNewOverlay) {
        supportNewOverlay.style.display = '';
        var asuntoInput = root.querySelector('[data-support-new-asunto]');
        if (asuntoInput) asuntoInput.focus();
    }
}

// Botón sidebar "+"
if (supportNewBtn) {
    supportNewBtn.addEventListener('click', openNewReportOverlay);
}
// Botón inline en empty state
var supportNewInlineBtn = root.querySelector('[data-action="new-support-conversation-inline"]');
if (supportNewInlineBtn) {
    supportNewInlineBtn.addEventListener('click', openNewReportOverlay);
}
```

---

## Archivos clave del sistema de chatbot

| Archivo | Propósito |
|---------|-----------|
| `modal_asistente_chatbot.html` | Template del modal dual-tab (Bootstrap 5) |
| `chatbot-mvp.js` | Toda la lógica JS: AI chatbot + soporte TI (~770 líneas) |
| `chatbot-mvp.css` | Todos los estilos del modal (~1200 líneas) |
| `context_processors.py` | `chatbot_global_context` — inyecta datos del chatbot IA |
| `api_chat.py` | Endpoints REST para soporte TI (`/api/chat/`) |
| `views_chatbot.py` | Endpoints REST para chatbot IA (`/api/chatbot/`) |

## Estado de tests

Todos los **94 tests** del chatbot pasaron correctamente durante la sesión:
```
correspondencia/tests/test_chatbot_mvp.py — 94 passed
```

## Collectstatic

Se ejecutó `python manage.py collectstatic --noinput` después de cada cambio en archivos estáticos para desplegar al directorio `staticfiles/`.

## Arquitectura del modal

```
┌─────────────────────────────────────┐
│  Header (título + botones)          │  row 1
├─────────────────────────────────────┤
│  Tab Bar [Asistente IA | Soporte]   │  row 2
├─────────────────────────────────────┤
│  Tab Content (superpuestos, row 3)  │  row 3
│  ┌──────────┬──────────────────┐    │
│  │ Sidebar  │  Chat area       │    │
│  │ (toggle) │  (mensajes)      │    │
│  └──────────┴──────────────────┘    │
└─────────────────────────────────────┘
```

- Las dos pestañas comparten `grid-row: 3; grid-column: 1`
- Solo la activa tiene `visibility: visible`
- Cada pestaña controla su sidebar independientemente
