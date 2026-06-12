# Guía de Testing - Modal V2 Full

## ✅ Validación Completada

El modal V2 Full ha pasado todas las validaciones:
- ✓ 16+ funciones/variables definidas
- ✓ 618 líneas de código limpio
- ✓ 5 endpoints configurados correctamente
- ✓ Todos los elementos HTML presentes
- ✓ FormData + fetch implementado
- ✓ Destinatarios con Map para gestión eficiente

## 📋 Plan de Testing

### Test 1: Carga Inicial del Modal
**Objetivo**: Verificar que el modal carga sin errores  
**Pasos**:
1. Abre navegador y ve a `/correspondencia/interna/recibidas/`
2. Haz clic en botón "Nuevo modal (V2)"
3. Verifica que se abra sin errores en consola

**Esperado**:
- ✓ Modal abre sin problemas
- ✓ Series se cargan automáticamente
- ✓ Oficinas se cargan automáticamente
- ✓ Sin errores en console (F12)

---

### Test 2: Carga de Series y Subseries
**Objetivo**: Verificar que series/subseries cargan y se autocompleta TRD  
**Pasos**:
1. Abre el modal V2 Full
2. Haz clic en dropdown "Serie documental"
3. Selecciona una serie de la lista
4. Verifica que se cargue subserie
5. Selecciona una subserie
6. Verifica que se autocomplete el TRD

**Esperado**:
- ✓ Series cargan de `/documentos/cargar_series/`
- ✓ Al seleccionar serie, subseries se cargan
- ✓ Al seleccionar subserie, TRD se autocompleta en formato: `OFICINA.SERIE.SUBSERIE`

**Consola esperada**:
```
[V2 Full] Enviando: USUARIO, Array(9)
```

---

### Test 3: Distribución por Usuario
**Objetivo**: Verificar multiselectores de usuarios  
**Pasos**:
1. Abre modal V2 Full
2. En "Tipo de Distribución" selecciona: **Usuario Específico**
3. Selecciona una oficina en el dropdown
4. Se debe mostrar lista de usuarios de esa oficina
5. Haz clic en 2-3 usuarios para seleccionar
6. Verifica que aparezcan como chips en "Seleccionados"
7. Haz clic en la X de un chip para deseleccionar

**Esperado**:
- ✓ Al cambiar tipo, sección de destinatarios se regenera
- ✓ Usuarios se cargan de esa oficina
- ✓ Tarjetas tienen hover visual
- ✓ Chips azules aparecen con nombres
- ✓ Contador actualiza dinámicamente
- ✓ Click en X deselecciona

---

### Test 4: Distribución por Oficina
**Objetivo**: Verificar multiselectores de oficinas  
**Pasos**:
1. Abre modal V2 Full
2. En "Tipo de Distribución" selecciona: **Oficina Completa**
3. Se debe mostrar grid de tarjetas con oficinas
4. Haz clic en 2-3 oficinas para seleccionar
5. Verifica que aparezcan como chips
6. Haz clic en la X para deseleccionar

**Esperado**:
- ✓ Oficinas se muestran como tarjetas
- ✓ Tarjetas cambian color al hacer clic
- ✓ Chips grises aparecen con nombres
- ✓ Contador actualiza

---

### Test 5: Distribución por Proceso
**Objetivo**: Verificar selector de proceso  
**Pasos**:
1. Abre modal V2 Full
2. En "Tipo de Distribución" selecciona: **Proceso Completo**
3. Se debe mostrar dropdown de procesos
4. Selecciona un proceso
5. Verifica que se guarde la selección

**Esperado**:
- ✓ Dropdown de procesos carga
- ✓ Se puede seleccionar un proceso
- ✓ La sección se reemplaza dinámicamente

---

### Test 6: Distribución a Entidad
**Objetivo**: Verificar distribución masiva  
**Pasos**:
1. Abre modal V2 Full
2. En "Tipo de Distribución" selecciona: **Toda la Entidad**
3. Verifica que muestre mensaje informativo

**Esperado**:
- ✓ Aparece alert con icono de personas
- ✓ Texto indica que se enviará a todos los usuarios
- ✓ No hay más selecciones necesarias

---

### Test 7: Validación de Anexos
**Objetivo**: Verificar validación de archivos  
**Pasos**:

#### Prueba 7a: Archivo válido
1. Abre modal V2 Full
2. Haz clic en selector de "Anexos"
3. Selecciona un PDF válido (< 2 MB)
4. Verifica que aparezca en lista con tamaño
5. Contador debe mostrar cantidad y tamaño total

**Esperado**:
- ✓ Archivo aparece en lista
- ✓ Se muestra tamaño correctamente
- ✓ Sin error

#### Prueba 7b: Múltiples archivos
1. Selecciona 3-5 archivos válidos
2. Verifica que todos aparezcan
3. Total debe ser < 10 MB

**Esperado**:
- ✓ Se muestran todos
- ✓ Total correcto

#### Prueba 7c: Archivo muy grande
1. Selecciona un archivo > 2 MB
2. Verifica que muestre error

**Esperado**:
- ✓ Error: "excede 2MB"
- ✓ Archivo rechazado
- ✓ Alert rojo visible

#### Prueba 7d: Formato inválido
1. Selecciona un .txt o .jpg
2. Verifica error

**Esperado**:
- ✓ Error: "formato no permitido"

#### Prueba 7e: Botón limpiar
1. Carga algunos archivos
2. Haz clic en botón X (Limpiar)
3. Verifica que se limpie todo

**Esperado**:
- ✓ Lista vacía
- ✓ Contador = 0
- ✓ Preview desaparece

---

### Test 8: Envío Completo
**Objetivo**: Verificar que la comunicación se cree y anexos se guarden  
**Pasos**:
1. Abre modal V2 Full
2. Llena todos los campos:
   - Ciudad: Saravena
   - Fecha: Hoy
   - Serie: Cualquiera
   - Subserie: Cualquiera
   - Tipo distribución: Usuario Específico
   - Usuarios: Selecciona 1-2
   - Asunto: "Test comunicación V2 Full"
   - Contenido: "Esto es un test"
   - Anexos: 1-2 archivos PDF válidos
3. Haz clic en "Enviar"
4. Verifica que:
   - Aparezca indicador de carga
   - Se muestre mensaje de éxito
   - Modal se cierre
   - Página se recargue
5. Verifica en base de datos:
   - Nueva ComunicacionInterna se creó
   - AnexoComunicacionInterna registros existen
   - Archivos existen en `/media/interna/anexos/YYYY/MM/`

**Esperado**:
- ✓ POST a `/correspondencia/interna/crear_comunicacion_interna_ajax/`
- ✓ Response: `{"success": true, "message": "..."}`
- ✓ Archivos guardados en media
- ✓ DB actualizada

---

### Test 9: Validaciones de Formulario
**Objetivo**: Verificar que rechaza envío sin datos requeridos  

#### Test 9a: Sin asunto
1. Llena todo menos asunto
2. Intenta enviar
3. Verifica que muestre alert: "Asunto... obligatorios"

#### Test 9b: Sin destinatarios
1. Llena todo pero no selecciona usuarios/oficinas
2. Intenta enviar
3. Verifica alert: "Seleccione al menos..."

#### Test 9c: Sin tipo distribución válido
1. No selecciona proceso en modo PROCESO
2. Intenta enviar
3. Verifica error

**Esperado**:
- ✓ Todos los validations funcionan
- ✓ User no puede enviar datos inválidos

---

### Test 10: Consola Browser
**Objetivo**: Verificar logs para debugging  
**Pasos**:
1. Abre DevTools (F12)
2. Ve a Console tab
3. Abre modal y envía comunicación
4. Busca logs con `[V2 Full]`

**Esperado**:
```
[V2 Full] Enviando: USUARIO, Array(9)
  ciudad: Saravena
  fecha_documento: 2024-12-XX
  trd: XX.XX.XX
  tipo_distribucion: USUARIO
  asunto: ...
  cuerpo: ...
  destinatarios_usuarios: [1, 2, 3]
  anexos: [File, File]
  anexos_count_client: 2
```

---

## 🔧 Troubleshooting

### "Series no cargan"
- Verificar endpoint: `GET /documentos/cargar_series/`
- Ver Network tab en DevTools
- Verificar permiso del usuario

### "Usuarios no aparecen"
- Verificar que oficina esté seleccionada
- Verificar endpoint: `GET /documentos/usuarios_por_oficina_ajax/`
- Verificar que usuarios existan en esa oficina

### "Anexos no se guardan"
- Verificar que `/media/` exista: `ls -ld /home/devdiego/Correspondencia-diciembre-1.0/media/`
- Verificar permisos: 755 o 777
- Revisar logs de Gunicorn y Nginx
- Verificar que AnexoComunicacionInterna.upload_to funcione

### "Errores 500"
- Revisar `/var/log/nginx/error.log` (o similar)
- Revisar logs de Gunicorn
- Verificar que todas las funciones del backend existan

### "TRD no se autocompleta"
- Verificar que `request.user.perfil.oficina.codigo_trd` esté lleno
- Verificar que serie y subserie tengan codigo_trd en BD

---

## 📊 Criterios de Éxito

✅ **Prueba Exitosa si**:
- Todos los 10 tests pasan
- Sin errores en console (excepto los esperados)
- Anexos se guardan en media
- DB se actualiza correctamente
- UI es responsiva y clara

---

## 📝 Reporte de Resultados

Cuando termines el testing, crea un reporte:

```
REPORTE DE TESTING - V2 FULL
============================
Fecha: YYYY-MM-DD
Testeador: [Tu nombre]

TESTS COMPLETADOS:
✓ Test 1: Carga inicial - PASÓ/FALLÓ
✓ Test 2: Series/Subseries - PASÓ/FALLÓ
✓ Test 3: Distribución usuario - PASÓ/FALLÓ
✓ Test 4: Distribución oficina - PASÓ/FALLÓ
✓ Test 5: Distribución proceso - PASÓ/FALLÓ
✓ Test 6: Distribución entidad - PASÓ/FALLÓ
✓ Test 7: Validación anexos - PASÓ/FALLÓ
✓ Test 8: Envío completo - PASÓ/FALLÓ
✓ Test 9: Validaciones - PASÓ/FALLÓ
✓ Test 10: Logs - PASÓ/FALLÓ

ERRORES ENCONTRADOS:
[Lista]

MEJORAS SUGERIDAS:
[Lista]

ESTADO FINAL: PRODUCCIÓN LISTA / NECESITA CORRECCIONES
```

---

## 🚀 Si Todo Funciona

1. Marcar V2 Full como default
2. Remover V1 de la interfaz (opcional)
3. Documentar para equipo
4. Capacitar usuarios si es necesario

---

**Última actualización**: Hoy  
**Versión**: V2 Full  
**Status**: ✅ Listo para testing
