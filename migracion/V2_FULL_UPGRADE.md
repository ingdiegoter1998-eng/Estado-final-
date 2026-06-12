# V2 Full - Actualización Completa del Modal

## Resumen
Se ha mejorado el modal V2 (modal_comunicacion_interna_v2.html) para incluir todas las funcionalidades avanzadas del V1 (modal_comunicacion_interna.html), manteniendo el mecanismo comprobado de carga de anexos basado en FormData y fetch.

## Cambios Realizados

### 1. **Estructura HTML Expandida**
- **Series y Subseries**: Se añadieron selectores para seleccionar serie documental y subserie asociada
- **Código TRD**: Campo de solo lectura que se autocompleta basado en la oficina del usuario + serie + subserie
- **Tipo de Distribución**: Selector que permite elegir entre:
  - `USUARIO`: Usuario específico (multi-select por oficina)
  - `OFICINA`: Oficina completa (multi-select de oficinas)
  - `PROCESO`: Proceso completo
  - `ENTIDAD`: Toda la entidad (distribución masiva)
- **Sección Dinámica de Destinatarios**: Contenedor que se rellena dinámicamente según el tipo de distribución elegido

### 2. **Lógica JavaScript Mejorada**

#### Carga de Catálogos
- `cargarSeries()`: Obtiene series desde `/documentos/cargar_series/`
- `cargarSubseries(serieId)`: Carga subseries filtradas por serie seleccionada
- `actualizarTrd()`: Construye automáticamente el código TRD combinando:
  - Código TRD de la oficina del usuario
  - Código TRD de la serie
  - Código TRD de la subserie

#### Gestión de Destinatarios
- **USUARIO**: 
  - Selector de oficina
  - Multiselect de usuarios con checkbox/tarjetas
  - Chips de selección visual
  - Conteo dinámico de usuarios seleccionados
  
- **OFICINA**: 
  - Multiselect de oficinas con tarjetas
  - Chips de selección visual
  - Conteo dinámico de oficinas seleccionadas

- **PROCESO**: 
  - Selector de proceso disponible

- **ENTIDAD**: 
  - Mensaje informativo indicando distribución a toda la entidad

#### Validación de Anexos
- Límite máximo: 10 archivos
- Formatos permitidos: PDF, DOC, DOCX, XLS, XLSX
- Tamaño máximo por archivo: 2 MB
- Tamaño total máximo: 10 MB
- Validación y visualización de errores en tiempo real

#### Envío del Formulario
- Construcción de FormData programático (igual que V2 original que funciona)
- Agregación dinámica de destinatarios según tipo seleccionado
- Envío de archivos adjuntos de forma robusta
- Logging en consola para diagnosticar problemas
- Indicador visual de carga durante el envío

### 3. **Endpoints Utilizados**

| Funcionalidad | Endpoint | Método |
|---|---|---|
| Series | `/documentos/cargar_series/` | GET |
| Subseries | `/documentos/cargar_subseries/?serie_id=X` | GET |
| Oficinas | {% url 'correspondencia:oficinas_todas_interna_ajax' %} | GET |
| Usuarios por Oficina | {% url 'correspondencia:usuarios_por_oficina_ajax' %}?oficina_id=X | GET |
| Procesos | {% url 'correspondencia:procesos_todos_ajax' %} | GET |
| Crear Comunicación | {% url 'correspondencia:crear_comunicacion_interna_ajax' %} | POST |

### 4. **Ventajas de esta Implementación**

✅ **Mantiene lo que funciona**: FormData + fetch (probado y verificado con anexos guardándose correctamente)

✅ **Completo**: Incluye todas las opciones de distribución del V1 (usuario, oficina, proceso, entidad)

✅ **TRD Automático**: El código TRD se construye automáticamente al seleccionar serie y subserie

✅ **UI Mejorada**: 
- Chips interactivos para multiselectores
- Tarjetas visuales con soporte de click
- Contadores de selección
- Validación visual de anexos

✅ **Robusto**: 
- Validación completa de datos antes de envío
- Logging en consola para debugging
- Manejo de errores graceful

✅ **Flexible**: 
- Sección de destinatarios se regenera dinámicamente al cambiar tipo de distribución
- Endpoints configurables vía data attributes

### 5. **Uso del Modal**

El modal V2 Full está disponible como el botón principal en:
- `/correspondencia/interna/recibidas.html` - Botón "Nuevo modal (V2)" con icono de rayo
- También disponible en otros listados (enviadas, etc.)

### 6. **Validación Backend**

El backend ya soporta todos estos tipos de distribución en la vista `crear_comunicacion_interna_ajax`:
- Validación de destinatarios según tipo
- Manejo de anexos (validación de tamaño, tipo de archivo)
- Guardado correcto de AnexoComunicacionInterna
- Envío a los usuarios correctos

## Próximos Pasos (Opcional)

1. **Deprecar V1**: Cuando se confirme que V2 Full funciona correctamente, se puede:
   - Remover el botón de V1 de la interfaz
   - Eventualmente eliminar modal_comunicacion_interna.html
   - Reemplazar todos los enlaces de V1 con V2 Full

2. **Mejorar UX**: 
   - Agregar confirmación antes de enviar
   - Mostrar preview de destinatarios antes de envío
   - Permitir borrador de comunicaciones

3. **Funcionalidades Adicionales**:
   - Firma digital
   - Templates de comunicaciones
   - Programación de envíos

## Testing Recomendado

1. **Anexos**: Seleccionar, validar límites, enviar y verificar guardado en media
2. **Series/Subseries**: Seleccionar serie y verificar autocomplete de TRD
3. **Distribución por Usuario**: Seleccionar oficina, usuarios múltiples, enviar
4. **Distribución por Oficina**: Seleccionar múltiples oficinas, enviar
5. **Distribución por Proceso**: Seleccionar proceso, enviar
6. **Distribución Entidad**: Enviar a toda la entidad
7. **Validaciones**: Intentar enviar sin destinatarios, sin asunto, archivos inválidos

## Logs Esperados

En la consola del navegador, se verá:
```
[V2 Full] Enviando: USUARIO, Array(9)  // O el tipo de distribución elegido
// Seguido de la respuesta del servidor
```
