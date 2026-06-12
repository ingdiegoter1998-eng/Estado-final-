# Poblado de datos demo en SQLite (desarrollo local)

Guía para trabajar con **SQLite** en local sin tocar la base de datos de **producción (SQL Server)**.

## Advertencia

| Entorno | Motor | Archivo / host |
|---------|--------|----------------|
| Producción | SQL Server (`mssql`) | `settings.py` por defecto |
| Desarrollo local | SQLite | `db_dev.sqlite3` vía `settings_local` |
| Tests automáticos | SQLite en memoria | `settings_test.py` → `db_test.sqlite3` |

**Nunca** ejecutes `poblar_vida_demo` sin `settings_local`: el comando se detiene si el motor no es SQLite, pero conviene no depender solo de eso.

---

## Configuración rápida

### 1. Archivo de settings local

Copia el ejemplo y ajústalo si hace falta:

```bash
cp hospital_document_management/settings_local.example.py \
   hospital_document_management/settings_local.py
```

Por defecto usa `db_dev.sqlite3` en la raíz del proyecto.

### 2. Migraciones en SQLite

```bash
export DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local
# Windows PowerShell:
# $env:DJANGO_SETTINGS_MODULE = "hospital_document_management.settings_local"

venv/bin/python manage.py migrate
```

### 3. Servidor de desarrollo

```bash
DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local \
  venv/bin/python manage.py runserver
```

---

## Comando `poblar_vida_demo`

**Ubicación:** `correspondencia/management/commands/poblar_vida_demo.py`

Poblado **incremental**: no borra datos existentes; añade registros demo encima de lo que ya haya.

### Uso básico

```bash
DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local \
  venv/bin/python manage.py poblar_vida_demo --confirm
```

Sin `--confirm` solo muestra la advertencia y no modifica nada.

### Parámetros

| Opción | Default | Descripción |
|--------|---------|-------------|
| `--confirm` | — | Obligatorio para ejecutar |
| `--correspondencias` | 45 | Entrantes con estados variados |
| `--prestamos` | 14 | Préstamos documentales |
| `--fuids` | 6 | FUIDs con registros asociados |
| `--correos` | 28 | Correos entrantes (IMAP) |
| `--salidas` | 12 | Correspondencia de salida |
| `--internas` | 8 | Comunicaciones internas |
| `--registros` | 35 | Registros de archivo (TRD) |

Ejemplo ligero (solo notificaciones vía distribuciones + correos):

```bash
DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local \
  venv/bin/python manage.py poblar_vida_demo --confirm \
  --correspondencias 20 --prestamos 0 --fuids 0 --registros 0 --internas 4
```

### Qué crea el comando

- **Correspondencia entrante:** estados `RADICADA`, `ASIGNADA_USUARIO`, `LEIDA`, `RESPONDIDA`; medios físico/electrónico; fechas repartidas en ~75 días.
- **Distribuciones internas:** asignaciones a usuarios con perfil; disparan notificaciones vía `signals.py`.
- **Notificaciones:** además de las automáticas por asignación, crea avisos de vencimiento, respuesta, acceso oficina, urgencia, etc.
- **Correos entrantes:** `message_id` únicos; parte procesados y vinculados a radicados.
- **Salidas:** borrador, pendiente aprobación, aprobada, enviada, rechazada; con destinatarios.
- **Comunicaciones internas:** borrador, pendiente, aprobadas y **distribuidas** (con distribución y notificación).
- **FUIDs** y **registros de archivo** para el módulo documental.
- **Préstamos documentales** en varios estados del flujo.

También completa `codigo_trd_comunicacion_interna` en oficinas que no lo tengan (necesario para oficios internos).

### Requisitos previos en la base

Debe existir al menos:

- Usuarios con grupo **Ventanilla** y usuarios con **PerfilUsuario** / oficina.
- Oficinas, series y subseries.
- Contactos externos con correo.

La base `db_dev.sqlite3` del equipo ya incluye usuarios `demo_user_01` … `demo_user_12` y estructura TRD demo.

---

## Verificación rápida

```bash
# Conteos con sqlite3
sqlite3 db_dev.sqlite3 "
SELECT 'correspondencias', COUNT(*) FROM correspondencia_correspondencia
UNION ALL SELECT 'notificaciones', COUNT(*) FROM correspondencia_notificacion
UNION ALL SELECT 'distribuciones', COUNT(*) FROM correspondencia_distribucioninternausuario
UNION ALL SELECT 'correos', COUNT(*) FROM correspondencia_correoentrante
UNION ALL SELECT 'salidas', COUNT(*) FROM correspondencia_correspondenciasalida
UNION ALL SELECT 'internas', COUNT(*) FROM correspondencia_comunicacioninterna
UNION ALL SELECT 'fuids', COUNT(*) FROM documentos_fuid
UNION ALL SELECT 'prestamos', COUNT(*) FROM documentos_prestamodocumental;
"
```

En la UI: iniciar sesión con `admin` o `demo_user_01` (contraseña la configurada en local) y revisar bandejas, campana de notificaciones, préstamos y FUIDs.

---

## Archivos SQLite en el proyecto

| Archivo | Uso |
|---------|-----|
| `db_dev.sqlite3` | Desarrollo local recomendado (`settings_local`) |
| `db.sqlite3` | Copia/alternativa antigua; puede estar desactualizada |
| `db_test.sqlite3` | Generado por pytest (`settings_test`) |

Todos están en `.gitignore` y **no** deben subirse al repositorio.

---

## Relación con otros comandos

| Comando | Notas |
|---------|--------|
| `populate_db` (`documentos`) | Estructura TRD y fichas; no cubre correspondencia/notificaciones |
| `poblar_datos_iniciales` | Importa CSV institucional (`Unitdadtotalitaria.csv`) |
| `poblar_datos_ejemplo` | Documentado en `LIMPIEZA_BASE_DATOS.md` pero **no** está en el árbol actual del repo |
| `inicializar_radicados` | Ajusta consecutivos de radicado; usar con cuidado |

Para “darle vida” a la app en local, el flujo recomendado es: **migrate** → **poblar_vida_demo** → **runserver** con `settings_local`.

---

## Historial

- **2026-05-31:** Comando `poblar_vida_demo`, `settings_local.example.py` y esta guía.
