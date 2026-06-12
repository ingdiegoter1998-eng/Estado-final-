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
CELERY_EMAIL_CHECK_INTERVAL=300  # Intervalo de revisión de emails en segundos (default: 300 = 5 min)

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

## 🚀 Despliegue en Producción (Intranet)

El sistema está configurado para despliegue con **Gunicorn + Nginx** en la intranet del hospital.

### Estructura de Despliegue

Todos los archivos de configuración están en:
```
deploy/
├── systemd/correspondencia.service    # Servicio para Gunicorn
├── nginx/correspondencia.conf         # Configuración de Nginx
├── logrotate/correspondencia          # Rotación de logs
├── scripts/apply.sh                   # Script de instalación
└── README.md                          # Documentación completa
```

### Instalación Rápida

```bash
# Activar virtualenv
source /home/devdiego/Correspondencia-diciembre-1.0/venv/bin/activate

# Instalar Gunicorn
pip install gunicorn

# Recolectar estáticos
python manage.py collectstatic --noinput

# Ejecutar script de despliegue
chmod +x /home/devdiego/Correspondencia-diciembre-1.0/deploy/scripts/apply.sh
/home/devdiego/Correspondencia-diciembre-1.0/deploy/scripts/apply.sh
```

### Acceso en Producción

- **Intranet (LAN):** `http://192.168.3.230/`
- **Ngrok (remoto):** `https://xxx-yyy-zzz.ngrok.io` (si tienes túnel activo)
- **DNS personalizado:** Ver sección de DNS más abajo

### Verificación del Despliegue

```bash
# Estado de servicios
sudo systemctl status correspondencia
sudo systemctl status nginx

# Prueba rápida
curl -I http://192.168.3.230/

# Monitorear logs
sudo journalctl -u correspondencia -f
sudo tail -f /var/log/nginx/correspondencia.error.log
```

### Configuración de Capacidad

Actualmente:
- **Workers Gunicorn:** 4 (optimizado para 4 cores)
- **Threads por worker:** 4
- **Capacidad:** 100-150 usuarios concurrentes
- **Base de datos:** SQL Server (192.168.1.15:1433) - Multiusuario

Para ajustar workers según CPU:
```bash
sudo nano /etc/systemd/system/correspondencia.service
# Editar línea ExecStart: --workers N (donde N = cores + 1)
sudo systemctl daemon-reload
sudo systemctl restart correspondencia
```

---

## 🌐 Configuración de DNS Personalizado

En lugar de acceder por IP (`192.168.3.230`), puedes usar un dominio como `correspondenciahospital.com` o similar.

### Opción 1: DNS Local (Recomendado para Intranet)

**En el servidor del hospital:**

1. Configura un servidor DNS local (BIND, Dnsmasq, Windows DNS, etc.).
2. Crea un registro A que apunte a tu servidor:
   ```
   correspondenciahospital.com  A  192.168.3.230
   ```

3. Configura todos los clientes para usar ese DNS.

**O manualmente en cada computadora:**

**Windows:**
- Abre `C:\Windows\System32\drivers\etc\hosts` (como admin).
- Añade la línea:
  ```
  192.168.3.230  correspondenciahospital.com
  ```

**Linux/Mac:**
- Edita `/etc/hosts`:
  ```bash
  sudo nano /etc/hosts
  # Añade:
  192.168.3.230  correspondenciahospital.com
  ```

4. Accede desde navegador:
   ```
   http://correspondenciahospital.com/
   ```

### Opción 2: DNS Externo (Para Acceso Remoto)

Si quieres acceder desde fuera del hospital:

1. Registra un dominio (ej: `correspondenciahospital.com`) en un registrador (GoDaddy, Namecheap, etc.).
2. Crea un registro A:
   ```
   correspondenciahospital.com  A  [IP_PUBLICA_HOSPITAL]
   ```
3. Requiere una IP pública estática y configuración de firewall.

### Opción 3: Ngrok + Dominio

Si usas Ngrok:
```bash
ngrok http 192.168.3.230:80
```
Ngrok proporciona una URL `https://xxx.ngrok.io`. La aplicación ya está configurada para Ngrok.

### Actualizar Django para Dominio Personalizado

Una vez configures el DNS, añade el dominio a `ALLOWED_HOSTS` en `settings.py`:

```python
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '192.168.3.230',
    'correspondenciahospital.com',  # Añadir aquí
    '.ngrok-free.app',
    '.ngrok.io',
]
```

Luego reinicia:
```bash
sudo systemctl restart correspondencia
```

### Actualizar Nginx para Dominio

Edita `/etc/nginx/sites-available/correspondencia`:

```nginx
server {
    listen 192.168.3.230:80;
    server_name 192.168.3.230 correspondenciahospital.com;  # Añadir dominio
    
    allow 192.168.0.0/16;
    deny all;
    # ... resto de configuración ...
}
```

Valida y recarga:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

Ahora puedes acceder desde:
- `http://192.168.3.230/`
- `http://correspondenciahospital.com/` (si DNS está configurado)

---

## ⚙️ Configuración de Celery (Procesamiento de Correos)

Celery se encarga de ejecutar tareas en segundo plano con Redis como broker (`redis://localhost:6379/0`).

### Tareas Programadas (Beat Schedule)

| Tarea | Intervalo | Descripción |
|-------|-----------|-------------|
| `procesar_emails_periodico` | 2 min (configurable) | Procesa correos UNSEEN desde INBOX (modo rápido) o INBOX+AllMail (recovery) |
| `watchdog_inbox` | 1 min | Vigila INBOX con filtro UNSEEN para detectar correos faltantes |
| `procesar_rebotes_periodico` | 10 min | Detecta y procesa correos de rebote |
| `actualizar_urgencias_pendientes` | 30 min | Actualiza horas transcurridas y marca urgencias vencidas |
| `verificar_escalamiento_urgencias` | 1 hora | Escala urgencias no atendidas al nivel superior |
| `auto_aprobar_correspondencia` | 1 min | Aprueba automáticamente correspondencia sin aprobador asignado |

### Mecanismo de Lock (Anti-colisión)

Las tareas `procesar_emails_periodico` y `watchdog_inbox` comparten un **lock Redis** para evitar procesamiento simultáneo de correos:

- Clave Redis: `correspondencia:email_processing_lock`
- Si una tarea tiene el lock, la otra omite su ejecución
- El lock se libera automáticamente al finalizar (incluso si hay errores) via `finally`
- Timeout de seguridad: 240s (tarea principal), 120s (watchdog)
- Fallback: Si no hay `django-redis`, usa el cache de Django (`LocMemCache`)

### Watchdog de INBOX

La tarea `watchdog_inbox` resuelve el problema de **correos que llegan a INBOX pero no se sincronizan inmediatamente a AllMail** en Gmail:

1. Filtra con `UNSEEN` + fecha de hoy a nivel IMAP (server-side, ultraligero)
2. Descarga solo **headers** de correos no leídos de hoy en INBOX
3. Compara message-ids con la base de datos
4. Descarga y guarda solo los correos faltantes (máximo 20 por ciclo)
5. Marca los correos como leídos en Gmail después de guardarlos

### Escaneo Optimizado

El comando `procesar_emails_seguro` tiene dos modos:

**Modo Normal (periódico):**
- Solo INBOX con filtro `UNSEEN` (server-side)
- Alcance: 1 día hacia atrás
- Tiempo típico: <1 segundo si no hay correos nuevos

**Modo Recovery (`--recovery`):**
- INBOX + `[Gmail]/Todos` (AllMail)
- Alcance: 7 días (configurable con `--days`)
- Escanea todos los correos (incluso leídos) y procesa los faltantes en BD
- Se usa un set de `message-id` para deduplicar entre carpetas

**Intervalo de Revisión de Emails:**
- Por defecto: **2 minutos** (120 segundos)
- Configurable con variable de entorno `CELERY_EMAIL_CHECK_INTERVAL`
- **Recomendaciones de carga:**
  - **Volumen bajo-medio** (< 100 emails/hora): 2 minutos es óptimo
  - **Volumen alto** (> 200 emails/hora): mantener 2 minutos (el filtro UNSEEN lo hace viable)
  - **Bandejas saturadas**: monitorear CPU/RAM del worker y ajustar a 5 min si necesario
  - Con filtro UNSEEN cada ejecución tarda <1 seg cuando no hay correos nuevos

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

### Servicios Systemd (Producción Linux)

```bash
sudo systemctl start correspondencia-celery-worker
sudo systemctl start correspondencia-celery-beat
sudo systemctl status correspondencia-celery-worker correspondencia-celery-beat
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
│   ├── procesar_rebotes.py       # Procesa rebotes DSN
│   └── poblar_vida_demo.py       # Datos demo en SQLite (solo desarrollo)
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

### Desarrollo local con SQLite

Producción usa SQL Server (`settings.py`). En local, usa SQLite para no tocar producción:

```bash
cp hospital_document_management/settings_local.example.py hospital_document_management/settings_local.py
export DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local
python manage.py migrate
python manage.py poblar_vida_demo --confirm
python manage.py runserver
```

Guía completa: [`documentacion/POBLADO_DESARROLLO_SQLITE.md`](documentacion/POBLADO_DESARROLLO_SQLITE.md)

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

## 🧪 Tests

Los tests usan **pytest** con **SQLite en memoria** (`settings_test.py`) para evitar depender de SQL Server.

```bash
# Ejecutar todos los tests
python -m pytest

# Ejecutar solo tests del watchdog
python -m pytest correspondencia/tests/test_watchdog_inbox.py -v

# Ejecutar sin coverage (más rápido)
python -m pytest --no-cov

# Ejecutar un test específico
python -m pytest correspondencia/tests/test_watchdog_inbox.py::WatchdogInboxTests::test_watchdog_detecta_y_guarda_faltante -v
```

### Archivos de Test Principales

| Archivo | Qué cubre |
|---------|-----------|
| `test_watchdog_inbox.py` | Lock Redis, watchdog_inbox, coordinación entre tareas (18 tests) |
| `test_procesar_emails_celery.py` | Procesamiento de correos vía Celery (3 tests) |
| `test_aprobacion_automatica.py` | Aprobación automática de correspondencia |
| `test_comunicaciones_internas.py` | Flujo de comunicaciones internas |
| `test_radicacion_module.py` | Módulo de radicación |
| `test_views_coverage.py` | Cobertura de vistas principales |

### Configuración

- **pytest.ini** — `DJANGO_SETTINGS_MODULE = hospital_document_management.settings_test`
- **Settings test** — SQLite `:memory:`, `LocMemCache`, `CELERY_TASK_ALWAYS_EAGER=True`

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
| `CELERY_EMAIL_CHECK_INTERVAL` | Intervalo revisión emails (segundos) | 120 |
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
- **Base de Datos:** SQLite (desarrollo) / Sqlserver (producción)
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
