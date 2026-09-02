"""Sello ZPL para Zebra ZD230 — etiqueta real de 2" x 1" (5cm x 2.5cm).

Diseño replicado a partir de la plantilla que envió el hospital, comprimido
para caber en el rollo real de Ventanilla (2" x 1", no 3" x 2" como se
asumió al principio — eso hacía que el sello saliera cortado/desbordado).
Sin QR y sin logo (a resolución térmica el badge institucional quedaba
ilegible/deforme y aquí ni siquiera hay espacio para él):
"RADICACIÓN DE CORRESPONDENCIA" arriba, radicado grande, fecha/hora y
oficina en una línea cada una, y una franja inferior negra con el tipo
(ENTRADA/SALIDA) en blanco.
"""
from __future__ import annotations

from django.utils import timezone

LABEL_WIDTH_DOTS = 406
LABEL_HEIGHT_DOTS = 203

# Ancho útil de contenido (dentro del borde) para calcular truncado de texto.
_IZQ = 10
_ANCHO_UTIL = LABEL_WIDTH_DOTS - 2 * _IZQ
_ANCHO_CHAR_APROX = 0.58  # fracción del alto de fuente que ocupa cada carácter (font 0, aprox)


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
    """URL pública del micro-sitio verificar-sello (/v/{radicado}).

    No se imprime en el sello actual (el diseño aprobado por el hospital no
    lleva QR, y en esta etiqueta de 2x1' tampoco cabría), pero se conserva
    por si se reactiva la verificación en otro canal.
    """
    from django.conf import settings

    base = getattr(settings, "SELLO_VERIFICAR_BASE_URL", "http://127.0.0.1:5174").rstrip("/")
    rad = (radicado or "").strip()
    return f"{base}/v/{rad}"


def _truncar_a_ancho(texto: str, font_height: int, ancho_disponible: int) -> str:
    max_chars = max(1, int(ancho_disponible / (font_height * _ANCHO_CHAR_APROX)))
    if len(texto) <= max_chars:
        return texto
    return texto[: max(1, max_chars - 1)].rstrip() + "…"


def _build_label(*, tipo: str, radicado: str, fecha: str, oficina: str) -> str:
    tipo = _zpl_escape((tipo or "").upper())
    radicado = _zpl_escape(radicado)
    fecha = _truncar_a_ancho(_zpl_escape(fecha), 16, _ANCHO_UTIL)
    oficina = _truncar_a_ancho(_zpl_escape(oficina).strip(), 16, _ANCHO_UTIL)

    lines = [
        "^XA",
        f"^PW{LABEL_WIDTH_DOTS}",
        f"^LL{LABEL_HEIGHT_DOTS}",
        "^CI28",
        # Borde exterior redondeado
        f"^FO4,4^GB{LABEL_WIDTH_DOTS - 8},{LABEL_HEIGHT_DOTS - 8},3,B,2^FS",
        # Encabezado (centrado, 2 líneas): hospital + título
        f"^FO0,7^A0N,12,12^FB{LABEL_WIDTH_DOTS},1,0,C^FDHOSPITAL DEL SARARE E.S.E^FS",
        f"^FO0,21^A0N,11,11^FB{LABEL_WIDTH_DOTS},1,0,C^FDRADICACIÓN DE CORRESPONDENCIA^FS",
        # Radicado (grande)
        f"^FO{_IZQ},36^GB{_ANCHO_UTIL},2,2^FS",
        f"^FO{_IZQ},43^A0N,30,18^FD{radicado}^FS",
        f"^FO{_IZQ},76^GB{_ANCHO_UTIL},2,2^FS",
        # Fecha / hora
        f"^FO{_IZQ},83^A0N,16,16^FD{fecha}^FS",
        # Oficina
        f"^FO{_IZQ},103^A0N,16,16^FD{oficina}^FS",
        # Franja inferior con el tipo (blanco sobre negro)
        f"^FO{_IZQ},142^GB{_ANCHO_UTIL},34,34^FS",
        f"^FO0,150^A0N,22,22^FB{LABEL_WIDTH_DOTS},1,0,C^FR^FD{tipo}^FS",
        "^XZ",
        "",
    ]
    return "\n".join(lines)


def datos_sello_entrada(correspondencia) -> dict:
    oficina = getattr(getattr(correspondencia, "oficina_destino", None), "nombre", None) or "Sin oficina"
    radicado = correspondencia.numero_radicado or ""
    return {
        "tipo": "ENTRADA",
        "radicado": radicado,
        "fecha": _fmt_fecha(getattr(correspondencia, "fecha_radicacion", None)),
        "oficina": oficina,
        "verificar_url": url_verificacion_radicado(radicado),
    }


def datos_sello_salida(salida) -> dict:
    oficina = getattr(getattr(salida, "oficina_emisora", None), "nombre", None) or "Sin oficina"
    fecha = (
        getattr(salida, "fecha_envio", None)
        or getattr(salida, "fecha_aprobacion", None)
        or getattr(salida, "fecha_creacion", None)
    )
    radicado = salida.numero_radicado_salida or ""
    return {
        "tipo": "SALIDA",
        "radicado": radicado,
        "fecha": _fmt_fecha(fecha),
        "oficina": oficina,
        "verificar_url": url_verificacion_radicado(radicado),
    }


def zpl_sello_entrada(correspondencia) -> str:
    datos = datos_sello_entrada(correspondencia)
    return _build_label(
        tipo=datos["tipo"],
        radicado=datos["radicado"],
        fecha=datos["fecha"],
        oficina=datos["oficina"],
    )


def zpl_sello_salida(salida) -> str:
    datos = datos_sello_salida(salida)
    return _build_label(
        tipo=datos["tipo"],
        radicado=datos["radicado"],
        fecha=datos["fecha"],
        oficina=datos["oficina"],
    )
