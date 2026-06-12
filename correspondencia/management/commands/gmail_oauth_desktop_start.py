from django.conf import settings
from django.core.management.base import BaseCommand

from correspondencia.integrations.gmail_client import GmailAPIClient


class Command(BaseCommand):
    help = 'Inicia el flujo OAuth de escritorio para Gmail API usando loopback localhost.'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', type=int, default=0)
        parser.add_argument(
            '--open-browser',
            action='store_true',
            help='Abre el navegador automaticamente en el host donde corre Django.',
        )

    def handle(self, *args, **options):
        client = GmailAPIClient(
            client_id=getattr(settings, 'GMAIL_API_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GMAIL_API_CLIENT_SECRET', ''),
            refresh_token=getattr(settings, 'GMAIL_API_REFRESH_TOKEN', ''),
            token_uri=getattr(settings, 'GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            scopes=getattr(settings, 'GMAIL_API_SCOPES', ['https://www.googleapis.com/auth/gmail.send']),
            user_id=getattr(settings, 'GMAIL_API_USER_ID', 'me'),
            redirect_uri=getattr(settings, 'GMAIL_API_REDIRECT_URI', ''),
            oauth_client_type='installed',
        )

        tokens = client.run_local_server_oauth(
            host=options['host'],
            port=options['port'],
            open_browser=options['open_browser'],
        )
        self.stdout.write(self.style.SUCCESS('Tokens obtenidos correctamente por flujo de escritorio.'))
        self.stdout.write(f"refresh_token={tokens.get('refresh_token') or ''}")
        self.stdout.write(f"access_token={tokens.get('token') or ''}")
        self.stdout.write(f"expiry={tokens.get('expiry') or ''}")
        self.stdout.write(f"scopes={tokens.get('scopes') or []}")