# GUÍA DE SEGURIDAD CIBERNÉTICA
## Sistema de Gestión de Correspondencia Hospitalaria

**Fecha:** Enero 2026  
**Versión:** 1.0  
**Tipo de Documento:** Guía Técnica de Seguridad

---

## 📋 ÍNDICE

1. [Seguridad a Nivel de Infraestructura (Ubuntu Server)](#1-seguridad-a-nivel-de-infraestructura-ubuntu-server)
2. [Seguridad a Nivel de Aplicación y Scripts](#2-seguridad-a-nivel-de-aplicación-y-scripts)
3. [Monitoreo y Respuesta a Incidentes](#3-monitoreo-y-respuesta-a-incidentes)
4. [Checklist de Implementación](#4-checklist-de-implementación)

---

## 1. SEGURIDAD A NIVEL DE INFRAESTRUCTURA (UBUNTU SERVER)

### 1.1. Configuración Inicial del Sistema

#### 🔒 Actualización del Sistema
```bash
# Actualizar lista de paquetes
sudo apt update && sudo apt upgrade -y

# Instalar actualizaciones de seguridad automáticas
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 🔒 Configuración de Firewall (UFW)
```bash
# Instalar y habilitar UFW
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (IMPORTANTE: hacerlo antes de activar el firewall)
sudo ufw allow 22/tcp

# Permitir HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Activar firewall
sudo ufw enable
sudo ufw status verbose
```

#### 🔒 Configuración SSH Segura
```bash
# Editar configuración SSH
sudo nano /etc/ssh/sshd_config

# Configuraciones recomendadas:
# Port 2222  (cambiar puerto por defecto)
# PermitRootLogin no
# PasswordAuthentication no  (usar solo claves SSH)
# PubkeyAuthentication yes
# MaxAuthTries 3
# ClientAliveInterval 300
# ClientAliveCountMax 2
# Protocol 2

# Reiniciar servicio SSH
sudo systemctl restart sshd
```

#### 🔒 Crear Usuario con Privilegios Limitados
```bash
# Crear usuario para la aplicación
sudo adduser djangoapp
sudo usermod -aG sudo djangoapp

# Deshabilitar login root
sudo passwd -l root
```

### 1.2. Protección de Servicios

#### 🔒 Fail2Ban (Protección contra Ataques de Fuerza Bruta)
```bash
# Instalar Fail2Ban
sudo apt install fail2ban

# Crear configuración personalizada
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Editar configuración
sudo nano /etc/fail2ban/jail.local

# Configuraciones recomendadas:
# [sshd]
# enabled = true
# port = 22
# maxretry = 3
# bantime = 3600
# findtime = 600

# [nginx-http-auth]
# enabled = true

# Reiniciar Fail2Ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

#### 🔒 Configuración de Nginx (Reverse Proxy)
```nginx
# /etc/nginx/sites-available/correspondencia
server {
    listen 80;
    server_name tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com;

    # Certificado SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    # Configuraciones SSL seguras
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Headers de seguridad
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Limitar tamaño de upload
    client_max_body_size 20M;

    # Ocultar versión de Nginx
    server_tokens off;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Bloquear acceso a archivos sensibles
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

#### 🔒 Certificado SSL con Let's Encrypt
```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d tu-dominio.com

# Renovación automática (ya está configurado en cron)
sudo certbot renew --dry-run
```

### 1.3. Protección de Base de Datos

#### 🔒 PostgreSQL (si se usa)
```bash
# Editar configuración
sudo nano /etc/postgresql/14/main/postgresql.conf

# Configuraciones recomendadas:
# listen_addresses = 'localhost'
# ssl = on
# password_encryption = scram-sha-256

# Editar pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Solo permitir conexiones locales
# local   all             all                                     scram-sha-256
# host    all             all             127.0.0.1/32            scram-sha-256
```

#### 🔒 SQLite (si se usa)
```bash
# Asegurar permisos del archivo de base de datos
sudo chmod 600 /ruta/a/db.sqlite3
sudo chown djangoapp:djangoapp /ruta/a/db.sqlite3
```

### 1.4. Monitoreo del Sistema

#### 🔒 Instalar y Configurar Logwatch
```bash
# Instalar Logwatch
sudo apt install logwatch

# Configurar para enviar reportes diarios
sudo nano /etc/logwatch/conf/logwatch.conf

# Configurar email para reportes
MailTo = admin@tu-dominio.com
MailFrom = logwatch@tu-dominio.com
```

#### 🔒 Monitoreo de Espacio en Disco
```bash
# Agregar a crontab
sudo crontab -e

# Verificar espacio cada día a las 6 AM
0 6 * * * df -h | mail -s "Espacio en disco" admin@tu-dominio.com
```

### 1.5. Backup Automático

#### 🔒 Script de Backup
```bash
#!/bin/bash
# /usr/local/bin/backup_correspondencia.sh

BACKUP_DIR="/backups/correspondencia"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Crear directorio si no existe
mkdir -p $BACKUP_DIR

# Backup de base de datos
python3 /ruta/a/manage.py dumpdata > $BACKUP_DIR/db_$DATE.json

# Backup de archivos media
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /ruta/a/media/

# Eliminar backups antiguos
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete

# Enviar a almacenamiento externo (opcional)
# rsync -avz $BACKUP_DIR/ usuario@servidor-backup:/backups/
```

```bash
# Hacer ejecutable
sudo chmod +x /usr/local/bin/backup_correspondencia.sh

# Agregar a crontab (diario a las 2 AM)
sudo crontab -e
0 2 * * * /usr/local/bin/backup_correspondencia.sh
```

---

## 2. SEGURIDAD A NIVEL DE APLICACIÓN Y SCRIPTS

### 2.1. Variables de Entorno y Secretos

#### 🔴 PROBLEMA ACTUAL: Credenciales Hardcodeadas
```python
# ❌ INCORRECTO (procesar_emails.py línea 18-19)
EMAIL_ACCOUNT = 'ingdiegoter1998@gmail.com'
EMAIL_PASSWORD = 'vivecbtxfklhkbvv'
```

#### ✅ SOLUCIÓN: Usar Variables de Entorno
```python
# ✅ CORRECTO
import os
from django.conf import settings

EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT', settings.EMAIL_HOST_USER)
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', settings.EMAIL_HOST_PASSWORD)
```

#### 🔒 Archivo .env (NUNCA subir a Git)
```bash
# .env (agregar a .gitignore)
SECRET_KEY=tu-secret-key-super-segura-aqui
EMAIL_ACCOUNT=ingdiegoter1998@gmail.com
EMAIL_PASSWORD=vivecbtxfklhkbvv
DATABASE_URL=sqlite:///db.sqlite3
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
```

#### 🔒 .gitignore
```
.env
*.pyc
__pycache__/
db.sqlite3
media/
staticfiles/
venv/
.venv/
```

### 2.2. Configuración Django Segura

#### 🔒 settings.py - Configuraciones de Seguridad
```python
# ====================================================================================
# SEGURIDAD
# ====================================================================================
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Seguridad HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Protección XSS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Protección Clickjacking
X_FRAME_OPTIONS = "DENY"

# Protección CSRF
CSRF_TRUSTED_ORIGINS = [
    "https://tu-dominio.com",
    "https://www.tu-dominio.com",
]

# Headers de seguridad adicionales
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
```

### 2.3. Validación de Entrada

#### 🔒 Sanitización de Datos de Usuario
```python
# En views.py - Validar y sanitizar inputs
from django.utils.html import escape
from django.core.exceptions import ValidationError
import re

def validar_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Formato de email inválido")
    return email.lower().strip()

def sanitizar_texto(texto):
    """Escape de HTML para prevenir XSS"""
    return escape(texto)
```

#### 🔒 Validación de Archivos Subidos
```python
# Validar tipo y tamaño de archivos
ALLOWED_FILE_TYPES = ['.pdf', '.jpg', '.jpeg', '.png', '.docx']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validar_archivo(archivo):
    import os
    from django.core.exceptions import ValidationError
    
    # Validar extensión
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise ValidationError(f"Tipo de archivo no permitido: {ext}")
    
    # Validar tamaño
    if archivo.size > MAX_FILE_SIZE:
        raise ValidationError(f"Archivo excede tamaño máximo: {MAX_FILE_SIZE}")
    
    # Validar contenido (opcional: usar python-magic)
    return archivo
```

### 2.4. Protección contra Ataques Comunes

#### 🔒 SQL Injection (Django ORM ya lo previene, pero verificar)
```python
# ✅ CORRECTO - Usar ORM
correspondencia = Correspondencia.objects.filter(numero_radicado=numero)

# ❌ NUNCA hacer esto
# query = f"SELECT * FROM correspondencia WHERE numero = '{numero}'"
```

#### 🔒 Cross-Site Scripting (XSS)
```python
# En templates, siempre usar:
{{ variable|escape }}  # o
{% autoescape on %}
    {{ variable }}
{% endautoescape %}
```

#### 🔒 Cross-Site Request Forgery (CSRF)
```python
# Django ya incluye protección CSRF, pero verificar:
# 1. En formularios: {% csrf_token %}
# 2. En AJAX: incluir token en headers
# 3. En settings: CSRF_COOKIE_SECURE = True (en producción)
```

#### 🔒 Rate Limiting (Protección contra Ataques de Fuerza Bruta)
```python
# Instalar django-ratelimit
# pip install django-ratelimit

# En views.py
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    # Máximo 5 intentos por minuto por IP
    pass
```

### 2.5. Autenticación y Autorización

#### 🔒 Política de Contraseñas Fuerte
```python
# En settings.py
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Mínimo 12 caracteres
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

#### 🔒 Bloqueo de Cuentas (django-axes ya está configurado)
```python
# Verificar configuración en settings.py
AXES_FAILURE_LIMIT = 6
AXES_LOCK_OUT_AT_FAILURE = True
AXES_COOLOFF_TIME = timedelta(hours=0.2)
AXES_LOCKOUT_PARAMETERS = ['username']
```

#### 🔒 Autenticación de Dos Factores (2FA) - Recomendado
```bash
# Instalar django-otp
pip install django-otp django-otp[qr]
```

### 2.6. Logging y Auditoría

#### 🔒 Configuración de Logging Seguro
```python
# En settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/correspondencia.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/security.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'correspondencia': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 2.7. Protección de Correos Electrónicos

#### 🔒 Validación de Emails Antes de Enviar
```python
# Ya implementado en views.py, pero reforzar:
def validar_email_destino(email):
    """Validación robusta de email"""
    import dns.resolver
    import socket
    
    # 1. Validar formato
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "Formato inválido"
    
    # 2. Validar MX Record
    try:
        domain = email.split('@')[1]
        mx_records = dns.resolver.resolve(domain, 'MX')
        if not mx_records:
            return False, "Dominio sin servidor de correo"
    except:
        return False, "Error validando dominio"
    
    # 3. Verificar conexión SMTP (opcional, puede ser lento)
    # ...
    
    return True, "Email válido"
```

#### 🔒 Rate Limiting para Envío de Emails
```python
# Limitar envíos por usuario/IP
from django.core.cache import cache

def puede_enviar_email(usuario_id, max_emails=50):
    """Verifica si el usuario puede enviar más emails hoy"""
    key = f"email_count_{usuario_id}_{timezone.now().date()}"
    count = cache.get(key, 0)
    
    if count >= max_emails:
        return False, "Límite diario de emails alcanzado"
    
    cache.set(key, count + 1, timeout=86400)  # 24 horas
    return True, "OK"
```

### 2.8. Protección de Archivos Media

#### 🔒 Validación de Archivos Subidos
```python
# En models.py o forms.py
import magic  # pip install python-magic

def validar_tipo_archivo_real(archivo):
    """Valida el tipo real del archivo (no solo extensión)"""
    file_type = magic.from_buffer(archivo.read(1024), mime=True)
    archivo.seek(0)  # Resetear posición
    
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if file_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"Tipo de archivo no permitido: {file_type}")
    
    return archivo
```

---

## 3. MONITOREO Y RESPUESTA A INCIDENTES

### 3.1. Monitoreo Continuo

#### 🔒 Alertas de Seguridad
```python
# Script para monitorear intentos de acceso fallidos
# /usr/local/bin/monitor_security.sh

#!/bin/bash
LOG_FILE="/var/log/django/security.log"
ALERT_EMAIL="admin@tu-dominio.com"

# Buscar intentos de login fallidos
FAILED_LOGINS=$(grep "Failed login" $LOG_FILE | wc -l)

if [ $FAILED_LOGINS -gt 10 ]; then
    echo "ALERTA: $FAILED_LOGINS intentos de login fallidos" | \
    mail -s "Alerta de Seguridad" $ALERT_EMAIL
fi

# Buscar errores 500
ERRORS_500=$(grep "HTTP 500" $LOG_FILE | wc -l)

if [ $ERRORS_500 -gt 5 ]; then
    echo "ALERTA: $ERRORS_500 errores 500 detectados" | \
    mail -s "Alerta de Errores" $ALERT_EMAIL
fi
```

### 3.2. Respuesta a Incidentes

#### 🔒 Plan de Respuesta
1. **Identificación**: Detectar el incidente
2. **Contención**: Aislar sistemas afectados
3. **Eradicación**: Eliminar la amenaza
4. **Recuperación**: Restaurar servicios
5. **Lecciones aprendidas**: Documentar y mejorar

#### 🔒 Script de Respuesta Rápida
```bash
#!/bin/bash
# /usr/local/bin/incident_response.sh

# 1. Bloquear IP sospechosa
IP_SOSPECHOSA=$1
sudo ufw deny from $IP_SOSPECHOSA

# 2. Crear backup de emergencia
python3 /ruta/a/manage.py dumpdata > /backups/emergency_$(date +%Y%m%d_%H%M%S).json

# 3. Notificar administradores
echo "INCIDENTE DETECTADO: IP $IP_SOSPECHOSA bloqueada" | \
mail -s "ALERTA DE SEGURIDAD" admin@tu-dominio.com

# 4. Registrar en log
echo "$(date): IP $IP_SOSPECHOSA bloqueada por actividad sospechosa" >> /var/log/security_incidents.log
```

---

## 4. CHECKLIST DE IMPLEMENTACIÓN

### Infraestructura
- [ ] Sistema actualizado (`apt update && apt upgrade`)
- [ ] Firewall UFW configurado y activo
- [ ] SSH configurado con claves (sin contraseñas)
- [ ] Fail2Ban instalado y configurado
- [ ] Nginx configurado con SSL (Let's Encrypt)
- [ ] Headers de seguridad en Nginx
- [ ] Backup automático configurado
- [ ] Monitoreo de logs configurado

### Aplicación
- [ ] Credenciales movidas a variables de entorno (.env)
- [ ] .env agregado a .gitignore
- [ ] DEBUG = False en producción
- [ ] ALLOWED_HOSTS configurado correctamente
- [ ] Configuraciones de seguridad Django activadas
- [ ] Validación de archivos implementada
- [ ] Rate limiting configurado
- [ ] Logging de seguridad configurado
- [ ] Autenticación 2FA (opcional pero recomendado)

### Monitoreo
- [ ] Alertas de seguridad configuradas
- [ ] Plan de respuesta a incidentes documentado
- [ ] Scripts de respuesta rápida creados
- [ ] Contactos de emergencia definidos

---

## 📞 CONTACTO Y SOPORTE

**Equipo de Seguridad:**  
Email: seguridad@tu-dominio.com  
Teléfono: [Número de emergencia]

**Recursos Adicionales:**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Ubuntu Security](https://ubuntu.com/security)

---

**Última actualización:** Enero 2026  
**Próxima revisión:** Trimestral

