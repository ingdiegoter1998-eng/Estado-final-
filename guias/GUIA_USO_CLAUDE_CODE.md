# 🎓 CÓMO USAR CLAUDE CODE PARA ESTA TAREA

## 🎨 SKILLS DE CLAUDE

Usa estas tres skills como prefieras, sin imponer flujo ni stack:

- frontend-design
- theme-factory
- web-artifacts-builder

---

## 📚 ORDEN DE LECTURA (Alto nivel)

Lee solo estos dos archivos y decide el resto con criterio propio:

1. **`documentacion/mapa_topologico_archivos.md`** ← GUIA PRINCIPAL
2. **`BRIEFING_CLAUDE_CODE.md`** (solo contexto general, no impone stack)

---

## 🚀 COMANDO INICIAL PARA CLAUDE CODE

```bash
cd /home/devdiego
claude "Lee documentacion/mapa_topologico_archivos.md. Usa tus 3 skills como prefieras. Define el stack y el plan de migracion con criterio propio. Pregunta si necesitas aclaraciones."
```

---

## ✅ INSTRUCCION DE ALTO NIVEL

- Usa el mapa topologico como guia principal.
- Define el stack y el plan de migracion con criterio propio.
- Aplica las 3 skills segun convenga, sin restricciones.
- Pregunta si faltan requisitos funcionales o de negocio.

---

## 🔍 VERIFICACIONES ENTRE FASES

Después de cada fase, verifica:

```bash
# 1. No errores TypeScript
npm run build

# 2. No errores de linting
npm run lint

# 3. Servidor dev funciona
npm run dev

# 4. Revisar console del navegador (F12)
# Sin errores rojos, solo warnings esperados
```

---

## 🆘 SI CLAUDE CODE SE BLOQUEA

### Opción 1: Dividir tarea más pequeña
En lugar de:
> "Implementa toda la funcionalidad de detalle del día"

Usa:
> "Primero crea solo el hook useInformeDia que haga fetch de la API"

### Opción 2: Proporcionar código existente
> "Aquí está el código del componente X que funciona. Ahora crea un componente similar Y pero para Z funcionalidad"

### Opción 3: Debugging específico
> "El componente DiaCelda no está mostrando los colores correctos. Aquí está el código actual [pega código]. Compáralo con EJEMPLOS_CODIGO_NEXTJS.md y corrige los errores"

### Opción 4: Referencia a ejemplos
> "Implementa TablaCorrespondencias siguiendo EXACTAMENTE el ejemplo en EJEMPLOS_CODIGO_NEXTJS.md líneas 250-350"

---

## 📊 TRACKING DE PROGRESO

Usa el archivo TAREAS_CLAUDE_CODE.md como checklist:

```markdown
# FASE 1: Setup
- [x] Tarea 1.1: Crear proyecto Next.js
- [x] Tarea 1.2: Instalar dependencias
- [ ] Tarea 1.3: Configurar carpetas
- [ ] Tarea 1.4: Crear tema MUI
```

Actualiza después de cada sesión con Claude Code.

---

## 🎭 ROL DE CLAUDE CODE

Claude Code actúa como:
- **Desarrollador Frontend Senior**: Escribe código TypeScript/React
- **Arquitecto**: Estructura componentes y hooks
- **Code Reviewer**: Revisa y mejora código existente
- **Debugger**: Encuentra y corrige errores

NO actúa como:
- **Diseñador UX**: Los diseños ya están definidos
- **Backend Developer**: Django ya existe
- **Project Manager**: Tú defines las prioridades

---

## 💡 TIPS PARA MEJORES RESULTADOS

1. **Sé específico**: 
   ❌ "Crea el calendario"
   ✅ "Crea el componente DiaCelda siguiendo la especificación en EJEMPLOS_CODIGO_NEXTJS.md líneas 180-250"

2. **Proporciona contexto**: 
   Siempre menciona qué archivo de documentación usar como referencia

3. **Usa ejemplos**: 
   Los ejemplos de código son tu mejor amigo, pide a Claude que los siga fielmente

4. **Valida frecuentemente**: 
   Después de cada componente, prueba que funcione antes de seguir

5. **Itera pequeño**: 
   1 componente → probar → siguiente componente
   NO: 5 componentes juntos → probar

---

## 🎬 EJEMPLO DE SESIÓN COMPLETA

```bash
# Sesión 1: Setup (30 min)
claude "Lee BRIEFING_CLAUDE_CODE.md y ejecuta tareas 1.1 a 1.5 de TAREAS_CLAUDE_CODE.md"

# Verificar
cd correspondencia-nextjs && npm run dev
# Abrir http://localhost:3000

# Sesión 2: Calendario Base (45 min)
claude "Implementa tareas 4.1 a 4.4 usando código de EJEMPLOS_CODIGO_NEXTJS.md"

# Verificar
# ¿Se ve el calendario? ¿Los colores son correctos?

# Sesión 3: Detalle Día (60 min)
claude "Implementa tareas 5.1 a 5.6 para vista detalle día"

# Verificar
# ¿Navegar desde calendario funciona? ¿Se muestran datos?

# ... continuar así hasta completar todas las fases
```

---

## 🏁 CRITERIO DE "TERMINADO"

La migración está completa cuando:
- ✅ Calendario se ve y funciona igual (o mejor) que versión Django
- ✅ Detalle del día muestra todos los datos correctamente
- ✅ Subida de archivos funciona
- ✅ Firma digital funciona en tablet con touch
- ✅ Descarga de Excel funciona
- ✅ No hay errores TypeScript
- ✅ Build de producción exitoso
- ✅ Funciona en móvil (360px width)
- ✅ Funciona en tablet (768px width)
- ✅ Funciona en desktop (1920px width)

---

## 📞 PREGUNTAS FRECUENTES

**P: ¿Qué hago si Claude Code sugiere una librería diferente?**
R: Si mejora la funcionalidad y no rompe compatibilidad, acepta. Sino, insiste en usar lo especificado (react-dropzone, MUI, etc.)

**P: ¿Puedo cambiar el diseño visual?**
R: Solo mejoras sutiles. Los colores y estructura general deben seguir CONTEXTO_MIGRACION_NEXTJS.md

**P: ¿Qué hago si hay conflicto entre documentos?**
R: Orden de prioridad: BRIEFING > EJEMPLOS > CONTEXTO > TAREAS

**P: ¿Debo crear tests unitarios?**
R: No es prioridad, pero si Claude Code los sugiere para componentes complejos, acepta.

**P: ¿Qué hago con los archivos Django originales?**
R: MANTENERLOS INTACTOS. Next.js no los reemplaza, convive con ellos.

---

## ✅ CHECKLIST PRE-INICIO

Antes de empezar con Claude Code:

- [ ] He leído BRIEFING_CLAUDE_CODE.md completo
- [ ] He revisado CONTEXTO_MIGRACION_NEXTJS.md
- [ ] He revisado EJEMPLOS_CODIGO_NEXTJS.md  
- [ ] Tengo Node.js instalado (✅ ya está)
- [ ] Tengo npm funcionando (✅ ya está)
- [ ] He creado carpeta para el proyecto
- [ ] Tengo acceso a Claude Code
- [ ] Tengo tiempo para sesión de al menos 30 min

---

## 🚀 COMANDO PARA EMPEZAR YA

```bash
cd /home/devdiego
claude "Hola! Voy a pedirte que me ayudes a migrar una funcionalidad de Django a Next.js. 

PASO 1: Lee estos archivos en orden:
1. BRIEFING_CLAUDE_CODE.md
2. CONTEXTO_MIGRACION_NEXTJS.md  
3. EJEMPLOS_CODIGO_NEXTJS.md
4. TAREAS_CLAUDE_CODE.md

PASO 2: Después de leerlos, confirma que entendiste el objetivo y pregúntame si tienes dudas.

PASO 3: Comenzaremos con la Fase 1 del checklist (Setup del Proyecto).

¿Listo? Empieza leyendo los archivos."
```

---

**¡Buena suerte con Claude Code! 🎉**

Recuerda: **Documentación → Planificación → Ejecución → Validación → Siguiente fase**
