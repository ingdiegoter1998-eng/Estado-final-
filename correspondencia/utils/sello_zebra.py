"""Sellos ZPL para Zebra ZD230 (3" x 2", 203 dpi).

Diseño replicado a partir de la plantilla que envió el hospital (sin QR y
sin logo — a esa resolución de impresión térmica el badge institucional
quedaba ilegible/deforme, así que el encabezado es solo tipografía):
"HOSPITAL DEL SARARE" + "RADICACIÓN DE CORRESPONDENCIA" en el encabezado,
número de radicado grande, fecha/hora con ícono de calendario, oficina con
ícono de persona, y una franja inferior negra con el tipo (ENTRADA/SALIDA)
en blanco.
"""
from __future__ import annotations

import os
from functools import lru_cache

from django.utils import timezone

LABEL_WIDTH_DOTS = 609
LABEL_HEIGHT_DOTS = 406

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "sello")
CALENDARIO_PATH = os.path.join(_ASSETS_DIR, "calendario.png")
PERSONA_PATH = os.path.join(_ASSETS_DIR, "persona.png")

# Tamaño de los íconos en la etiqueta (ancho en puntos @203dpi; el alto se
# escala manteniendo la proporción original de cada imagen).
_ICONO_WIDTH = 38


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
    lleva QR), pero se conserva por si se reactiva la verificación en otro
    canal.
    """
    from django.conf import settings

    base = getattr(settings, "SELLO_VERIFICAR_BASE_URL", "http://127.0.0.1:5174").rstrip("/")
    rad = (radicado or "").strip()
    return f"{base}/v/{rad}"


@lru_cache(maxsize=None)
def _image_to_zpl_gf(path: str, width: int) -> tuple[str, int, int]:
    """Convierte un PNG monocromo en un campo gráfico ZPL (``^GFA`` hex ASCII).

    Devuelve ``(comando, ancho_px, alto_px)``. Cacheado: las imágenes son
    fijas (logo e íconos institucionales empacados con la app).
    """
    from PIL import Image

    im = Image.open(path).convert("L")
    height = round(im.height * width / im.width)
    im = im.resize((width, height), Image.LANCZOS)
    # Reforzar blanco/negro puro tras el resize (evita grises del filtro).
    im = im.point(lambda p: 0 if p < 140 else 255)

    bytes_per_row = (width + 7) // 8
    total_bytes = bytes_per_row * height
    px = im.load()
    filas_hex = []
    for y in range(height):
        fila = bytearray()
        byte = 0
        bits = 0
        for x in range(width):
            bit = 1 if px[x, y] < 128 else 0
            byte = (byte << 1) | bit
            bits += 1
            if bits == 8:
                fila.append(byte)
                byte = 0
                bits = 0
        if bits:
            byte <<= (8 - bits)
            fila.append(byte)
        filas_hex.append(fila.hex())
    hexdata = "".join(filas_hex)
    return f"^GFA,{total_bytes},{total_bytes},{bytes_per_row},{hexdata}", width, height


def _build_label(*, tipo: str, radicado: str, fecha: str, oficina: str) -> str:
    tipo = _zpl_escape((tipo or "").upper())
    radicado = _zpl_escape(radicado)
    fecha = _zpl_escape(fecha)
    oficina = _zpl_escape(oficina).strip()
    if len(oficina) > 33:
        oficina = oficina[:32].rstrip() + "…"

    cal_gf, cal_w, cal_h = _image_to_zpl_gf(CALENDARIO_PATH, _ICONO_WIDTH)
    per_gf, per_w, per_h = _image_to_zpl_gf(PERSONA_PATH, _ICONO_WIDTH)

    texto_x = 26
    divisor_x = 350
    col_derecha_x = divisor_x + 18

    lines = [
        "^XA",
        f"^PW{LABEL_WIDTH_DOTS}",
        f"^LL{LABEL_HEIGHT_DOTS}",
        "^CI28",
        # Borde exterior redondeado
        "^FO10,10^GB589,386,4,B,2^FS",
        # Nombre del hospital + subtítulo (encabezado solo tipográfico)
        f"^FO{texto_x},30^A0N,28,28^FDHOSPITAL DEL SARARE^FS",
        f"^FO{texto_x},64^A0N,15,15^FDEmpresa Social del Estado^FS",
        # Divisor vertical + título de la derecha
        f"^FO{divisor_x},22^GB2,88,2^FS",
        f"^FO{col_derecha_x},26^A0N,22,22^FDRADICACIÓN DE^FS",
        f"^FO{col_derecha_x},54^A0N,22,22^FDCORRESPONDENCIA^FS",
        # Radicado (grande)
        "^FO26,126^GB557,2,2^FS",
        f"^FO24,138^A0N,50,28^FD{radicado}^FS",
        "^FO26,200^GB557,2,2^FS",
        # Fecha / hora
        f"^FO24,222{cal_gf}^FS",
        f"^FO72,224^A0N,28,28^FD{fecha}^FS",
        # Oficina
        f"^FO24,268{per_gf}^FS",
        f"^FO72,270^A0N,28,28^FD{oficina}^FS",
        # Franja inferior con el tipo (blanco sobre negro)
        "^FO26,326^GB557,58,58^FS",
        f"^FO0,346^A0N,34,34^FB609,1,0,C^FR^FD{tipo}^FS",
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
