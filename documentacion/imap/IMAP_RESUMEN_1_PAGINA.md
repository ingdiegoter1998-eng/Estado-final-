# 📧 PROTOCOLO IMAP - RESUMEN EJECUTIVO
## Sistema de Correspondencia Hospitalaria

**Para responder preguntas rápidamente** | 21 de octubre de 2025

---

## 🎯 ¿QUÉ ES IMAP?

**IMAP** = **I**nternet **M**essage **A**ccess **P**rotocol  
**RFC 3501** - Protocolo para **leer** correos que están en un servidor remoto

**Propósito:** Acceder a emails **sin descargarlos** del servidor

---

## ⚡ CARACTERÍSTICAS PRINCIPALES

| ✅ IMAP | ❌ POP3 (el otro protocolo) |
|---------|----------------------------|
| Correos permanecen en servidor | Se eliminan del servidor |
| Acceso desde múltiples dispositivos | Solo un dispositivo |
| Sincronización bidireccional | Descarga unidireccional |
| Gestión de carpetas en servidor | Solo buzón local |
| Búsqueda en servidor | Búsqueda local |

**¿Por qué IMAP y no POP3?**  
✅ Múltiples usuarios pueden acceder al buzón institucional  
✅ No se pierden correos (quedan en Gmail como respaldo)  
✅ Auditoría completa (todos los correos históricos disponibles)

---

## 🔧 CÓMO FUNCIONA EN NUESTRO SISTEMA

### **Configuración:**
- **Servidor:** `imap.gmail.com`
- **Puerto:** `993` (SSL/TLS - **encriptado**)
- **Cuenta:** `hospitalsararecolombia@gmail.com`
- **Frecuencia:** Cada **5 minutos** (automático con Celery)

### **Proceso en 7 Pasos:**

```
1. CONECTAR   → imap.gmail.com:993 (SSL)
2. AUTENTICAR → Login con credenciales
3. SELECCIONAR→ Carpeta INBOX
4. BUSCAR     → Solo correos NO LEÍDOS (UNSEEN)
5. OBTENER    → Descargar headers, cuerpo, adjuntos
6. GUARDAR    → En BD (CorreoEntrante + Adjuntos)
7. MARCAR     → Como leído (SOLO si guardó bien)
```

### **Código Principal:**

```python
# 1. Conectar
mailbox = MailBox('imap.gmail.com')
mailbox.login(EMAIL, PASSWORD, initial_folder='INBOX')

# 2. Buscar no leídos
messages = mailbox.fetch(AND(seen=False), mark_seen=False)

# 3. Procesar cada uno
for msg in messages:
    # Validar Message-ID único
    if not CorreoEntrante.objects.filter(message_id=msg.message_id).exists():
        # Guardar en BD
        correo = CorreoEntrante.objects.create(
            message_id=msg.message_id,
            remitente=msg.from_,
            asunto=msg.subject,
            cuerpo_texto=msg.text,
        )
        # Guardar adjuntos
        for att in msg.attachments:
            adjunto.archivo.save(att.filename, att.payload)
        
        # ✅ MARCAR COMO LEÍDO (solo si TODO fue exitoso)
        mailbox.flag(msg.uid, MailMessageFlags.SEEN, True)

# 4. Cerrar conexión
mailbox.logout()
```

---

## 🛡️ SEGURIDAD Y NORMATIVA

| Aspecto | Implementación | Normativa |
|---------|---------------|-----------|
| **Encriptación** | SSL/TLS Puerto 993 | Ley 1581/2012 Art. 4 |
| **Contraseña** | Contraseña de aplicación Gmail | Buenas prácticas Google |
| **No duplicados** | Validación Message-ID único | Integridad de datos |
| **Trazabilidad** | Logs de cada ejecución | Ley 1712/2014 Art. 16 |
| **Respaldo** | Correos permanecen en Gmail | Ley 594/2000 Art. 46 |

---

## ❓ PREGUNTAS FRECUENTES - RESPUESTAS RÁPIDAS

### **¿Por qué cada 5 minutos y no en tiempo real?**
**R:** Balance eficiencia/recursos. Gmail permite IMAP IDLE para tiempo real, pero genera mucha carga. 5 minutos es suficiente para correspondencia administrativa.

### **¿Qué pasa si hay error al conectar?**
**R:** Se registra el error, NO se marcan correos como leídos, se reintenta automáticamente en 5 minutos.

### **¿Cómo evitamos duplicados?**
**R:** Cada email tiene `Message-ID` único. Antes de guardar, validamos si ya existe en BD. Si existe, solo marcamos como leído.

### **¿Por qué `mark_seen=False`?**
**R:** NO marcar como leído al buscar. Solo marcamos DESPUÉS de guardar exitosamente en BD. Si falla el guardado, el correo queda "no leído" para reprocesarlo.

### **¿Qué es la contraseña de aplicación?**
**R:** Gmail requiere contraseña específica (no la normal) para apps que usan IMAP. Se genera en https://myaccount.google.com/apppasswords

### **¿Se pueden perder correos?**
**R:** NO. Permanecen en Gmail hasta que se marquen como leídos. Si falla algo, quedan "no leídos" para siguiente ciclo.

---

## 📊 IMAP vs SMTP (Diferencia Importante)

| IMAP | SMTP |
|------|------|
| **LEER** correos del servidor | **ENVIAR** correos al servidor |
| Puerto 993 (SSL) | Puerto 587 (TLS) |
| `imap.gmail.com` | `smtp.gmail.com` |
| Para **recibir** correspondencia | Para **responder** correspondencia |

**Analogía:**  
- IMAP = Ir al buzón a **recoger** cartas  
- SMTP = Ir al correo a **enviar** cartas

---

## 🔑 PUNTOS CLAVE PARA PRESENTACIÓN

1. ✅ **IMAP es para LEER**, SMTP es para ENVIAR
2. ✅ **Puerto 993 SSL** = Conexión encriptada (segura)
3. ✅ **Cada 5 minutos** automático con Celery Beat
4. ✅ **Message-ID único** previene duplicados
5. ✅ **Marcar leído SOLO después de guardar** = No se pierden correos
6. ✅ **Correos permanecen en Gmail** = Respaldo y auditoría
7. ✅ **Sincronización bidireccional** = Múltiples dispositivos

---

## 📁 ARCHIVOS RELACIONADOS

- **Código principal:** `correspondencia/management/commands/procesar_emails.py`
- **Tarea automática:** `correspondencia/tasks.py`
- **Configuración:** `hospital_document_management/settings.py` línea 311-313
- **Guía completa:** `GUIA_PROTOCOLO_IMAP_SISTEMA.md` (40 páginas con todos los detalles)

---

**Preparado por:** Equipo Técnico | **Fecha:** 21/10/2025 | **Versión:** 1.0

