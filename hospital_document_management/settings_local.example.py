"""
Plantilla de configuración local — copiar a settings_local.py (no versionado).

    cp hospital_document_management/settings_local.example.py \\
       hospital_document_management/settings_local.py

Uso:
    DJANGO_SETTINGS_MODULE=hospital_document_management.settings_local python manage.py runserver
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_dev.sqlite3",
    }
}
