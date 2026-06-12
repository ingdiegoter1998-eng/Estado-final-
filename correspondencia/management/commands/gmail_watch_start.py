from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from correspondencia.integrations.gmail_client import GmailAPIClient
from correspondencia.models import EstadoSincronizacionCorreos
from correspondencia.utils.email_provider import get_email_ingestion_sync_source


def _build_client():
    return GmailAPIClient(
        client_id=getattr(settings, 'GMAIL_API_CLIENT_ID', ''),
        client_secret=getattr(settings, 'GMAIL_API_CLIENT_SECRET', ''),
        refresh_token=getattr(settings, 'GMAIL_API_REFRESH_TOKEN', ''),
        token_uri=getattr(settings, 'GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
        scopes=getattr(settings, 'GMAIL_API_SCOPES', ['https://www.googleapis.com/auth/gmail.modify']),
        user_id=getattr(settings, 'GMAIL_API_USER_ID', 'me'),
        redirect_uri=getattr(settings, 'GMAIL_API_REDIRECT_URI', ''),
        oauth_client_type=getattr(settings, 'GMAIL_API_OAUTH_CLIENT_TYPE', 'web'),
    )


class Command(BaseCommand):
    help = 'Inicia o renueva Gmail users.watch y persiste historyId/expiración en EstadoSincronizacionCorreos.'

    def handle(self, *args, **options):
        topic_name = getattr(settings, 'GMAIL_API_PUBSUB_TOPIC', '')
        label_ids = getattr(settings, 'GMAIL_API_WATCH_LABEL_IDS', ['INBOX'])
        label_filter_action = getattr(settings, 'GMAIL_API_WATCH_LABEL_FILTER_ACTION', 'include')

        client = _build_client()
        response = client.start_watch(
            topic_name=topic_name,
            label_ids=label_ids,
            label_filter_action=label_filter_action,
        )

        sync, _ = EstadoSincronizacionCorreos.objects.get_or_create(fuente=get_email_ingestion_sync_source())
        sync.ultimo_history_id = str(response.get('historyId') or sync.ultimo_history_id or '')
        sync.watch_topic = topic_name
        sync.ultima_renovacion_watch = timezone.now()

        expiration = response.get('expiration')
        if expiration:
            sync.watch_expira_en = datetime.fromtimestamp(int(expiration) / 1000, tz=dt_timezone.utc)

        sync.save(update_fields=['ultimo_history_id', 'watch_topic', 'ultima_renovacion_watch', 'watch_expira_en', 'actualizado_en'])

        self.stdout.write(self.style.SUCCESS('Watch de Gmail API iniciado/renovado correctamente.'))
        self.stdout.write(f"historyId={sync.ultimo_history_id}")
        self.stdout.write(f"watch_topic={sync.watch_topic}")
        self.stdout.write(f"watch_expira_en={sync.watch_expira_en.isoformat() if sync.watch_expira_en else ''}")