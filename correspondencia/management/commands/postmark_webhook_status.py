from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from correspondencia.models import PostmarkWebhookEvento


class Command(BaseCommand):
    help = 'Muestra los últimos eventos webhook recibidos desde Postmark.'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='Ventana en horas (default: 24).')
        parser.add_argument('--limit', type=int, default=20, help='Máximo de filas a listar.')

    def handle(self, *args, **options):
        hours = max(1, int(options['hours']))
        limit = max(1, int(options['limit']))
        cutoff = timezone.now() - timedelta(hours=hours)

        qs = PostmarkWebhookEvento.objects.filter(recibido_at__gte=cutoff).order_by('-recibido_at')[:limit]
        total = PostmarkWebhookEvento.objects.filter(recibido_at__gte=cutoff).count()

        self.stdout.write(f'Eventos Postmark (últimas {hours}h): {total}')
        if not qs:
            self.stdout.write(self.style.WARNING('Sin eventos en la ventana indicada.'))
            return

        for evento in qs:
            self.stdout.write(
                f"  {evento.recibido_at:%Y-%m-%d %H:%M:%S} | {evento.record_type:10} | "
                f"{evento.postmark_message_id[:36]:36} | {evento.recipient or '-':30} | "
                f"proc={evento.procesado} | {evento.resultado or '-'}"
            )
