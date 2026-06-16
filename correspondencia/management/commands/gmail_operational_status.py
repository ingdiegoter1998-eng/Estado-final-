import json

from django.conf import settings
from django.core.management.base import BaseCommand

from correspondencia.utils.gmail_pipeline import build_operational_status


class Command(BaseCommand):
    help = 'Muestra el estado operativo de Gmail API (watch, history, Pub/Sub, proveedores).'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        payload = build_operational_status()
        if options['json']:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write('=== Estado operativo Gmail API ===')
        for key, value in payload.items():
            self.stdout.write(f'{key}: {value}')
        if getattr(settings, 'EMAIL_PROVIDER', '').strip().lower() == 'postmark':
            if payload.get('postmark_outbound_ready'):
                self.stdout.write(self.style.SUCCESS('Salida Postmark: From y token coherentes.'))
            else:
                for issue in payload.get('postmark_outbound_issues') or []:
                    self.stdout.write(self.style.ERROR(f'Postmark salida: {issue}'))
                self.stdout.write(
                    self.style.WARNING('Corrija OUTBOUND_EMAIL_ADDRESS (Sender Signature) y reinicie Gunicorn/Celery.')
                )
        if payload.get('celery_gmail_api_tasks_paused'):
            self.stdout.write(self.style.WARNING(
                'Celery: tareas Gmail API pausadas (CELERY_PAUSE_GMAIL_API_TASKS=true). '
                'Use SMTP/IMAP manual; reactive cuando pase el rate limit.'
            ))
        if payload.get('watch_missing'):
            self.stdout.write(self.style.WARNING('Watch no inicializado o incompleto → ejecutar gmail_watch_start'))
        if payload.get('watch_expires_soon'):
            self.stdout.write(self.style.WARNING('Watch expira en <24h → se renovará con gmail_pipeline_tick'))
        if payload.get('cuenta_institucional_pendiente'):
            self.stdout.write(self.style.WARNING('Cuenta institucional: pendiente para go-live hospital'))
        else:
            self.stdout.write(self.style.SUCCESS('Cuenta institucional: configurada para go-live hospital'))
        if not payload.get('is_production_database'):
            self.stdout.write(self.style.WARNING(
                f"Base de datos NO producción: {payload.get('database_engine')} "
                f"({payload.get('database_name')}) — settings={payload.get('django_settings_module')}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Base de datos producción: {payload.get('database_name')} @ {payload.get('database_host')}"
            ))
        profile = payload.get('gmail_profile_email') or ''
        if profile:
            self.stdout.write(self.style.SUCCESS(f'Cuenta Gmail OAuth vinculada: {profile}'))
        elif payload.get('gmail_profile_error'):
            self.stdout.write(self.style.WARNING(f'Gmail OAuth: {payload.get("gmail_profile_error")}'))
