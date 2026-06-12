# 🧹 Limpieza y Poblado de Base de Datos

Este documento explica cómo realizar una limpieza profunda de la base de datos y poblar con datos de ejemplo para el sistema de correspondencia.

## 🚨 Advertencia Importante

**ESTOS COMANDOS ELIMINARÁN TODOS LOS DATOS DE CORRESPONDENCIA**

- ✅ Se mantienen: Usuarios, estructura organizacional (opcional)
- ❌ Se eliminan: Correspondencias, contactos, entidades externas, archivos

## 📋 Comandos Disponibles

### 1. Limpieza Profunda

```bash
# Limpieza básica (con confirmación)
python manage.py limpiar_base_datos

# Limpieza automática (sin confirmación)
python manage.py limpiar_base_datos --confirm

# Limpieza completa incluyendo archivos de media
python manage.py limpiar_base_datos --confirm --clean-media

# Mantener usuarios del sistema
python manage.py limpiar_base_datos --confirm --preserve-users

# Mantener estructura organizacional
python manage.py limpiar_base_datos --confirm --preserve-structure
```

### 2. Poblado con Datos de Ejemplo

> **Desarrollo local (SQLite, 2026):** usar [`POBLADO_DESARROLLO_SQLITE.md`](POBLADO_DESARROLLO_SQLITE.md) y el comando `poblar_vida_demo` con `settings_local`. Los comandos `poblar_datos_ejemplo` / `limpiar_y_poblar.py` de esta guía pueden no estar presentes en el repositorio actual.

```bash
# Poblado básico (si el comando existe en tu copia del repo)
python manage.py poblar_datos_ejemplo

# Poblado personalizado
python manage.py poblar_datos_ejemplo --usuarios 10 --oficinas 5 --contactos 20 --correspondencia 50

# Poblado automático (sin confirmación)
python manage.py poblar_datos_ejemplo --confirm
```

### 3. Script de Conveniencia

```bash
# Ejecutar limpieza y poblado automáticamente
python limpiar_y_poblar.py
```

## 🔧 Opciones de Limpieza

### `limpiar_base_datos`

| Opción | Descripción |
|--------|-------------|
| `--confirm` | Ejecutar sin confirmación interactiva |
| `--preserve-users` | Mantener usuarios del sistema |
| `--preserve-structure` | Mantener oficinas, series y subseries |
| `--clean-media` | Eliminar archivos de media |

### `poblar_datos_ejemplo`

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--usuarios` | Número de usuarios a crear | 3 |
| `--oficinas` | Número de oficinas a crear | 5 |
| `--contactos` | Número de contactos externos | 10 |
| `--correspondencia` | Número de correspondencias | 20 |
| `--confirm` | Ejecutar sin confirmación | False |

## 📊 Datos Creados

### Usuarios
- **Superusuario**: `admin` / `admin123`
- **Usuarios de ejemplo**: `[nombre.apellido]` / `password123`
- **Grupos**: Ventanilla, Administradores, Oficinas

### Estructura Organizacional
- **Oficinas**: Dirección General, RRHH, Contabilidad, etc.
- **Series**: Correspondencia, Contratos, Personal, etc.
- **Subseries**: Entrante, Saliente, Interna, etc.

### Contactos Externos
- **Entidades**: Ministerio de Salud, Alcaldía, Proveedores, etc.
- **Contactos**: Con nombres, apellidos, cargos, correos, teléfonos

### Correspondencia de Ejemplo
- **Tipos**: Entrante, con diferentes estados
- **Medios**: Físico y Electrónico
- **Estados**: Radicada, Asignada, Leída, Respondida
- **Notificaciones**: Asociadas a las correspondencias

## 🚀 Uso Recomendado

### Para Desarrollo/Pruebas

```bash
# Limpieza completa y poblado automático
python limpiar_y_poblar.py
```

### Para Producción (Cuidado!)

```bash
# Solo limpiar datos de correspondencia, mantener usuarios y estructura
python manage.py limpiar_base_datos --confirm --preserve-users --preserve-structure

# Luego poblar con datos reales manualmente
```

## 🔍 Verificación

Después de ejecutar los comandos, puede verificar que todo funciona:

1. **Acceder al admin**: `http://127.0.0.1:8000/admin/`
2. **Login**: `admin` / `admin123`
3. **Verificar datos**: Revisar que aparecen usuarios, oficinas, contactos y correspondencias
4. **Probar funcionalidad**: Crear nueva correspondencia, asignar usuarios, etc.

## ⚠️ Solución de Problemas

### Error: "No se puede eliminar Contactos Externos"

Este error es normal y esperado. Los comandos de limpieza manejan las dependencias automáticamente en el orden correcto.

### Error: "Permission denied" en archivos de media

```bash
# En Windows
python manage.py limpiar_base_datos --confirm

# En Linux/Mac
sudo python manage.py limpiar_base_datos --confirm --clean-media
```

### Error: "Database is locked"

Cerrar todas las conexiones a la base de datos y ejecutar nuevamente.

## 📝 Notas Importantes

1. **Backup**: Siempre hacer backup antes de limpiar en producción
2. **Dependencias**: Los comandos manejan automáticamente las dependencias entre modelos
3. **Transacciones**: Todo se ejecuta en transacciones para garantizar consistencia
4. **Media**: Los archivos de media se eliminan solo si se especifica `--clean-media`

## 🎯 Casos de Uso

### Desarrollo Local
```bash
python limpiar_y_poblar.py
```

### Pruebas de Funcionalidad
```bash
python manage.py poblar_datos_ejemplo --correspondencia 100
```

### Limpieza Selectiva
```bash
python manage.py limpiar_base_datos --confirm --preserve-users --preserve-structure
```

### Reset Completo
```bash
python manage.py limpiar_base_datos --confirm --clean-media
python manage.py poblar_datos_ejemplo --confirm
```
