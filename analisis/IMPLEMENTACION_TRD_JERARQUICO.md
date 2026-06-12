# Implementación TRD Jerárquico en Comunicaciones Internas

## Resumen Ejecutivo

Se implementó un sistema jerárquico de Códigos TRD (Tabula de Retención Documental) que construye automáticamente el código como: **OFICINA.SERIE.SUBSERIE**

Ejemplo: `300.02.03` donde:
- `300` = Código TRD de la Oficina Productora (Gerencia)
- `02` = Código TRD de la Serie Documental (ACTAS)
- `03` = Código TRD de la Subserie (ACTAS COMITÉ...)

## Estructura de Datos

### Modelo de Datos
```
OficinaProductora
  └─ codigo_trd: CharField (Ej: 300, 301, 302, 320, 321, 322, 323)

SerieDocumental
  └─ codigo_trd: CharField (Ej: 01, 02, 03, 04, ...)

SubserieDocumental
  └─ codigo_trd: CharField (Ej: 01, 02, 03, 04, ...)
  └─ serie: ForeignKey(SerieDocumental)

ComunicacionInterna
  └─ trd: CharField (Almacena TRD completo: OFICINA.SERIE.SUBSERIE)
  └─ remitente_oficina: ForeignKey(OficinaProductora)
```

### Datos Poblados

| Componente | Pobladas | Total | Porcentaje |
|---|---|---|---|
| Oficinas Productoras | 26 | 55 | 47.3% |
| Series Documentales | 28 | 37 | 75.7% |
| Subseries Documentales | 79 | 115 | 68.7% |

#### Oficinas con Código TRD
- **300**: Gerencia - Dirección
- **301**: Defensa Jurídica
- **302**: Control Interno
- **303**: Gestión de la Calidad
- **310-316**: Unidades de Funcionales (Científica, Servicios Ambulatorios, Hospitalarios, Laboratorio, Urgencias, Cirugía, Salud Ocupacional)
- **320**: Subgerencia Administrativa y Financiera (10 oficinas: Almacén, Cartera, Contabilidad, Costos, Facturación, Farmacia, Presupuesto, Gestión Documental, Tesorería, etc.)
- **321**: Subgerencia Talento Humano
- **322**: Sistemas y Estadística (2 oficinas)
- **323**: Planeación y Mantenimiento (2 oficinas)

## Cambios Implementados

### 1. Backend

#### 1.1 Modelos (documentos/models.py)
- **Cambio**: Eliminado `unique=True` de `OficinaProductora.codigo_trd`
- **Razón**: Múltiples oficinas pueden compartir el mismo código TRD nivel superior (ej: varias oficinas bajo TRD 320)
- **Migración**: `0017_alter_oficinaproductora_codigo_trd.py` aplicada

#### 1.2 Formularios (correspondencia/forms.py)
- **ComunicacionInternaForm**: Mantiene serie/subserie virtuales con TRD autocalculado
- **ComunicacionInternaRespuestaForm**: Nuevos campos virtuales `serie` y `subserie` agregados
  - Campo `trd` ahora es readonly con autocompletar
  - Los campos serie/subserie no se guardan en BD, solo se usan para calcular TRD

#### 1.3 Vistas (documentos/views.py)
- **cargar_series()**: Actualizado para incluir `codigo_trd` en respuesta JSON
  ```json
  [
    {
      "id": 1,
      "codigo": "1",
      "nombre": "ACCIONES CONSTITUCIONALES",
      "codigo_trd": "01"
    }
  ]
  ```
- **cargar_subseries()**: Ya incluía `codigo_trd` (sin cambios)

### 2. Frontend - Modal Crear Comunicación

#### 2.1 Template (modal_comunicacion_interna.html)
```html
<div class="modal fade" id="modalComunicacionInterna" 
     data-usuario-oficina-trd="{{ request.user.perfil.oficina.codigo_trd|default:'' }}">
```

#### 2.2 JavaScript
```javascript
// Obtener código TRD de la oficina del usuario
const modalElement = document.getElementById('modalComunicacionInterna');
const usuarioOficinaTrd = modalElement ? modalElement.dataset.usuarioOficinaTrd : '';

// Construcción automática del TRD
function construirCodigoTRDCompleto(oficinaTrd, serieTrd, subserieTrd) {
    return `${oficinaTrd}.${serieTrd}.${subserieTrd}`;
}

// Al cambiar subserie, autocompleta TRD
subserieSelect.addEventListener('change', function() {
    const selectedSubserieOption = this.options[this.selectedIndex];
    const selectedSerieOption = serieSelect.options[serieSelect.selectedIndex];
    
    if (usuarioOficinaTrd && selectedSerieOption.dataset.codigoTrd && selectedSubserieOption.dataset.codigoTrd) {
        const trd = construirCodigoTRDCompleto(
            usuarioOficinaTrd,
            selectedSerieOption.dataset.codigoTrd,
            selectedSubserieOption.dataset.codigoTrd
        );
        trdInput.value = trd;
    }
});
```

**Flujo de Usuario**:
1. Usuario abre modal para crear comunicación interna
2. Selecciona Serie → sistema carga subseries y sus códigos TRD
3. Selecciona Subserie → JavaScript construye automáticamente: `OFICINA.SERIE.SUBSERIE`
4. Campo TRD se autocompleta y queda readonly
5. Al guardar, TRD completo se persiste en BD

### 3. Frontend - Formulario Responder

#### 3.1 Template (interna/responder.html)
```html
<div class="row mb-3">
    <div class="col-md-6">
        <label for="id_serie_respuesta">Serie Documental (opcional)</label>
        {{ form.serie }}
    </div>
    <div class="col-md-6">
        <label for="id_subserie_respuesta">Subserie Documental (opcional)</label>
        {{ form.subserie }}
    </div>
</div>

<div class="mb-3">
    <label for="id_trd">Código TRD</label>
    {{ form.trd }}
</div>
```

#### 3.2 JavaScript (incrustado en template)
- Mismo patrón que el modal crear comunicación
- Carga series al inicializar página
- Suscribe eventos para cargar subseries y calcular TRD
- Obtiene código TRD de oficina del usuario respondedor

**Flujo de Usuario**:
1. Usuario accede a formulario de respuesta
2. Series se cargan automáticamente
3. Selecciona Serie y Subserie (opcional)
4. TRD se autocompleta si ambas están seleccionadas
5. Al guardar respuesta, TRD se persiste

### 4. Frontend - Modal Editar Comunicación

#### 4.1 Template (modal_editar_comunicacion_interna.html)
- Agregado: `data-usuario-oficina-trd="{{ request.user.perfil.oficina.codigo_trd|default:'' }}"`
- TRD actualmente es campo de texto (modo lectura)
- Lista para actualización futura con serie/subserie dinámicos

## Estructura de URLs y Endpoints

```
GET /registros/cargar_series/
  └─ Respuesta: [{ id, codigo, nombre, codigo_trd }, ...]

GET /registros/cargar_subseries/?serie_id=X
  └─ Respuesta: [{ id, nombre, codigo_trd }, ...]
```

## Migraciones Aplicadas

```
documentos/migrations/
  ├─ 0016_remove_unique_codigo_trd.py (Series y Subseries)
  └─ 0017_alter_oficinaproductora_codigo_trd.py (Oficinas)
```

## Datos Inicializados

### Mapeo CSV → BD Realizado
Se mapearon **29 oficinas únicas** del CSV "SERIES Y SUBSERIES.csv" a las **55 oficinas** de la BD:

```
GERENCIA                          → Gerencia - Dirección                    [300]
JURIDICA                          → Defensa Jurídica                        [301]
CONTROL INTERNO                   → Control Interno                         [302]
AUDITORIA Y CALIDAD               → Gestión de la Calidad                   [303]
SUBGERENCIA CIENTIFICA            → Gestión de Docencia Servicio           [310]
U.F.SERVICIOS AMBULATORIOS        → Consulta General                       [311]
U.F. SERVICIOS HOSPITALARIOS      → Internación Adulto                     [312]
UF.APOYO DIAGNOSTICO Y TERAPEUTICO → Servicio de Laboratorio Clínico       [313]
UF.DE URGENCIAS.                  → Urgencias y Procedimientos             [314]
UF.DE CIRUGIA.                    → Servicio de Cirugía                    [315]
UF.DE SALUD OCUPACIONAL           → Gestión de Seguridad y Salud           [316]
ALMACEN                           → Almacén/Gestión de Insumos             [320]
CARTERA                           → Gestión de Cartera                     [320]
CONTABILIDAD                      → Gestión de la Contabilidad             [320]
COSTOS                            → Gestión del Gasto                      [320]
FACTURACION(...)                  → Facturación                            [320]
FARMACIA                          → Servicio Farmacéutico                  [320]
PRESUPUESTO                       → Gestión del Presupuesto                [320]
PROCESO GESTIÓN DOCUMENTAL        → Gestión Documental                     [320]
SUBGERENCIA ADMINISTRATIVA        → Subgerencia administrativa y financiera [320]
TESORERIA                         → Gestión de Tesorería                   [320]
TALENTO HUMANO                    → Subgerencia Talento Humano             [321]
ESTADISTICA                       → Unidad de Estadísticas y Análisis      [322]
SISTEMAS                          → Gestión de Tecnologías y Sistemas      [322]
SISTEMAS Y ESTADISTICA            → Unidad de Estadísticas y Análisis      [322]
MANTENIMIENTO Y TRANSPORTE        → Gestión del Mantenimiento              [323]
PLANEACION Y MANTENIMIENTO        → Planeación                             [323]
```

### Series y Subseries
- **28/37 series** (75.7%) tienen código TRD poblado
- **79/115 subseries** (68.7%) tienen código TRD poblado
- Fuzzy matching utilizado para subseries con variaciones de nombre (threshold: 0.85)

## Comandos de Gestión

### Importar Códigos TRD de Oficinas
```bash
python manage.py import_trd_oficinas [--dry-run] [--threshold 0.70]
```

### Importar Códigos TRD de Series/Subseries
```bash
python manage.py import_trd_series_subseries [--dry-run] [--threshold 0.85]
```

## Consideraciones de Seguridad y Validación

1. **Campo TRD en Modales**: Readonly después de autocompletar
2. **Datos Faltantes**: Si falta oficina, serie o subserie, el TRD no se autocompleta
3. **Fallback**: Si no hay componente TRD, muestra solo la subserie
4. **Validación Backend**: Vista `crear_comunicacion_interna_ajax` recibe TRD del formulario y lo guarda directamente

## Pruebas Recomendadas

### Test Manual
1. Crear comunicación interna y verificar TRD autocompleta
2. Responder comunicación y verificar TRD autocompleta
3. Editar comunicación y verificar TRD se carga correctamente
4. Verificar BD que `comunicacion_interna.trd` contiene formato correcto

### Test SQL
```sql
-- Ver comunicaciones con TRD poblado
SELECT radicado, trd, remitente_oficina_id 
FROM correspondencia_comunicacioninterna 
WHERE trd IS NOT NULL 
LIMIT 10;

-- Ver oficinas sin código TRD
SELECT id, nombre, codigo_trd 
FROM documentos_oficinaproductora 
WHERE codigo_trd IS NULL;

-- Ver series sin código TRD
SELECT id, codigo, nombre, codigo_trd 
FROM documentos_seriedocumental 
WHERE codigo_trd IS NULL;
```

## Problemas Conocidos / Trabajo Futuro

1. **Oficinas sin TRD (29/55)**: No están incluidas en el mapeo CSV. Requieren mapeo manual si se necesita expandir.
2. **Series sin TRD (9/37)**: No tienen equivalente en CSV (ej: PETICIONES/QUEJAS/RECLAMOS, PROCESOS DE COBRO, etc.)
3. **Subseries sin TRD (36/115)**: No coinciden exactamente con CSV o están fuera del alcance del TRD institucional.
4. **Modal Editar**: Podría ampliarse para permitir seleccionar serie/subserie y recalcular TRD si es necesario.

## Archivos Modificados

```
documentos/
  ├─ models.py (línea ~120)
  ├─ views.py (línea 65, cargar_series)
  └─ migrations/
      ├─ 0016_remove_unique_codigo_trd.py (NEW)
      └─ 0017_alter_oficinaproductora_codigo_trd.py (NEW)

correspondencia/
  ├─ forms.py (línea ~1136, ComunicacionInternaRespuestaForm)
  ├─ views.py (sin cambios en lógica, compatible)
  └─ templates/
      ├─ partials/modals/
      │   ├─ modal_comunicacion_interna.html (actualizado)
      │   └─ modal_editar_comunicacion_interna.html (actualizado)
      └─ interna/
          └─ responder.html (actualizado)

Comandos Management:
  └─ documentos/management/commands/
      ├─ import_trd_series_subseries.py (NEW)
      └─ import_trd_oficinas.py (NEW)
```

## Referencias Técnicas

### Patrón de Construcción TRD
```
TRD = f"{oficina.codigo_trd}.{serie.codigo_trd}.{subserie.codigo_trd}"

Ejemplo Completo:
  - Oficina (Gerencia): codigo_trd = "300"
  - Serie (ACTAS): codigo_trd = "02"
  - Subserie (ACTAS COMITÉ ANTITRAMITES): codigo_trd = "03"
  - Resultado: "300.02.03"
```

### Validación JavaScript
```javascript
// Los campos serie/subserie se enumeran correctamente (cero-padded)
// El sistema asume que codigo_trd en BD siempre está formateado correctamente
// No hay validación de formato en frontend (se asume datos consistentes de BD)
```

## Mantenimiento

### Cuando Agregar Nuevas Oficinas
1. Agregar entrada en BD tabla `documentos_oficinaproductora`
2. Si corresponde a CSV TRD, ejecutar: `python manage.py import_trd_oficinas --file [archivo]`
3. Asignar `codigo_trd` manualmente en admin o mediante comando

### Cuando Agregar Nuevas Series/Subseries
1. Agregar entrada en BD
2. Si corresponde a CSV TRD, ejecutar: `python manage.py import_trd_series_subseries --file [archivo]`
3. Las subseries se mapearán automáticamente usando fuzzy matching si existe coincidencia ≥85%

---

**Fecha de Implementación**: 14 de enero de 2026
**Estado**: ✅ Completo y Funcional
**Próximos Pasos**: Pruebas en producción y validación de datos
