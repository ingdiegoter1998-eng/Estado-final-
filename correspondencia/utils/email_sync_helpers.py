from django.conf import settings


def get_email_ingestion_provider_name():
    return getattr(settings, 'EMAIL_INGESTION_PROVIDER', 'imap').strip().lower()


def get_email_ingestion_sync_source():
    return 'GMAIL_API' if get_email_ingestion_provider_name() == 'gmail_api' else 'GMAIL_IMAP'


def is_gmail_api_ingestion():
    return get_email_ingestion_provider_name() == 'gmail_api'
