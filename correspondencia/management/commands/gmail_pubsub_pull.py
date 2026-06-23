import json
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from correspondencia.models import EstadoSincronizacionCorreos
from correspondencia.utils.email_sync_helpers import get_email_ingestion_sync_source
from correspondencia.utils.gmail_history_queue import merge_pending_ids
from correspondencia.utils.gmail_rate_limit import get_gmail_rate_limit_until

try:
    from google.cloud.pubsub_v1 import SubscriberClient
    from google.oauth2 import service_account
except ImportError:  # pragma: no cover - cubierto por validación de entorno/comando
    SubscriberClient = None
    service_account = None


class Command(BaseCommand):
    help = 'Consume notificaciones Gmail watch desde una suscripción Pub/Sub por pull y dispara gmail_history_sync.'

    def add_arguments(self, parser):
        parser.add_argument('--max-messages', type=int, default=10)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--no-ack', action='store_true')

    def handle(self, *args, **options):
        if SubscriberClient is None:
            raise RuntimeError('Falta google-cloud-pubsub. Instálalo para consumir notificaciones Pub/Sub.')

        subscription = getattr(settings, 'GMAIL_API_PUBSUB_SUBSCRIPTION', '')
        if not subscription:
            raise ValueError('Se requiere GMAIL_API_PUBSUB_SUBSCRIPTION para consumir Pub/Sub.')

        max_messages = int(options.get('max_messages') or 10)
        dry_run = bool(options.get('dry_run'))
        do_ack = not bool(options.get('no_ack'))

        subscriber = self._build_subscriber_client()
        response = subscriber.pull(subscription=subscription, max_messages=max_messages)
        received_messages = list(response.received_messages or [])
        if not received_messages:
            self.stdout.write('Sin mensajes Pub/Sub pendientes.')
            return

        ack_ids = []
        history_ids = []
        for received in received_messages:
            ack_ids.append(received.ack_id)
            try:
                payload = json.loads(received.message.data.decode('utf-8'))
            except Exception:
                payload = {}
            history_id = str(payload.get('historyId') or '').strip()
            if history_id:
                history_ids.append(history_id)

        max_history_id = max(history_ids, key=int) if history_ids else ''
        if max_history_id and not dry_run:
            sync, _ = EstadoSincronizacionCorreos.objects.get_or_create(
                fuente=get_email_ingestion_sync_source(),
            )
            start_history_id = (sync.ultimo_history_id or '').strip()
            merge_pending_ids([], target_history_id=max_history_id)
            self.stdout.write(
                f'history_checkpoint_persistido={max_history_id} '
                f'(desde ultimo_history_id={start_history_id or "vacío"})'
            )

        read_cooldown = get_gmail_rate_limit_until('read')
        sync_output = ''
        rate_limited = bool(read_cooldown)

        if read_cooldown:
            self.stdout.write(self.style.WARNING(
                f'Pub/Sub recibió {len(received_messages)} mensaje(s); Gmail API en cooldown de lectura. '
                f'Sync diferido; checkpoint persistido. Reintentar después de {read_cooldown.isoformat()}'
            ))
        else:
            from io import StringIO

            sync_buffer = StringIO()
            call_command('gmail_history_sync', dry_run=dry_run, stdout=sync_buffer)
            sync_output = sync_buffer.getvalue()
            rate_limited = 'rate_limited=True' in sync_output

            if rate_limited:
                self.stdout.write(self.style.WARNING(
                    'History sync detenido por rate limit Gmail API durante el drenaje.'
                ))
                self.stdout.write(sync_output)

        if do_ack and ack_ids and not dry_run:
            subscriber.acknowledge(subscription=subscription, ack_ids=ack_ids)

        if sync_output.strip() and not rate_limited:
            self.stdout.write(sync_output)

        self.stdout.write(self.style.SUCCESS('Consumo Pub/Sub completado.'))
        self.stdout.write(f'mensajes_pubsub={len(received_messages)}')
        self.stdout.write(f'history_ids={history_ids}')
        self.stdout.write(f'ack={do_ack and not dry_run}')
        self.stdout.write(f'rate_limited={rate_limited}')

    def _build_subscriber_client(self):
        credentials_file = getattr(settings, 'GMAIL_API_PUBSUB_CREDENTIALS_FILE', '').strip()
        if not credentials_file:
            credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '').strip()

        if credentials_file:
            if service_account is None:
                raise RuntimeError('Falta google-cloud-pubsub/google-auth para credenciales de service account.')
            if not os.path.isfile(credentials_file):
                raise ValueError(
                    f'No existe el archivo de credenciales Pub/Sub: {credentials_file}. '
                    'Crea una service account con rol Pub/Sub Subscriber, descarga el JSON y configura '
                    'GMAIL_API_PUBSUB_CREDENTIALS_FILE o GOOGLE_APPLICATION_CREDENTIALS.'
                )
            credentials = service_account.Credentials.from_service_account_file(credentials_file)
            return SubscriberClient(credentials=credentials)

        return SubscriberClient()
