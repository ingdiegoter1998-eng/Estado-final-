"""
Settings para ejecutar tests con SQLite (sin depender de SQL Server).
Uso: python manage.py test --settings=hospital_document_management.settings_test ...
"""
from pathlib import Path

from .settings import *  # noqa: F401, F403

# Aislar tests del .env de producción (EMAIL_PROVIDER, Postmark, etc.).
EMAIL_PROVIDER = 'smtp'
POSTMARK_SERVER_TOKEN = ''
POSTMARK_WEBHOOK_ENABLED = False
POSTMARK_BOUNCES_VIA_WEBHOOK = False
OUTBOUND_EMAIL_ADDRESS = 'correspondencia@esehospitaldelsarare.gov.co'
EMAIL_HOST_USER = 'correspondencia@esehospitaldelsarare.gov.co'

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_test.sqlite3",
    },
}
