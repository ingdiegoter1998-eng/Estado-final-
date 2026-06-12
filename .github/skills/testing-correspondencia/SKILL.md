# Skill: Testing del Proyecto de Correspondencia

## Para que Existe

Estandarizar la forma de escribir, ejecutar y mantener tests automatizados en el proyecto
de correspondencia del Hospital E.S.E. Saravena. Aplica cuando se necesita:

- Escribir tests nuevos para cualquier feature
- Diagnosticar o arreglar tests rotos
- Correr la suite de tests o generar cobertura
- Agregar fixtures o datos de prueba
- Configurar o depurar la infraestructura de testing

**Palabras clave:** test, pytest, fixture, cobertura, coverage, assert, mock, TestCase,
conftest, TDD, prueba, pruebas, testing

## Stack de Testing

| Capa | Herramienta | Propósito |
|---|---|---|
| Unit / Integration | **pytest 9.0.2** + **pytest-django 4.12.0** | Runner principal |
| Cobertura | **pytest-cov 7.0.0** | Reportes coverage |
| Base de datos test | **SQLite** via `settings_test.py` | Rápido, sin SQL Server |
| Datos ficticios | **Faker 37.1.0** | Generación de datos aleatorios |
| E2E (opcional) | **Playwright** | Tests de navegador |
| Mocking | `unittest.mock` (stdlib) | Mockear I/O externo |

## Configuración Activa

### pytest.ini (única config válida)

```ini
[pytest]
DJANGO_SETTINGS_MODULE = hospital_document_management.settings_test
python_files = test_*.py *_tests.py
testpaths = correspondencia/tests documentos
addopts =
  --reuse-db
  --nomigrations
  --tb=short
  -q
```

Flags clave:
- `--nomigrations`: NO ejecuta migraciones, crea tablas directamente → evita bugs de data migrations en SQLite
- `--reuse-db`: Reutiliza la BD de test entre corridas → velocidad
- Settings: `settings_test.py` usa SQLite → no requiere SQL Server

### settings_test.py

Importa todo desde `settings.py` y sobreescribe DATABASES a SQLite:

```python
from .settings import *
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_test.sqlite3",
    },
}
```

## Estructura de Archivos

```
conftest.py                           ← fixtures globales (usuarios, oficinas, entidades)
correspondencia/
  tests.py                            ← monolítico legacy (NO descubierto por pytest)
  tests/
    __init__.py                       ← re-exporta clases de tests.py para manage.py test
    conftest.py                       ← fixtures de correspondencia (radicados, correos)
    test_views_coverage.py            ← tests de vistas
    test_procesar_emails_celery.py    ← tests de tareas Celery
    test_procesar_rebotes.py          ← tests de rebotes DSN
    test_comunicaciones_internas.py   ← tests de comunicaciones internas
    test_chatbot_mvp.py               ← tests del chatbot IA
    test_watchdog_inbox.py            ← tests del watchdog
    test_manual_radicacion_form.py    ← tests de formulario de radicación
    ...
    e2e/                              ← Playwright E2E tests
documentos/
  tests.py                            ← tests de oficinas y préstamos documentales
```

## Fixtures Disponibles

### Globales (conftest.py raíz)

| Fixture | Retorna | Depende de |
|---|---|---|
| `ventanilla_group` | Group "Ventanilla" | `db` |
| `admin_group` | Group "Admin" | `db` |
| `ventanilla_user` | User con grupo Ventanilla | `ventanilla_group` |
| `admin_user` | User staff con grupo Admin | `admin_group` |
| `regular_user` | User sin grupo (para tests de acceso) | `db` |
| `entidad_productora` | EntidadProductora | `db` |
| `unidad_administrativa` | UnidadAdministrativa | `entidad_productora` |
| `proceso` | Proceso + MacroProceso | `db` |
| `oficina` | OficinaProductora "Oficina Test" | `unidad_administrativa`, `proceso` |
| `oficina_secundaria` | OficinaProductora "Oficina Jurídica" | `unidad_administrativa`, `proceso` |
| `entidad_externa` | EntidadExterna | `db` |
| `contacto` | Contacto con correo | `entidad_externa` |
| `serie` | SerieDocumental | `db` |
| `subserie` | SubserieDocumental | `serie` |
| `perfil_ventanilla` | PerfilUsuario (ventanilla + oficina) | `ventanilla_user`, `oficina` |
| `auth_client` | Client con sesión ventanilla | `ventanilla_user` |
| `admin_client_logged` | Client con sesión admin | `admin_user` |

### De correspondencia (correspondencia/tests/conftest.py)

| Fixture | Retorna | Depende de |
|---|---|---|
| `correspondencia_entrante` | Correspondencia tipo ENTRADA radicada | `contacto`, `oficina`, `ventanilla_user`, `serie`, `subserie` |
| `correo_entrante` | CorreoEntrante sin procesar | `db` |
| `correo_procesado` | CorreoEntrante procesado vinculado a radicado | `correo_entrante`, `correspondencia_entrante` |

## Cómo Escribir un Test Nuevo

### Reglas obligatorias

1. **Archivo**: Crear en `correspondencia/tests/test_<modulo>.py`
2. **Estilo**: Funciones pytest con fixtures inyectados (NO clases TestCase para tests nuevos)
3. **Nombre**: `test_<qué_hace>` — descriptivo, en español está bien
4. **Mock**: Todo I/O externo se mockea (IMAP, SMTP, Celery `.delay()`, APIs externas)
5. **Assertions**: Usar `assert` nativo de pytest (no `self.assertEqual`)
6. **Imports**: Imports de modelos al inicio del archivo, imports de fixtures por nombre

### Plantilla de test nuevo

```python
"""Tests para <descripción del módulo>."""
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse

from correspondencia.models import Correspondencia, HistorialCorrespondencia


class TestRadicacionEntrante:
    """Tests de radicación de correspondencia entrante."""

    def test_radicar_crea_historial(self, auth_client, oficina, contacto, serie, subserie):
        """Radicar correspondencia entrante genera registro de historial."""
        data = {
            "tipo_radicado": "ENTRADA",
            "asunto": "Solicitud de prueba",
            "remitente": contacto.pk,
            "oficina_destino": oficina.pk,
            "serie": serie.pk,
            "subserie": subserie.pk,
        }
        response = auth_client.post(reverse("correspondencia:radicar"), data)
        assert response.status_code == 302
        assert HistorialCorrespondencia.objects.filter(evento="RADICACION").exists()

    def test_sin_ventanilla_redirige_a_welcome(self, regular_user):
        """Usuario sin grupo Ventanilla no puede radicar."""
        from django.test import Client
        c = Client()
        c.force_login(regular_user)
        response = c.get(reverse("correspondencia:radicar"))
        assert response.status_code == 302
        assert "welcome" in response.url


class TestProcesamientoCorreo:
    """Tests de ingesta de correos IMAP."""

    @patch("correspondencia.utils.email_ingestion.imaplib.IMAP4_SSL")
    def test_correo_nuevo_se_guarda_en_bd(self, mock_imap, db):
        """Un correo leído por IMAP se persiste como CorreoEntrante."""
        from correspondencia.models import CorreoEntrante
        # ... configurar mock_imap ...
        assert CorreoEntrante.objects.filter(message_id="<test@example.com>").exists()
```

### Lo que NO hacer

- **NO usar `setUp()`/`tearDown()`** en tests nuevos → usar fixtures
- **NO crear objetos que ya existen como fixtures** (usuarios, oficinas, etc.)
- **NO hacer queries a SQL Server** → todo corre contra SQLite
- **NO dejar tests que hacen I/O real** (IMAP, email, HTTP) → mockear
- **NO importar `from django.test import TestCase`** en tests nuevos → usar clases planas o funciones

### Excepción: tests legacy con TestCase

Los tests existentes que usan `TestCase` con `setUp()` funcionan perfectamente con pytest.
No es necesario migrarlos. Solo aplicar el estándar nuevo a tests **nuevos**.

## Cómo Ejecutar Tests

```bash
# Activar entorno
source venv/bin/activate

# Correr TODOS los tests
pytest

# Correr un archivo específico
pytest correspondencia/tests/test_views_coverage.py

# Correr un test o clase específica
pytest correspondencia/tests/test_views_coverage.py::TestRadicacionVistas::test_home_redirige_sin_login

# Correr tests que matcheen un nombre
pytest -k "rebote"
pytest -k "radicacion and not email"

# Con cobertura (no activada por defecto para velocidad)
pytest --cov=correspondencia --cov-report=term-missing

# Cobertura con reporte HTML
pytest --cov=correspondencia --cov-report=html:reports/coverage_html

# Ver tests descubiertos sin ejecutar
pytest --co -q

# Solo tests marcados
pytest -m "not slow"
```

## Cómo Mockear Componentes Comunes

### Celery tasks (evitar ejecución real)

```python
from unittest.mock import patch, MagicMock

@patch("correspondencia.views.procesar_emails_periodico")
def test_encola_tarea(mock_task, auth_client):
    mock_task.delay = MagicMock()
    response = auth_client.get(reverse("correspondencia:procesar_emails_manual"))
    mock_task.delay.assert_called_once()
```

### IMAP (sin conexión real a Gmail)

```python
@patch("correspondencia.management.commands.procesar_emails_seguro.imaplib.IMAP4_SSL")
def test_procesa_correo(mock_imap_class, db):
    mock_mail = MagicMock()
    mock_imap_class.return_value = mock_mail
    mock_mail.search.return_value = ("OK", [b"1"])
    mock_mail.fetch.return_value = ("OK", [(b"1", b"raw email bytes")])
    # ... resto del test
```

### Gemini API (chatbot sin llamada real)

```python
@patch("correspondencia.rag.gemini_client.genai.GenerativeModel")
def test_chatbot_responde(mock_model, auth_client):
    mock_model.return_value.generate_content.return_value.text = "Respuesta de prueba"
    # ... test del endpoint de chat
```

## Markers Disponibles

```python
@pytest.mark.slow        # Tests que tardan >5s
@pytest.mark.sqlserver   # Tests que requieren SQL Server real
@pytest.mark.e2e         # Tests Playwright (E2E)
```

Para excluir tests lentos: `pytest -m "not slow"`

## Diagnóstico de Problemas Comunes

### "ContentType.DoesNotExist" en migraciones

**Causa**: Una data migration hace `.get()` de ContentType que no existe en SQLite fresco.
**Solución**: Ya corregido en migración 0071 con `try/except`. Si aparece en otra migración,
aplicar el mismo patrón. El flag `--nomigrations` también lo evita.

### Tests tardan mucho en iniciar

**Causa**: Sin `--reuse-db`, pytest crea la BD from scratch cada corrida.
**Solución**: `--reuse-db` está activo en `pytest.ini`. Si cambió un modelo, forzar
recreación con `pytest --create-db`.

### Colisión entre `tests.py` y `tests/`

El archivo `correspondencia/tests.py` (monolítico) y el paquete `correspondencia/tests/`
coexisten. `pytest.ini` solo descubre `correspondencia/tests/` (el paquete).
Para correr los tests legacy del monolítico con `manage.py test`, el `__init__.py`
del paquete los re-exporta con un hack de importlib.

### "Module not found" al importar

Verificar que `DJANGO_SETTINGS_MODULE` apunta a `hospital_document_management.settings_test`.
Si se usa `manage.py test`, pasar `--settings=hospital_document_management.settings_test`.

### Tests pasan en local pero fallan en otro entorno

Verificar que el entorno tiene:
- `pytest`, `pytest-django`, `pytest-cov` instalados (están en `requirements.txt`)
- El ODBC driver para SQL Server NO es necesario para tests (usa SQLite)
- `db_test.sqlite3` puede borrarse sin miedo (se recrea con `--create-db`)

## Checklist para Agregar Tests a una Feature Nueva

- [ ] Crear `correspondencia/tests/test_<feature>.py`
- [ ] Usar fixtures del conftest, no crear objetos duplicados
- [ ] Mockear todo I/O externo
- [ ] Verificar que `pytest correspondencia/tests/test_<feature>.py` pasa
- [ ] Si el test necesita datos complejos reutilizables, agregar fixture a `conftest.py`
- [ ] Si el test tarda >5s, marcarlo con `@pytest.mark.slow`

## Archivos Clave

| Archivo | Propósito |
|---|---|
| `pytest.ini` | Config principal de pytest |
| `conftest.py` (raíz) | Fixtures globales |
| `correspondencia/tests/conftest.py` | Fixtures de correspondencia |
| `hospital_document_management/settings_test.py` | Settings con SQLite para tests |
| `correspondencia/tests/` | Directorio principal de tests |
| `reports/` | Output de coverage y JUnit XML |
