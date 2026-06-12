"""
Fixtures compartidos para toda la suite de tests.

Uso: pytest descubre este archivo automáticamente.
Los fixtures definidos aquí están disponibles en TODOS los tests del proyecto.
"""
import pytest
from django.contrib.auth.models import User, Group


# ---------------------------------------------------------------------------
# Usuarios y grupos
# ---------------------------------------------------------------------------

@pytest.fixture
def ventanilla_group(db):
    """Grupo 'Ventanilla' — requerido para acceder a radicación y procesamiento."""
    return Group.objects.get_or_create(name="Ventanilla")[0]


@pytest.fixture
def admin_group(db):
    return Group.objects.get_or_create(name="Admin")[0]


@pytest.fixture
def ventanilla_user(db, ventanilla_group):
    """Usuario con rol Ventanilla — el más usado en tests de correspondencia."""
    user = User.objects.create_user("ventanilla", password="test123")
    user.groups.add(ventanilla_group)
    return user


@pytest.fixture
def admin_user(db, admin_group):
    user = User.objects.create_user("admin", password="test123", is_staff=True)
    user.groups.add(admin_group)
    return user


@pytest.fixture
def regular_user(db):
    """Usuario sin grupo especial — para tests de acceso denegado."""
    return User.objects.create_user("usuario_regular", password="test123")


# ---------------------------------------------------------------------------
# Jerarquía organizacional
# ---------------------------------------------------------------------------

@pytest.fixture
def entidad_productora(db):
    from documentos.models import EntidadProductora
    return EntidadProductora.objects.create(nombre="ESE Sarare Test")


@pytest.fixture
def unidad_administrativa(db, entidad_productora):
    from documentos.models import UnidadAdministrativa
    return UnidadAdministrativa.objects.create(
        nombre="Unidad Test", entidad_productora=entidad_productora
    )


@pytest.fixture
def proceso(db):
    from documentos.models import MacroProceso, Proceso
    macro = MacroProceso.objects.create(numero=1, nombre="Macro Test")
    return Proceso.objects.create(numero=1, nombre="Proceso Test", sigla="PT", macroproceso=macro)


@pytest.fixture
def oficina(db, unidad_administrativa, proceso):
    """Oficina productora principal para tests."""
    from documentos.models import OficinaProductora
    return OficinaProductora.objects.create(
        nombre="Oficina Test",
        unidad_administrativa=unidad_administrativa,
        proceso=proceso,
    )


@pytest.fixture
def oficina_secundaria(db, unidad_administrativa, proceso):
    from documentos.models import OficinaProductora
    return OficinaProductora.objects.create(
        nombre="Oficina Jurídica",
        unidad_administrativa=unidad_administrativa,
        proceso=proceso,
    )


# ---------------------------------------------------------------------------
# Entidades y contactos externos
# ---------------------------------------------------------------------------

@pytest.fixture
def entidad_externa(db):
    from correspondencia.models import EntidadExterna
    return EntidadExterna.objects.create(nombre="Entidad Externa Test")


@pytest.fixture
def contacto(db, entidad_externa):
    from correspondencia.models import Contacto
    return Contacto.objects.create(
        entidad_externa=entidad_externa,
        nombres="Juan",
        apellidos="Pérez",
        correo_electronico="juan@test.com",
    )


# ---------------------------------------------------------------------------
# TRD (Series / Subseries)
# ---------------------------------------------------------------------------

@pytest.fixture
def serie(db):
    from documentos.models import SerieDocumental
    return SerieDocumental.objects.create(nombre="Serie Test", codigo="SERIE-001")


@pytest.fixture
def subserie(db, serie):
    from documentos.models import SubserieDocumental
    return SubserieDocumental.objects.create(
        nombre="Subserie Test", codigo="SUBSERIE-001", serie=serie
    )


# ---------------------------------------------------------------------------
# Perfiles de usuario con oficina asignada
# ---------------------------------------------------------------------------

@pytest.fixture
def perfil_ventanilla(db, ventanilla_user, oficina):
    from documentos.models import PerfilUsuario
    return PerfilUsuario.objects.create(user=ventanilla_user, oficina=oficina)


# ---------------------------------------------------------------------------
# Clients autenticados (atajos para tests de vistas)
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client(ventanilla_user):
    """Django test client con sesión de usuario Ventanilla."""
    from django.test import Client
    c = Client()
    c.force_login(ventanilla_user)
    return c


@pytest.fixture
def admin_client_logged(admin_user):
    """Django test client con sesión de admin."""
    from django.test import Client
    c = Client()
    c.force_login(admin_user)
    return c
