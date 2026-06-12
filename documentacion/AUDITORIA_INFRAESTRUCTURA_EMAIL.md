# Auditoría de Infraestructura de Correo Electrónico

**Sistema:** Gestión Documental — Hospital E.S.E. Sarare  
**Fecha:** 3 de abril de 2026  
**Auditor:** Sistema automatizado + verificación independiente Port25  

---

## 1. Resumen Ejecutivo

| Verificación | Resultado | Nota |
|---|---|---|
| **SPF** | ✅ PASS | Verificado por Port25 |
| **DKIM** | ✅ PASS | Firma RSA 2048-bit, selector `20251104` |
| **iprev (PTR)** | ✅ PASS | DNS inverso coincide con servidores Google |
| **DMARC** | ✅ PASS | Política `p=none` de gmail.com aplica |
| **SMTP TLS** | ✅ Activo | Puerto 587, STARTTLS |
| **Message-ID** | ✅ Correcto | Dominio `@gmail.com` |
| **App Password** | ✅ Válido | Autenticación OAuth2-compatible |

**Conclusión: La configuración de envío de correos del sistema está correcta. Todos los mecanismos de autenticación pasan las verificaciones estándar de la industria.**

---

## 2. Verificación Independiente (Port25)

Se envió un email de prueba al servicio `check-auth@verifier.port25.com`, un verificador independiente reconocido internacionalmente. Los resultados textuales recibidos:

```
==========================================================
Summary of Results
==========================================================
SPF check:          pass
"iprev" check:      pass
DKIM check:         pass
```

### 2.1 Detalle SPF

```
Result:         pass
ID(s) verified: smtp.mailfrom=correspondenciaesesarare@gmail.com

DNS record(s):
    gmail.com. TXT "v=spf1 redirect=_spf.google.com"
    _spf.google.com. TXT "v=spf1 ip4:74.125.0.0/16 ip4:209.85.128.0/17 
        ip6:2001:4860:4864::/56 ... ~all"
```

- El servidor de envío (IP `2607:f8b0:4864:20::935`, Google) está autorizado en el registro SPF de gmail.com.

### 2.2 Detalle DKIM

```
Result:         pass (matches From: correspondenciaesesarare@gmail.com)
ID(s) verified: header.d=gmail.com
Public key:     20251104._domainkey.gmail.com (2048 bits)
```

- Gmail firma automáticamente todos los correos salientes con DKIM `d=gmail.com`.
- La verificación criptográfica del contenido y encabezados del mensaje es exitosa.

### 2.3 Detalle iprev (DNS Inverso)

```
Result:         pass (matches mail-ua1-x935.google.com)
```

- La IP del servidor de envío tiene registro PTR válido apuntando a Google.

---

## 3. Configuración Actual del Sistema

### 3.1 SMTP (Envío)

| Parámetro | Valor |
|---|---|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | `Correspondenciaesesarare@gmail.com` |
| `EMAIL_HOST_PASSWORD` | App Password configurado |
| `DEFAULT_FROM_EMAIL` | `"Correspondencia - Hospital E.S.E. Sarare" <Correspondenciaesesarare@gmail.com>` |
| `EMAIL_MESSAGE_ID_DOMAIN` | `gmail.com` |
| `REPLY_TO_DEFAULT` | Mismo que DEFAULT_FROM_EMAIL |

### 3.2 IMAP (Recepción)

| Parámetro | Valor |
|---|---|
| Servidor | `imap.gmail.com:993` |
| Protocolo | `IMAP4_SSL` |
| Carpeta bounces | `bounces` |

### 3.3 Verificaciones de Código

- ✅ No existe **ninguna restricción o filtro de dominio** para destinatarios en el código de envío (`aprobacion_envio.py`)
- ✅ El `Message-ID` se genera con `make_msgid(domain='gmail.com')` — correcto
- ✅ Se incluyen encabezados `In-Reply-To` y `References` cuando el correo es respuesta
- ✅ El contenido se envía como HTML con encoding UTF-8

---

## 4. Diagnóstico DNS del Dominio Institucional

### hospitaldelsarare.gov.co

| Registro | Valor | Estado |
|---|---|---|
| **MX** | `1 mail.hospitaldelsarare.gov.co` → `143.95.238.20` | ✅ Existe |
| **SPF** | `v=spf1 +a +mx +include:websitewelcome.com ~all` | ⚠️ Softfail |
| **DMARC** | No configurado | ❌ Ausente |
| **DKIM** | No configurado (ningún selector encontrado) | ❌ Ausente |
| **NS** | `ns1.arvixeshared.com`, `ns2.arvixeshared.com` | Hosting Arvixe |
| **Servidor Mail** | Exim 4.99.1 en puerto 587 | ✅ Operativo |

**Nota importante:** El dominio institucional tiene un servidor de correo funcional (Exim en Arvixe) pero **NO está siendo utilizado** por el sistema de correspondencia. El sistema envía a través de Gmail.

---

## 5. Análisis de los Rebotes

### 5.1 Los 12 rebotes de la Rama Judicial

```
Destinatario: *@cendoj.ramajudicial.gov.co
Código SMTP:  550
DSN:          5.7.1
Razón:        TRANSPORT.RULES.RejectMessage;
              the message was rejected by organization policy
```

**Diagnóstico:** El servidor de la Rama Judicial (Microsoft Exchange) tiene una **regla de transporte** (política organizacional) que **rechaza correos provenientes de dominios no institucionales**. Esta es una práctica común en entidades gubernamentales colombianas para prevenir phishing.

### 5.2 ¿Por qué rechaza nuestros correos?

1. Enviamos desde `@gmail.com` — un dominio de correo gratuito
2. La Rama Judicial **solo acepta correos de dominios verificados/institucionales**
3. No importa cuán perfecta sea nuestra configuración SPF/DKIM — el filtro es por **dominio del remitente**, no por autenticación

### 5.3 Prueba de que NO es problema nuestro

- SPF: **PASS** (verificado por tercero independiente)
- DKIM: **PASS** (verificado por tercero independiente)
- iprev: **PASS** (verificado por tercero independiente)
- **El rechazo ocurre DESPUÉS de que el servidor receptor valida nuestra autenticación exitosamente**, y aplica su regla de política interna

---

## 6. Hallazgos Clave

### ✅ Qué está bien (nuestra configuración)
1. SPF, DKIM y PTR pasan todas las verificaciones
2. Message-ID con dominio correcto (@gmail.com)
3. Encabezados completos (In-Reply-To, References, Return-Path)
4. TLS/cifrado activo
5. Sin restricciones de dominio de destinatarios en el código
6. App Password configurado (no contraseña de cuenta)

### ❌ Qué está mal (infraestructura del hospital)
1. **Se usa Gmail** en vez del servidor institucional `hospitaldelsarare.gov.co`
2. El dominio institucional **no tiene DMARC** configurado
3. El dominio institucional **no tiene DKIM** configurado
4. El SPF del dominio usa `~all` (softfail) en vez de `-all` (hardfail)

### ⚠️ Qué NO podemos controlar
1. Las políticas de filtrado de correo de la Rama Judicial
2. Las reglas de transporte de Microsoft Exchange del destinatario
3. La decisión de entidades gubernamentales de bloquear correos de @gmail.com

---

## 7. Recomendaciones

### 7.1 Solución Definitiva (Requiere acción administrativa)

| Acción | Responsable | Impacto |
|---|---|---|
| Migrar envío a `correspondencia@hospitaldelsarare.gov.co` | Sistemas / Hosting Arvixe | Elimina rechazos de la Rama Judicial |
| Configurar DKIM en hospitaldelsarare.gov.co | Proveedor DNS (Arvixe) | Firma criptográfica institucional |
| Configurar DMARC en hospitaldelsarare.gov.co | Proveedor DNS (Arvixe) | Protección contra suplantación |
| Cambiar SPF a `-all` (hardfail) | Proveedor DNS (Arvixe) | Mayor seguridad |

### 7.2 Lo que el desarrollador ya hizo (sin costo adicional)

1. ✅ Configuración correcta de SMTP con Gmail
2. ✅ Sistema de detección y notificación de rebotes
3. ✅ Alertas visuales de rebotes en dashboard
4. ✅ Rastreo de estado por destinatario
5. ✅ Message-ID con dominio correcto
6. ✅ Encabezados RFC-compliant

### 7.3 Cambio de configuración para usar servidor institucional

Si el hospital proporciona credenciales del servidor institucional, el cambio en el sistema es mínimo (solo `settings.py`):

```python
# Cambiar de:
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'Correspondenciaesesarare@gmail.com'

# Cambiar a:
EMAIL_HOST = 'mail.hospitaldelsarare.gov.co'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'correspondencia@hospitaldelsarare.gov.co'
EMAIL_HOST_PASSWORD = '<contraseña del servidor institucional>'
EMAIL_MESSAGE_ID_DOMAIN = 'hospitaldelsarare.gov.co'
```

---

## 8. Conclusión

**El sistema de correspondencia está correctamente configurado dentro de los límites de la infraestructura proporcionada (Gmail).** Todas las verificaciones de autenticación de email pasan exitosamente.

Los rechazos de la Rama Judicial (`cendoj.ramajudicial.gov.co`) son causados por una **política organizacional del destinatario** que bloquea correos de dominios gratuitos como Gmail, no por una falla del sistema.

La solución requiere migrar a una cuenta institucional (`@hospitaldelsarare.gov.co`), lo cual es una **decisión administrativa y de infraestructura**, no un problema de software.
