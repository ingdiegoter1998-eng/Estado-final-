"""Sello en PDF (3x2) — alternativa al ZPL para equipos sin software Zebra."""
from types import SimpleNamespace

from django.utils import timezone

from correspondencia.utils.sello_pdf import pdf_sello_entrada, pdf_sello_salida


def test_pdf_entrada_es_un_pdf_valido():
    corr = SimpleNamespace(
        numero_radicado="ENTRANTE-2026-00001",
        fecha_radicacion=timezone.now(),
        oficina_destino=SimpleNamespace(nombre="Ventanilla Única"),
    )
    pdf_bytes = pdf_sello_entrada(corr)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes


def test_pdf_salida_es_un_pdf_valido():
    salida = SimpleNamespace(
        numero_radicado_salida="SALIENTE-2026-00010",
        fecha_envio=timezone.now(),
        fecha_aprobacion=None,
        fecha_creacion=timezone.now(),
        oficina_emisora=SimpleNamespace(nombre="Archivo Central"),
        respuesta_a=None,
    )
    pdf_bytes = pdf_sello_salida(salida)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes


def test_pdf_no_revienta_con_oficina_muy_larga():
    salida = SimpleNamespace(
        numero_radicado_salida="SALIENTE-2026-00011",
        fecha_envio=timezone.now(),
        fecha_aprobacion=None,
        fecha_creacion=timezone.now(),
        oficina_emisora=SimpleNamespace(
            nombre="Coordinación de Talento Humano y Bienestar Laboral Institucional"
        ),
        respuesta_a=None,
    )
    pdf_bytes = pdf_sello_salida(salida)
    assert pdf_bytes.startswith(b"%PDF-")
