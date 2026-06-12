# Estructura Visual - Modal V2 Full

```
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║         ✎ Nueva Comunicación Interna              [X]             ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  📍 Ciudad              📅 Fecha del Documento                    ║
║  [Saravena............] [________________]                         ║
║                                                                    ║
║  📚 Serie Documental        📋 Subserie Asociada                  ║
║  [Seleccione una serie...] [Seleccione serie primero...]         ║
║                                                                    ║
║  🏷️  Código TRD                                                     ║
║  [________________________] (readonly - autocompleta)             ║
║                                                                    ║
║  📤 Tipo de Distribución *                                         ║
║  ▼ Usuario Específico ◄─ (selector: Usuario/Oficina/Proceso/...)  ║
║                                                                    ║
║  ┌────────────────────────────────────────────────────┐            ║
║  │ SECCIÓN DINÁMICA DE DESTINATARIOS                  │            ║
║  │ (Cambia según tipo de distribución)                │            ║
║  │                                                    │            ║
║  │ 🏢 Oficina *                                       │            ║
║  │ [Seleccione una oficina...]                        │            ║
║  │                                                    │            ║
║  │ 👥 Usuarios disponibles                            │            ║
║  │ ┌──────────────┐  ┌──────────────┐                │            ║
║  │ │ 👤 Usuario 1 │  │ 👤 Usuario 2 │  ...           │            ║
║  │ └──────────────┘  └──────────────┘                │            ║
║  │                                                    │            ║
║  │ 👥 Seleccionados (0)                               │            ║
║  │ ┌────────────────────────────────────────────┐    │            ║
║  │ │ 📥 No hay usuarios seleccionados           │    │            ║
║  │ └────────────────────────────────────────────┘    │            ║
║  │ (Chips azules aparecerán aquí al seleccionar)     │            ║
║  └────────────────────────────────────────────────────┘            ║
║                                                                    ║
║  📝 Asunto *                                                       ║
║  [_______________________________________]                       ║
║                                                                    ║
║  💬 Contenido *                                                     ║
║  ┌─────────────────────────────────────────────────┐               ║
║  │ Escriba aquí...                                 │               ║
║  │                                                 │               ║
║  │                                                 │               ║
║  │                                                 │               ║
║  │                                                 │               ║
║  │                                                 │               ║
║  └─────────────────────────────────────────────────┘               ║
║                                                                    ║
║  ────────────────────────────────────────────────────────────     ║
║                                                                    ║
║  📎 Anexos (Opcional)                                              ║
║  Hasta 10 archivos. PDF, DOC, DOCX, XLS, XLSX.                   ║
║  Máx 2MB c/u, 10MB total.                                         ║
║                                                                    ║
║  [Seleccionar archivos...] [X Limpiar]                            ║
║                                                                    ║
║  (Preview aparece aquí: Seleccionados: 0 (0 KB))                 ║
║                                                                    ║
║                                                                    ║
║                          [Cancelar] [✓ Enviar]                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 🎯 Estados Dinámicos de Sección de Destinatarios

### Estado 1: USUARIO Específico
```
┌────────────────────────────────────┐
│ Oficina *                           │
│ [Seleccione una oficina...]         │
│                                     │
│ Usuarios disponibles                │
│ ┌──────────┐  ┌──────────┐          │
│ │ Usuario1 │  │ Usuario2 │          │
│ │          │  │          │          │
│ └──────────┘  └──────────┘          │
│               ┌──────────┐          │
│               │ Usuario3 │          │
│               │          │          │
│               └──────────┘          │
│                                     │
│ Seleccionados (2)                   │
│ ┌─────────────────────────────┐     │
│ │ [Usuario1] ✕  [Usuario2] ✕ │     │
│ └─────────────────────────────┘     │
└────────────────────────────────────┘
```

### Estado 2: OFICINA Completa
```
┌────────────────────────────────────┐
│ Oficinas disponibles                │
│ ┌──────────┐  ┌──────────┐          │
│ │ Oficina1 │  │ Oficina2 │          │
│ │          │  │          │          │
│ └──────────┘  └──────────┘          │
│ ┌──────────┐  ┌──────────┐          │
│ │ Oficina3 │  │ Oficina4 │          │
│ │          │  │          │          │
│ └──────────┘  └──────────┘          │
│                                     │
│ Seleccionadas (2)                   │
│ ┌──────────────────────────────┐    │
│ │ [Oficina1] ✕  [Oficina3] ✕  │    │
│ └──────────────────────────────┘    │
└────────────────────────────────────┘
```

### Estado 3: PROCESO Completo
```
┌────────────────────────────────────┐
│ Proceso Destino *                   │
│ [▼ Seleccionar Proceso...]          │
│  - Proceso A                        │
│  - Proceso B  ◄─ (seleccionado)     │
│  - Proceso C                        │
│                                     │
│ (Simple, solo 1 proceso)            │
└────────────────────────────────────┘
```

### Estado 4: ENTIDAD Completa
```
┌────────────────────────────────────┐
│ ℹ️  Distribución a toda la entidad  │
│                                     │
│ Esta comunicación se enviará a      │
│ todos los usuarios del sistema.     │
│                                     │
│ (Sin selector, solo informativo)    │
└────────────────────────────────────┘
```

---

## 📱 Comportamiento del Modal

### Al Abrir
```
1. Cargan en paralelo:
   - Series desde /documentos/cargar_series/
   - Subseries (vacío hasta seleccionar serie)
   - Oficinas desde correspondencia:oficinas_todas_interna_ajax
   - Usuarios (vacío hasta seleccionar oficina)

2. Se muestra sección de destinatarios para USUARIO por defecto

3. Fecha se auto-rellena con hoy

4. TRD está vacío (se llena al seleccionar serie+subserie)
```

### Al Seleccionar Serie
```
1. Se cargan subseries para esa serie
2. Dropdown de subseries pasa de "disabled" a "enabled"
3. TRD permanece vacío
```

### Al Seleccionar Subserie
```
1. Se autocompleta TRD combinando:
   - TRD oficina del usuario (desde data attribute)
   - TRD serie (desde option dataset)
   - TRD subserie (desde option dataset)
   
   Resultado: 01.02.03.04.05
```

### Al Cambiar Tipo de Distribución
```
1. Sección destinatarios completa se regenra
2. Se carga el contenido dinámicamente
3. Destinatarios previamente seleccionados se pierden
   (Advertencia: no hay confirmación, selecciona de nuevo)
```

### Al Seleccionar Usuario/Oficina
```
1. Tarjeta cambia color (border-primary, bg-light)
2. Se agrega a Map destinatariosSeleccionados
3. Se regeneran chips
4. Contador se actualiza
```

### Al Hacer Click en X del Chip
```
1. Se quita del Map
2. Tarjeta vuelve a color original
3. Chips se regeneran
4. Contador se decrementa
```

### Al Seleccionar Anexo
```
1. Se valida en tiempo real:
   - Formato (PDF/DOC/DOCX/XLS/XLSX)
   - Tamaño individual (< 2 MB)
   - Total (< 10 MB)
   - Cantidad (< 10 archivos)

2. Si hay error, aparece alert rojo

3. Si no hay error, aparece preview con:
   - Lista de archivos
   - Tamaño de cada uno
   - Total de tamaño
   - Contador
```

### Al Hacer Click en Enviar
```
1. Se validan:
   - Asunto no vacío
   - Contenido no vacío
   - Al menos 1 destinatario
   - Anexos válidos

2. Se construye FormData con:
   - Todos los campos del formulario
   - Arrays de destinatarios
   - Archivos anexados
   - Meta: anexos_count_client

3. Se hace POST a crear_comunicacion_interna_ajax

4. Botón muestra spinner mientras se envía

5. Si éxito:
   - Alert: "Comunicación creada"
   - Modal se cierra
   - Página se recarga

6. Si error:
   - Alert: "Error: [mensaje]"
   - Botón vuelve a normal
   - Usuario puede reintentar
```

---

## 🎨 Estilos Visuales

### Colores y Elementos
- **Azul Primario**: Chips de usuarios seleccionados
- **Gris Secundario**: Chips de oficinas seleccionadas
- **Gris Claro (hover)**: Tarjetas de selección
- **Rojo de Error**: Validaciones fallidas
- **Verde Éxito**: Confirmaciones

### Animaciones (Implícitas en Bootstrap)
- Modal fade-in
- Componentes transitados
- Spinners durante carga

---

## 🔄 Flujo Completo de Uso

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│ USUARIO ABRE MODAL                                         │
│   ↓                                                        │
│ [Cargan catálogos]                                         │
│   ↓                                                        │
│ USUARIO SELECCIONA SERIE                                  │
│   ↓                                                        │
│ [Cargan subseries]                                         │
│   ↓                                                        │
│ USUARIO SELECCIONA SUBSERIE                               │
│   ↓                                                        │
│ [Se autocompleta TRD]                                      │
│   ↓                                                        │
│ USUARIO SELECCIONA TIPO DISTRIBUCION                      │
│   ↓                                                        │
│ [Se regenera sección destinatarios]                       │
│   ↓                                                        │
│ USUARIO SELECCIONA DESTINATARIOS                          │
│   ↓                                                        │
│ [Aparecen chips con selecciones]                          │
│   ↓                                                        │
│ USUARIO LLENA ASUNTO Y CONTENIDO                          │
│   ↓                                                        │
│ USUARIO SELECCIONA ANEXOS (opcional)                      │
│   ↓                                                        │
│ [Se valida y muestra preview]                             │
│   ↓                                                        │
│ USUARIO HACE CLICK EN ENVIAR                              │
│   ↓                                                        │
│ [Se validan todos los campos]                             │
│   ↓                                                        │
│ [Se construye FormData]                                   │
│   ↓                                                        │
│ [Se hace POST con fetch]                                  │
│   ↓                                                        │
│ [Backend procesa y guarda]                                │
│   ↓                                                        │
│ [Backend responde con éxito]                              │
│   ↓                                                        │
│ [Modal se cierra, página se recarga]                      │
│   ↓                                                        │
│ COMUNICACIÓN CREADA Y VISIBLE EN LISTADO                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Mapeo de Validaciones

```
CAMPO               VALIDACIÓN              MENSAJES
─────────────────────────────────────────────────────────
Asunto              Requerido               "Asunto... obligatorios"
Contenido           Requerido               "Asunto... obligatorios"
Destinatarios       Mín 1 (según tipo)      "Seleccione al menos..."
Anexos - Cantidad   Máx 10                  "Máximo 10 archivos"
Anexos - Formato    PDF/DOC/DOCX/XLS/XLSX  "{nombre} formato no permitido"
Anexos - Tamaño     < 2 MB cada             "{nombre} excede 2MB"
Anexos - Total      < 10 MB                 "Total excede 10MB"
Proceso (si req.)   Requerido               "Seleccione un proceso"
```

---

**Última actualización**: Hoy  
**Versión**: V2 Full  
**Estado**: ✅ Documentado y listo
