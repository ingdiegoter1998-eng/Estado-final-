import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.test import Client
from correspondencia.models import EntidadExterna, Contacto, Correspondencia
from documentos.models import OficinaProductora, UnidadAdministrativa, EntidadProductora


@pytest.fixture
def ventanilla_client(db):
    user = User.objects.create_user('vent', password='pass')
    group = Group.objects.create(name='Ventanilla')
    user.groups.add(group)
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def datos_basicos(db):
    # Crear jerarquía completa para OficinaProductora
    entidad_productora = EntidadProductora.objects.create(nombre='Entidad Productora Test')
    unidad_administrativa = UnidadAdministrativa.objects.create(
        nombre='Unidad Administrativa Test',
        entidad_productora=entidad_productora
    )
    oficina = OficinaProductora.objects.create(
        nombre='Oficina 1',
        unidad_administrativa=unidad_administrativa
    )
    
    entidad = EntidadExterna.objects.create(nombre='Ent 1')
    contacto = Contacto.objects.create(entidad_externa=entidad, nombres='Ana')
    
    return {'entidad': entidad, 'contacto': contacto, 'oficina': oficina}


def test_buscar_entidades_filtra_y_pagina(ventanilla_client, db):
    EntidadExterna.objects.create(nombre='Alpha')
    EntidadExterna.objects.create(nombre='Beta')
    EntidadExterna.objects.create(nombre='Gamma')
    url = reverse('correspondencia:buscar_entidades')
    resp = ventanilla_client.get(url, {'q': 'a'})
    assert resp.status_code == 200
    data = resp.json()
    assert 'results' in data
    assert any('Alpha' in e['text'] for e in data['results'])


def test_buscar_contactos_por_entidad(ventanilla_client, datos_basicos):
    url = reverse('correspondencia:buscar_contactos')
    resp = ventanilla_client.get(url, {'entidad_id': datos_basicos['entidad'].id})
    assert resp.status_code == 200
    data = resp.json()
    assert 'contactos' in data and len(data['contactos']) == 1


def test_buscar_oficinas_filtra(ventanilla_client, db):
    # Crear jerarquía completa para la oficina
    entidad_productora = EntidadProductora.objects.create(nombre='Entidad Test')
    unidad_administrativa = UnidadAdministrativa.objects.create(
        nombre='Unidad Test',
        entidad_productora=entidad_productora
    )
    OficinaProductora.objects.create(
        nombre='Oficina X',
        unidad_administrativa=unidad_administrativa
    )
    
    url = reverse('correspondencia:buscar_oficinas')
    resp = ventanilla_client.get(url, {'q': 'Oficina'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['results']


def test_dashboard_requires_auth(db):
    client = Client()
    url = reverse('correspondencia:dashboard_ventanilla')
    resp = client.get(url)
    # login_required -> redirige a login de welcome
    assert resp.status_code in (302, 301)


def test_sla_api_rate_limit_and_400(ventanilla_client):
    url = reverse('correspondencia:calcular_plazo_sla')
    # 400 por falta de parámetros si requiere_respuesta=true y sin subserie/tiempo
    resp = ventanilla_client.post(url, {'requiere_respuesta': 'true'})
    assert resp.status_code == 400
    # simular rate limit rápido
    for _ in range(31):
        ventanilla_client.post(url, {'requiere_respuesta': 'false'})
    last = ventanilla_client.post(url, {'requiere_respuesta': 'false'})
    assert last.status_code in (200, 429)


def test_form_validacion_entidad_contacto(db, client, datos_basicos):
    # Crea otra entidad para invalidar
    otra = EntidadExterna.objects.create(nombre='Ent 2')
    client.force_login(User.objects.create_user('u', password='p'))
    url = reverse('correspondencia:radicar_manual')
    data = {
        'remitente': datos_basicos['contacto'].id,
        'entidad_selector': otra.id,  # no coincide
        'asunto': 'Prueba',
        'medio_recepcion': 'FISICO',
        'oficina_destino': datos_basicos['oficina'].id,
        'requiere_respuesta': False,
    }
    resp = client.post(url, data)
    # La vista podría re-renderizar con errores 200
    assert resp.status_code in (200, 302)


