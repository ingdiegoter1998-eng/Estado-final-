"""Validación de adjuntos en radicación rápida (entrante y saliente).

Antes de este cambio, radicación rápida no validaba tamaño/tipo/cantidad de
adjuntos en absoluto (a diferencia de radicación física). El síntoma real
reportado por Ventanilla era "no se pueden hacer salientes rápidos": al
adjuntar una evidencia grande, nginx cortaba la petición con 413 sin ningún
mensaje. Estas pruebas cubren la parte de Django: que ahora exista un límite
explícito y un mensaje claro en español, igual que en física.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

import pytest

from correspondencia.forms import RadicacionRapidaEntranteForm, RadicacionRapidaSalienteForm
from correspondencia.utils.adjuntos_radicacion import (
    EXTENSIONES_GENERAL,
    MAX_FILE_SIZE_MB,
    validar_lista_adjuntos,
)
from documentos.models import (
    EntidadProductora,
    MacroProceso,
    OficinaProductora,
    Proceso,
    UnidadAdministrativa,
)


def _archivo(nombre, size_mb):
    contenido = b'x' * int(size_mb * 1024 * 1024)
    return SimpleUploadedFile(nombre, contenido, content_type='application/pdf')


# --- Validador compartido ---

def test_validar_lista_adjuntos_rechaza_archivo_muy_grande():
    archivo = _archivo('escaneo.pdf', MAX_FILE_SIZE_MB + 1)
    with pytest.raises(ValidationError, match='excede el tamaño máximo'):
        validar_lista_adjuntos([archivo], allowed_extensions=EXTENSIONES_GENERAL)


def test_validar_lista_adjuntos_rechaza_extension_no_permitida():
    archivo = SimpleUploadedFile('virus.exe', b'contenido', content_type='application/octet-stream')
    with pytest.raises(ValidationError, match='Formato no permitido'):
        validar_lista_adjuntos([archivo], allowed_extensions=EXTENSIONES_GENERAL)


def test_validar_lista_adjuntos_acepta_archivo_normal():
    archivo = _archivo('oficio.pdf', 2)
    validar_lista_adjuntos([archivo], allowed_extensions=EXTENSIONES_GENERAL)  # no debe lanzar


# --- Formulario de radicación rápida ENTRANTE ---

@pytest.fixture
def oficina(db):
    ep = EntidadProductora.objects.create(nombre='EP Test Rapida')
    ua = UnidadAdministrativa.objects.create(nombre='UA Test Rapida', entidad_productora=ep)
    macro = MacroProceso.objects.create(numero=901, nombre='Macro Test Rapida')
    proceso = Proceso.objects.create(numero=1, nombre='Proceso Test Rapida', sigla='PTR', macroproceso=macro)
    return OficinaProductora.objects.create(
        nombre='Oficina Rapida', unidad_administrativa=ua, proceso=proceso,
    )


def test_rapida_entrante_rechaza_adjunto_grande(db, oficina):
    archivo = _archivo('escaneo.pdf', MAX_FILE_SIZE_MB + 1)
    data = {
        'rapida_ent-asunto': 'Prueba adjunto grande',
        'rapida_ent-oficina_destino': str(oficina.id),
        'rapida_ent-medio_recepcion': 'FISICO',
    }
    files = MultiValueDict({'rapida_ent-adjuntos_archivos': [archivo]})
    form = RadicacionRapidaEntranteForm(data, files, prefix='rapida_ent')
    assert not form.is_valid()
    assert any('excede el tamaño máximo' in e for e in form.non_field_errors())


def test_rapida_entrante_acepta_sin_adjuntos(db, oficina):
    data = {
        'rapida_ent-asunto': 'Prueba sin adjuntos',
        'rapida_ent-oficina_destino': str(oficina.id),
        'rapida_ent-medio_recepcion': 'FISICO',
    }
    form = RadicacionRapidaEntranteForm(data, prefix='rapida_ent')
    assert form.is_valid(), form.errors


# --- Formulario de radicación rápida SALIENTE ---

@pytest.fixture
def usuario_ventanilla(db):
    return User.objects.create_user('vent_rapida', password='x')


def test_rapida_saliente_rechaza_evidencia_grande(db, oficina, usuario_ventanilla):
    archivo = _archivo('evidencia.pdf', MAX_FILE_SIZE_MB + 1)
    data = {
        'rapida_sal-asunto': 'Prueba evidencia grande',
        'rapida_sal-cuerpo': 'Contenido de prueba',
        'rapida_sal-oficina_emisora': str(oficina.id),
        'rapida_sal-destinatario_texto': 'Destinatario prueba',
    }
    files = MultiValueDict({'rapida_sal-evidencia_respuesta': [archivo]})
    form = RadicacionRapidaSalienteForm(data, files, user=usuario_ventanilla, prefix='rapida_sal')
    assert not form.is_valid()
    assert any('excede el tamaño máximo' in e for e in form.errors.get('evidencia_respuesta', []))


def test_rapida_saliente_acepta_evidencia_normal(db, oficina, usuario_ventanilla):
    archivo = _archivo('evidencia.pdf', 2)
    data = {
        'rapida_sal-asunto': 'Prueba evidencia normal',
        'rapida_sal-cuerpo': 'Contenido de prueba',
        'rapida_sal-oficina_emisora': str(oficina.id),
        'rapida_sal-destinatario_texto': 'Destinatario prueba',
    }
    files = MultiValueDict({'rapida_sal-evidencia_respuesta': [archivo]})
    form = RadicacionRapidaSalienteForm(data, files, user=usuario_ventanilla, prefix='rapida_sal')
    assert form.is_valid(), form.errors
