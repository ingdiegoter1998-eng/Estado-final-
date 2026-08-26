"""Sellos ZPL para Zebra ZD230 (diseño replicado del formato enviado por el hospital)."""
from types import SimpleNamespace

from django.utils import timezone

from correspondencia.utils.sello_zebra import (
    url_verificacion_radicado,
    zpl_sello_entrada,
    zpl_sello_salida,
)


def test_zpl_entrada_incluye_datos_clave():
    corr = SimpleNamespace(
        numero_radicado="ENTRANTE-2026-00001",
        fecha_radicacion=timezone.now(),
        oficina_destino=SimpleNamespace(nombre="Ventanilla Única"),
        medio_recepcion="CORREO_ELECTRONICO",
        get_medio_recepcion_display=lambda: "Correo electrónico",
    )
    zpl = zpl_sello_entrada(corr)
    assert zpl.startswith("^XA")
    assert zpl.strip().endswith("^XZ")
    assert "ENTRADA" in zpl
    assert "ENTRANTE-2026-00001" in zpl
    assert "Ventanilla" in zpl  # oficina_destino
    # El diseño aprobado por el hospital no lleva QR.
    assert "^BQN" not in zpl


def test_zpl_salida_incluye_datos_clave():
    salida = SimpleNamespace(
        numero_radicado_salida="SALIENTE-2026-00010",
        fecha_envio=timezone.now(),
        fecha_aprobacion=None,
        fecha_creacion=timezone.now(),
        oficina_emisora=SimpleNamespace(nombre="Archivo Central"),
        respuesta_a=SimpleNamespace(numero_radicado="ENTRANTE-2026-00001"),
    )
    zpl = zpl_sello_salida(salida)
    assert "SALIDA" in zpl
    assert "SALIENTE-2026-00010" in zpl
    assert "Archivo Central" in zpl
    assert "^BQN" not in zpl


def test_zpl_trunca_oficinas_muy_largas():
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
    zpl = zpl_sello_salida(salida)
    assert "…" in zpl


def test_url_verificacion_respeta_setting(settings):
    settings.SELLO_VERIFICAR_BASE_URL = 'http://127.0.0.1:5174/'
    assert url_verificacion_radicado('ENTRANTE-2026-04091') == (
        'http://127.0.0.1:5174/v/ENTRANTE-2026-04091'
    )
