# 🗃️ POBLADO MASIVO DE BASE DE DATOS - COMPLETADO

## ✅ OBJETIVOS ALCANZADOS

Se ha completado exitosamente el poblado masivo de la base de datos con datos ficticios realistas para pruebas de carga y rendimiento.

### 📊 ESTADÍSTICAS FINALES

| Categoría | Cantidad | Descripción |
|-----------|----------|-------------|
| **👥 Usuarios** | 200 | Distribución: 120 Ventanilla, 80 Oficinas |
| **📄 Correspondencias Físicas** | 800 | Todas con números radicados FISICO-2025-XXXXXX |
| **👨‍💼 Contactos Externos** | 455 | Personas con datos completos |
| **🏢 Entidades Externas** | 155 | Empresas e instituciones ficticias |
| **🏬 Oficinas** | 8 | Estructura organizacional completa |
| **📁 Series Documentales** | 5 | Correspondencia, Contratos, Personal, etc. |
| **📋 Subseries** | 10 | Entrante, Saliente, Interna, etc. |

### 🎯 CARACTERÍSTICAS DE LOS DATOS

#### Usuarios
- **200 usuarios activos** distribuidos en grupos de trabajo
- **Nombres realistas** en español con apellidos comunes
- **Usernames únicos** en formato [nombre.apellido]
- **Contraseñas estándar** para facilitar pruebas
- **Distribución equilibrada** entre Ventanilla (60%) y Oficinas (40%)

#### Correspondencias Físicas
- **800 documentos** de tipo físico (no electrónico)
- **Números radicados únicos**: FISICO-2025-000001 a FISICO-2025-000800
- **Asuntos realistas**: Cartas, Memorandos, Oficios, Informes, etc.
- **Fechas distribuidas** en los últimos 90 días
- **Estados uniformes**: Todas en estado RADICADA
- **Distribución equilibrada** entre usuarios y oficinas

#### Contactos y Entidades
- **455 contactos externos** con datos completos
- **155 entidades ficticias** con nombres realistas
- **Información completa**: nombres, apellidos, cargos, correos, teléfonos
- **Entidades por sector**: Tecnología, Salud, Educación, Construcción, etc.
- **Ubicaciones geográficas**: Principales ciudades de Colombia

### 📋 DISTRIBUCIÓN DETALLADA

#### Por Grupos de Usuarios
```
Ventanilla: 120 usuarios (60%)
Oficinas: 80 usuarios (40%)
```

#### Por Oficinas de Destino
```
Contabilidad: 126 correspondencias (15.8%)
Atención al Usuario: 104 correspondencias (13.0%)
Recursos Humanos: 99 correspondencias (12.4%)
Compras: 99 correspondencias (12.4%)
Gestión Documental: 99 correspondencias (12.4%)
Mantenimiento: 97 correspondencias (12.1%)
Servicios Generales: 90 correspondencias (11.3%)
Dirección General: 86 correspondencias (10.8%)
```

#### Por Tipos de Documentos
```
Otros documentos: 344 (43.0%)
Certificados: 57 (7.1%)
Memorandos: 55 (6.9%)
Recibos: 53 (6.6%)
Oficios: 53 (6.6%)
Informes: 50 (6.3%)
Solicitudes: 48 (6.0%)
Cartas: 48 (6.0%)
Notas: 46 (5.8%)
Facturas: 46 (5.8%)
```

### 🔐 CREDENCIALES DE ACCESO

#### Superusuario
```
Usuario: admin
Contraseña: admin123
```

#### Usuarios Regulares (200 usuarios)
```
Formato: [nombre.apellido]
Ejemplos:
- ana.garcia
- carlos.rodriguez
- maria.lopez
- jose.martinez
- laura.gonzalez
...
- alejandro.guerrero
- lucia.torres
- pilar.mendoza

Contraseña: password123 (para todos)
```

### 📁 ESTRUCTURA DE DATOS

#### Series Documentales
1. **COR - Correspondencia** (Subseries: Entrante, Saliente, Interna)
2. **CON - Contratos** (Subseries: Contratos de Servicio, Convenios, Adiciones)
3. **PER - Personal** (Subseries: Nómina, Contrataciones, Despidos)
4. **COM - Compras** (Subseries: Órdenes de Compra, Facturas, Cotizaciones)
5. **PRO - Proyectos** (Subseries: Planificación, Ejecución, Seguimiento)

#### Oficinas
1. Dirección General
2. Recursos Humanos
3. Contabilidad
4. Compras
5. Mantenimiento
6. Servicios Generales
7. Atención al Usuario
8. Gestión Documental

### 🚀 APLICACIONES PRÁCTICAS

#### Para Pruebas de Carga
- **800 correspondencias** para evaluar rendimiento
- **200 usuarios** para pruebas de concurrencia
- **Datos realistas** para escenarios de producción

#### Para Pruebas Funcionales
- **Distribución equilibrada** entre oficinas y usuarios
- **Datos consistentes** para validaciones
- **Información completa** para pruebas de integración

#### Para Pruebas de UI/UX
- **Variedad de datos** para interfaces de usuario
- **Nombres realistas** para búsquedas y filtros
- **Fechas distribuidas** para calendarios y reportes

### 📋 EJEMPLOS DE USO

#### Ver todas las correspondencias
```sql
SELECT * FROM correspondencia_correspondencia
WHERE numero_radicado LIKE 'FISICO-2025-%'
ORDER BY fecha_radicacion DESC;
```

#### Ver correspondencias por oficina
```sql
SELECT o.nombre, COUNT(*) as cantidad
FROM correspondencia_correspondencia c
JOIN documentos_oficinaproductora o ON c.oficina_destino_id = o.id
WHERE numero_radicado LIKE 'FISICO-2025-%'
GROUP BY o.id, o.nombre;
```

#### Ver usuarios más activos
```sql
SELECT u.username, u.first_name, u.last_name, COUNT(*) as correspondencias
FROM correspondencia_correspondencia c
JOIN auth_user u ON c.usuario_radicador_id = u.id
WHERE numero_radicado LIKE 'FISICO-2025-%'
GROUP BY u.id, u.username, u.first_name, u.last_name
ORDER BY correspondencias DESC;
```

### ✅ CALIDAD DE DATOS

- **✅ Consistencia**: Todos los datos siguen las mismas reglas
- **✅ Unicidad**: Números de radicado y usernames únicos
- **✅ Realismo**: Nombres, direcciones y datos coherentes
- **✅ Distribución**: Equilibrio entre usuarios y oficinas
- **✅ Completitud**: Toda la información requerida presente
- **✅ Trazabilidad**: Fechas y usuarios de creación incluidos

### 🎯 RESULTADO FINAL

**Base de datos completamente poblada y lista para:**
- ✅ Pruebas de carga y rendimiento
- ✅ Validación de funcionalidades
- ✅ Demostraciones del sistema
- ✅ Entrenamiento de usuarios
- ✅ Desarrollo de nuevas características

**Sistema operativo y funcional con datos realistas para escenarios de producción.**
