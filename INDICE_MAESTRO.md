# 📚 ÍNDICE MAESTRO - Migración Django → Next.js

## 🎯 OBJETIVO DEL PROYECTO
Migrar el sistema de **Calendario de Informes y Firma de Planillas** desde Django/HTML estatico a un frontend moderno, responsive y optimizado para tablets y moviles.

---

## 🧭 GUIA PRINCIPAL

Usa este mapa como referencia central del proyecto:

- [documentacion/mapa_topologico_archivos.md](documentacion/mapa_topologico_archivos.md)

---

## 📌 CONTEXTO MINIMO

- [GUIA_USO_CLAUDE_CODE.md](GUIA_USO_CLAUDE_CODE.md) (alto nivel)
- [BRIEFING_CLAUDE_CODE.md](BRIEFING_CLAUDE_CODE.md) (contexto general)

---

## 📎 DOCUMENTOS OPCIONALES

Usa solo si necesitas detalle tecnico o una referencia puntual:

- [CONTEXTO_MIGRACION_NEXTJS.md](CONTEXTO_MIGRACION_NEXTJS.md)
- [EJEMPLOS_CODIGO_NEXTJS.md](EJEMPLOS_CODIGO_NEXTJS.md)
- [TAREAS_CLAUDE_CODE.md](TAREAS_CLAUDE_CODE.md)
- [DJANGO_REST_API_PLAN.md](DJANGO_REST_API_PLAN.md)
    └── next.config.js
```

---

## 🎯 ALCANCE DEL PROYECTO

### ✅ Lo que SE migra a Next.js:
- Vista de calendario mensual
- Detalle del día con lista de correspondencias
- Sistema de firma digital (canvas)
- Subida de archivos firmados (PDF/imágenes)
- Descarga de informes Excel
- UI responsive para tablets y móviles

### ❌ Lo que NO se migra (permanece en Django):
- Toda la lógica de negocio
- Base de datos y modelos
- Autenticación y permisos
- Generación de archivos Excel
- Sistema de radicación
- Otras funcionalidades del sistema

---

## 🔑 DATOS TÉCNICOS CLAVE

### Stack Tecnológico
| Capa | Tecnología | Versión |
|------|-----------|---------|
| Frontend Framework | Next.js | 14+ (App Router) |
| Lenguaje | TypeScript | 5+ |
| UI Library | Material-UI | 5+ |
| HTTP Client | Axios | 1.6+ |
| Data Fetching | SWR | 2.2+ |
| Date Utils | date-fns | 3.0+ |
| File Upload | react-dropzone | 14+ |
| Backend API | Django REST Framework | 3.14+ |
| CORS | django-cors-headers | 4+ |

### Responsive Breakpoints
- **Móvil**: 0-600px (1 columna)
- **Tablet**: 600-960px (2 columnas o scroll)
- **Desktop**: 960px+ (calendario completo 7 columnas)

### Colores Corporativos
```css
--primary: #1a5276        /* Azul principal */
--success: #28a745        /* Verde firmado */
--success-light: #d1e7dd  /* Fondo verde */
--warning: #ffc107        /* Amarillo pendiente */
--warning-light: #fff3cd  /* Fondo amarillo */
--grey-light: #f1f3f5     /* Sin datos */
--secondary: #0d6efd      /* Hoy (borde) */
```

---

## ⏱️ ESTIMACIÓN DE TIEMPO

### Por Fase (trabajo con Claude Code)
| Fase | Descripción | Tiempo Estimado |
|------|------------|-----------------|
| 1 | Setup proyecto + dependencias | 30 min |
| 2 | API Client + Types | 30 min |
| 3 | Hooks personalizados | 45 min |
| 4 | Calendario completo | 2 horas |
| 5 | Detalle del día | 2 horas |
| 6 | Firma digital | 1.5 horas |
| 7 | Auth + seguridad | 45 min |
| 8 | Responsive + UX | 1 hora |
| 9 | Testing | 1 hora |
| 10 | Deploy + docs | 45 min |
| **TOTAL** | | **~11 horas** |

### Backend Django (API REST)
- Implementación: 2-3 horas
- Testing: 1 hora
- **Total**: ~4 horas

### **GRAN TOTAL: ~15 horas** (2 días full-time o 1 semana part-time)

---

## ✅ CRITERIOS DE ÉXITO

### Funcionales
- [ ] Calendario muestra estados correctos (verde/amarillo/gris)
- [ ] Navegación entre meses funciona
- [ ] Click en día abre detalle correcto
- [ ] Tabla muestra todas las correspondencias
- [ ] Subida de archivos funciona (validaciones + preview)
- [ ] Firma digital funciona con mouse
- [ ] Firma digital funciona con touch en tablet
- [ ] Descarga de Excel funciona
- [ ] Todas las validaciones cliente funcionan

### Técnicos
- [ ] Build de Next.js sin errores
- [ ] Sin errores TypeScript
- [ ] Sin warnings críticos en console
- [ ] Lighthouse score > 90
- [ ] First Contentful Paint < 1.5s
- [ ] Funciona en Chrome, Safari, Firefox, Edge

### UX/Responsive
- [ ] Funciona en móvil (360px width)
- [ ] Funciona en tablet (768px width)
- [ ] Funciona en desktop (1920px+)
- [ ] Touch events funcionan en tablet
- [ ] Transiciones suaves
- [ ] Loading states claros
- [ ] Mensajes de error amigables

---

## 🆘 SOPORTE Y TROUBLESHOOTING

### Problemas Comunes

#### Frontend (Next.js)
- **Error CORS**: Ver DJANGO_REST_API_PLAN.md sección Troubleshooting
- **Cookies no se envían**: `withCredentials: true` en Axios
- **Canvas no dibuja**: Verificar touch events y `touchAction: 'none'`
- **Build falla**: Revisar tipos TypeScript

#### Backend (Django)
- **403 Forbidden**: Usuario no en grupo Ventanilla
- **CORS blocked**: Verificar CORS_ALLOWED_ORIGINS
- **Sesión no válida**: Verificar cookies SAMESITE y SECURE

### Contacto
- Revisar documentación específica
- Buscar en el archivo correspondiente según el problema
- Usar Claude Code para debugging específico

---

## 📦 ENTREGABLES FINALES

### Código
- [ ] Repositorio Next.js con código completo
- [ ] API Views de Django implementadas
- [ ] Serializers de Django
- [ ] Configuración CORS

### Documentación
- [ ] README.md con instrucciones de setup
- [ ] Documentación de API (opcional: Swagger)
- [ ] Variables de entorno documentadas
- [ ] Guía de deploy

### Testing
- [ ] Capturas de pantalla en diferentes dispositivos
- [ ] Video demo de funcionalidad principal
- [ ] Reporte de Lighthouse

---

## 🎓 RECURSOS DE APRENDIZAJE

### Oficial Documentation
- [Next.js Docs](https://nextjs.org/docs)
- [Material-UI Docs](https://mui.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

### Tutoriales Relevantes
- [Next.js App Router Tutorial](https://nextjs.org/learn)
- [MUI Responsive Design](https://mui.com/material-ui/guides/responsive-design/)
- [Canvas API Touch Events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)

---

## 📝 GLOSARIO

| Término | Definición |
|---------|-----------|
| **Informe Diario** | Documento (Excel) con todas las correspondencias de un día específico |
| **Planilla** | Sinónimo de Informe Diario |
| **Firma Digital** | Firma dibujada en canvas y guardada como imagen Base64 |
| **Archivo Firmado** | PDF o imagen escaneada de la planilla con firmas físicas |
| **Radicado** | Número único de correspondencia (ej: E-2026-001234) |
| **TRD** | Tabla de Retención Documental |
| **Ventanilla** | Grupo de usuarios con permisos para gestionar informes |

---

## 📞 PRÓXIMOS PASOS

### 1. Preparación (10 min)
- [ ] Leer GUIA_USO_CLAUDE_CODE.md
- [ ] Leer BRIEFING_CLAUDE_CODE.md
- [ ] Verificar Node.js y npm instalados ✅
- [ ] Preparar workspace

### 2. Backend (2-3 horas)
- [ ] Seguir DJANGO_REST_API_PLAN.md
- [ ] Implementar serializers
- [ ] Implementar API views
- [ ] Configurar CORS
- [ ] Probar endpoints con curl

### 3. Frontend (8-10 horas)
- [ ] Usar Claude Code siguiendo TAREAS_CLAUDE_CODE.md
- [ ] Implementar fase por fase
- [ ] Validar después de cada componente
- [ ] Testing responsive continuo

### 4. Integración (1 hora)
- [ ] Conectar Next.js con API Django
- [ ] Probar flujo completo
- [ ] Resolver issues de CORS/cookies

### 5. Deploy (1 hora)
- [ ] Build de producción
- [ ] Deploy a Vercel o servidor Node.js
- [ ] Configurar variables de entorno producción
- [ ] Testing en producción

---

## 🏆 CONCLUSIÓN

Este proyecto tiene:
- ✅ **Documentación completa** (6 archivos, 1500+ líneas)
- ✅ **Código de ejemplo listo** para copy-paste
- ✅ **Checklist detallado** (60+ tareas)
- ✅ **Guía paso a paso** para Claude Code
- ✅ **Plan de backend** (Django REST API)
- ✅ **Estimaciones de tiempo** realistas
- ✅ **Criterios de éxito** claros

**Todo está preparado para que Claude Code pueda ayudarte eficientemente. 🚀**

---

## 📅 Información del Documento

- **Creado**: 17 de febrero de 2026
- **Versión**: 1.0
- **Autor**: Sistema de documentación
- **Propósito**: Índice maestro de la migración Django → Next.js
- **Audiencia**: Desarrolladores, Claude Code, Project Managers

---

**¡Éxito en tu migración! 🎉**

*Comienza leyendo [GUIA_USO_CLAUDE_CODE.md](./GUIA_USO_CLAUDE_CODE.md)*
