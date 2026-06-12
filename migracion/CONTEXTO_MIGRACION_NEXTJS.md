# 🎯 Contexto para Migración Django → Next.js
## Sistema de Calendario de Informes y Firma de Planillas

Nota: Este documento es referencia opcional. La guia principal es documentacion/mapa_topologico_archivos.md.

---

## 🎨 SKILLS DE CLAUDE OBLIGATORIAS

**Usa estas 3 agent skills en TODAS las fases de desarrollo**:

- 🎨 **frontend-design**: Diseño high-end profesional, evita estética genérica AI
- 🎭 **theme-factory**: Sistema de diseño coherente con colores corporativos  
- 🏗️ **web-artifacts-builder**: Arquitectura React + Tailwind CSS + shadcn/ui

---

## 📋 OBJETIVO
Migrar la funcionalidad de calendario de informes diarios y firma de planillas desde Django/HTML estático a Next.js con **Tailwind CSS + shadcn/ui**, optimizado para tablets y móviles con diseño profesional distintivo.

---

## 🏗️ ARQUITECTURA DEFINIDA

### Backend Strategy
- **Enfoque**: Next.js como frontend puro consumiendo API REST de Django
- **Backend actual**: Django continúa manejando toda la lógica de negocio
- **Comunicación**: API REST endpoints desde Django (Django REST Framework)

### Autenticación
- **Método**: Reutilizar sesiones Django existentes (cookies/tokens)
- **Usuario**: Sistema ya tiene django.contrib.auth
- **Permisos**: Grupo 'Ventanilla' tiene acceso

### UI Framework
- **Librería**: Tailwind CSS v3 + shadcn/ui
- **Responsive**: Mobile-first approach (sm:, md:, lg:, xl:)
- **Tema**: Corporativo (azules: #1a5276, #0d6efd)
- **Diseño**: High-end profesional (skills: frontend-design + theme-factory)

---

## 📦 FUNCIONALIDADES A MIGRAR

### ✅ 1. Vista de Calendario Mensual
**Ruta Django Actual**: `/informes/calendario/`
**Vista**: `calendario_informes_view` (views.py línea 8968)

**Características**:
- Calendario mensual completo
- Navegación entre meses (anterior/siguiente)
- Estados visuales por día:
  - ✅ **Firmado** (verde #d1e7dd): Informe tiene archivo firmado
  - ⏱️ **Pendiente Firma** (amarillo #fff3cd): Tiene correspondencias sin firma
  - ⬜ **Sin Registros** (gris #f1f3f5): Sin correspondencias ese día
  - 🔵 **Hoy** (borde azul #0d6efd)
  - 📅 **Días de otro mes** (gris deshabilitado)
- Badge con cantidad de correspondencias por día
- Check icon (✓ verde) cuando está firmado
- Click en día → Redirige a detalle

**Datos que necesita**:
```javascript
// Por cada día del mes:
{
  fecha: "2026-02-17",
  es_mes_actual: true,
  es_hoy: true,
  es_futuro: false,
  total_correspondencias: 12,
  informe: {
    estado: "FIRMADO" | "PENDIENTE",
    archivo_firmado_url: "/media/...",
    fecha_subida_firma: "2026-02-17T10:30:00Z"
  }
}
```

### ✅ 2. Detalle del Día
**Ruta Django Actual**: `/informes/dia/<fecha>/`
**Vista**: `detalle_dia_informe` (views.py línea 9215)

**Características**:
- Header con fecha formateada y estado del informe
- Estadísticas:
  - Total de correspondencias
  - Número de descargas del informe
  - Firmas recibidas vs pendientes (X/Y)
  - Porcentaje de completitud
- Tabla de correspondencias del día:
  - Radicado (clickeable → detalle correspondencia)
  - Remitente
  - Asunto
  - Destinatario (Oficina/Usuario)
  - Estado de firma (✅ firmada / ⏱️ pendiente)
  - Acción: Modal de firma digital
- Botones de acción:
  - Ver Excel (descarga informe del día)
  - Subir archivo firmado (PDF/JPG/PNG)
  - Recolectar firmas digitalmente
- Historial de descargas (últimas 10)

**Datos que necesita**:
```javascript
{
  fecha: "2026-02-17",
  informe: {
    id: 123,
    estado: "PENDIENTE",
    total_correspondencias: 12,
    archivo_firmado: null
  },
  correspondencias: [
    {
      id: 456,
      numero_radicado: "E-2026-001234",
      remitente: "Alcaldía Municipal",
      asunto: "Solicitud de información...",
      destinatario: "Dirección Administrativa",
      tiene_firma: false,
      requiere_firma: true,
      fecha_radicacion: "2026-02-17T09:15:00Z"
    }
  ],
  historial_descargas: [
    {
      usuario: "Juan Pérez",
      fecha_descarga: "2026-02-17T14:30:00Z",
      tipo_formato: "Excel"
    }
  ],
  stats_firmas: {
    total: 12,
    firmadas: 8,
    pendientes: 4,
    porcentaje: 66.7
  }
}
```

### ✅ 3. Firma de Informes
**Funcionalidades**:

#### A. Subida de Archivo Firmado
**Endpoint Django**: `POST /informes/subir-firmado/`
**Vista**: `subir_informe_firmado` (views.py línea 9060)

- Drag & drop o selector de archivo
- Validaciones:
  - Tipos permitidos: PDF, JPG, PNG
  - Tamaño máximo: 10MB
- Preview del archivo actual (si existe)
- Confirmación de reemplazo

#### B. Recolección de Firmas Digitales
**Características**:
- Canvas HTML5 para dibujar firma
- Soporte táctil (touch events)
- Botones: Limpiar, Guardar, Cancelar
- Vista previa de firma guardada
- Modal por cada correspondencia
- Almacenamiento: Base64 PNG en modelo FirmaRecibida

---

## 🗄️ MODELOS DJANGO (Base de Datos)

### InformeDiarioCorrespondencia
```python
class InformeDiarioCorrespondencia(models.Model):
    fecha = models.DateField(unique=True)  # Una planilla por día
    archivo_firmado = models.FileField(
        upload_to='informes/firmados/%Y/%m/',
        null=True, blank=True
    )
    estado = models.CharField(
        max_length=20,
        choices=[('PENDIENTE', 'Pendiente'), ('FIRMADO', 'Firmado')],
        default='PENDIENTE'
    )
    total_correspondencias = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_subida_firma = models.DateTimeField(null=True, blank=True)
    subido_por = models.ForeignKey(User, ...)
```

### Correspondencia (Modelo Principal)
```python
class Correspondencia(models.Model):
    numero_radicado = models.CharField(max_length=50, unique=True)
    tipo_radicado = models.CharField(
        choices=[('ENTRANTE', 'Entrante'), ('SALIENTE', 'Saliente'), ...]
    )
    fecha_radicacion = models.DateTimeField()
    remitente = models.ForeignKey(ContactoEntidadExterna, ...)
    asunto = models.TextField()
    
    # Destinatario (uno de los dos)
    usuario_destino_inicial = models.ForeignKey(User, ...)
    oficina_destino = models.ForeignKey(Oficina, ...)
    
    # Relación con firma
    # firma_recibida → FirmaRecibida (One-to-One reverse)
```

### FirmaRecibida
```python
class FirmaRecibida(models.Model):
    correspondencia = models.OneToOneField(Correspondencia, ...)
    firma_imagen = models.TextField(help_text="Base64 PNG de la firma")
    fecha_firma = models.DateTimeField(auto_now_add=True)
    firmado_por = models.ForeignKey(User, ...)
```

---

## 🔌 ENDPOINTS API NECESARIOS (Django REST Framework)

### 📅 Calendario
```
GET /api/correspondencia/calendario/informes/
Query params:
  - year: int (default: año actual)
  - month: int (default: mes actual)

Response: {
  year: 2026,
  month: 2,
  month_name: "Febrero",
  prev_month: 1, prev_year: 2026,
  next_month: 3, next_year: 2026,
  dias: [
    {
      fecha: "2026-02-01",
      es_mes_actual: true,
      es_hoy: false,
      es_futuro: false,
      total_correspondencias: 5,
      tiene_correspondencias: true,
      informe: {
        id: 100,
        estado: "FIRMADO",
        tiene_archivo: true
      }
    },
    ...
  ]
}
```

### 📋 Detalle del Día
```
GET /api/correspondencia/informes/dia/<fecha>/
Params: fecha (formato YYYY-MM-DD)

Response: {
  fecha: "2026-02-17",
  informe: { ... },
  correspondencias: [ ... ],
  historial_descargas: [ ... ],
  stats_firmas: { ... }
}
```

### 📤 Subir Archivo Firmado
```
POST /api/correspondencia/informes/subir-firmado/
Content-Type: multipart/form-data
Body:
  - fecha: "2026-02-17"
  - archivo_firmado: <file>

Response: {
  success: true,
  message: "Archivo subido correctamente",
  informe: { ... }
}
```

### ✍️ Guardar Firma Digital
```
POST /api/correspondencia/firmas/guardar/
Content-Type: application/json
Body: {
  correspondencia_id: 456,
  firma_base64: "data:image/png;base64,iVBORw0KGgoA..."
}

Response: {
  success: true,
  firma_id: 789,
  correspondencia_id: 456
}
```

### 📥 Descargar Excel del Día
```
GET /api/correspondencia/informes/dia/<fecha>/descargar/
Response: application/vnd.openxmlformats... (archivo Excel)
Headers:
  Content-Disposition: attachment; filename="informe_2026-02-17.xlsx"
```

---

## 🎨 GUÍA DE DISEÑO UI/UX

### Paleta de Colores
```css
--primary: #1a5276;        /* Azul corporativo principal */
--primary-light: #2874a6;  /* Azul claro */
--secondary: #0d6efd;      /* Azul acento (hoy) */
--success: #28a745;        /* Verde firmado */
--success-bg: #d1e7dd;     /* Fondo verde claro */
--warning: #ffc107;        /* Amarillo pendiente */
--warning-bg: #fff3cd;     /* Fondo amarillo claro */
--gray-light: #f1f3f5;     /* Sin registros */
--gray: #6c757d;           /* Texto secundario */
--border: #dee2e6;         /* Bordes */
```

### Componentes shadcn/ui a Usar
- **Calendar**: Custom Grid con shadcn Card components + Tailwind grid
- **Tabla**: shadcn Table component con sorting
- **Modal**: shadcn Dialog component
- **Upload**: react-dropzone + shadcn Button
- **Stats**: shadcn Card con grid Tailwind
- **Canvas Firma**: HTML5 Canvas + shadcn Dialog container
- **Badges**: shadcn Badge component
- **Navigation**: shadcn Button con Lucide React icons (ChevronLeft/Right)
- **Toast**: shadcn Toast / Sonner para notificaciones

**Skill**: Usa **frontend-design** en cada componente para diseño distintivo

### Responsive Breakpoints
```javascript
{
  mobile: '0-600px',     // 1 col
  tablet: '600-960px',   // 2 cols
  desktop: '960px+',     // Full calendar
}
```

---

## 🔐 PERMISOS Y SEGURIDAD

### Grupo Requerido
- **Django Group**: 'Ventanilla'
- **Decorator actual**: `@user_passes_test(lambda u: u.groups.filter(name='Ventanilla').exists())`

### Validaciones Backend
- Usuario autenticado
- Usuario en grupo Ventanilla
- Validación de tipos de archivo (MIME type)
- Validación de tamaño (10MB máx)
- CSRF protection en Django

### Next.js Middleware
```javascript
// middleware.ts
// Verificar token/sesión Django
// Redirigir a login si no autenticado
// Verificar permisos del grupo
```

---

## 📁 ESTRUCTURA DE ARCHIVOS SUGERIDA

```
nextjs-correspondencia/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx
│   ├── calendario/
│   │   ├── page.tsx                    # Vista calendario
│   │   └── [fecha]/page.tsx            # Detalle día
│   └── layout.tsx
├── components/
│   ├── ui/                              # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── table.tsx
│   │   ├── badge.tsx
│   │   └── toast.tsx
│   ├── calendario/
│   │   ├── CalendarioMensual.tsx      # Componente principal
│   │   ├── DiaCelda.tsx               # Cada celda del día
│   │   ├── LeyendaCalendario.tsx      # Leyenda inferior
│   │   └── NavegacionMeses.tsx        # Botones anterior/siguiente
│   ├── informes/
│   │   ├── DetalleInforme.tsx         # Card con info del informe
│   │   ├── TablaCorrespondencias.tsx  # shadcn Table
│   │   ├── SubirArchivo.tsx           # react-dropzone component
│   │   ├── ModalFirma.tsx             # shadcn Dialog con canvas
│   │   └── CanvasFirma.tsx            # Canvas HTML5 para firmar
│   └── common/
│       ├── Layout.tsx
│       ├── ErrorBoundary.tsx
│       └── LoadingSpinner.tsx
├── lib/
│   ├── api/
│   │   ├── calendario.ts              # Llamadas API calendario
│   │   ├── informes.ts                # Llamadas API informes
│   │   └── firmas.ts                  # Llamadas API firmas
│   ├── hooks/
│   │   ├── useCalendario.ts           # Hook custom calendario
│   │   ├── useInformeDia.ts           # Hook detalle día
│   │   └── useFirmaCanvas.ts          # Hook manejo firma
│   ├── types/
│   │   └── informes.ts                # TypeScript interfaces
│   └── utils/
│       ├── dateUtils.ts               # Formateo fechas
│       ├── validations.ts             # Validaciones cliente
│       └── cn.ts                      # Tailwind class merger
├── public/
└── styles/
    └── globals.css                     # Tailwind + Custom CSS
```

---

## 🚀 ROADMAP DE IMPLEMENTACIÓN

### Fase 1: Setup & API (Django)
1. Instalar Django REST Framework
2. Crear serializers (InformeDiarioSerializer, CorrespondenciaSerializer)
3. Crear ViewSets/APIViews
4. Configurar CORS
5. Testing endpoints con Postman/Thunder Client

### Fase 2: Setup Next.js
1. `npx create-next-app@latest --typescript --tailwind`
2. Inicializar shadcn/ui: `npx shadcn-ui@latest init`
3. Añadir componentes: `npx shadcn-ui@latest add button card dialog table badge toast`
4. Configurar Tailwind con colores corporativos (tailwind.config.ts)
5. Setup axios para API calls
6. Crear estructura de carpetas
**Skill**: web-artifacts-builder + theme-factory

### Fase 3: Calendario
1. Componente CalendarioMensual con shadcn Card
2. Lógica de generación de días del mes
3. Estados visuales con Tailwind (bg-green-100, bg-yellow-100, etc.)
4. Navegación con shadcn Button + Lucide icons
5. Grid responsive con Tailwind (grid-cols-7, sm:grid-cols-1)
**Skill**: frontend-design

### Fase 4: Detalle del Día
1. Page dinámica [fecha]
2. Componente DetalleInforme con shadcn Card
3. TablaCorrespondencias con shadcn Table (responsive)
4. Estadísticas con shadcn Cards + Tailwind grid
5. Historial de descargas
**Skill**: frontend-design

### Fase 5: Subida de Archivos
1. Componente SubirArchivo con react-dropzone
2. Preview con shadcn Card
3. Validaciones cliente (tipo, tamaño)
4. Progress bar con Tailwind animations
5. Toast notifications con shadcn Toast
**Skill**: frontend-design

### Fase 6: Firma Digital
1. ModalFirma con shadcn Dialog
2. CanvasFirma con HTML5 Canvas + touch support
3. Conversión canvas → Base64 PNG
4. Preview de firma con shadcn Card
5. API integration con validaciones
**Skill**: frontend-design

### Fase 7: Testing & Deploy
1. Testing en móviles/tablets
2. Optimización performance
3. Accesibilidad (WCAG)
4. Build producción
5. Deploy (Vercel/Node.js)

---

## 🧪 CASOS DE PRUEBA IMPORTANTES

### Calendario
- [ ] Días de meses pasados clickeables
- [ ] Días futuros NO clickeables
- [ ] Correcta visualización en mobile (scroll horizontal)
- [ ] Estados visuales correctos
- [ ] Navegación fluida entre meses

### Detalle
- [ ] Tabla responsive en móvil
- [ ] Ordenamiento de columnas funciona
- [ ] Descarga de Excel funciona
- [ ] Modal de firma se abre correctamente

### Firma Canvas
- [ ] Dibujo fluido con mouse
- [ ] Touch events funcionan en tablet/móvil
- [ ] Botón limpiar funciona
- [ ] Guardado genera Base64 válido
- [ ] Se guarda correctamente en BD

### Subida Archivo
- [ ] Drag & drop funciona
- [ ] Validación de tipo archivo
- [ ] Validación de tamaño
- [ ] Preview se muestra
- [ ] Reemplazo de archivo confirma

---

## 📚 RECURSOS Y REFERENCIAS

### Documentación
- [shadcn/ui Components](https://ui.shadcn.com/docs/components)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [HTML Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [Lucide React Icons](https://lucide.dev/)

### Librerías Útiles
```json
{
  "react-dropzone": "^14.2.3",        // Subida de archivos drag & drop
  "date-fns": "^3.0.0",               // Manejo y formato de fechas
  "axios": "^1.6.0",                  // HTTP client
  "swr": "^2.2.4",                    // Data fetching con cache
  "lucide-react": "^0.300.0",         // Iconos (incluido en shadcn/ui)
  "class-variance-authority": "^0.7.0", // CVA para variants
  "clsx": "^2.0.0",                   // Conditional classes
  "tailwind-merge": "^2.0.0"          // Merge Tailwind classes
}
```

### Archivos Clave Django Actuales
- `correspondencia/views.py` → líneas 8968-9320
- `correspondencia/models.py` → líneas 1581-1630
- `correspondencia/templates/correspondencia/admin/calendario_informes.html`
- `correspondencia/templates/correspondencia/admin/detalle_dia_informe.html`
- `correspondencia/urls.py` → línea 148

---

## ⚠️ NOTAS IMPORTANTES

1. **Seguridad**: NUNCA exponer API keys en frontend
2. **Performance**: Implementar lazy loading en tabla de correspondencias
3. **UX Móvil**: Priorizar gestures naturales (swipe para cambiar mes)
4. **Offline**: Considerar Service Worker para funcionamiento offline básico
5. **Accesibilidad**: Todos los componentes deben ser navegables por teclado
6. **Browser Support**: Chrome, Safari, Firefox, Edge (últimas 2 versiones)

---

## 🎯 OBJETIVOS DE RENDIMIENTO

- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Lighthouse Score: > 90
- Mobile-friendly test: Pass
- Core Web Vitals: All green

---

## 💬 PREGUNTAS FRECUENTES

**P: ¿Mantenemos la funcionalidad de historial de descargas?**
R: Sí, se mantiene en la sección de detalle del día.

**P: ¿La firma digital reemplaza la subida de archivo?**
R: No, son complementarias. Firma digital es para firmas individuales por correspondencia, archivo escaneado es para la planilla completa firmada físicamente.

**P: ¿Qué pasa si Django está caído?**
R: Next.js debe mostrar error amigable y permitir retry. Considerar cache con SWR.

**P: ¿Soporte para navegadores antiguos?**
R: No. Solo últimas 2 versiones de navegadores modernos.

---

**Documento creado**: 17 de febrero de 2026
**Versión**: 1.0
**Para**: Claude Code Migration Task
