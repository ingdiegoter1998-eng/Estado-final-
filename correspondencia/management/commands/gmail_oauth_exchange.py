from django.conf import settings
from django.core.management.base import BaseCommand

from correspondencia.integrations.gmail_client import GmailAPIClient


class Command(BaseCommand):
    help = 'Intercambia el authorization code de OAuth 2.0 por token y refresh token de Gmail API.'

    def add_arguments(self, parser):
        parser.add_argument('--code', required=True)
        parser.add_argument('--code-verifier', default=None)

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

        tokens = client.exchange_code_for_tokens(options['code'], code_verifier=options.get('code_verifier'))
        self.stdout.write(self.style.SUCCESS('Tokens obtenidos correctamente.'))
        self.stdout.write(f"refresh_token={tokens.get('refresh_token') or ''}")
        self.stdout.write(f"access_token={tokens.get('token') or ''}")
        self.stdout.write(f"expiry={tokens.get('expiry') or ''}")
        self.stdout.write(f"scopes={tokens.get('scopes') or []}")