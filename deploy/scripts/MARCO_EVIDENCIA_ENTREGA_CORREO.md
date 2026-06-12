# Marco de evidencia y reducción de riesgo — envío por correo

Documento operativo para el Hospital del Sarare E.S.E. (no constituye asesoría jurídica).

## Qué demuestra el sistema

1. **Radicado de salida** con fecha/hora de creación, aprobación y envío.
2. **Usuario aprobador** (ventanilla o proceso documentado).
3. **MessageID Postmark** — identificador en poder de un tercero (proveedor de correo).
4. **Webhook Delivery** — confirmación de que el servidor de correo del destinatario aceptó el mensaje (respuesta SMTP registrada).
5. **Webhook Bounce** — registro de rechazo técnico con tipo y descripción.
6. **Historial inmutable** en base de datos (`HistorialSalida`, `PostmarkWebhookEvento`).
7. **Constancia imprimible** con huella SHA-256 truncada de referencia.

## Pantallas

| Ruta | Uso |
|------|-----|
| `/registros/correspondencia/ventanilla/seguimiento-entrega/` | Panel de rebotes y entregas |
| `.../seguimiento-entrega/<id>/` | Detalle y línea de tiempo |
## Argumentos ante reclamo de “no llegó” o “llegó tarde”

| Situación | Respuesta documentada |
|-----------|------------------------|
| Entrega confirmada (Delivery) | Exhibir panel de trazabilidad + SMTP del destinatario; la entidad cumplió remisión al servidor del destinatario. |
| Rebote (Soft/Hard) | Exhibir tipo de rebote; ofrecer canal alternativo; no imputable a omisión del hospital si el buzón/dominio es inválido. |
| Enviado sin confirmación | Indicar límite de trazabilidad; reenvío o verificación con destinatario / IT del destinatario. |
| Demora en lectura | Distinguir **envío** (timestamp sistema) vs **lectura** (no controlada); SLA interno de aprobación documentado aparte. |

## Recomendaciones institucionales

- Conservar historial y logs **mínimo 5 años** (alinear con archivo y términos legales).
- Mantener **DKIM/SPF** en dominio institucional (menos spam, más credibilidad).
- Política de **reenvío** tras rebote blando documentada en procedimiento de correspondencia.
- No prometer en plantillas “entrega instantánea”; usar “remitido por correo electrónico institucional”.
- Capacitar ventanilla en uso del panel **Entrega y Rebotes**.

## Límites (transparencia)

- El hospital no certifica que el destinatario **leyó** el correo.
- Filtros antispam, cuarentena y reglas del destinatario son ajenos al emisor.
- La trazabilidad en sistema es **soporte probatorio operativo**; valoración legal corresponde a jurídica de la entidad.
