"""
Django settings for hospital_document_management project.
Generado por 'django-admin startproject' usando Django 5.1.3.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default=None):
    value = os.getenv(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]

# Cargar variables de entorno desde .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ====================================================================================
# SEGURIDAD
# ====================================================================================
DEBUG = _env_bool("DJANGO_DEBUG", False)

# runserver local con settings de producción (BD real, DEBUG=False): nginx no está
# delante; activar RUNSERVER_LOCAL=1 para servir /static/ y /media/ desde STATIC_ROOT.
RUNSERVER_LOCAL = _env_bool("RUNSERVER_LOCAL", False)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está configurada. Usa deploy/env/.env.example como base para tu .env."
    )

ALLOWED_HOSTS = _env_list(
    "ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
        "192.168.2.23",
        "192.168.3.230",
        "100.104.246.117",
        ".ngrok.io",
        ".ngrok-free.app",
        ".ngrok-free.dev",
    ],
)


# Configuración CORS
CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://127.0.0.1:3000",  # Next.js dev server
    "http://127.0.0.1:3001",  # Next.js dev server (alt port)
    "http://localhost",
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",  # Next.js dev server (alt port)
    "http://192.168.2.23",
    "https://192.168.2.23",  # Agregar esquema HTTPS
    "http://192.168.3.230",
    "https://192.168.3.230",
    "http://100.104.246.117",  # Tailscale
    "https://*.ngrok-free.app", # Añadido para permitir orígenes ngrok seguros
    "https://*.ngrok-free.dev", # Añadido para permitir orígenes ngrok .dev
    "https://*.ngrok.io", # Dominios ngrok antiguos
]

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1",
    "http://127.0.0.1:3000",  # Next.js dev server
    "http://127.0.0.1:3001",  # Next.js dev server (alt port)
    "http://localhost",
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",  # Next.js dev server (alt port)
    "http://192.168.2.23",
    "https://192.168.2.23",  # Agregar esquema HTTPS
    "http://192.168.3.230",
    "https://192.168.3.230",
    "http://100.104.246.117",  # Tailscale
    "https://*.ngrok-free.app",
    "https://*.ngrok-free.dev",
    "https://*.ngrok.io",
]

# Permitir cookies de sesión Django desde Next.js
CORS_ALLOW_CREDENTIALS = True


# Ajusta si no quieres que embedan el sitio (Clickjacking):
X_FRAME_OPTIONS = "DENY"

# Configuración de cookies para permitir acceso desde Next.js (localhost cross-port)
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_DOMAIN = None    # None = usa el host actual (localhost)

# ====================================================================================
# APLICACIONES Y MIDDLEWARE
# ====================================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_extensions",
    "django_dbml",
    "documentos",
    "widget_tweaks",
    "adminlte3",
    "adminlte3_theme",
    "corsheaders",
    "rest_framework",
    "admin_interface",
    "colorfield",
    'axes',
    "guardian",
    'allauth',
    'allauth.account',
    'correspondencia',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_htmx',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "hospital_document_management.urls"

WSGI_APPLICATION = "hospital_document_management.wsgi.application"

AUTHENTICATION_BACKENDS = (
    "axes.backends.AxesStandaloneBackend",  # <-- añadido (django-axes >=5.0)
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)
# bloqueo de usuario por exceder numeros de intentos
# Número de intentos permitidos
AXES_FAILURE_LIMIT = 6

# Bloquear cuando se alcance el límite
AXES_LOCK_OUT_AT_FAILURE = True

# Tiempo de bloqueo (ejemplo: 1 hora)
# Acepta un objeto timedelta, por ejemplo:
from datetime import timedelta
AXES_COOLOFF_TIME = timedelta(hours=0.2)  # Ajusta según tu preferencia

# Si solo quieres bloquear por nombre de usuario (no por IP):
# AXES_ONLY_USER_FAILURES está deprecado en django-axes 5.0+
# Se usa AXES_LOCKOUT_PARAMETERS en su lugar
AXES_LOCKOUT_PARAMETERS = ['username']  # Bloquear solo por nombre de usuario

# ====================================================================================
# BASE DE DATOS
# ====================================================================================
def _detect_odbc_driver():
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        for candidate in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
            if candidate in drivers:
                return candidate
    except Exception:
        pass
    return os.getenv("DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

ODBC_DRIVER = _detect_odbc_driver()

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": os.getenv("DB_NAME", "GestionDocumental"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "1433"),
        "CONN_MAX_AGE": 600,  # Reciclar conexiones cada 10 min para evitar conexiones stale con SQL Server
        "OPTIONS": {
            "driver": ODBC_DRIVER,
            "extra_params": "Encrypt=yes;TrustServerCertificate=yes",  # <-- añade para evitar fallo SSL (solo dev)
        },
    },
}
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     },
# }

# ====================================================================================
# VALIDACIÓN DE CONTRASEÑAS
# ====================================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ====================================================================================
# INICIO DE SESIÓN
# ====================================================================================
LOGIN_URL = "/registros/login/"
LOGOUT_REDIRECT_URL = "/registros/login/"
LOGIN_REDIRECT_URL = "/registros/welcome/"

# App Next.js de monitoreo/tickets (ruta pública). Vacío = mismo host que la petición + /monitoreo/chat.
MONITOREO_CHAT_URL = os.getenv("MONITOREO_CHAT_URL", "").strip()

# ====================================================================================
# INTERNACIONALIZACIÓN
# ====================================================================================
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# SLA: la jornada laboral para conteo de términos cierra a las 18:00 hora Colombia.
import datetime
SLA_CUTOFF_HOUR = datetime.time(18, 0)

# ====================================================================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ====================================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "correspondencia" / "static",
    BASE_DIR / "documentos" / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ====================================================================================
# VERIFICACIÓN DE EMAIL EXTERNA (configurable)
# ====================================================================================
# Proveedor por defecto: MailboxLayer (APILayer)
# Dashboard: https://mailboxlayer.com/dashboard
# Endpoint: https://apilayer.net/api/check
# Parámetros: access_key (API key), email, smtp=1, format=1

EMAIL_VERIFIER_API_URL = os.getenv('EMAIL_VERIFIER_API_URL', 'https://apilayer.net/api/check')
EMAIL_VERIFIER_API_KEY = os.getenv('EMAIL_VERIFIER_API_KEY', '')
EMAIL_VERIFIER_API_KEY_PARAM = os.getenv('EMAIL_VERIFIER_API_KEY_PARAM', 'access_key')
# Extra params opcionales (JSON en string)
import json as _json
EMAIL_VERIFIER_API_EXTRA_PARAMS = _json.loads(os.getenv('EMAIL_VERIFIER_API_EXTRA_PARAMS', '{"smtp": 1, "format": 1}'))

# Lista blanca de dominios de correo públicos para validación preliminar
EMAIL_DOMAINS_WHITELIST = _json.loads(os.getenv('EMAIL_DOMAINS_WHITELIST', '["gmail.com","hotmail.com","outlook.com","yahoo.com","icloud.com","live.com"]'))

# Modo offline: si True, solo usa validación MX local, no consulta API externa
EMAIL_VERIFICATION_OFFLINE_MODE = os.getenv('EMAIL_VERIFICATION_OFFLINE_MODE', 'true').lower() == 'true'
# ====================================================================================
# LOGGING
# ====================================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "correspondencia": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ====================================================================================
# TEMPLATES
# ====================================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "documentos" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "correspondencia.context_processors.urgencias_pendientes",
                "correspondencia.context_processors.correos_pendientes_sidebar",
                "correspondencia.context_processors.chatbot_global_context",
                "correspondencia.context_processors.monitoreo_chat_url",
                "correspondencia.context_processors.outbound_attachments_limits",
                "correspondencia.context_processors.blocked_recipients_context",
                "documentos.context_processors.prestamos_nuevos_sidebar",
            ],
        },
    },
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 110 * 1024 * 1024

# ====================================================================================
# OTRAS CONFIGURACIONES
# ====================================================================================
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # Ajusta según tu caso

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"



# ====================================================================================
# CACHE COMPARTIDO (Redis)
# ====================================================================================
# Crítico: sin un cache compartido entre procesos (Gunicorn, Celery worker y beat),
# los cooldowns de rate limit de Gmail API y los locks de recepción de correo quedaban
# en memoria por proceso (LocMemCache) y NO se respetaban entre procesos. Eso permitía
# que múltiples procesos siguieran golpeando Gmail API durante un 429 y reextendieran el
# bloqueo. Usamos el backend Redis nativo de Django (5.0) sobre la DB 1 (la DB 0 es el
# broker de Celery), sin dependencias extra.
DJANGO_CACHE_URL = os.getenv('DJANGO_CACHE_URL', 'redis://localhost:6379/1')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': DJANGO_CACHE_URL,
        'KEY_PREFIX': 'correspondencia',
    }
}

# ====================================================================================
# CONFIGURACIÓN DE CELERY
# ====================================================================================
# Dirección del broker (Redis en este caso)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
# Dirección del backend de resultados (también Redis)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
# Formato de contenido aceptado para las tareas
CELERY_ACCEPT_CONTENT = ['json']
# Serializador para las tareas
CELERY_TASK_SERIALIZER = 'json'
# Serializador para los resultados de las tareas
CELERY_RESULT_SERIALIZER = 'json'
# Zona horaria para la programación de tareas
CELERY_TIMEZONE = TIME_ZONE # Usar la misma que Django

# Configuración de Celery Beat (para tareas periódicas)
# Intervalo de revisión de correos (en segundos) - configurable por entorno
CELERY_EMAIL_CHECK_INTERVAL = int(os.getenv('CELERY_EMAIL_CHECK_INTERVAL', '300'))  # Default: 5 minutos
# Intervalo del watchdog IMAP (en segundos) - configurable por entorno.
# Se mantiene más conservador para evitar saturar la cuota/bandwidth de Gmail.
CELERY_IMAP_WATCHDOG_INTERVAL = int(os.getenv('CELERY_IMAP_WATCHDOG_INTERVAL', '900'))  # Default: 15 minutos
# Intervalo de aprobación automática de respuestas pendientes (segundos). Default: 60 (cada minuto).
CELERY_APROBAR_RESPUESTAS_INTERVAL = int(os.getenv('CELERY_APROBAR_RESPUESTAS_INTERVAL', '180'))
# Usuario usado como aprobador en aprobación automática (Celery). Opcional; si no se define se usa None.
# CELERY_APROBACION_USER = os.getenv('CELERY_APROBACION_USER', 'sistema_correspondencia')

CELERY_BEAT_SCHEDULE = {
    'procesar-emails-cada-5-minutos': {
        'task': 'correspondencia.tasks.procesar_emails_periodico', # Nombre completo de la tarea
        'schedule': float(CELERY_EMAIL_CHECK_INTERVAL),  # Intervalo configurable por entorno
        # 'args': (16, 16), # Argumentos posicionales para la tarea (si los necesita)
        # 'kwargs': {'param': 'valor'}, # Argumentos de palabra clave (si los necesita)
    },
    # Nueva tarea para rebotes
    'procesar-rebotes-cada-10-minutos': {
        'task': 'correspondencia.tasks.procesar_rebotes_periodico',
        'schedule': 600.0,
    },
    # Entregas Postmark sin webhook local (consulta API en background)
    'sincronizar-entregas-postmark-cada-15-minutos': {
        'task': 'correspondencia.tasks.sincronizar_entregas_postmark_periodico',
        'schedule': 900.0,
    },
    # Cache SLA (IDs entrantes respondidos) — evita consultas de 30-100s en HTTP
    'precalentar-cache-sla-cada-4-minutos': {
        'task': 'correspondencia.tasks.precalentar_cache_sla_periodico',
        'schedule': 240.0,
    },
    # Tareas para urgencias
    'actualizar-urgencias-cada-30-minutos': {
        'task': 'correspondencia.tasks.actualizar_urgencias_pendientes',
        'schedule': 1800.0,  # 30 minutos
    },
    'escalar-urgencias-criticas-cada-hora': {
        'task': 'correspondencia.tasks.escalar_urgencias_criticas',
        'schedule': 3600.0,  # 1 hora
    },
    # Aprobación automática de respuestas pendientes (cada minuto por defecto)
    'aprobar-respuestas-pendientes-cada-minuto': {
        'task': 'correspondencia.tasks.aprobar_y_enviar_respuestas_pendientes_periodico',
        'schedule': float(CELERY_APROBAR_RESPUESTAS_INTERVAL),
    },
    # Watchdog: vigila INBOX con un intervalo configurable para no saturar IMAP.
    'watchdog-inbox-cada-45-segundos': {
        'task': 'correspondencia.tasks.watchdog_inbox',
        'schedule': float(CELERY_IMAP_WATCHDOG_INTERVAL),
    },
}

# Opcional: Mejorar el manejo de resultados y estados
CELERY_RESULT_EXPIRES = timedelta(days=1) # Tiempo que se guardan los resultados
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True

# Reciclaje de workers: previene memory leaks acumulativos que causan bloqueo tras ~7 días
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200  # Reiniciar worker cada 200 tareas para liberar memoria
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 300_000  # 300MB límite por worker (en KB)

# Evitar prefetch agresivo que acumula tareas en memoria
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Cerrar conexiones DB al finalizar cada tarea para evitar conexiones stale
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}  # 1 hora
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Asegúrate de importar timedelta si usas crontab o result_expires
from datetime import timedelta
from celery.schedules import crontab

# Si en algún momento usas Azure Storage, activa y configura aquí:
# DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
# AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME")
# AZURE_ACCOUNT_KEY = os.getenv("AZURE_ACCOUNT_KEY")
# AZURE_CONTAINER = os.getenv("AZURE_CONTAINER")

# ====================================================================================
# CONFIGURACIÓN DE CORREO ELECTRÓNICO
# ====================================================================================
EMAIL_PROVIDER = os.getenv('EMAIL_PROVIDER', 'smtp').strip().lower()
EMAIL_INGESTION_PROVIDER = os.getenv('EMAIL_INGESTION_PROVIDER', 'imap').strip().lower()

OUTBOUND_EMAIL_ADDRESS = os.getenv('OUTBOUND_EMAIL_ADDRESS', '').strip()
if not OUTBOUND_EMAIL_ADDRESS:
    OUTBOUND_EMAIL_ADDRESS = os.getenv('EMAIL_HOST_USER', '').strip()
OUTBOUND_EMAIL_NAME = os.getenv('OUTBOUND_EMAIL_NAME', 'Correspondencia - Hospital E.S.E. Sarare').strip()
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    f'"{OUTBOUND_EMAIL_NAME}" <{OUTBOUND_EMAIL_ADDRESS}>'
).strip()

POSTMARK_SERVER_TOKEN = os.getenv('POSTMARK_SERVER_TOKEN', '').strip()
POSTMARK_MESSAGE_STREAM = os.getenv('POSTMARK_MESSAGE_STREAM', 'outbound').strip() or 'outbound'
POSTMARK_API_URL = os.getenv('POSTMARK_API_URL', 'https://api.postmarkapp.com/email').strip()
# Límite API Postmark: suma de adjuntos < 10 MB (ErrorCode 300). No configurable por Postmark.
POSTMARK_MAX_ATTACHMENTS_BYTES = 10 * 1024 * 1024
POSTMARK_ATTACHMENTS_MAX_BYTES = POSTMARK_MAX_ATTACHMENTS_BYTES  # alias legacy
# Límite de negocio para carga de adjuntos en salidas (UI). El envío por Postmark sigue en 10 MB.
CORRESPONDENCIA_MAX_OUTBOUND_ATTACHMENTS_BYTES = int(
    os.getenv('CORRESPONDENCIA_MAX_OUTBOUND_ATTACHMENTS_BYTES', str(25 * 1024 * 1024))
)
# Remitente(s) con Sender Signature verificada en Postmark (coma-separados).
POSTMARK_VERIFIED_SENDER = os.getenv(
    'POSTMARK_VERIFIED_SENDER',
    'correspondencia@esehospitaldelsarare.gov.co',
).strip()
POSTMARK_VERIFIED_SENDERS = _env_list('POSTMARK_VERIFIED_SENDERS') or (
    [POSTMARK_VERIFIED_SENDER] if POSTMARK_VERIFIED_SENDER else []
)
# Buzones institucionales que no deben usarse como destinatarios en salidas (UI + backend).
CORRESPONDENCIA_INSTITUTIONAL_INBOX_DEFAULTS = [
    'correspondencia@esehospitaldelsarare.gov.co',
    'correspondencia@hospitaldelsarare.gov.co',
]
CORRESPONDENCIA_BLOCKED_RECIPIENT_EMAILS = _env_list('CORRESPONDENCIA_BLOCKED_RECIPIENT_EMAILS')
POSTMARK_WEBHOOK_USER = os.getenv('POSTMARK_WEBHOOK_USER', '').strip()
POSTMARK_WEBHOOK_PASSWORD = os.getenv('POSTMARK_WEBHOOK_PASSWORD', '').strip()
# Basic Auth para webhook (formato usuario:contraseña). Vacío = sin auth (solo dev local).
POSTMARK_WEBHOOK_HTTP_AUTH = os.getenv('POSTMARK_WEBHOOK_HTTP_AUTH', '').strip()
POSTMARK_WEBHOOK_ENABLED = os.getenv('POSTMARK_WEBHOOK_ENABLED', 'true').lower() == 'true'
POSTMARK_BOUNCES_VIA_WEBHOOK = os.getenv('POSTMARK_BOUNCES_VIA_WEBHOOK', 'true').lower() == 'true'
GMAIL_API_CLIENT_ID = os.getenv('GMAIL_API_CLIENT_ID', '').strip()
GMAIL_API_CLIENT_SECRET = os.getenv('GMAIL_API_CLIENT_SECRET', '').strip()
GMAIL_API_REFRESH_TOKEN = os.getenv('GMAIL_API_REFRESH_TOKEN', '').strip()
GMAIL_API_TOKEN_URI = os.getenv('GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token').strip()
GMAIL_API_USER_ID = os.getenv('GMAIL_API_USER_ID', 'me').strip() or 'me'
GMAIL_API_REDIRECT_URI = os.getenv('GMAIL_API_REDIRECT_URI', 'http://localhost:8000/oauth2/callback').strip()
GMAIL_API_OAUTH_CLIENT_TYPE = os.getenv('GMAIL_API_OAUTH_CLIENT_TYPE', 'web').strip().lower() or 'web'
GMAIL_API_SCOPES = _json.loads(
    os.getenv(
        'GMAIL_API_SCOPES',
        '["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.modify"]',
    )
)
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '').strip()
GMAIL_API_PUBSUB_TOPIC = os.getenv('GMAIL_API_PUBSUB_TOPIC', '').strip()
GMAIL_API_PUBSUB_SUBSCRIPTION = os.getenv('GMAIL_API_PUBSUB_SUBSCRIPTION', '').strip()
# JSON de service account con rol Pub/Sub Subscriber (o ADC vía GOOGLE_APPLICATION_CREDENTIALS).
GMAIL_API_PUBSUB_CREDENTIALS_FILE = os.getenv(
    'GMAIL_API_PUBSUB_CREDENTIALS_FILE',
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''),
).strip()
GMAIL_API_WATCH_LABEL_IDS = _json.loads(os.getenv('GMAIL_API_WATCH_LABEL_IDS', '["INBOX"]'))
GMAIL_API_WATCH_LABEL_FILTER_ACTION = os.getenv('GMAIL_API_WATCH_LABEL_FILTER_ACTION', 'include').strip().lower() or 'include'
GMAIL_API_HISTORY_SYNC_MAX_RESULTS = int(os.getenv('GMAIL_API_HISTORY_SYNC_MAX_RESULTS', '200'))
# Cuántos messages.get se ejecutan por ciclo de history sync (evita 429 por ráfaga).
GMAIL_API_HISTORY_FETCH_BATCH_SIZE = int(os.getenv('GMAIL_API_HISTORY_FETCH_BATCH_SIZE', '12'))
# Pausa entre cada messages.get dentro de un lote (ms).
GMAIL_API_HISTORY_FETCH_DELAY_MS = int(os.getenv('GMAIL_API_HISTORY_FETCH_DELAY_MS', '120'))

if EMAIL_PROVIDER == 'gmail_api':
    EMAIL_BACKEND = 'correspondencia.email_backends.GmailAPIEmailBackend'
elif EMAIL_PROVIDER == 'postmark':
    EMAIL_BACKEND = 'correspondencia.email_backends.PostmarkEmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Solo notificaciones al funcionario en radicación rápida entrante (aparecen en Enviados de Gmail).
RADICACION_RAPIDA_ENTRANTE_EMAIL_BACKEND = os.getenv(
    'RADICACION_RAPIDA_ENTRANTE_EMAIL_BACKEND',
    'correspondencia.email_backends.GmailAPIEmailBackend',
).strip()

if os.getenv('E2E_CAPTURE_EMAIL', '').strip().lower() in {'1', 'true', 'yes', 'on'}:
    EMAIL_BACKEND = 'correspondencia.email_backends.E2ECaptureEmailBackend'

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '').strip()

# IMAP para recepción y rebotes mientras se termina la migración a webhooks.
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
IMAP_FOLDER_BOUNCES = os.getenv('IMAP_FOLDER_BOUNCES', 'bounces')
# Credenciales usadas por el botón manual "Procesar por IMAP". Separarlas de
# EMAIL_INGESTION_PROVIDER permite mantener Gmail API como tubería principal y
# ejecutar IMAP sólo bajo demanda.
IMAP_MANUAL_EMAIL_USER = os.getenv('IMAP_MANUAL_EMAIL_USER', EMAIL_HOST_USER).strip()
IMAP_MANUAL_EMAIL_PASSWORD = os.getenv('IMAP_MANUAL_EMAIL_PASSWORD', EMAIL_HOST_PASSWORD).strip()
IMAP_MANUAL_SERVER = os.getenv('IMAP_MANUAL_SERVER', IMAP_SERVER).strip()
IMAP_MANUAL_PORT = int(os.getenv('IMAP_MANUAL_PORT', str(IMAP_PORT)))

# Dominio para Message-ID salientes. Debe coincidir con el dominio del remitente.
# Sin esto, Python usa socket.getfqdn() que en este servidor devuelve el dominio Tailscale.
EMAIL_MESSAGE_ID_DOMAIN = os.getenv(
    'EMAIL_MESSAGE_ID_DOMAIN',
    OUTBOUND_EMAIL_ADDRESS.split('@', 1)[-1] if '@' in OUTBOUND_EMAIL_ADDRESS else 'gmail.com'
)

# Gmail API — tubería incremental (Ruta 1 dev/staging)
GMAIL_API_PUBSUB_PULL_MAX_MESSAGES = int(os.getenv('GMAIL_API_PUBSUB_PULL_MAX_MESSAGES', '10'))
GMAIL_API_WATCH_RENEW_HOURS_BEFORE = int(os.getenv('GMAIL_API_WATCH_RENEW_HOURS_BEFORE', '24'))
# Pub/Sub pull: 90 s por defecto — suficiente para tiempo real sin ráfagas sobre Gmail API.
CELERY_GMAIL_PUBSUB_PULL_INTERVAL = float(os.getenv('CELERY_GMAIL_PUBSUB_PULL_INTERVAL', '90'))
CELERY_GMAIL_WATCH_RENEW_INTERVAL = float(os.getenv('CELERY_GMAIL_WATCH_RENEW_INTERVAL', '21600'))  # 6 h
CELERY_DISABLE_WATCHDOG_WHEN_GMAIL_API = os.getenv('CELERY_DISABLE_WATCHDOG_WHEN_GMAIL_API', 'true').lower() == 'true'
# El poll de respaldo por Gmail API es redundante con Pub/Sub (que es el camino principal).
# Antes corría cada 5 min y duplicaba la presión sobre la cuota de Gmail por usuario, lo que
# contribuyó al 429 en cascada. Se espacia a 30 min como red de seguridad; configurable por entorno.
CELERY_GMAIL_BACKUP_POLL_INTERVAL = float(os.getenv('CELERY_GMAIL_BACKUP_POLL_INTERVAL', '1800'))  # 30 min

if EMAIL_INGESTION_PROVIDER == 'gmail_api':
    CELERY_BEAT_SCHEDULE['gmail-pubsub-pull'] = {
        'task': 'correspondencia.tasks.gmail_pubsub_pull_periodico',
        'schedule': CELERY_GMAIL_PUBSUB_PULL_INTERVAL,
    }
    CELERY_BEAT_SCHEDULE['gmail-watch-renew'] = {
        'task': 'correspondencia.tasks.gmail_watch_renew_periodico',
        'schedule': CELERY_GMAIL_WATCH_RENEW_INTERVAL,
    }
    if CELERY_DISABLE_WATCHDOG_WHEN_GMAIL_API:
        CELERY_BEAT_SCHEDULE.pop('watchdog-inbox-cada-45-segundos', None)
    CELERY_BEAT_SCHEDULE['procesar-emails-cada-5-minutos']['schedule'] = CELERY_GMAIL_BACKUP_POLL_INTERVAL

# ====================================================================================
# CONFIGURACIÓN PARA ENVÍO MASIVO BCC (Sprint 2)
# ====================================================================================
# Email opcional visible en el campo "To" para envíos BCC.
# Si queda vacío, no se enviará copia real a ningún destinatario adicional.
TO_DEFAULT = os.getenv('TO_DEFAULT', '').strip()
# Email para respuestas (Reply-To). Por defecto usa la cuenta remitente real.
REPLY_TO_DEFAULT = os.getenv('REPLY_TO_DEFAULT', DEFAULT_FROM_EMAIL).strip()


# ====================================================================================
# DJANGO REST FRAMEWORK CONFIGURATION
# ====================================================================================
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}
