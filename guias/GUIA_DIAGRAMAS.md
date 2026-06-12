# 🎨 GUÍA PRÁCTICA: Cómo Crear Diagramas para tu Presentación

## 🎯 OBJETIVO

Crear diagramas visuales profesionales que puedas incluir en tus diapositivas para explicar el sistema a los directivos.

---

## 🛠️ HERRAMIENTAS RECOMENDADAS

### **1. Draw.io (diagrams.net)** ⭐ **LA MEJOR**

**Por qué:**
- Gratis, sin registro
- Funciona offline
- Exporta a PNG de alta calidad
- Plantillas profesionales

**Cómo usar:**

1. **Abre:** https://app.diagrams.net/
2. **Elige:** "Create New Diagram"
3. **Selecciona:** Blank Diagram
4. **Panel izquierdo:** Arrastra formas
5. **Exportar:** File → Export as → PNG

**Plantillas útiles:**
- Entity Relation Diagram (para modelos de BD)
- Flowchart (para procesos)
- UML Class Diagram (para modelos Django)

---

### **2. Mermaid Live Editor**

**Por qué:**
- Diagramas con código (fácil de editar)
- Perfecto para diagramas de flujo

**Cómo usar:**

1. **Abre:** https://mermaid.live/
2. **Pega** el código que te di en DIAGRAMA_MODELOS.md
3. **Edita** el código según necesites
4. **Exporta:** PNG o SVG

---

### **3. Excalidraw**

**Por qué:**
- Estilo "dibujado a mano" (moderno)
- Muy rápido para bocetos

**Cómo usar:**

1. **Abre:** https://excalidraw.com/
2. **Dibuja** con las herramientas
3. **Exporta:** PNG

---

## 📊 DIAGRAMAS QUE DEBES CREAR

### **1. DIAGRAMA DE FLUJO: RADICACIÓN**

**Para explicar:** Cómo se radica un documento

**Herramienta:** Draw.io (Flowchart)

**Pasos:**

```
Inicio
  ↓
Llega documento (físico/email)
  ↓
¿Es correo electrónico? → NO → Radicación manual
  ↓ SÍ
Se guarda en CorreoEntrante
  ↓
Usuario revisa y radica
  ↓
Se crea Correspondencia
  ↓
Sistema genera número radicado
  ↓
Se asigna a OficinaProductora
  ↓
Se calcula fecha límite SLA
  ↓
Se crea HistorialCorrespondencia
  ↓
Aparece en Bandeja de Oficina
  ↓
Fin
```

**Cómo hacerlo en Draw.io:**

1. Arrastra "Rectangle" para cada paso
2. Conecta con flechas
3. Usa "Diamond" para decisiones (¿Es correo?)
4. Colores:
   - Inicio/Fin: Verde oscuro
   - Procesos: Azul
   - Decisiones: Naranja
   - Sistema automático: Morado

---

### **2. DIAGRAMA DE ENTIDAD-RELACIÓN: CORRESPONDENCIA**

**Para explicar:** Cómo se relacionan los modelos principales

**Herramienta:** Draw.io (Entity Relation)

**Modelos a incluir:**

```
┌─────────────────┐
│ Correspondencia │
├─────────────────┤
│ numero_radicado │
│ fecha_radicacion│
│ asunto          │
│ estado          │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│ Historial       │
├─────────────────┤
│ evento          │
│ fecha_hora      │
│ usuario         │
└─────────────────┘
```

**Relaciones a mostrar:**

- Correspondencia → Contacto (N:1)
- Correspondencia → OficinaProductora (N:1)
- Correspondencia → HistorialCorrespondencia (1:N)
- Correspondencia → CorrespondenciaSalida (1:N)

---

### **3. DIAGRAMA DE ARQUITECTURA: VISTA GENERAL**

**Para explicar:** La estructura completa del sistema

**Herramienta:** Draw.io (Blank)

**Capas:**

```
┌─────────────────────────────────────────┐
│         INTERFAZ DE USUARIO             │
│  (Dashboards, Bandejas, Formularios)    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│         LÓGICA DE NEGOCIO               │
│  • Radicación                           │
│  • Cálculo SLA                          │
│  • Distribución                         │
│  • Notificaciones                       │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│         BASE DE DATOS                   │
│  • Correspondencia                      │
│  • Documentos                           │
│  • Usuarios                             │
│  • Historial                            │
└─────────────────────────────────────────┘
```

---

### **4. DIAGRAMA DE FLUJO: SISTEMA SLA**

**Para explicar:** Cómo se calculan las fechas límite

```
Correspondencia creada
requiere_respuesta = True
         │
         ▼
¿Tiene subserie_id?
    │
    ├─ SÍ → Buscar en SubserieTramite
    │        │
    │        ├─ ¿Existe mapeo?
    │        │   │
    │        │   ├─ SÍ → Obtener TramiteTipo.plazo_dias_habiles
    │        │   │         plazo_origen = 'TRD'
    │        │   │
    │        │   └─ NO → Ir a Fallback
    │        │
    │        
    └─ NO → Fallback: tiempo_respuesta
             │
             ├─ NORMAL → 15 días
             ├─ URGENTE → 5 días
             └─ MUY_URGENTE → 3 días
             plazo_origen = 'FALLBACK'
         │
         ▼
Aplicar corte horario
(si después de 5pm, inicio = siguiente día hábil)
         │
         ▼
Sumar X días HÁBILES
(saltando fines de semana y CalendarioLaboral)
         │
         ▼
Persistir:
- plazo_respuesta_dias
- fecha_limite_respuesta_persist
- plazo_origen
- tramite_aplicado (si TRD)
```

---

### **5. DIAGRAMA DE CASOS DE USO**

**Para explicar:** Quién hace qué en el sistema

```
     ┌─────────────┐
     │  CIUDADANO  │
     └──────┬──────┘
            │
            │ Envía solicitud
            │
            ▼
     ┌─────────────┐
     │ VENTANILLA  │────► Radica documento
     │   ÚNICA     │────► Distribuye a oficina
     └─────────────┘

     ┌─────────────┐
     │  USUARIO    │────► Consulta bandeja
     │  OFICINA    │────► Lee documento
     │             │────► Crea respuesta
     └─────────────┘

     ┌─────────────┐
     │ADMINISTRADOR│────► Configura TRD
     │             │────► Gestiona usuarios
     │             │────► Genera reportes
     └─────────────┘
```

---

### **6. DIAGRAMA DE SECUENCIA: RESPONDER CORRESPONDENCIA**

**Para explicar:** El flujo temporal de respuesta

```
Usuario    │  Sistema   │  Base Datos  │  Email
───────────┴────────────┴──────────────┴────────
    │
    ├─── Abre Correspondencia
    │         │
    │         ├─── Busca en BD
    │         │         │
    │         │         └─── Devuelve datos
    │         │
    │         └─── Muestra detalle
    │
    ├─── Click "Responder"
    │         │
    │         └─── Abre formulario
    │
    ├─── Escribe respuesta
    │
    ├─── Selecciona destinatario
    │
    ├─── Adjunta archivos
    │
    ├─── Click "Enviar"
    │         │
    │         ├─── Crea CorrespondenciaSalida
    │         │         │
    │         │         └─── INSERT INTO
    │         │
    │         ├─── Crea SalidaDestinatario
    │         │         │
    │         │         └─── INSERT INTO
    │         │
    │         ├─── Actualiza estado Correspondencia
    │         │         │
    │         │         └─── UPDATE
    │         │
    │         ├─── Envía email
    │         │                     │
    │         │                     └─── SMTP Send
    │         │
    │         └─── Mensaje: "Enviado"
    │
```

---

## 🎨 PALETA DE COLORES PROFESIONAL

### **Para tus diagramas:**

```
Primario:     #667eea (Azul morado)
Secundario:   #764ba2 (Morado)
Éxito:        #4CAF50 (Verde)
Advertencia:  #FF9800 (Naranja)
Error:        #F44336 (Rojo)
Información:  #2196F3 (Azul)
Neutral:      #9E9E9E (Gris)
```

**Uso sugerido:**

- **Procesos normales:** Azul (#667eea)
- **Decisiones:** Naranja (#FF9800)
- **Inicio/Fin:** Verde (#4CAF50)
- **Errores:** Rojo (#F44336)
- **Sistema automático:** Morado (#764ba2)

---

## 📐 PLANTILLA BÁSICA EN DRAW.IO

### **Paso a Paso:**

**1. Abrir Draw.io**
   - Ve a https://app.diagrams.net/
   - Click "Create New Diagram"
   - Nombre: "Flujo_Radicacion"
   - Template: "Blank Diagram"

**2. Configurar página**
   - File → Page Setup
   - Format: A4 Landscape
   - Grid: 10px

**3. Panel izquierdo (formas)**
   - General → Rectangle (para procesos)
   - General → Diamond (para decisiones)
   - General → Ellipse (para inicio/fin)
   - Arrows → Arrows (para conectores)

**4. Crear primer diagrama: Flujo de Radicación**

   a. Arrastra un **Ellipse** (inicio)
      - Doble click → escribe "Inicio"
      - Click derecho → Edit Style
      - Fill: #4CAF50 (verde)
      - Font Color: White

   b. Arrastra un **Rectangle** (proceso)
      - Escribe: "Llega documento"
      - Fill: #667eea (azul)
      - Font Color: White

   c. Arrastra un **Diamond** (decisión)
      - Escribe: "¿Es correo?"
      - Fill: #FF9800 (naranja)
      - Font Color: White

   d. Conecta con flechas
      - Click en forma 1
      - Arrastra el punto azul a forma 2

**5. Exportar**
   - File → Export as → PNG
   - Zoom: 100%
   - Border: 0
   - Transparent: Yes
   - Download

---

## 🎯 DIAGRAMAS PRIORITARIOS PARA TU PRESENTACIÓN

### **MUST HAVE (Debes hacerlos):**

1. ✅ **Flujo de Radicación** (slide demo)
2. ✅ **Modelo de Datos Principal** (arquitectura técnica)
3. ✅ **Diagrama SLA** (valor diferenciador)

### **NICE TO HAVE (Si tienes tiempo):**

4. ⭐ **Casos de Uso** (roles y funciones)
5. ⭐ **Arquitectura General** (vista de alto nivel)

---

## 💡 TIPS PARA BUENOS DIAGRAMAS

### **DO's (Haz esto):**

✅ **Usa colores consistentes** - Mismo color para mismo tipo de elemento
✅ **Etiquetas claras** - Texto legible desde 3 metros
✅ **Flujo de arriba a abajo** o de izquierda a derecha
✅ **Agrupa elementos relacionados** con cajas de fondo
✅ **Leyenda** si usas muchos símbolos

### **DON'Ts (No hagas esto):**

❌ **Demasiados elementos** - Máximo 10 por diagrama
❌ **Colores random** - Mantén paleta consistente
❌ **Texto muy pequeño** - Mínimo 12pt
❌ **Flechas cruzadas** - Evita que se crucen líneas
❌ **Información técnica excesiva** - Solo lo esencial

---

## 📚 RECURSOS ADICIONALES

### **Tutoriales Draw.io:**
- YouTube: "Draw.io tutorial español"
- https://www.diagrams.net/doc/

### **Ejemplos de diagramas profesionales:**
- Pinterest: "database diagram design"
- Dribbble: "flowchart design"

### **Iconos gratis:**
- https://www.flaticon.com/
- https://icons8.com/

---

## ⏰ PLAN DE TRABAJO (2 horas)

**30 min:** Flujo de Radicación (Draw.io)
**30 min:** Modelo de Datos (Mermaid + exportar)
**30 min:** Diagrama SLA (Draw.io)
**30 min:** Insertar en presentación + ajustes

---

## 🎬 CHECKLIST FINAL

Antes de la presentación, verifica:

- [ ] Todos los diagramas en alta resolución (PNG, min 1920x1080)
- [ ] Fondo transparente o blanco
- [ ] Texto legible al proyectar
- [ ] Colores consistentes con la presentación
- [ ] Flujo lógico fácil de seguir
- [ ] Sin información técnica excesiva
- [ ] Archivos fuente guardados (.drawio, .mmd) por si necesitas editar

---

**¿Listo para crear tus diagramas? Te recomiendo empezar con el Flujo de Radicación en Draw.io. ¡Es el más impactante para los directivos!** 🚀

