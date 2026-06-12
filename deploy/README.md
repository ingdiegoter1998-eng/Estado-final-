# Manual de Despliegue: Correspondencia Django

## Estructura de despliegue

```
deploy/
├── nginx/
│   └── correspondencia.conf              # Config del proxy Nginx
├── systemd/
│   ├── correspondencia.service           # Servicio systemd para Gunicorn
│   ├── correspondencia-nextjs.service         # Servicio Next.js (Calendario)
│   ├── correspondencia-celery-worker.service  # Celery worker (correos, respuestas)
│   └── correspondencia-celery-beat.service    # Celery beat (tareas programadas)
├── logrotate/
│   └── correspondencia                   # Rotación de logs
├── scripts/
│   └── apply.sh                          # Script de instalación/despliegue
└── README.md                             # Este archivo
```

## Instalación rápida

1. **Activar virtualenv:**
   ```bash
   source /home/devdiego/Correspondencia-diciembre-1.0/venv/bin/activate
   ```

2. **Instalar Gunicorn y collectstatic:**
   ```bash
   pip install gunicorn
   python manage.py collectstatic --noinput
   ```

3. **Ejecutar script de despliegue:**
   ```bash
   chmod +x /home/devdiego/Correspondencia-diciembre-1.0/deploy/scripts/apply.sh
   /home/devdiego/Correspondencia-diciembre-1.0/deploy/scripts/apply.sh
   ```

   El script automáticamente:
   - Instala Nginx (si falta).
   - Crea directorios de logs.
   - Habilita y arranca `correspondencia.service`.
   - Configura el sitio en Nginx.
   - Aplica logrotate.
   - Valida sintaxis Nginx.

4. **Verificar estado:**
   ```bash
   sudo systemctl status correspondencia
   sudo systemctl status nginx
   curl -I http://192.168.3.230/
   ```

## Acceso a la aplicación

### Intranet (LAN hospital)
- URL: `http://192.168.3.230/`
- Restricción: Solo equipos con IP `192.168.0.0/16` pueden acceder.

### Ngrok (acceso remoto)
- Si tienes un túnel ngrok activo, la URL es proporcionada por ngrok (ej: `https://xxx-yyy-zzz.ngrok.io`).
- Asegúrate de:
  1. Iniciar ngrok: `ngrok http 192.168.3.230:80`
  2. Copiar la URL https proporcionada (ej: `https://abc123.ngrok.io`).
  3. La aplicación ya está configurada para permitir ngrok en `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `CORS_ALLOWED_ORIGINS`.

## Logs y monitoreo

### Ver logs de Gunicorn
```bash
sudo journalctl -u correspondencia -f          # Logs del servicio
sudo tail -f /var/log/correspondencia/gunicorn.access.log   # Acceso
sudo tail -f /var/log/correspondencia/gunicorn.error.log    # Errores
```

### Ver logs de Nginx
```bash
sudo tail -f /var/log/nginx/correspondencia.error.log
sudo tail -f /var/log/nginx/correspondencia.access.log
```

### Rotación de logs
Configurada en `/etc/logrotate.d/correspondencia`:
- Rota diariamente.
- Mantiene 14 días de histórico.
- Comprimidos automáticamente.

Prueba manual:
```bash
sudo logrotate -d /etc/logrotate.d/correspondencia
```

## Operación diaria

### Después de cambios en el código
```bash
cd /home/devdiego/Correspondencia-diciembre-1.0
source venv/bin/activate
git pull origin main  # o tu rama correspondiente
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart correspondencia
sudo systemctl restart correspondencia-celery-worker correspondencia-celery-beat  # Si usas Celery
```

### Después de cambios en Nginx
```bash
sudo nginx -t          # Validar sintaxis
sudo systemctl reload nginx
```

### Monitorear Gunicorn
```bash
sudo systemctl status correspondencia
ps aux | grep gunicorn
```

### Reiniciar servicios
```bash
sudo systemctl restart correspondencia          # Gunicorn
sudo systemctl restart correspondencia-nextjs    # Next.js (Calendario)
sudo systemctl restart nginx                     # Nginx
sudo systemctl restart correspondencia correspondencia-nextjs nginx  # Todos
```

### Dimensionamiento Gunicorn (VM producción)

| Recurso VM actual | Valor típico | Notas |
|-------------------|--------------|-------|
| vCPU | 4 | Comprobar con `nproc` |
| RAM | ~8 GiB | Comprobar con `free -h` |
| Slots Gunicorn | workers × threads | Cuello de botella bajo estrés concurrente |

**Config recomendada (4 vCPU, ~6 GiB RAM libre):**

```ini
--worker-class gthread --workers 6 --threads 3
```

→ **18 peticiones HTTP concurrentes** (antes: 4×3 = 12).

| Si aumenta vCPU en el hipervisor | workers sugeridos | threads | slots |
|----------------------------------|-------------------|---------|-------|
| 4 (actual) | 6 | 3 | 18 |
| 6 | 8 | 3 | 24 |
| 8 | 10 | 3 | 30 |

- **RAM:** ~150–250 MiB por worker; 6 workers ≈ 1,2 GiB (cabe en la VM actual).
- **SQL Server:** `CONN_MAX_AGE=600` → hasta ~1 conexión persistente por hilo activo; vigilar el pool del servidor si se suben mucho workers+threads.
- **Nginx:** `proxy_read_timeout 60s` (sin cambio); Gunicorn `--timeout 90` da margen al worker.

**Aplicar cambio de workers en la VM:**

```bash
sudo cp /home/devdiego/Correspondencia-diciembre-1.0/deploy/systemd/correspondencia.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart correspondencia
sudo systemctl status correspondencia
ps aux | grep gunicorn   # debe mostrar 6 workers + 1 master
```

> **CPUs en la VM:** sí se pueden aumentar desde el panel del hipervisor (VMware/Hyper-V/etc.) si el host físico tiene capacidad. Tras el cambio, reiniciar la VM y recalcular workers con la tabla anterior (`nproc`).

> Nota: `correspondencia-nextjs` solo reinicia el servicio. Si hubo cambios en el código del calendario, primero hay que recompilar dentro de `calendario-informes-nextjs`.

## Next.js (Calendario de Planillas)

El calendario de planillas corre como app Next.js en puerto 3000. Nginx lo proxyea bajo `/calendario`.

### 1. Instalar servicio

```bash
sudo cp /home/devdiego/Correspondencia-diciembre-1.0/deploy/systemd/correspondencia-nextjs.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable correspondencia-nextjs
sudo systemctl start correspondencia-nextjs
```

### 2. Verificar

```bash
sudo systemctl status correspondencia-nextjs
curl -I http://localhost:3000/calendario/login
```

### 3. Rebuild tras cambios en código Next.js

```bash
cd /home/devdiego/Correspondencia-diciembre-1.0/calendario-informes-nextjs
npm run build
sudo systemctl restart correspondencia-nextjs
```

Si se ejecuta `npm run build` desde `/home/devdiego/Correspondencia-diciembre-1.0`, fallará porque ese `package.json` no tiene script `build`.

### 4. Logs

```bash
sudo journalctl -u correspondencia-nextjs -f
```

## Celery y Redis (correos entrantes y respuestas automáticas)

Celery procesa correos entrantes (IMAP), rebotes, urgencias y aprobaciones automáticas de respuestas. Requiere **Redis** como broker.

### 1. Instalar Redis (sin Docker)

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 2. Activar servicios Celery

```bash
# Copiar los archivos de servicio
sudo cp /home/devdiego/Correspondencia-diciembre-1.0/deploy/systemd/correspondencia-celery-worker.service /etc/systemd/system/
sudo cp /home/devdiego/Correspondencia-diciembre-1.0/deploy/systemd/correspondencia-celery-beat.service /etc/systemd/system/

# Recargar systemd e iniciar
sudo systemctl daemon-reload
sudo systemctl enable correspondencia-celery-worker correspondencia-celery-beat
sudo systemctl start correspondencia-celery-worker correspondencia-celery-beat
```

### 3. Verificar

```bash
sudo systemctl status correspondencia-celery-worker
sudo systemctl status correspondencia-celery-beat
sudo systemctl status redis-server
```

### 4. Logs de Celery

```bash
sudo journalctl -u correspondencia-celery-worker -f
sudo journalctl -u correspondencia-celery-beat -f
```

### 5. Reiniciar Celery (tras cambios en código)

```bash
sudo systemctl restart correspondencia-celery-worker correspondencia-celery-beat
```

Con esto, Celery worker y beat arrancan automáticamente al encender la máquina y se reinician si fallan. Si tu Redis tiene otro nombre de servicio (ej. `redis.service`), edita los `.service` y cambia `redis-server.service` por el correcto.

## Configuración de seguridad

### Restricción a intranet (Nginx)
- El sitio solo escucha en `192.168.3.230:80`.
- Regla: `allow 192.168.0.0/16; deny all;`.
- Para extender a otras subredes, editar `/etc/nginx/sites-available/correspondencia`.

### DEBUG y ALLOWED_HOSTS (Django)
- `DEBUG` debe estar en `False` en producción (revisar `hospital_document_management/settings.py`).
- `ALLOWED_HOSTS` incluye:
  - `192.168.3.230` (intranet)
  - `localhost` (local)
  - `*.ngrok.io`, `*.ngrok-free.app`, `*.ngrok-free.dev` (ngrok remoto)

## Tamaño máximo de subida
- Configurado en Nginx: `client_max_body_size 20M`.
- Para cambiar, editar `/etc/nginx/sites-available/correspondencia` y recargar.

## Troubleshooting

### "502 Bad Gateway"
- Gunicorn podría estar caído.
  ```bash
  sudo systemctl status correspondencia
  sudo journalctl -u correspondencia -n 50
  ```
- O el socket Unix podría tener permisos incorrectos.
  ```bash
  ls -la /run/correspondencia/gunicorn.sock
  ```

### "Connection refused" desde intranet
- Verifica que la IP está en rango `192.168.0.0/16` (Nginx lo bloquea si no).
- Comprueba que `correspondencia.service` está activo.

### "ALLOWED_HOSTS" error
- Si se accede con una URL no autorizada, Django rechazará la solicitud.
- Añadir la URL a `ALLOWED_HOSTS` en `settings.py` y recargar.

## Performance (workers y threads)

Configuración actual en `correspondencia.service`:
```
--workers 4 --threads 4
```

Para ~100 usuarios concurrentes:
- **CPUs < 4:** Reducir a `--workers 2 --threads 8` o similar.
- **CPUs = 4:** Mantener `--workers 4 --threads 4`.
- **CPUs > 4:** Aumentar a `--workers 6 --threads 6` o `--workers N+1` (donde N = CPUs).

Para ajustar, editar `/etc/systemd/system/correspondencia.service` y recargar:
```bash
sudo nano /etc/systemd/system/correspondencia.service
# Editar línea ExecStart con nuevos --workers y --threads
sudo systemctl daemon-reload
sudo systemctl restart correspondencia
```

## Ngrok (acceso remoto)

### Iniciar ngrok
```bash
ngrok http 192.168.3.230:80
```

### Copiar URL
ngrok mostrará algo como:
```
Forwarding  https://abc123.ngrok.io -> http://192.168.3.230:80
```

### Nota
- El certificado HTTPS de ngrok es válido automáticamente.
- La aplicación ya está configurada para ngrok (ver `ALLOWED_HOSTS` en `settings.py`).

## Cierre/Mantenimiento

### Detener servicios
```bash
sudo systemctl stop correspondencia correspondencia-nextjs nginx
sudo systemctl stop correspondencia-celery-worker correspondencia-celery-beat  # Opcional
```

### Habilitar/Deshabilitar arranque automático
```bash
sudo systemctl disable correspondencia correspondencia-nextjs nginx  # Desactivar
sudo systemctl enable correspondencia correspondencia-nextjs nginx   # Activar
# Celery:
sudo systemctl disable correspondencia-celery-worker correspondencia-celery-beat  # Desactivar
sudo systemctl enable correspondencia-celery-worker correspondencia-celery-beat   # Activar
```

---

**Última actualización:** 18 de febrero de 2026
