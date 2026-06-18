# Ley 527 de 1999 — Comercio Electrónico, Mensajes de Datos y Firma Digital

## Datos Generales

| Campo | Detalle |
|-------|---------|
| **Norma** | Ley 527 de 1999 |
| **Fecha** | 18 de agosto de 1999 |
| **Objeto** | Definir y reglamentar el acceso y uso de los mensajes de datos, del comercio electrónico y de las firmas digitales, y establecer las entidades de certificación. |
| **Reglamentada por** | Decreto 1747 de 2000; Decreto 2364 de 2012 |
| **Estado** | Vigente |

---

## Importancia para Correspondencia

Esta ley proporciona el **marco jurídico para la validez de los documentos electrónicos**, las firmas digitales y los mensajes de datos. Es fundamental para el sistema de correspondencia porque:

1. Otorga **validez jurídica** a los documentos electrónicos (correos, PDF, archivos digitales).
2. Define los requisitos del **mensaje de datos** como equivalente funcional del documento escrito.
3. Regula la **firma electrónica y digital** para autenticar comunicaciones.
4. Establece reglas sobre **envío y recepción** de mensajes de datos.

---

## Mensaje de Datos (Art. 2)

**Definición**: Información generada, enviada, recibida, almacenada o comunicada por medios electrónicos, ópticos o similares, como:
- Intercambio Electrónico de Datos (EDI)
- Internet
- Correo electrónico
- Telegrama
- Télex
- Telefax

---

## Equivalentes Funcionales

### Escrito (Art. 6)
Un mensaje de datos satisface el requisito de que la información conste por **escrito** cuando:
- La información contenida es accesible para su posterior consulta.

### Firma (Art. 7)
Un mensaje de datos cumple el requisito de **firma** cuando:
- Se ha utilizado un método que permita identificar al iniciador.
- Que dicho método sea confiable y apropiado.

### Original (Art. 8)
Un mensaje de datos satisface el requisito de **original** cuando:
- Existe garantía confiable de que se ha conservado la integridad de la información desde su generación.
- La información es accesible para su posterior consulta.

### Conservación (Art. 12)
Los mensajes de datos se **conservarán** cuando:
- La información sea accesible para posterior consulta.
- Se conserve en el formato original o en uno que reproduzca con exactitud la información.
- Se conserve información que permita determinar el origen, destino, fecha y hora de envío y recepción.

---

## Admisibilidad y Fuerza Probatoria (Art. 10-11)

### Admisibilidad (Art. 10)
- Los mensajes de datos serán **admisibles como medios de prueba**.
- Su fuerza probatoria es la otorgada por las disposiciones del Código de Procedimiento Civil (hoy CGP).

### Criterio para valorar (Art. 11)
Para la valoración de la fuerza probatoria de un mensaje de datos se tendrá en cuenta:
1. La **confiabilidad** de la forma en que se generó, archivó o comunicó.
2. La confiabilidad de la forma en que se conservó la **integridad**.
3. La forma en que se identifica a su **iniciador**.
4. Cualquier otro factor pertinente.

---

## Firma Digital (Art. 28)

**Definición**: Valor numérico que se adhiere a un mensaje de datos, utilizando un procedimiento matemático conocido, vinculado a la clave del iniciador y al texto del mensaje, que permite determinar que el valor se ha obtenido exclusivamente con la clave del iniciador y que el mensaje inicial no ha sido modificado después de efectuada la transformación.

### Atributos de la firma digital:
1. Es **única** a la persona que la usa.
2. Es susceptible de ser **verificada**.
3. Está bajo el control exclusivo de la persona que la usa.
4. Está ligada a la información del mensaje de tal forma que si esta se **cambia, la firma se invalida**.

---

## Firma Electrónica (Decreto 2364 de 2012)

El Decreto 2364 de 2012 reglamenta el artículo 7 de la Ley 527 y define la **firma electrónica**:

| Aspecto | Detalle |
|---------|---------|
| **Definición** | Métodos tales como códigos, contraseñas, datos biométricos, o claves criptográficas privadas, que permiten identificar a una persona en relación con un mensaje de datos, siempre y cuando el mismo sea confiable y apropiado. |
| **Validez** | Tiene la misma validez y efectos jurídicos que la firma manuscrita, si cumple con los requisitos del artículo 7 de la Ley 527. |
| **Autonomía** | Las partes pueden acordar el tipo de firma electrónica a utilizar. |

---

## Envío y Recepción de Mensajes de Datos (Arts. 23-25)

### Envío (Art. 23)
Un mensaje de datos se tiene por **expedido** cuando:
- Entra en un sistema de información que no esté bajo el control del iniciador o la persona que envió el mensaje.

### Acuse de recibo (Art. 24)
- Si el iniciador ha **solicitado o acordado** que se confirme la recepción, el mensaje de datos se tendrá como no enviado hasta que se reciba el acuse.
- Si no ha solicitado acuse, podrá solicitar confirmación por sí mismo.

### Recepción (Art. 25)
Un mensaje de datos se tiene por **recibido**:
- Cuando entra en un sistema de información designado por el destinatario.
- Si no hay sistema designado, cuando llega al sistema del destinatario.

### Lugar de envío y recepción (Art. 25 parágrafo)
- Se tendrá por expedido en el **lugar de establecimiento del iniciador**.
- Se tendrá por recibido en el **lugar de establecimiento del destinatario**.

---

## Entidades de Certificación (Arts. 29-44)

- Son las autorizadas para emitir **certificados de firma digital**.
- En Colombia están supervisadas por la **ONAC** (Organismo Nacional de Acreditación) y la **SIC**.
- Los certificados digitales vinculan una clave pública con la identidad de un suscriptor.

---

## Relevancia para el Aplicativo

| Funcionalidad | Artículos | Implementación |
|---------------|-----------|----------------|
| **Correo electrónico como comunicación válida** | Arts. 2, 6, 10 | Los correos recibidos e integrados al sistema tienen validez como mensajes de datos. |
| **Documentos PDF adjuntos** | Arts. 6, 8 | Los documentos digitalizados y archivos PDF gozan de validez probatoria. |
| **Radicación electrónica** | Arts. 6, 23, 25 | La radicación de documentos recibidos electrónicamente tiene la misma validez que la presencial. |
| **Acuse de recibo automático** | Art. 24 | Confirmación automática cuando se integra un correo al sistema. |
| **Integridad de documentos** | Arts. 8, 12 | Almacenamiento que garantice que el documento no ha sido modificado. |
| **Notificaciones electrónicas** | Arts. 23, 25 | Envío de notificaciones por correo electrónico con constancia de recepción. |
| **Firma electrónica/digital** | Arts. 7, 28, D.2364/2012 | Para firmar comunicaciones oficiales electrónicas (aprobación de salidas). |
| **Conservación de documentos electrónicos** | Art. 12 | Preservación en formato original con metadatos de origen, destino y fecha. |
