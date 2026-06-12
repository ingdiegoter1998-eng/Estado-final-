from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from correspondencia.models import SalidaDestinatario
from correspondencia.utils.postmark_message_details import (
    message_ids_pendientes_sync,
    sincronizar_lote_desde_api,
)


class Command(BaseCommand):
    help = (
        'Sincroniza eventos Delivery/Bounce desde la API de Postmark para destinatarios '
        'ENVIADO sin webhook local (backfill operativo).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Ventana hacia atrás (default: 30).')
        parser.add_argument('--limit', type=int, default=50, help='Máximo de MessageIDs a consultar.')
        parser.add_argument('--dry-run', action='store_true', help='Solo listar IDs pendientes.')

    def handle(self, *args, **options):
        days = max(1, int(options['days']))
        limit = max(1, int(options['limit']))
        cutoff = timezone.now() - timedelta(days=days)

        destinatarios = list(
            SalidaDestinatario.objects.filter(
                estado='ENVIADO',
                postmark_message_id__gt='',
                fecha_envio__gte=cutoff,
            ).order_by('-fecha_envio')
        )
        pendientes = message_ids_pendientes_sync(destinatarios)
        self.stdout.write(
            f'Destinatarios ENVIADO en {days}d: {len(destinatarios)} · '
            f'MessageIDs pendientes sync: {len(pendientes)}'
        )

        if not pendientes:
            self.stdout.write(self.style.SUCCESS('Nada pendiente por sincronizar.'))
            return

        preview = pendientes[:limit]
        for message_id in preview:
            self.stdout.write(f'  - {message_id}')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run: no se consultó la API.'))
            return

        consultados = sincronizar_lote_desde_api(preview, max_fetch=limit)
        self.stdout.write(self.style.SUCCESS(f'Consultados en API Postmark: {consultados}'))
