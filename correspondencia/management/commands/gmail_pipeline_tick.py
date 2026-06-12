from django.core.management.base import BaseCommand

from correspondencia.utils.gmail_pipeline import run_pipeline_tick


class Command(BaseCommand):
    help = (
        'Ejecuta un ciclo operativo Gmail API: renovar watch si corresponde y consumir Pub/Sub. '
        'Pensado para cron en dev/staging sin depender de Celery Beat.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--skip-watch', action='store_true')
        parser.add_argument('--skip-pubsub', action='store_true')

    def handle(self, *args, **options):
        result = run_pipeline_tick(
            renew_watch=not options['skip_watch'],
            pubsub_pull=not options['skip_pubsub'],
        )
        self.stdout.write(result.output)
        if result.status == 'SUCCESS':
            self.stdout.write(self.style.SUCCESS(f'Pipeline Gmail API OK ({result.summary})'))
        elif result.status == 'WARN':
            self.stdout.write(self.style.WARNING(f'Pipeline Gmail API con advertencias ({result.summary})'))
        else:
            self.stdout.write(self.style.ERROR(f'Pipeline Gmail API falló ({result.summary})'))
            raise SystemExit(1)
