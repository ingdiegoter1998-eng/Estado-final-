"""Sello en PDF (3" x 2"), mismo diseño que el ZPL de sello_zebra.py.

Ventanilla tenía que descargar un .zpl (texto plano con comandos Zebra) y no
todos los equipos tienen el software para mandarlo a imprimir — terminaban
pegando el código en visores online. El PDF resuelve eso: se abre con
cualquier lector y se imprime directo (o se manda por USB/red a la Zebra
usando el driver de Windows, que sí sabe convertir un PDF a impresión
térmica).
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from correspondencia.utils.sello_zebra import (
    CALENDARIO_PATH,
    PERSONA_PATH,
    datos_sello_entrada,
    datos_sello_salida,
)

PAGE_WIDTH = 3 * inch
PAGE_HEIGHT = 2 * inch


def _y(top_pt: float) -> float:
    """Convierte una coordenada 'desde arriba' (como ZPL) a Y de reportlab (desde abajo)."""
    return PAGE_HEIGHT - top_pt


def _fit_font_size(c: canvas.Canvas, text: str, font: str, start_size: float, max_width: float, min_size: float = 6) -> float:
    """Tamaño de fuente más grande (hasta ``start_size``) que cabe en ``max_width``."""
    size = start_size
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def _draw_label(c: canvas.Canvas, *, tipo: str, radicado: str, fecha: str, oficina: str) -> None:
    from PIL import Image
    from reportlab.lib.utils import ImageReader

    tipo = (tipo or "").upper()
    oficina = (oficina or "").strip()
    if len(oficina) > 33:
        oficina = oficina[:32].rstrip() + "…"

    # Borde exterior redondeado
    margen = 4
    c.setLineWidth(1.3)
    c.roundRect(
        margen, margen, PAGE_WIDTH - 2 * margen, PAGE_HEIGHT - 2 * margen,
        radius=7, stroke=1, fill=0,
    )

    izq = 13
    der = PAGE_WIDTH - izq
    divisor_x = 122
    gap = 6

    # Encabezado: nombre del hospital + subtítulo (autoajustado para no chocar con el divisor)
    hospital_w = divisor_x - gap - izq
    hospital_size = _fit_font_size(c, "HOSPITAL DEL SARARE", "Helvetica-Bold", 10, hospital_w)
    c.setFont("Helvetica-Bold", hospital_size)
    c.drawString(izq, _y(20), "HOSPITAL DEL SARARE")
    sub_size = _fit_font_size(c, "Empresa Social del Estado", "Helvetica-Bold", 5.5, hospital_w)
    c.setFont("Helvetica-Bold", sub_size)
    c.drawString(izq, _y(29), "Empresa Social del Estado")

    # Divisor vertical + título derecho (autoajustado al ancho disponible)
    c.setLineWidth(0.8)
    c.line(divisor_x, _y(10), divisor_x, _y(41))
    titulo_x = divisor_x + gap
    titulo_w = der - titulo_x
    titulo_size = min(
        _fit_font_size(c, "RADICACIÓN DE", "Helvetica-Bold", 8, titulo_w),
        _fit_font_size(c, "CORRESPONDENCIA", "Helvetica-Bold", 8, titulo_w),
    )
    c.setFont("Helvetica-Bold", titulo_size)
    c.drawString(titulo_x, _y(19), "RADICACIÓN DE")
    c.drawString(titulo_x, _y(28), "CORRESPONDENCIA")

    # Regla + radicado grande
    c.setLineWidth(0.7)
    c.line(izq, _y(46), PAGE_WIDTH - izq, _y(46))
    c.setFont("Helvetica-Bold", 17)
    radicado_size = 17
    ancho_disponible = PAGE_WIDTH - 2 * izq
    while c.stringWidth(radicado, "Helvetica-Bold", radicado_size) > ancho_disponible and radicado_size > 10:
        radicado_size -= 1
    c.setFont("Helvetica-Bold", radicado_size)
    c.drawString(izq, _y(63), radicado)
    c.setLineWidth(0.7)
    c.line(izq, _y(72), PAGE_WIDTH - izq, _y(72))

    # Fecha / hora con ícono de calendario
    icono_w = 11
    cal_img = ImageReader(Image.open(CALENDARIO_PATH))
    c.drawImage(cal_img, izq, _y(89), icono_w, icono_w, mask="auto")
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(izq + icono_w + 6, _y(83), fecha or "")

    # Oficina con ícono de persona
    per_img = ImageReader(Image.open(PERSONA_PATH))
    c.drawImage(per_img, izq, _y(106), icono_w, icono_w, mask="auto")
    c.drawString(izq + icono_w + 6, _y(100), oficina or "")

    # Franja inferior negra con el tipo (blanco sobre negro)
    franja_y_top = 115
    franja_alto = 21
    c.setFillColorRGB(0, 0, 0)
    c.roundRect(
        izq, _y(franja_y_top + franja_alto), PAGE_WIDTH - 2 * izq, franja_alto,
        radius=3, stroke=0, fill=1,
    )
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(PAGE_WIDTH / 2, _y(franja_y_top + franja_alto - 6), tipo)
    c.setFillColorRGB(0, 0, 0)


def _render_pdf(*, tipo: str, radicado: str, fecha: str, oficina: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(f"Sello {tipo} {radicado}")
    _draw_label(c, tipo=tipo, radicado=radicado, fecha=fecha, oficina=oficina)
    c.showPage()
    c.save()
    return buf.getvalue()


def pdf_sello_entrada(correspondencia) -> bytes:
    datos = datos_sello_entrada(correspondencia)
    return _render_pdf(
        tipo=datos["tipo"], radicado=datos["radicado"], fecha=datos["fecha"], oficina=datos["oficina"],
    )


def pdf_sello_salida(salida) -> bytes:
    datos = datos_sello_salida(salida)
    return _render_pdf(
        tipo=datos["tipo"], radicado=datos["radicado"], fecha=datos["fecha"], oficina=datos["oficina"],
    )
