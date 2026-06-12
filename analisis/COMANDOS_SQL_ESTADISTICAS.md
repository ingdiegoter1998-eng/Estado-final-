# 📊 COMANDOS SQL PARA ESTADÍSTICAS DE CORRESPONDENCIAS

## 🚀 CONSULTAS SQL DIRECTAS

### 1. **Usuarios con más correspondencias radicadas**
```sql
SELECT
    u.first_name || ' ' || u.last_name as usuario,
    g.name as grupo,
    COUNT(*) as correspondencias
FROM correspondencia_correspondencia c
JOIN auth_user u ON c.usuario_radicador_id = u.id
JOIN auth_user_groups ug ON u.id = ug.user_id
JOIN auth_group g ON ug.group_id = g.id
WHERE c.numero_radicado LIKE 'FISICO-2025-%'
GROUP BY u.id, u.first_name, u.last_name, g.name
ORDER BY correspondencias DESC
LIMIT 10;
```

### 2. **Oficinas con más correspondencias asignadas**
```sql
SELECT
    o.nombre as oficina,
    COUNT(*) as correspondencias,
    ROUND(COUNT(*) * 100.0 / 800, 2) as porcentaje
FROM correspondencia_correspondencia c
JOIN documentos_oficinaproductora o ON c.oficina_destino_id = o.id
WHERE c.numero_radicado LIKE 'FISICO-2025-%'
GROUP BY o.id, o.nombre
ORDER BY correspondencias DESC;
```

### 3. **Estados de las correspondencias**
```sql
SELECT
    estado,
    COUNT(*) as cantidad,
    ROUND(COUNT(*) * 100.0 / 800, 2) as porcentaje
FROM correspondencia_correspondencia
WHERE numero_radicado LIKE 'FISICO-2025-%'
GROUP BY estado
ORDER BY cantidad DESC;
```

### 4. **Contactos externos más frecuentes**
```sql
SELECT
    c.nombres || ' ' || c.apellidos as contacto,
    e.nombre as entidad,
    COUNT(*) as correspondencias
FROM correspondencia_correspondencia cor
JOIN correspondencia_contacto c ON cor.remitente_id = c.id
JOIN correspondencia_entidadexterna e ON c.entidad_externa_id = e.id
WHERE cor.numero_radicado LIKE 'FISICO-2025-%'
GROUP BY c.id, c.nombres, c.apellidos, e.nombre
ORDER BY correspondencias DESC
LIMIT 10;
```

### 5. **Productividad por grupo de usuarios**
```sql
SELECT
    g.name as grupo,
    COUNT(DISTINCT u.id) as usuarios,
    COUNT(c.id) as correspondencias,
    ROUND(COUNT(c.id) * 1.0 / COUNT(DISTINCT u.id), 2) as promedio_por_usuario
FROM auth_user u
JOIN auth_user_groups ug ON u.id = ug.user_id
JOIN auth_group g ON ug.group_id = g.id
LEFT JOIN correspondencia_correspondencia c ON u.id = c.usuario_radicador_id
    AND c.numero_radicado LIKE 'FISICO-2025-%'
WHERE u.is_superuser = 0
GROUP BY g.id, g.name
ORDER BY correspondencias DESC;
```

### 6. **Correspondencias por día (últimos 7 días)**
```sql
SELECT
    DATE(fecha_radicacion) as fecha,
    COUNT(*) as cantidad
FROM correspondencia_correspondencia
WHERE numero_radicado LIKE 'FISICO-2025-%'
    AND fecha_radicacion >= date('now', '-7 days')
GROUP BY DATE(fecha_radicacion)
ORDER BY fecha DESC;
```

### 7. **Distribución por medio de recepción**
```sql
SELECT
    medio_recepcion,
    COUNT(*) as cantidad,
    ROUND(COUNT(*) * 100.0 / 800, 2) as porcentaje
FROM correspondencia_correspondencia
WHERE numero_radicado LIKE 'FISICO-2025-%'
GROUP BY medio_recepcion
ORDER BY cantidad DESC;
```

### 8. **Series documentales más utilizadas**
```sql
SELECT
    s.nombre as serie,
    s.codigo,
    COUNT(*) as correspondencias,
    ROUND(COUNT(*) * 100.0 / 800, 2) as porcentaje
FROM correspondencia_correspondencia c
JOIN documentos_seriedocumental s ON c.serie_id = s.id
WHERE c.numero_radicado LIKE 'FISICO-2025-%'
GROUP BY s.id, s.nombre, s.codigo
ORDER BY correspondencias DESC;
```

### 9. **Usuario más activo por oficina**
```sql
SELECT
    o.nombre as oficina,
    u.first_name || ' ' || u.last_name as usuario,
    COUNT(*) as correspondencias
FROM correspondencia_correspondencia c
JOIN auth_user u ON c.usuario_radicador_id = u.id
JOIN documentos_oficinaproductora o ON c.oficina_destino_id = o.id
WHERE c.numero_radicado LIKE 'FISICO-2025-%'
GROUP BY o.id, o.nombre, u.id, u.first_name, u.last_name
ORDER BY o.nombre, correspondencias DESC;
```

### 10. **Entidades externas más frecuentes**
```sql
SELECT
    e.nombre as entidad,
    COUNT(*) as correspondencias,
    COUNT(DISTINCT c.id) as contactos_unicos
FROM correspondencia_correspondencia cor
JOIN correspondencia_contacto c ON cor.remitente_id = c.id
JOIN correspondencia_entidadexterna e ON c.entidad_externa_id = e.id
WHERE cor.numero_radicado LIKE 'FISICO-2025-%'
GROUP BY e.id, e.nombre
ORDER BY correspondencias DESC
LIMIT 10;
```

## 📋 RESULTADOS ACTUALES (datos de muestra)

### **Top Usuarios:**
1. **Alejandro Guerrero Álvarez** (Ventanilla): 12 correspondencias
2. **Sergio Díaz García** (Oficinas): 10 correspondencias
3. **Rosa Hernández Sánchez** (Ventanilla): 9 correspondencias
4. **Lucía Fernández Ramírez** (Oficinas): 9 correspondencias
5. **Silvia Fernández Flores** (Ventanilla): 9 correspondencias

### **Top Oficinas:**
1. **Contabilidad**: 126 correspondencias (15.8%)
2. **Atención al Usuario**: 104 correspondencias (13.0%)
3. **Recursos Humanos**: 99 correspondencias (12.4%)
4. **Compras**: 99 correspondencias (12.4%)
5. **Gestión Documental**: 99 correspondencias (12.4%)

### **Distribución por Grupo:**
- **Ventanilla**: 117 usuarios, 476 correspondencias (promedio: 4.07 por usuario)
- **Oficinas**: 78 usuarios, 324 correspondencias (promedio: 4.15 por usuario)

### **Estados:**
- **RADICADA**: 800 correspondencias (100%)

### **Medios de Recepción:**
- **FISICO**: 800 correspondencias (100%)

## 🚀 CÓMO EJECUTAR LAS CONSULTAS

### Opción 1: Python Script
```bash
python -c "
import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Pegar cualquier consulta SQL aquí
cursor.execute('TU_CONSULTA_SQL_AQUI')
resultados = cursor.fetchall()

for fila in resultados:
    print(fila)

conn.close()
"
```

### Opción 2: Script Python
Crear un archivo `consultas.py`:
```python
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Consulta de ejemplo
cursor.execute("""
    SELECT u.first_name || ' ' || u.last_name, COUNT(*)
    FROM correspondencia_correspondencia c
    JOIN auth_user u ON c.usuario_radicador_id = u.id
    WHERE c.numero_radicado LIKE 'FISICO-2025-%'
    GROUP BY u.id ORDER BY COUNT(*) DESC LIMIT 5;
""")

for usuario, cantidad in cursor.fetchall():
    print(f"{usuario}: {cantidad}")

conn.close()
```

### Opción 3: Cliente SQLite (si está instalado)
```bash
sqlite3 db.sqlite3
> SELECT u.first_name || ' ' || u.last_name, COUNT(*)
  FROM correspondencia_correspondencia c
  JOIN auth_user u ON c.usuario_radicador_id = u.id
  WHERE c.numero_radicado LIKE 'FISICO-2025-%'
  GROUP BY u.id ORDER BY COUNT(*) DESC LIMIT 5;
> .exit
```

## 📈 ANÁLISIS DE LOS DATOS

### **Insights Importantes:**
1. **Distribución equilibrada**: Las correspondencias están bien distribuidas entre usuarios y oficinas
2. **Productividad similar**: Ambos grupos (Ventanilla y Oficinas) tienen promedios muy similares
3. **Oficina más demandada**: Contabilidad recibe significativamente más correspondencias
4. **Concentración de actividad**: El 5% de usuarios más activos generan ~6% de correspondencias

### **Posibles Análisis Adicionales:**
- Rendimiento por período de tiempo
- Patrones de radicación por usuario
- Distribución por tipo de documento
- Análisis de carga de trabajo por oficina

## 🎯 USO RECOMENDADO

Estas consultas son útiles para:
- ✅ **Evaluación de carga de trabajo** por usuario/oficina
- ✅ **Identificación de usuarios más productivos**
- ✅ **Planificación de recursos** según demanda
- ✅ **Análisis de rendimiento** del sistema
- ✅ **Auditoría y trazabilidad** de correspondencias
