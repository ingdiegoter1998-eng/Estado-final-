import json

from django.core.management.base import BaseCommand

from correspondencia.utils.postmark_outbound import build_postmark_outbound_status


class Command(BaseCommand):
    help = 'Verifica configuración de salida Postmark (From verificado, token, stream).'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true')
        parser.add_argument(
            '--probe-api',
            action='store_true',
            help='Consulta la API de Postmark (GET /senders) sin enviar correo.',
        )

    def handle(self, *args, **options):
        payload = build_postmark_outbound_status(probe_api=options['probe_api'])
        if options['json']:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write('=== Salida Postmark ===')
        for key in (
            'email_provider',
            'outbound_email_address',
            'postmark_message_stream',
            'postmark_token_configured',
            'postmark_verified_senders',
            'outbound_matches_verified_sender',
            'postmark_outbound_ready',
        ):
            self.stdout.write(f'{key}: {payload.get(key)}')

        issues = payload.get('postmark_outbound_issues') or []
        if issues:
            for issue in issues:
                self.stdout.write(self.style.ERROR(f'  • {issue}'))
        elif payload.get('postmark_outbound_ready'):
            self.stdout.write(self.style.SUCCESS('Salida Postmark: configuración coherente.'))

        if options['probe_api']:
            api_ok = payload.get('postmark_api_reachable')
            detail = payload.get('postmark_api_detail') or ''
            if api_ok is True:
                self.stdout.write(self.style.SUCCESS(f'API Postmark: OK — {detail}'))
            elif api_ok is False:
                self.stdout.write(self.style.ERROR(f'API Postmark: fallo — {detail}'))
            else:
                self.stdout.write(self.style.WARNING('API Postmark: no consultada (falta token o provider).'))

        if not payload.get('postmark_outbound_ready'):
            raise SystemExit(1)
