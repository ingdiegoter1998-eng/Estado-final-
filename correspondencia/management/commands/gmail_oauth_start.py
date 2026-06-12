from django.conf import settings
from django.core.management.base import BaseCommand

from correspondencia.integrations.gmail_client import GmailAPIClient


class Command(BaseCommand):
    help = 'Genera la URL de autorización OAuth 2.0 para Gmail API.'

    def add_arguments(self, parser):
        parser.add_argument('--state', default='gmail-api-correspondencia')

    def handle(self, *args, **options):
        client = GmailAPIClient(
            client_id=getattr(settings, 'GMAIL_API_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GMAIL_API_CLIENT_SECRET', ''),
            refresh_token=getattr(settings, 'GMAIL_API_REFRESH_TOKEN', ''),
            token_uri=getattr(settings, 'GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            scopes=getattr(settings, 'GMAIL_API_SCOPES', ['https://www.googleapis.com/auth/gmail.send']),
            user_id=getattr(settings, 'GMAIL_API_USER_ID', 'me'),
            redirect_uri=getattr(settings, 'GMAIL_API_REDIRECT_URI', ''),
            oauth_client_type=getattr(settings, 'GMAIL_API_OAUTH_CLIENT_TYPE', 'web'),
        )

        auth_url, state, code_verifier = client.build_authorization_url(state=options['state'])
        self.stdout.write(self.style.SUCCESS('URL de autorización generada:'))
        self.stdout.write(auth_url)
        self.stdout.write(f'State: {state}')
        self.stdout.write(f'Code verifier: {code_verifier or "(sin PKCE)"}')
        self.stdout.write(f'Redirect URI: {client.redirect_uri or "(sin redirect URI configurada)"}')
