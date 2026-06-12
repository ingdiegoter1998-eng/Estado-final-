"""
Fixtures específicos para tests del módulo de correspondencia.

Estos complementan los fixtures globales de conftest.py raíz.
"""
import pytest
from correspondencia.models import Correspondencia, CorreoEntrante, EntidadExterna, Contacto


@pytest.fixture
def correspondencia_entrante(db, contacto, oficina, ventanilla_user, serie, subserie):
    """Correspondencia entrante radicada — objeto base para tests de flujo."""
    return Correspondencia.objects.create(
        tipo_radicado="ENTRADA",
        asunto="Test correspondencia entrante",
        remitente=contacto,
        oficina_destino=oficina,
        serie=serie,
        subserie=subserie,
        usuario_radicador=ventanilla_user,
        medio_recepcion="CORREO_ELECTRONICO",
        requiere_respuesta=True,
        tiempo_respuesta=15,
    )


@pytest.fixture
def correo_entrante(db):
    """CorreoEntrante sin procesar — para tests de ingesta IMAP."""
    return CorreoEntrante.objects.create(
        message_id="<test-001@example.com>",
        remitente="remitente@example.com",
        asunto="Correo de prueba",
        cuerpo_texto="Cuerpo del correo de prueba",
        procesado=False,
    )


@pytest.fixture
def correo_procesado(db, correo_entrante, correspondencia_entrante):
    """CorreoEntrante ya procesado y vinculado a un radicado."""
    correo_entrante.procesado = True
    correo_entrante.radicado_asociado = correspondencia_entrante
    correo_entrante.save()
    return correo_entrante
