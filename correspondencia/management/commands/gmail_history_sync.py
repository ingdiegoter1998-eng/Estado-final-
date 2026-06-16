import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from correspondencia.integrations.gmail_client import GmailAPIClient
from correspondencia.models import EstadoSincronizacionCorreos
from correspondencia.utils.email_ingestion import procesar_mensaje_imap
from correspondencia.utils.email_provider import build_email_inbox_provider, get_email_ingestion_sync_source
from correspondencia.utils.gmail_history_queue import (
    clear_pending,
    get_pending_ids,
    get_target_history_id,
    mark_processed,
    merge_pending_ids,
    pending_count,
    prepend_pending,
    take_batch,
)
from correspondencia.utils.gmail_rate_limit import (
    get_gmail_rate_limit_until,
    is_gmail_rate_limit_error,
    remember_gmail_rate_limit,
)


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
    help = (
        'Sincroniza mensajes añadidos usando Gmail users.history.list desde el último historyId '
        'almacenado. Drena la cola por lotes pequeños para no saturar la cuota por usuario.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--start-history-id', default='')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--max-results', type=int, default=None)
        parser.add_argument('--fetch-batch-size', type=int, default=None)

    def handle(self, *args, **options):
        retry_after = get_gmail_rate_limit_until()
        if retry_after:
            raise CommandError(f'Gmail API en rate limit; reintentar después de {retry_after.isoformat()}')

        sync, _ = EstadoSincronizacionCorreos.objects.get_or_create(fuente=get_email_ingestion_sync_source())
        start_history_id = (options.get('start_history_id') or sync.ultimo_history_id or '').strip()
        if not start_history_id:
            raise ValueError('No hay historyId inicial. Ejecuta primero gmail_watch_start o pasa --start-history-id.')

        dry_run = bool(options.get('dry_run'))
        max_results = options.get('max_results') or getattr(settings, 'GMAIL_API_HISTORY_SYNC_MAX_RESULTS', 200)
        fetch_batch_size = options.get('fetch_batch_size') or getattr(settings, 'GMAIL_API_HISTORY_FETCH_BATCH_SIZE', 12)
        fetch_delay_ms = int(getattr(settings, 'GMAIL_API_HISTORY_FETCH_DELAY_MS', 120))
        fallback_domain = (
            getattr(settings, 'EMAIL_HOST_USER', '').split('@')[-1]
            if '@' in getattr(settings, 'EMAIL_HOST_USER', '')
            else 'local.host'
        )

        client = _build_client()
        provider = build_email_inbox_provider(provider_name='gmail_api').connect()

        latest_history_id = start_history_id
        history_ids_discovered = 0
        rate_limited = False
        fetch_omitidos = 0
        saved = 0
        duplicates = 0
        problematic = 0
        fetched = 0

        try:
            latest_history_id, history_ids_discovered = self._refresh_pending_queue(
                client,
                start_history_id=start_history_id,
                max_results=max_results,
            )

            batch_ids = take_batch(fetch_batch_size)
            messages = []
            handled_ids = []

            for index, message_id in enumerate(batch_ids):
                if index and fetch_delay_ms > 0:
                    time.sleep(fetch_delay_ms / 1000.0)

                retry_after = get_gmail_rate_limit_until()
                if retry_after:
                    prepend_pending(batch_ids[index:])
                    rate_limited = True
                    break

                try:
                    messages.extend(provider.fetch_messages_by_uids('INBOX', [message_id]))
                    fetched += 1
                    handled_ids.append(message_id)
                except Exception as exc:
                    status = getattr(getattr(exc, 'resp', None), 'status', None)
                    if status == 404:
                        fetch_omitidos += 1
                        handled_ids.append(message_id)
                        self.stdout.write(self.style.WARNING(
                            f'Mensaje Gmail no disponible; omitido del history sync: {message_id}'
                        ))
                        continue
                    if is_gmail_rate_limit_error(exc):
                        remember_gmail_rate_limit(exc)
                        prepend_pending(batch_ids[index:])
                        rate_limited = True
                        break
                    raise

            if handled_ids and not dry_run:
                mark_processed(handled_ids)

            for msg in messages:
                result = procesar_mensaje_imap(
                    msg,
                    folder_name='INBOX',
                    flow_label='gmail_history',
                    persist=not dry_run,
                    fallback_domain=fallback_domain,
                )
                if result['status'] == 'saved':
                    saved += 1
                elif result['status'] == 'duplicate':
                    duplicates += 1
                elif result['status'] == 'problematic':
                    problematic += 1

            pending_left = pending_count()
            target_history_id = get_target_history_id() or latest_history_id
            advanced_history = False

            if not dry_run and pending_left == 0 and not rate_limited:
                sync.ultimo_history_id = target_history_id
                sync.estado = 'SUCCESS'
                sync.ultimo_error = ''
                sync.ultimo_fin = timezone.now()
                sync.save(update_fields=['ultimo_history_id', 'estado', 'ultimo_error', 'ultimo_fin', 'actualizado_en'])
                clear_pending()
                advanced_history = True
            elif not dry_run and rate_limited:
                sync.estado = 'SUCCESS'
                sync.ultimo_error = (
                    f'Drenaje parcial: quedan {pending_left} mensaje(s) en cola; '
                    f'esperando cooldown Gmail API.'
                )
                sync.ultimo_fin = timezone.now()
                sync.save(update_fields=['estado', 'ultimo_error', 'ultimo_fin', 'actualizado_en'])
            elif not dry_run and pending_left > 0:
                sync.estado = 'SUCCESS'
                sync.ultimo_error = f'Drenaje parcial: quedan {pending_left} mensaje(s) en cola.'
                sync.ultimo_fin = timezone.now()
                sync.save(update_fields=['estado', 'ultimo_error', 'ultimo_fin', 'actualizado_en'])

            self.stdout.write(self.style.SUCCESS('Sincronización por history completada.'))
            self.stdout.write(f'mensajes_history_nuevos={history_ids_discovered}')
            self.stdout.write(f'mensajes_procesados_lote={len(batch_ids)}')
            self.stdout.write(f'mensajes_fetch_ok={fetched}')
            self.stdout.write(f'guardados={saved}')
            self.stdout.write(f'duplicados={duplicates}')
            self.stdout.write(f'problematicos={problematic}')
            self.stdout.write(f'omitidos_fetch={fetch_omitidos}')
            self.stdout.write(f'pendientes_cola={pending_left}')
            self.stdout.write(f'ultimo_history_id={sync.ultimo_history_id if not dry_run else start_history_id}')
            self.stdout.write(f'target_history_id={target_history_id}')
            self.stdout.write(f'history_id_avanzado={advanced_history}')
            self.stdout.write(f'rate_limited={rate_limited}')
            if dry_run:
                self.stdout.write('dry_run=true')
        finally:
            provider.logout()

    def _refresh_pending_queue(self, client, *, start_history_id: str, max_results: int) -> tuple[str, int]:
        """Consulta history.list y fusiona IDs nuevos en la cola persistente."""
        page_token = None
        latest_history_id = start_history_id
        discovered_ids = []
        seen_ids = set(get_pending_ids())

        while True:
            retry_after = get_gmail_rate_limit_until()
            if retry_after:
                raise CommandError(f'Gmail API en rate limit; reintentar después de {retry_after.isoformat()}')

            response = client.list_history(
                start_history_id=start_history_id,
                history_types=['messageAdded'],
                max_results=max_results,
                page_token=page_token,
            )
            latest_history_id = str(response.get('historyId') or latest_history_id)
            for entry in response.get('history', []) or []:
                for added in entry.get('messagesAdded', []) or []:
                    message = added.get('message', {}) or {}
                    message_id = str(message.get('id') or '')
                    if not message_id or message_id in seen_ids:
                        continue
                    # Solo bandeja de entrada: los enviados por el buzón (Fwd manuales
                    # del personal, notificaciones) no son correos entrantes.
                    label_ids = set(message.get('labelIds') or [])
                    if 'SENT' in label_ids and 'INBOX' not in label_ids:
                        seen_ids.add(message_id)
                        continue
                    seen_ids.add(message_id)
                    discovered_ids.append(message_id)
            page_token = response.get('nextPageToken')
            if not page_token:
                break

        if discovered_ids or get_target_history_id():
            merge_pending_ids(discovered_ids, target_history_id=latest_history_id)
        elif not get_pending_ids():
            merge_pending_ids([], target_history_id=latest_history_id)

        return latest_history_id, len(discovered_ids)
