# Guía de Modificación de Diagramas

## 🎯 **OPCIONES PARA MODIFICAR TU DIAGRAMA**

### **1. MERMAID LIVE (Recomendado para principiantes)**
**URL:** https://mermaid.live/

**Ventajas:**
- ✅ Editor visual en tiempo real
- ✅ No necesita instalación
- ✅ Exporta PNG/SVG/PDF
- ✅ Fácil de usar

**Cómo usar:**
1. Copia el código de `diagrama_completo_mermaid.md`
2. Pégalo en https://mermaid.live/
3. Modifica directamente en el editor
4. Ve cambios en tiempo real
5. Exporta cuando esté listo

### **2. DRAW.IO (Recomendado para control total)**
**URL:** https://app.diagrams.net/

**Ventajas:**
- ✅ Control visual completo
- ✅ Muchas plantillas
- ✅ Fácil arrastrar y soltar
- ✅ Exporta múltiples formatos

**Cómo usar:**
1. Crea nuevo diagrama
2. Usa el código Mermaid como referencia
3. Dibuja manualmente cada elemento
4. Aplica estilos y colores
5. Conecta elementos con flechas

### **3. VS CODE (Para desarrolladores)**
**Extensiones necesarias:**
- Mermaid Preview
- Markdown Preview Enhanced

**Cómo usar:**
1. Instala las extensiones
2. Crea archivo `.md`
3. Pega el código Mermaid
4. Usa preview en tiempo real
5. Exporta desde preview

## 🔧 **TIPOS DE MODIFICACIONES QUE PUEDES HACER**

### **A) CAMBIAR TEXTOS**
```mermaid
# ANTES
MANUAL[👤 Radicación Manual]

# DESPUÉS
MANUAL[📝 Registro Físico de Documentos]
```

### **B) AGREGAR ELEMENTOS**
```mermaid
# AGREGAR NUEVO PROCESO
PROCESAR --> VALIDAR[🔍 Validar Documento]
VALIDAR --> APROBAR{¿Aprobado?}
APROBAR -->|Sí| CONTINUAR[➡️ Continuar]
APROBAR -->|No| RECHAZAR[❌ Rechazar]
```

### **C) CAMBIAR FLUJO**
```mermaid
# ANTES: Línea directa
A --> B --> C

# DESPUÉS: Con decisión
A --> B
B --> DECISION{¿Continuar?}
DECISION -->|Sí| C
DECISION -->|No| D
```

### **D) CAMBIAR COLORES**
```mermaid
# COLORES DISPONIBLES:
style ELEMENTO fill:#e3f2fd,stroke:#1565c0,stroke-width:2px  # Azul
style ELEMENTO fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px  # Verde
style ELEMENTO fill:#fff3e0,stroke:#e65100,stroke-width:2px  # Naranja
style ELEMENTO fill:#f3e5f5,stroke:#4a148c,stroke-width:2px  # Morado
style ELEMENTO fill:#ffebee,stroke:#c62828,stroke-width:2px  # Rojo
```

### **E) AGREGAR FUNCIONES TRANSVERSALES**
```mermaid
# AGREGAR NUEVA FUNCIÓN AUTOMÁTICA
PROCESO -.->|Automático| NUEVA_FUNC[🤖 Nueva Función<br/>Automática]
```

## 📋 **CHECKLIST DE MODIFICACIÓN**

### **ANTES DE EMPEZAR:**
- [ ] ¿Qué versión prefieres? (Completa o Simplificada)
- [ ] ¿Qué herramienta usarás? (Mermaid Live, Draw.io, VS Code)
- [ ] ¿Qué nivel de detalle quieres? (Alto, Medio, Bajo)

### **DURANTE LA MODIFICACIÓN:**
- [ ] Mantén consistencia en colores
- [ ] Usa emojis para claridad visual
- [ ] Mantén flujo lógico
- [ ] Prueba en tiempo real

### **DESPUÉS DE MODIFICAR:**
- [ ] Revisa flujo completo
- [ ] Verifica que no hay elementos sueltos
- [ ] Exporta en alta calidad
- [ ] Guarda código fuente

## 🎨 **CONSEJOS DE DISEÑO**

### **1. COLORES CONSISTENTES:**
- 🔵 **Azul:** Procesos principales
- 🟠 **Naranja:** Decisiones
- 🟢 **Verde:** Resultados exitosos
- 🔴 **Rojo:** Errores o rechazos
- 🟣 **Morado:** Funciones automáticas

### **2. FORMAS CORRECTAS:**
- **Óvalo `()`:** Inicio y fin
- **Rectángulo `[]`:** Procesos
- **Rombo `{}`:** Decisiones
- **Cilindro `[]`:** Base de datos

### **3. TEXTO CLARO:**
- Máximo 3-4 palabras por caja
- Usa verbos para acciones
- Usa preguntas para decisiones
- Incluye emojis para claridad

### **4. FLUJO LÓGICO:**
- De arriba hacia abajo
- O de izquierda a derecha
- NUNCA mezclar ambos
- Conecta todos los elementos

## 🚀 **COMANDOS ÚTILES EN MERMAID**

### **DIRECCIONES:**
```mermaid
flowchart TD  # Top Down (arriba-abajo)
flowchart LR  # Left Right (izquierda-derecha)
flowchart TB  # Top Bottom (arriba-abajo)
flowchart RL  # Right Left (derecha-izquierda)
```

### **TIPOS DE LÍNEAS:**
```mermaid
A --> B        # Línea normal
A -.-> B       # Línea punteada
A ==> B        # Línea gruesa
A --x B        # Línea con X
```

### **ESTILOS:**
```mermaid
classDef className fill:#color,stroke:#color,stroke-width:2px
class element1,element2 className
```

## 💡 **EJEMPLOS DE MODIFICACIONES COMUNES**

### **EJEMPLO 1: Agregar validación**
```mermaid
# ANTES
ENVIAR --> RESULTADO

# DESPUÉS
ENVIAR --> VALIDAR[🔍 Validar Envío]
VALIDAR --> RESULTADO
```

### **EJEMPLO 2: Agregar decisión**
```mermaid
# ANTES
PROCESAR --> RESPONDER

# DESPUÉS
PROCESAR --> NECESITA{¿Requiere respuesta?}
NECESITA -->|Sí| RESPONDER
NECESITA -->|No| ARCHIVAR
```

### **EJEMPLO 3: Cambiar colores**
```mermaid
# ANTES
style PROCESO fill:#e3f2fd,stroke:#1565c0,stroke-width:2px

# DESPUÉS
style PROCESO fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
```

¿Necesitas ayuda con alguna modificación específica? 🎯













