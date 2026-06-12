# 🎯 BRIEFING EJECUTIVO - Claude Code

## 🎨 SKILLS DE CLAUDE

Usa estas 3 skills como prefieras. No hay stack impuesto:

- frontend-design
- theme-factory
- web-artifacts-builder

---

## MISIÓN
Migrar calendario de informes y firma de planillas de Django/HTML estático a un frontend moderno, responsive y optimizado para tablets y móviles.

---

## 🗂️ ARCHIVOS DE CONTEXTO (Alto nivel)

1. **`documentacion/mapa_topologico_archivos.md`** ← Guia principal
2. **`BRIEFING_CLAUDE_CODE.md`** ← Solo contexto general

Nota: Todo lo demas en este archivo es referencia opcional. No impone stack ni pasos.

---

## ⚡ QUICK START

### Stack Tecnológico
- **Frontend**: Next.js 14 (App Router) + TypeScript
- **UI**: Tailwind CSS v3 + shadcn/ui
- **HTTP**: Axios + SWR
- **Fechas**: date-fns
- **Backend Actual**: Django REST API (ya existe)

### Arquitectura
- Next.js consume API REST de Django
- Autenticación: Cookies de sesión Django reutilizadas
- Responsive: Mobile-first con Tailwind (sm:, md:, lg:)
- Deploy: Vercel o Docker + Node.js
- **Diseño**: High-end profesional (evita look genérico AI)

---

## 🎨 FUNCIONALIDADES CLAVE

### 1️⃣ Calendario Mensual
- Vista calendario con 7 columnas (semana)
- Estados visuales: Firmado (verde), Pendiente (amarillo), Sin datos (gris)
- Badge con cantidad de correspondencias por día
- Navegación: anterior/siguiente mes
- Click en día → Detalle

### 2️⃣ Detalle del Día
- Lista de correspondencias del día
- Estadísticas: total, firmas, descargas
- Tabla con destinatarios, remitentes, asuntos
- Botón descargar Excel
- Botón subir archivo firmado (PDF/JPG/PNG)
- Modal de firma digital por correspondencia

### 3️⃣ Firma Digital
- Canvas HTML5 con soporte mouse + touch
- Conversión a Base64 PNG
- Guardado individual por correspondencia
- Preview de firma guardada

---

## 📋 PRIORIDADES

### FASE 1 (CRÍTICA): Setup + API
1. Crear proyecto Next.js con TS + Tailwind
2. Inicializar shadcn/ui (Button, Card, Dialog, Table, Badge)
3. Configurar Tailwind con colores corporativos (#1a5276)
4. Crear tipos TypeScript
5. Configurar cliente API Axios
**Skills**: web-artifacts-builder + theme-factory

### FASE 2 (ALTA): Calendario
1. Hook useCalendario
2. Componente DiaCelda con estados visuales (Tailwind gradients)
3. Página calendario completa (grid responsive)
4. Navegación meses (shadcn/ui Button)
5. Leyenda de colores (shadcn/ui Badge)
**Skills**: frontend-design

### FASE 3 (ALTA): Detalle
1. Página detalle del día
2. Tabla de correspondencias (shadcn/ui Table)
3. Stats cards (shadcn/ui Card + Tailwind)
4. Botón descarga Excel (shadcn/ui Button)
**Skills**: frontend-design

### FASE 4 (MEDIA): Archivos  
1. Componente drag & drop con react-dropzone
2. Validaciones cliente (PDF/JPG/PNG, máx 10MB)
3. Preview con shadcn/ui Card
4. Progress bar (Tailwind animations)
5. Toast notifications (shadcn/ui Toast)
**Skills**: frontend-design

### FASE 5 (MEDIA): Firma Canvas
1. CanvasFirma: HTML5 canvas + mouse + touch
2. Modal con shadcn/ui Dialog
3. Botones: Limpiar, Guardar, Cancelar (shadcn/ui)
4. Conversión canvas → Base64 PNG
5. API Django POST /firmas/guardar/
**Skills**: frontend-design

### FASE 6 (BAJA): Polish
1. Transiciones Tailwind (transition, duration, ease)
2. Loading skeletons con Tailwind animate-pulse
3. Error boundaries React
4. Accesibilidad (aria-labels, focus-visible)
5. Testing responsive (360px, 768px, 1920px)
**Skills**: frontend-design

---

## 🔑 DATOS CLAVE

### Colores Corporativos
```css
Primary: #1a5276       /* Azul principal */
Success: #28a745       /* Verde firmado */
Success Light: #d1e7dd /* Fondo verde */
Warning: #ffc107       /* Amarillo pendiente */
Warning Light: #fff3cd /* Fondo amarillo */
Grey Light: #f1f3f5    /* Sin datos */
Secondary: #0d6efd     /* Hoy (borde azul) */
```

### Estructura Django (Referencia)
```python
class InformeDiarioCorrespondencia:
    fecha: DateField (unique)
    estado: "PENDIENTE" | "FIRMADO"
    total_correspondencias: int
    archivo_firmado: FileField

class Correspondencia:
    numero_radicado: str
    remitente: FK
    asunto: str
    destinatario: FK (User o Oficina)
    firma_recibida: OneToOne FK
```

### API Endpoints Necesarios (Django REST)
```
GET  /api/correspondencia/calendario/informes/?year=2026&month=2
GET  /api/correspondencia/informes/dia/{fecha}/
POST /api/correspondencia/informes/subir-firmado/
POST /api/correspondencia/firmas/guardar/
GET  /api/correspondencia/informes/dia/{fecha}/descargar/
```

---

## 🚨 PUNTOS CRÍTICOS

1. **Canvas Touch**: Usar `touchAction: 'none'` para evitar scroll
2. **Fechas**: Siempre formatear con `date-fns` en español (locale/es)
3. **CORS**: Django debe permitir origen de Next.js
4. **Cookies**: `withCredentials: true` en Axios para sesiones Django
5. **Responsive**: Grid 7 columnas en desktop, ajustable en móvil
6. **Validaciones**: Cliente y servidor (tipos archivo, tamaño 10MB)

---

## 📐 ESTRUCTURA DE CARPETAS

```
src/
├── app/
│   ├── calendario/
│   │   ├── page.tsx              # Vista calendario
│   │   └── [fecha]/page.tsx      # Detalle día
│   └── layout.tsx
├── components/
│   ├── calendario/
│   │   ├── DiaCelda.tsx
│   │   └── LeyendaCalendario.tsx
│   ├── informes/
│   │   ├── TablaCorrespondencias.tsx
│   │   ├── SubirArchivo.tsx
│   │   └── CanvasFirma.tsx
│   └── common/
├── lib/
│   ├── api/
│   │   ├── client.ts              # Axios config
│   │   ├── calendario.ts
│   │   └── informes.ts
│   ├── hooks/
│   │   ├── useCalendario.ts
│   │   └── useInformeDia.ts
│   ├── types/
│   │   └── informes.ts            # TypeScript interfaces
│   └── utils/
└── styles/
    └── theme.ts                    # MUI Theme
```

---

## ✅ CRITERIOS DE ACEPTACIÓN

- [ ] Calendario muestra estados correctos (verde/amarillo/gris)
- [ ] Click en día navega a detalle
- [ ] Tabla de correspondencias responsive
- [ ] Subida de archivos funciona (drag & drop)
- [ ] Firma digital funciona en tablet con touch
- [ ] Descarga de Excel funciona
- [ ] Mobile-first: se ve bien en 360px width
- [ ] Lighthouse score > 90
- [ ] Sin errores TypeScript
- [ ] Sin warnings críticos en console

---

## 🚀 COMANDOS INICIALES

```bash
# Crear proyecto Next.js con Tailwind
npx create-next-app@latest correspondencia-nextjs --typescript --tailwind --app

# Entrar al proyecto
cd correspondencia-nextjs

# Inicializar shadcn/ui
npx shadcn-ui@latest init
# Seleccionar: Default style, Base color (slate)

# Añadir componentes shadcn/ui necesarios
npx shadcn-ui@latest add button card dialog table badge toast

# Instalar dependencias adicionales
npm install axios swr date-fns react-dropzone
npm install -D @types/node

# Iniciar desarrollo
npm run dev
```

---

## 💡 CONSEJOS

1. **Empieza por el calendario**: Es la funcionalidad visual más importante
2. **Usa los ejemplos**: EJEMPLOS_CODIGO_NEXTJS.md tiene código listo
3. **Testea en móvil primero**: Es el objetivo principal
4. **Componentes pequeños**: Divide todo en componentes reutilizables
5. **TypeScript strict**: Usa tipos en todo momento
6. **shadcn/ui consistente**: Usa componentes de la librería, personaliza con Tailwind
7. **Performance**: Lazy load componentes pesados, optimiza canvas
8. **Skills de Claude**: Usa frontend-design en TODOS los componentes para diseño high-end

---

## 📚 REFERENCIAS

- [shadcn/ui Components](https://ui.shadcn.com/docs/components)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Next.js App Router Docs](https://nextjs.org/docs/app)
- [date-fns Format](https://date-fns.org/docs/format)
- [Canvas API MDN](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [React Dropzone](https://react-dropzone.js.org/)

---

## 🎯 OBJETIVO FINAL

Una aplicación Next.js moderna, responsive y mobile-first que permita:
- Ver calendario mensual de informes con estados visuales
- Ver detalle de correspondencias por día
- Subir plantillas firmadas (PDF/imágenes)
- Firmar digitalmente con canvas (táctil)
- Descargar informes en Excel

**Todo consumiendo la API REST de Django existente.**

---

**¡Adelante! Usa TAREAS_CLAUDE_CODE.md como guía paso a paso. 🚀**
