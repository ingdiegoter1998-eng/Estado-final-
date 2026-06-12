# Sistema de Gestión de Correspondencia - Hospital del Sarare

Sistema web para la gestión integral de correspondencia entrante, saliente y comunicaciones internas en instituciones de salud. Desarrollado en Django con procesamiento automático de correos electrónicos.

## 📋 Características Principales

- ✅ **Radicación Automática** con numeración consecutiva única
- ✅ **Procesamiento Automático de Correos** mediante IMAP (cada 5 minutos)
- ✅ **Cálculo Automático de SLA** considerando días hábiles y festivos
- ✅ **Digitalización de Documentos** físicos con sello QR
- ✅ **Flujo de Aprobación** multinivel para respuestas
- ✅ **Seguimiento DSN** de entrega de correos y rebotes
- ✅ **Comunicaciones Internas** (Oficios entre oficinas)
- ✅ **Historial Completo** de todas las acciones (trazabilidad)

---

## 🛠️ Requisitos Previos

| Requisito | Versión Mínima |
|-----------|----------------|
| Python | 3.10+ |
| Redis | 6.0+ (para Celery) |
| Git | 2.0+ |

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Magicyasuo/Correspondencia-diciembre-1.0
cd correspondencia
```

### 2. Crear y activar entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Django
SECRET_KEY=tu-clave-secreta-aqui

# Email SMTP (Gmail)
EMAIL_HOST_USER=tu-correo@gmail.com
EMAIL_HOST_PASSWORD=tu-contraseña-de-aplicacion

# IMAP (lectura de correos)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_FOLDER_BOUNCES=bounces

# Celery (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Verificación de Email (opcional)
EMAIL_VERIFICATION_OFFLINE_MODE=true
```

> **Nota:** Para Gmail, debes usar una [Contraseña de Aplicación](https://support.google.com/accounts/answer/185833), no tu contraseña normal.

### 5. Crear migraciones y migrar base de datos

```bash
# Crear migraciones para cada aplicación
python manage.py makemigrations documentos
python manage.py migrate documentos

python manage.py makemigrations correspondencia
python manage.py migrate correspondencia

# Aplicar todas las migraciones restantes
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

El sistema estará disponible en: `http://127.0.0.1:8000`

---

## ⚙️ Configuración de Celery (Procesamiento de Correos)

Celery se encarga de ejecutar tareas en segundo plano:
- **Procesar correos entrantes** (cada 5 minutos)
- **Procesar rebotes** (cada 10 minutos)

### Iniciar Redis (Windows)

```bash
# Usando Docker (recomendado)
docker run -d -p 6379:6379 redis

# O instalar Redis para Windows
# https://github.com/microsoftarchive/redis/releases
```

### Iniciar Worker de Celery

```bash
celery -A hospital_document_management worker -l info --pool=solo
```

### Iniciar Celery Beat (Tareas Programadas)

```bash
celery -A hospital_document_management beat -l info
```

> **Tip:** En Windows, usa `--pool=solo` para evitar problemas con el pool de procesos.

---

## 📁 Estructura del Proyecto

```
hospital_document_management/     # Configuración principal Django
├── settings.py                   # Configuraciones del proyecto
├── urls.py                       # URLs principales
├── celery.py                     # Configuración de Celery
└── wsgi.py / asgi.py

correspondencia/                  # Aplicación principal
├── models.py                     # Modelos de datos (25+)
├── views.py                      # Vistas y lógica de negocio
├── urls.py                       # URLs de la app
├── templates/                    # Plantillas HTML (81)
├── static/                       # CSS, JS, imágenes
├── management/commands/          # Comandos de gestión
│   ├── procesar_emails_seguro.py # Lee correos de IMAP con validación
│   └── procesar_rebotes.py       # Procesa rebotes DSN
├── utils_sla.py                  # Cálculo de días hábiles
└── signals.py                    # Señales de Django

documentos/                       # Aplicación de gestión documental
├── models.py                     # OficinaProductora, Series, etc.
└── templates/

diagramas/                        # Diagramas de base de datos (DBML)
```

---

## 📊 Modelo de Datos Principal

| Modelo | Descripción |
|--------|-------------|
| `Correspondencia` | Correspondencia entrante |
| `CorrespondenciaSalida` | Respuestas y comunicaciones salientes |
| `Contacto` | Contactos externos (personas) |
| `EntidadExterna` | Empresas/instituciones externas |
| `CorreoEntrante` | Correos pendientes de radicar |
| `HistorialCorrespondencia` | Auditoría y trazabilidad |
| `ComunicacionInterna` | Oficios entre oficinas |
| `Notificacion` | Alertas del sistema |
| `GrupoAgenda` | Grupos para envíos masivos |

Ver diagramas completos en: `diagramas/`

---

## 🔄 Flujos Principales

### Flujo 1: Correspondencia Entrante
```
Documento llega → Radicación → Cálculo SLA → Asignación → Respuesta → Envío
     ↓                              ↓
   Físico                     Días hábiles
   Email (IMAP)               + Festivos
```

### Flujo 2: Correspondencia Saliente
```
Crear Borrador → Adjuntar archivos → Solicitar Aprobación → Aprobada → Envío SMTP
                                            ↓
                                        Rechazada → Correcciones
```

### Flujo 3: Comunicaciones Internas
```
Crear Oficio → Aprobación Líder → Firma Digital (si aplica) → Distribución → Notificación
```

---

## 🔧 Comandos Útiles

```bash
# Procesar correos manualmente (con validación de adjuntos)
python manage.py procesar_emails_seguro

# Procesar rebotes manualmente
python manage.py procesar_rebotes

# Recolectar archivos estáticos (producción)
python manage.py collectstatic

# Crear migración específica
python manage.py makemigrations correspondencia --name descripcion_cambio
```

---

## 📚 Documentación Adicional

- **Resumen del Aplicativo:** `documentacion/RESUMEN_APLICATIVO_CORRESPONDENCIA.md`
- **Guía de Seguridad:** `documentacion/GUIA_SEGURIDAD_CIBERNETICA.md`
- **Flujogramas:** `archivos afuera/flujograma_correspondencia_mejorado.md`
- **Diagramas de BD:** `diagramas/`

---

## 🔐 Variables de Entorno

| Variable | Descripción | Valor por Defecto |
|----------|-------------|-------------------|
| `SECRET_KEY` | Clave secreta de Django | (requerido) |
| `EMAIL_HOST_USER` | Correo para envío SMTP | - |
| `EMAIL_HOST_PASSWORD` | Contraseña de aplicación | - |
| `IMAP_SERVER` | Servidor IMAP | imap.gmail.com |
| `IMAP_PORT` | Puerto IMAP | 993 |
| `CELERY_BROKER_URL` | URL del broker Redis | redis://localhost:6379/0 |
| `EMAIL_VERIFICATION_OFFLINE_MODE` | Modo offline para validación | true |

---

## 👥 Roles del Sistema

| Rol | Permisos |
|-----|----------|
| **Ventanilla** | Radicar, imprimir sellos, aprobar respuestas |
| **Líder de Oficina** | Aprobar comunicaciones, gestionar oficina |
| **Usuario** | Leer, responder correspondencia asignada |
| **Administrador** | Acceso completo al sistema |

---

## 📝 Tecnologías Utilizadas

- **Backend:** Django 5.0, Python 3.x
- **Frontend:** Bootstrap 5, AdminLTE 3, HTMX
- **Base de Datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **Cola de Tareas:** Celery + Redis
- **Correo:** Gmail SMTP/IMAP
- **Autenticación:** django-allauth, django-axes

---

## 📄 Licencia

Desarrollado para el Hospital del Sarare E.S.E.  
Todos los derechos reservados © 2026

---

## 🤝 Contacto

Para soporte técnico o consultas, contactar al equipo de desarrollo.
