# Tests para el módulo de correspondencia.
# Las clases de test definidas en correspondencia/tests.py se exponen aquí
# para que "python manage.py test correspondencia.tests.NombreClase" funcione
# (correspondencia.tests es este paquete, no el archivo tests.py).

import importlib.util
import sys
import os

_tests_py = os.path.join(os.path.dirname(__file__), "..", "tests.py")
_spec = importlib.util.spec_from_file_location("correspondencia._tests_loader", _tests_py)
_loader = importlib.util.module_from_spec(_spec)
_loader.__package__ = "correspondencia"  # para que "from .models" etc. resuelvan bien
_spec.loader.exec_module(_loader)
sys.modules["correspondencia._tests_loader"] = _loader

BandejaRadicacionRapidaTests = _loader.BandejaRadicacionRapidaTests
HistorialCorrespondenciaViewTests = _loader.HistorialCorrespondenciaViewTests
RadicacionRapidaEntranteFormTests = _loader.RadicacionRapidaEntranteFormTests
CorrespondenciaTipoTramiteModelTests = _loader.CorrespondenciaTipoTramiteModelTests
RadicacionRapidaEntranteEmailTests = _loader.RadicacionRapidaEntranteEmailTests

__all__ = [
    "BandejaRadicacionRapidaTests",
    "HistorialCorrespondenciaViewTests",
    "RadicacionRapidaEntranteFormTests",
    "CorrespondenciaTipoTramiteModelTests",
    "RadicacionRapidaEntranteEmailTests",
]
