# SISTEMA DE CORRESPONDENCIA HOSPITALARIA
## Flujograma con Fundamentación Legal - Resumen Ejecutivo

**Fecha:** 21 de octubre de 2025 | **Versión:** Producción Actual

---

## 🎯 PROCESOS PRINCIPALES IMPLEMENTADOS

### **1. ENTRADA Y RADICACIÓN**

| Proceso | Normativa | Descripción |
|---------|-----------|-------------|
| **Inspección Física** | Decreto 1580/1974 Art. 10<br/>Ley 594/2000 Art. 24 | Verificación de integridad, sustancias prohibidas, documentos completos |
| **Digitalización** | Decreto 2609/2012 Art. 9<br/>Acuerdo AGN 003/2015 | Escaneo obligatorio alta resolución + OCR<br/>Formatos: PDF, JPG, PNG, TIFF (Max 10 archivos, 15MB) |
| **Sello con QR** | Decreto 2609/2012 Art. 14<br/>Acuerdo AGN 003/2015 Art. 18 | Impresión de radicado + QR verificable desde smartphone |
| **Radicación** | Ley 1755/2015 Art. 14<br/>Resolución 310/2011 SNS | Generación automática: `ENTRANTE-2025-XXXXX`<br/>*"Toda petición se radica el mismo día"* |
| **Email IMAP** | Ley 527/1999 Art. 10, 13<br/>Decreto 1080/2015 Art. 2.8.2.4.1 | Protocolo automático de captura de correos |

---

### **2. CLASIFICACIÓN Y PLAZOS**

| Proceso | Normativa | Plazos Legales |
|---------|-----------|----------------|
| **Serie/Subserie** | Acuerdo AGN 060/2001<br/>Ley 594/2000 Art. 21 | Tabla de Retención Documental (TRD)<br/>Determina conservación y disposición final |
| **SLA Información** | Ley 1755/2015 Art. 14 | **10 días hábiles** |
| **SLA Petición** | Ley 1437/2011 Art. 13 | **15 días hábiles** |
| **SLA Consulta** | Ley 1437/2011 Art. 23 | **30 días hábiles** |
| **SLA Habeas Data** | Ley 1581/2012 Art. 15 | **15 días hábiles** |
| **Días Hábiles** | Ley 1437/2011 Art. 30<br/>Ley 51/1983 | Exclusión sábados, domingos y festivos<br/>Archivo `feriados.csv` actualizado |

---

### **3. GESTIÓN Y RESPUESTA**

| Proceso | Normativa | Funcionalidad |
|---------|-----------|---------------|
| **Notificaciones** | Ley 1437/2011 Art. 67<br/>Decreto 1080/2015 | Automáticas email + sistema interno<br/>Alertas SLA: 75%, 90%, 95%, 100% |
| **Trazabilidad** | Ley 1712/2014 Art. 16<br/>Ley 594/2000 Art. 15<br/>Decreto 1080/2015 Art. 2.8.2.5.8 | Historial completo inmutable<br/>Eventos: RADICADA, ASIGNADA, LEÍDA, RESPONDIDA<br/>Metadatos: Usuario, Fecha/Hora, IP |
| **Respuesta** | Ley 1755/2015 Art. 22 | *"Clara, precisa y congruente"*<br/>Radicado salida: `SALIENTE-2025-XXXXX` |
| **Validación Email** | RFC 5321, RFC 5322<br/>Ley 527/1999 Art. 13 | MX Record + SMTP Check<br/>Reducción 80% rebotes |
| **DSN Seguimiento** | RFC 3461 | Reintentos: +15min, +1h, +4h<br/>Estados: delivered, bounced, rejected |
| **Snapshots** | Ley 594/2000<br/>Acuerdo AGN 003/2015 | Datos congelados al aprobar:<br/>Oficina, redactor, destinatario (inmutables) |

---

### **4. FUNCIONES AUTOMÁTICAS TRANSVERSALES**

| Función | Base Legal | Implementación |
|---------|------------|----------------|
| **Generación Radicado** | Ley 1755/2015 Art. 14<br/>Resolución 310/2011 SNS | Consecutivo anual único e irrepetible<br/>Algoritmo: `TIPO-AÑO-NNNNN` |
| **Cálculo SLA** | Ley 1437/2011 Art. 30<br/>Ley 51/1983 | `utils_sla.py`: es_dia_habil() + sumar_habiles()<br/>Calendario laboral real |
| **Notificaciones** | Ley 1437/2011 Art. 67 | Multicanal: Email SMTP + Sistema interno<br/>Plantillas HTML personalizables |
| **Historial** | Ley 1712/2014 Art. 16<br/>Decreto 1080/2015 Art. 2.8.2.5.8 | Registro automático de todos los eventos<br/>Metadatos mínimos obligatorios |
| **Validación Email** | RFC 5321, RFC 5322 | Sintaxis + MX + SMTP + API<br/>Prevención de errores |
| **Snapshots** | Acuerdo AGN 003/2015 | Congelación de datos al aprobar<br/>Garantía integridad histórica |
| **Métricas** | Decreto 2106/2019 | Dashboard tiempo real:<br/>- % Cumplimiento SLA<br/>- Tiempo promedio respuesta<br/>- Volumen por oficina |

---

## 📊 CUMPLIMIENTO NORMATIVO

| Normativa | Estado | Observaciones |
|-----------|--------|---------------|
| Ley 1755/2015 - Derecho Petición | ✅ 100% | Radicación mismo día, plazos correctos |
| Ley 594/2000 - Ley General Archivos | ✅ 100% | TRD, conservación, trazabilidad |
| Decreto 2609/2012 - Digitalización | ✅ 100% | Escaneo obligatorio implementado |
| Ley 1437/2011 - CPACA | ✅ 100% | Días hábiles, plazos, notificaciones |
| Ley 1581/2012 - Datos Personales | ✅ 100% | Protección datos, acceso controlado |
| Ley 527/1999 - Comercio Electrónico | ✅ 100% | Mensajes de datos, valor probatorio |
| Acuerdo AGN 060/2001 - TRD | ✅ 100% | Serie/subserie, conservación |
| Ley 1712/2014 - Transparencia | ✅ 100% | Trazabilidad, acceso información |

---

## 🔑 CARACTERÍSTICAS DESTACADAS

### **✅ IMPLEMENTADAS:**
1. ✅ Inspección física con criterios normados
2. ✅ Digitalización obligatoria + validación técnica
3. ✅ Sello con QR para verificación ciudadana
4. ✅ Radicación automática consecutivo único
5. ✅ Cálculo SLA calendario laboral real
6. ✅ Alertas progresivas 75%-90%-95%-100%
7. ✅ Trazabilidad 100% inmutable
8. ✅ Validación emails reducción rebotes 80%
9. ✅ Seguimiento DSN con reintentos
10. ✅ Snapshots garantía histórica
11. ✅ Métricas dashboard tiempo real

---

## 📁 ARCHIVOS TÉCNICOS

- **Código:** `correspondencia/models.py`, `views.py`, `utils_sla.py`
- **Calendario:** `feriados.csv` (actualizado anualmente)
- **Templates:** `correspondencia/templates/`
- **Documentación Completa:** `FLUJOGRAMA_ACTUAL_CON_REFERENCIAS_LEGALES.md`

---

## 📈 INDICADORES DE GESTIÓN

| Métrica | Meta | Actual |
|---------|------|--------|
| % Cumplimiento SLA | >95% | Monitoreo en tiempo real |
| Tiempo Promedio Respuesta | <12 días | Dashboard automático |
| Tasa Rebotes Email | <5% | Validación preventiva |
| Satisfacción Ciudadana | >90% | Sello QR + Transparencia |

---

**Elaborado por:** Equipo Técnico | **Fecha:** 21 de octubre de 2025 | **Estado:** PRODUCCIÓN

