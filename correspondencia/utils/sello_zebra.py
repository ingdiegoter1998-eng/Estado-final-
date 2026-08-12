"""Sellos ZPL para Zebra ZD230 (3\" x 2\", 203 dpi) con QR de verificación."""
from __future__ import annotations

from django.conf import settings
from django.utils import timezone


LABEL_WIDTH_DOTS = 609
LABEL_HEIGHT_DOTS = 406


def _zpl_escape(texto: str) -> str:
    if not texto:
        return ""
    return (
        str(texto)
        .replace("\\", " ")
        .replace("^", " ")
        .replace("~", " ")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _fmt_fecha(dt) -> str:
    if not dt:
        return ""
    try:
        return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M")
    except Exception:
        try:
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(dt)


def url_verificacion_radicado(radicado: str) -> str:
    """URL pública del micro-sitio verificar-sello (/v/{radicado})."""
    base = getattr(settings, "SELLO_VERIFICAR_BASE_URL", "http://127.0.0.1:5174").rstrip("/")
    rad = (radicado or "").strip()
    return f"{base}/v/{rad}"


def _build_label(
    *,
    tipo: str,
    radicado: str,
    fecha: str,
    linea3: str,
    linea4: str = "",
    qr_url: str = "",
) -> str:
    tipo = _zpl_escape((tipo or "").upper())
    radicado = _zpl_escape(radicado)
    fecha = _zpl_escape(fecha)
    oficina = _zpl_escape(linea3.replace("OFICINA:", "").strip())[:34]
    extra = _zpl_escape(
        (linea4 or "")
        .replace("MEDIO:", "")
        .replace("RESPUESTA A:", "Rta:")
        .strip()
    )[:34]
    qr_payload = _zpl_escape(qr_url or url_verificacion_radicado(radicado))

    # Texto a la izquierda, QR a la derecha (etiqueta 3x2).
    lines = [
        "^XA",
        f"^PW{LABEL_WIDTH_DOTS}",
        f"^LL{LABEL_HEIGHT_DOTS}",
        "^LH0,0",
        "^CI28",
        "^FO12,12^GB585,382,3^FS",
        "^FO22,22^GB565,362,2^FS",
        # Encabezado
        "^FO36,40^A0N,26,26^FDE.S.E. HOSPITAL DEL SARARE^FS",
        "^FO36,72^A0N,22,22^FDRADICACION DE CORRESPONDENCIA^FS",
        "^FO36,104^GB360,2,2^FS",
        # Cuerpo
        f"^FO36,122^A0N,28,28^FD{radicado}^FS",
        f"^FO36,168^A0N,24,24^FD{fecha}^FS",
        f"^FO36,206^A0N,22,22^FD{oficina}^FS",
    ]
    if extra:
        lines.append(f"^FO36,240^A0N,20,20^FD{extra}^FS")
    lines.extend(
        [
            f"^FO36,290^A0N,28,28^FD{tipo}^FS",
            # QR → micro-sitio /v/{radicado}
            "^FO410,120^BQN,2,4",
            f"^FDQA,{qr_payload}^FS",
            "^FO410,340^A0N,16,16^FDEscanear^FS",
            "^XZ",
            "",
        ]
    )
    return "\n".join(lines)


def datos_sello_entrada(correspondencia) -> dict:
    oficina = getattr(getattr(correspondencia, "oficina_destino", None), "nombre", None) or "Sin oficina"
    medio = getattr(correspondencia, "get_medio_recepcion_display", lambda: "")() or getattr(
        correspondencia, "medio_recepcion", ""
    )
    radicado = correspondencia.numero_radicado or ""
    return {
        "tipo": "ENTRADA",
        "radicado": radicado,
        "fecha": _fmt_fecha(getattr(correspondencia, "fecha_radicacion", None)),
        "linea3": f"OFICINA: {oficina}",
        "linea4": f"MEDIO: {medio}" if medio else "",
        "oficina": oficina,
        "extra": medio or "",
        "verificar_url": url_verificacion_radicado(radicado),
    }


def datos_sello_salida(salida) -> dict:
    oficina = getattr(getattr(salida, "oficina_emisora", None), "nombre", None) or "Sin oficina"
    fecha = (
        getattr(salida, "fecha_envio", None)
        or getattr(salida, "fecha_aprobacion", None)
        or getattr(salida, "fecha_creacion", None)
    )
    respuesta_a = ""
    entrada = getattr(salida, "respuesta_a", None)
    if entrada is not None and getattr(entrada, "numero_radicado", None):
        respuesta_a = entrada.numero_radicado

    radicado = salida.numero_radicado_salida or ""
    return {
        "tipo": "SALIDA",
        "radicado": radicado,
        "fecha": _fmt_fecha(fecha),
        "linea3": f"OFICINA: {oficina}",
        "linea4": f"RESPUESTA A: {respuesta_a}" if respuesta_a else "",
        "oficina": oficina,
        "extra": f"Rta: {respuesta_a}" if respuesta_a else "",
        "verificar_url": url_verificacion_radicado(radicado),
    }


def zpl_sello_entrada(correspondencia) -> str:
    datos = datos_sello_entrada(correspondencia)
    return _build_label(
        tipo=datos["tipo"],
        radicado=datos["radicado"],
        fecha=datos["fecha"],
        linea3=datos["linea3"],
        linea4=datos["linea4"],
        qr_url=datos["verificar_url"],
    )


def zpl_sello_salida(salida) -> str:
    datos = datos_sello_salida(salida)
    return _build_label(
        tipo=datos["tipo"],
        radicado=datos["radicado"],
        fecha=datos["fecha"],
        linea3=datos["linea3"],
        linea4=datos["linea4"],
        qr_url=datos["verificar_url"],
    )
