# 📋 Explicación: Sistema de Contactos en Correspondencia

## 🎯 Overview General

El sistema de contactos está diseñado con una **estructura de múltiples niveles** que permite:
- Crear contactos globales (agenda general)
- Asignar contactos a oficinas específicas (agenda por oficina)
- Usarlos en respuestas de correspondencia
- Agruparlos en grupos de agenda para envíos masivos

---

## 📊 Estructura de Modelos

### 1. **EntidadExterna** 🏢
```
EntidadExterna (Tabla global)
├── nombre: "Hospital Central", "Ministerio de Salud", etc.
├── telefono
├── direccion
└── email_institucional
```
**Propósito:** Representa organizaciones/instituciones externas.  
**Uso:** Clasificar contactos por entidad para mejor organización.

---

### 2. **Contacto** 👤 (El modelo principal)
```
Contacto
├── entidad_externa ⬅️ FK a EntidadExterna (obligatorio)
│   └── "Hospital Central"
├── nombres: "Juan"
├── apellidos: "Pérez"
├── cargo: "Director General"
├── correo_electronico: "juan@hospital.com"
├── telefono_contacto: "+573001234567"
│
└── oficina_propietaria ⬅️ FK a OficinaProductora (OPCIONAL)
    └── "Dirección Administrativa" (NULL = contacto global)
```

**Dos tipos de contactos:**

#### A) **Contactos Globales** (sin oficina propietaria)
- `oficina_propietaria = NULL`
- Visibles para TODAS las oficinas
- Se usan cuando "es relevante para el sistema en general"
- Ejemplo: Director General del hospital

#### B) **Contactos por Oficina** (con oficina propietaria)
- `oficina_propietaria = "Dirección Administrativa"`
- Solo visibles para esa oficina específica
- Cada oficina mantiene su propia "agenda"
- Ejemplo: Secretaria de la Dirección Administrativa

---

## 🔄 Relaciones de Correspondencia

### Flujo Completo:

```
Correo Entrante
    ↓
[Remitente = Contacto] ← Seleccionar remitente (cualquier contacto)
    ↓
Se radica en Correspondencia
    ↓
Se genera CorrespondenciaSalida (respuesta)
    ↓
Ventanillero selecciona destinatarios:
    ├─ Solo contactos de su oficina propietaria
    └─ O contactos globales (sin oficina)
    ↓
[SalidaDestinatario] ← Crear una línea por cada destinatario
    ├─ contacto: FK al Contacto
    ├─ correspondencia_salida: FK a la respuesta
    ├─ email_snapshot: Copia del email en ese momento
    └─ nombre_snapshot: Copia del nombre en ese momento
```

---

## 🎯 Cómo Funciona en la Práctica

### Scenario 1: Crear un Contacto Global

**Quién:** Ventanillero  
**Dónde:** Menu → Contactos → Agregar  
**Campos:**
```
Entidad Externa: "Ministerio de Salud" ← Seleccionar
Nombres: "Ana"
Apellidos: "García"
Cargo: "Ministra"
Correo: ana@minsalud.gov.co
Teléfono: +570123456789
Oficina Propietaria: [DEJAR EN BLANCO] ← ¡Importante!
```

**Resultado:**
- Contacto creado sin oficina
- Visible para TODAS las oficinas
- Puede ser remitente O destinatario en cualquier respuesta

---

### Scenario 2: Crear un Contacto por Oficina

**Quién:** Ventanillero de la Dirección Administrativa  
**Dónde:** Dashboard → Crear Contacto de Oficina  
**Campos:**
```
Entidad Externa: "Hospital Central" ← Seleccionar
Nombres: "Carlos"
Apellidos: "López"
Cargo: "Secretario de Dirección"
Correo: carlos@hospital-interno.com
Teléfono: +5733338889999
Oficina Propietaria: "Dirección Administrativa" ← Se asigna automáticamente
```

**Resultado:**
- Contacto creado EN la oficina del ventanillero
- **Solo visible** para personal de esa oficina
- NO visible para otras oficinas
- Útil para contactos internos o de uso exclusivo

---

### Scenario 3: Enviar Respuesta a Múltiples Destinatarios

**Contexto:** Ventanillero de "Dirección Administrativa" redacta respuesta

**Paso 1: Crear Respuesta**
```
Asunto: "Re: Solicitud de información"
Cuerpo: "Estimado remitente, le informamos que..."
```

**Paso 2: Seleccionar Destinatarios**

El sistema le muestra:

```
✓ Contactos de su oficina (Dirección Administrativa):
  ├─ Juan Pérez (juan@mail.com)
  ├─ María García (maria@mail.com)
  └─ Carlos López (carlos@mail.com)

✓ Contactos Globales (sin oficina):
  ├─ Ana García - Ministerio (ana@minsalud.com)
  ├─ Director General (director@hospital.com)
  └─ Supervisor Regional (supervisor@region.com)

✗ BLOQUEADOS - Contactos de otras oficinas:
  └─ No puede ver contactos de "Farmacia" u otras áreas
```

**Paso 3: Ventanillero elige:**
- Juan Pérez (su oficina)
- María García (su oficina)
- Ana García (global)
- Total: 3 destinatarios

**Paso 4: Sistema crea SalidaDestinatario (3 registros)**
```
SalidaDestinatario #1:
├─ contacto: Juan Pérez
├─ email_snapshot: juan@mail.com
└─ estado: PENDIENTE_APROBACION

SalidaDestinatario #2:
├─ contacto: María García
├─ email_snapshot: maria@mail.com
└─ estado: PENDIENTE_APROBACION

SalidaDestinatario #3:
├─ contacto: Ana García (global)
├─ email_snapshot: ana@minsalud.com
└─ estado: PENDIENTE_APROBACION
```

---

## 🔒 Validaciones de Seguridad

El sistema valida automáticamente:

### En `SalidaDestinatario.clean()`:
```python
# 1. El contacto debe tener correo
if not self.contacto.correo_electronico:
    ❌ Error: "El contacto no tiene correo"

# 2. El contacto debe ser de la oficina correcta
if self.contacto.oficina_propietaria != self.correspondencia_salida.oficina_emisora:
    if self.contacto.oficina_propietaria is not None:  # Si no es global
        ❌ Error: "El contacto no pertenece a la oficina"

# 3. Si es global, se permite
if self.contacto.oficina_propietaria is None:
    ✓ Permitido (es contacto global)
```

---

## 🎭 Casos de Uso Típicos

### Caso 1: Responder a un Paciente
```
Correo de: Juan Martínez (paciente)
Entidad: [Sin especificar]
Oficina destino: Urgencias

Respuesta se envía a:
✓ Juan Martínez (remitente original)
✓ Supervisor de Urgencias (contacto de la oficina)
✓ Director General (contacto global, para seguimiento)
```

### Caso 2: Comunicación Interinstitucional
```
Correo de: Ana García (Ministerio de Salud)
Entidad: Ministerio de Salud
Oficina destino: Dirección Administrativa

Respuesta se envía a:
✓ Ana García (remitente)
✓ Secretaria de Dirección (contacto de oficina)
✓ Otros contactos globales según corresponda
```

### Caso 3: Notificación Interna
```
Correo de: Sistema (radicación interna)
Entidad: Hospital Central (interna)
Oficina destino: Farmacia

Respuesta se envía a:
✓ Jefe de Farmacia (contacto de farmacia)
✓ Asistente de Farmacia (contacto de farmacia)
✓ Director General (contacto global, para auditoría)
```

---

## 📊 Diagram de Relaciones

```
┌─────────────────────────────────────────────────────────┐
│                   EntidadExterna                        │
│  (Hospital Central, Ministerio, Alcaldía, etc.)       │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ FK
                          │
┌─────────────────────────────────────────────────────────┐
│                      Contacto                           │
│  (Persona física: Juan, María, etc.)                  │
│                                                         │
│  oficina_propietaria: NULL (global) o OficinaID      │
└─────────────────────────────────────────────────────────┘
                    ▲          ▲
         Remitente │          │ Destinatario
                   │          │
┌──────────────────┘          └──────────────────┐
│                                                │
│         CorrespondenciaSalida                 │
│  (Respuesta de correspondencia entrante)      │
│                                                │
│         ┌──────────────────────────┐          │
│         │   SalidaDestinatario     │          │
│         │  (1 por cada destino)    │          │
│         │  - email_snapshot        │          │
│         │  - estado (PENDIENTE)    │          │
│         │  - fecha_envio           │          │
│         └──────────────────────────┘          │
│                                                │
└────────────────────────────────────────────────┘
```

---

## 🔑 Resumen de Conceptos Clave

| Concepto | Definición | Uso |
|----------|-----------|-----|
| **EntidadExterna** | Organización/institución externa | Clasificar contactos |
| **Contacto Global** | Contacto sin oficina propietaria | Visible para todas las oficinas |
| **Contacto por Oficina** | Contacto asignado a una oficina | Solo visible para esa oficina |
| **SalidaDestinatario** | Registro de envío a UN destinatario | Tracking de envíos individuales |
| **email_snapshot** | Copia del email en el momento del envío | Auditoría si cambia el email |
| **nombre_snapshot** | Copia del nombre en el momento del envío | Auditoría si cambia el nombre |

---

## 💡 Mejor Práctica de Diseño

```
RECOMENDACIÓN: Crear 3 niveles de contactos

1️⃣ NIVEL GLOBAL (sin oficina):
   - Director General
   - Coordinador de Correspondencia
   - Contactos interinstitucionales clave
   
2️⃣ NIVEL DE OFICINA (con oficina propietaria):
   - Personal interno de cada oficina
   - Secretarias
   - Coordinadores por área
   
3️⃣ NIVEL DE CONTACTOS MASIVOS:
   - Usar GrupoAgenda para agrupar
   - Ejemplo: "Direcciones de todas las clínicas"
   - Ejemplo: "Coordinadores de urgencias"
```

---

## ❓ Preguntas Frecuentes

**P: ¿Puedo enviar a contactos de otra oficina?**  
R: No. El sistema valida que el destinatario pertenezca a tu oficina O sea global.

**P: ¿Qué pasa si cambio el email de un contacto?**  
R: El snapshot guarda el email original. El siguiente envío usará el nuevo email.

**P: ¿Puedo tener dos contactos con el mismo email?**  
R: Solo uno por oficina. A nivel global sí, pero no se recomienda.

**P: ¿Cómo creo un contacto global?**  
R: Crea un contacto sin seleccionar "Oficina Propietaria".

**P: ¿Qué es un GrupoAgenda?**  
R: Agrupa contactos de tu oficina para envíos masivos rápidos.

---

## 📝 Código Relevante

### Creación de Contacto (ventanillero)
```python
# forms.py - ContactoForm
campos = [
    'entidad_externa',     # Obligatorio
    'nombres',             # Obligatorio
    'apellidos',           # Opcional
    'cargo',               # Opcional
    'correo_electronico',  # Obligatorio para envíos
    'telefono_contacto'    # Opcional
    # NOTA: 'oficina_propietaria' se asigna automáticamente o es NULL
]
```

### Validación en SalidaDestinatario
```python
def clean(self):
    # Solo permite:
    # 1. Contactos de tu oficina
    # 2. Contactos globales (sin oficina)
    if contacto.oficina_propietaria != oficina_emisora:
        if contacto.oficina_propietaria is not None:
            raise ValidationError("Contacto no permitido")
```

### Filtrado de Contactos en Vistas
```python
# views.py - línea 265
contactos = Contacto.objects.filter(
    Q(oficina_propietaria=perfil.oficina) |  # Mi oficina
    Q(oficina_propietaria__isnull=True)       # O globales
)
```

---

## 🎓 Conclusión

El sistema es **jerárquico pero flexible**:
- ✅ Contactos globales para comunicaciones transversales
- ✅ Contactos por oficina para control y privacidad
- ✅ Snapshots para auditoría y trazabilidad
- ✅ Validaciones automáticas para seguridad

¡Así se asegura que cada ventanillero solo vea y use los contactos permitidos! 🔒
