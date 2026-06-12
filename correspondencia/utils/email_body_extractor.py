from email import message_from_bytes, message_from_string, policy
from email.message import Message
import re


HTML_TAG_RE = re.compile(r'<\s*(html|body|div|table|tr|td|p|br|span|img|a|style|head|meta|!doctype)\b', re.IGNORECASE)


def _normalizar_cuerpo(valor):
    if valor is None:
        return ''
    if isinstance(valor, bytes):
        return valor.decode('utf-8', errors='replace')
    return str(valor)


def _parece_html(valor):
    valor = _normalizar_cuerpo(valor).strip()
    if not valor:
        return False
    return bool(HTML_TAG_RE.search(valor) or re.search(r'<[a-z][^>]*>', valor, re.IGNORECASE))


def _decodificar_parte_email(part):
    try:
        contenido = part.get_content()
    except Exception:
        payload = part.get_payload(decode=True)
        if payload is None:
            payload = part.get_payload()
        if isinstance(payload, bytes):
            charset = part.get_content_charset() or 'utf-8'
            try:
                return payload.decode(charset, errors='replace')
            except LookupError:
                return payload.decode('utf-8', errors='replace')
        return _normalizar_cuerpo(payload)
    return _normalizar_cuerpo(contenido)


def _obtener_objeto_email(msg):
    candidato = getattr(msg, 'obj', None)
    if isinstance(candidato, Message):
        return candidato

    for attr in ('raw', 'raw_message', 'source'):
        candidato = getattr(msg, attr, None)
        if isinstance(candidato, bytes):
            try:
                return message_from_bytes(candidato, policy=policy.default)
            except Exception:
                continue
        if isinstance(candidato, str):
            try:
                return message_from_string(candidato, policy=policy.default)
            except Exception:
                continue

    return None


def _extraer_desde_objeto_email(email_obj):
    if not isinstance(email_obj, Message):
        return '', ''

    texto_plano = ''
    cuerpo_html = ''

    try:
        html_part = email_obj.get_body(preferencelist=('html',))
        if html_part is not None:
            cuerpo_html = _decodificar_parte_email(html_part)

        text_part = email_obj.get_body(preferencelist=('plain',))
        if text_part is not None:
            texto_plano = _decodificar_parte_email(text_part)
    except Exception:
        pass

    if cuerpo_html and texto_plano:
        return texto_plano, cuerpo_html

    textos = []
    htmls = []
    for part in email_obj.walk():
        if part.is_multipart():
            continue

        content_disposition = (part.get_content_disposition() or '').lower()
        if content_disposition == 'attachment':
            continue

        content_type = (part.get_content_type() or '').lower()
        contenido = _decodificar_parte_email(part).strip()
        if not contenido:
            continue

        if content_type == 'text/html':
            htmls.append(contenido)
        elif content_type == 'text/plain':
            textos.append(contenido)

    if not texto_plano and textos:
        texto_plano = '\n\n'.join(textos)
    if not cuerpo_html and htmls:
        cuerpo_html = '\n\n'.join(htmls)

    return texto_plano, cuerpo_html


def extraer_cuerpos_correo(msg):
    """Obtiene el texto plano y el HTML real del correo usando el MIME original como respaldo."""
    cuerpo_texto = _normalizar_cuerpo(getattr(msg, 'text', '')).strip()
    cuerpo_html = _normalizar_cuerpo(getattr(msg, 'html', '')).strip()

    email_obj = _obtener_objeto_email(msg)
    texto_mime, html_mime = _extraer_desde_objeto_email(email_obj)

    if not cuerpo_texto and texto_mime:
        cuerpo_texto = texto_mime.strip()

    if html_mime and (not cuerpo_html or not _parece_html(cuerpo_html)):
        cuerpo_html = html_mime.strip()

    return cuerpo_texto, cuerpo_html