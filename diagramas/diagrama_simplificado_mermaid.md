# Diagrama Simplificado - Sistema de Correspondencia

## 🎯 **OPCIÓN 2: Versión Simplificada (Más fácil de modificar)**

```mermaid
flowchart TD
    %% ENTRADA
    START([📥 Inicio])
    
    %% MEDIOS DE ENTRADA
    START --> INPUT{¿Medio de entrada?}
    INPUT -->|Físico| MANUAL[👤 Radicación Manual]
    INPUT -->|Email| EMAIL[📧 Correo Electrónico]
    
    %% PROCESAMIENTO CENTRAL
    MANUAL --> RADICADO[🔢 Generación Radicado]
    EMAIL --> RADICADO
    RADICADO --> CLASIFICAR[📚 Clasificación TRD]
    CLASIFICAR --> ASIGNAR[🏢 Asignación Oficina]
    
    %% DISTRIBUCIÓN
    ASIGNAR --> USUARIO[👤 Asignar Usuario]
    USUARIO --> NOTIFICAR[🔔 Notificación]
    
    %% RECEPCIÓN
    NOTIFICAR --> RECIBIR[📥 Recepción]
    RECIBIR --> LEER{¿Leído?}
    LEER -->|No| ALERTA[🚨 Alerta SLA]
    LEER -->|Sí| PROCESAR[📋 Procesar]
    
    ALERTA --> LEER
    
    %% ACCIONES
    PROCESAR --> ACCION{¿Acción?}
    ACCION -->|Compartir| COMPARTIR[🔄 Compartir]
    ACCION -->|Responder| RESPONDER[💬 Responder]
    ACCION -->|Archivar| ARCHIVAR[📁 Archivar]
    
    %% RESPUESTA
    RESPONDER --> APROBAR{¿Aprobar?}
    APROBAR -->|Sí| ENVIAR[📤 Enviar]
    APROBAR -->|No| RECHAZAR[❌ Rechazar]
    
    %% ENVÍO
    ENVIAR --> VALIDAR[🔍 Validar Email]
    VALIDAR --> SMTP[📧 Envío SMTP]
    SMTP --> RESULTADO{¿Enviado?}
    RESULTADO -->|Sí| EXITO[✅ Éxito]
    RESULTADO -->|No| ERROR[⚠️ Error]
    
    %% FIN
    EXITO --> FIN([🏁 Fin])
    ERROR --> FIN
    ARCHIVAR --> FIN
    RECHAZAR --> FIN
    COMPARTIR --> FIN
    
    %% FUNCIONES AUTOMÁTICAS (Simplificadas)
    RADICADO -.-> AUTO1[🤖 Auto: Número]
    CLASIFICAR -.-> AUTO2[🤖 Auto: SLA]
    NOTIFICAR -.-> AUTO3[🤖 Auto: Notificación]
    VALIDAR -.-> AUTO4[🤖 Auto: Validación]
    
    %% ESTILOS
    style START fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    style FIN fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    style AUTO1 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style AUTO2 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style AUTO3 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style AUTO4 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style INPUT fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style LEER fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style ACCION fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style APROBAR fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style RESULTADO fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

## 🎨 **VENTAJAS DE ESTA VERSIÓN:**

### **✅ MÁS SIMPLE:**
- Menos elementos
- Flujo más claro
- Fácil de modificar

### **✅ MANTIENE LO ESENCIAL:**
- Funciones transversales
- Procesos automáticos
- Flujo completo

### **✅ FÁCIL DE PERSONALIZAR:**
- Textos más cortos
- Menos decisiones
- Estructura clara

## 🔧 **CÓMO MODIFICAR:**

### **1. Cambiar textos:**
```mermaid
MANUAL[👤 Tu texto aquí]
```

### **2. Agregar elementos:**
```mermaid
NUEVO[📝 Nuevo proceso]
ACCION --> NUEVO
NUEVO --> FIN
```

### **3. Cambiar colores:**
```mermaid
style NUEVO fill:#tu_color,stroke:#tu_borde,stroke-width:2px
```

### **4. Agregar decisiones:**
```mermaid
NUEVO{¿Nueva decisión?}
NUEVO -->|Sí| PROCESO1
NUEVO -->|No| PROCESO2
```

¿Te gusta más esta versión simplificada? ¿Quieres que la modifique de alguna manera específica? 🎯













