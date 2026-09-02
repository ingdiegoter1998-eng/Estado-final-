"""Sello en PDF — etiqueta real de 2" x 1" (5cm x 2.5cm), mismo diseño que el ZPL.

Ventanilla no tenía forma confiable de mandar un .zpl a imprimir (el sistema
no reconoce la extensión) y terminaban pegando el código en visores online.
El PDF se abre con cualquier lector y se imprime directo. El tamaño de
página coincide con el rollo real de la Zebra (2" x 1"), no con el 3" x 2"
que se asumió al principio.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from correspondencia.utils.sello_zebra import datos_sello_entrada, datos_sello_salida

PAGE_WIDTH = 2 * inch
PAGE_HEIGHT = 1 * inch


def _y(top_pt: float) -> float:
    """Convierte una coordenada 'desde arriba' (como ZPL) a Y de reportlab (desde abajo)."""
    return PAGE_HEIGHT - top_pt


def _fit_font_size(c: canvas.Canvas, text: str, font: str, start_size: float, max_width: float, min_size: float = 5) -> float:
    """Tamaño de fuente más grande (hasta ``start_size``) que cabe en ``max_width``."""
    size = start_size
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def _draw_label(c: canvas.Canvas, *, tipo: str, radicado: str, fecha: str, oficina: str) -> None:
    tipo = (tipo or "").upper()
    oficina = (oficina or "").strip()

    izq = 6
    ancho_util = PAGE_WIDTH - 2 * izq

    # Borde exterior redondeado
    margen = 3
    c.setLineWidth(1)
    c.roundRect(
        margen, margen, PAGE_WIDTH - 2 * margen, PAGE_HEIGHT - 2 * margen,
        radius=4, stroke=1, fill=0,
    )

    # Encabezado centrado: hospital + título (2 líneas)
    hospital_size = _fit_font_size(c, "HOSPITAL DEL SARARE E.S.E", "Helvetica-Bold", 5.5, ancho_util)
    c.setFont("Helvetica-Bold", hospital_size)
    c.drawCentredString(PAGE_WIDTH / 2, _y(9), "HOSPITAL DEL SARARE E.S.E")

    titulo = "RADICACIÓN DE CORRESPONDENCIA"
    titulo_size = _fit_font_size(c, titulo, "Helvetica-Bold", 5, ancho_util)
    c.setFont("Helvetica-Bold", titulo_size)
    c.drawCentredString(PAGE_WIDTH / 2, _y(17), titulo)

    # Regla + radicado grande
    c.setLineWidth(0.6)
    c.line(izq, _y(19), PAGE_WIDTH - izq, _y(19))
    radicado_size = _fit_font_size(c, radicado, "Helvetica-Bold", 12, ancho_util)
    c.setFont("Helvetica-Bold", radicado_size)
    c.drawString(izq, _y(30), radicado)
    c.line(izq, _y(34), PAGE_WIDTH - izq, _y(34))

    # Fecha / hora
    fecha_size = _fit_font_size(c, fecha or "", "Helvetica-Bold", 6, ancho_util)
    c.setFont("Helvetica-Bold", fecha_size)
    c.drawString(izq, _y(42), fecha or "")

    # Oficina (trunca con elipsis si no cabe)
    oficina_mostrar = oficina
    oficina_size = 6
    while oficina_mostrar and c.stringWidth(oficina_mostrar, "Helvetica-Bold", oficina_size) > ancho_util:
        oficina_mostrar = oficina_mostrar[:-1]
    if oficina_mostrar != oficina and oficina_mostrar:
        oficina_mostrar = oficina_mostrar[:-1].rstrip() + "…"
    c.setFont("Helvetica-Bold", oficina_size)
    c.drawString(izq, _y(50), oficina_mostrar)

    # Franja inferior negra con el tipo (blanco sobre negro)
    franja_y_top = 54
    franja_alto = 13
    c.setFillColorRGB(0, 0, 0)
    c.roundRect(
        izq, _y(franja_y_top + franja_alto), ancho_util, franja_alto,
        radius=2, stroke=0, fill=1,
    )
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(PAGE_WIDTH / 2, _y(franja_y_top + franja_alto - 4), tipo)
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
