import base64
from datetime import datetime

from correspondencia.utils.gmail_rate_limit import is_gmail_rate_limit_error, remember_gmail_rate_limit


class GmailAPIClient:
    def __init__(
        self,
        *,
        client_id,
        client_secret,
        refresh_token,
        token_uri,
        scopes,
        user_id='me',
        redirect_uri=None,
        oauth_client_type='web',
        service=None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.token_uri = token_uri
        self.scopes = scopes or ['https://www.googleapis.com/auth/gmail.send']
        self.user_id = user_id or 'me'
        self.redirect_uri = redirect_uri
        self.oauth_client_type = oauth_client_type or 'web'
        self._service = service

    @staticmethod
    def _raise_missing_dependency(package_name):
        raise RuntimeError(
            f'Faltan dependencias de Gmail API. Instala {package_name}.'
        )

    def _get_request_class(self):
        try:
            from google.auth.transport.requests import Request
        except ImportError as exc:
            self._raise_missing_dependency('google-auth, google-auth-oauthlib y google-api-python-client')
            raise exc
        return Request

    def _get_credentials_class(self):
        try:
            from google.oauth2.credentials import Credentials
        except ImportError as exc:
            self._raise_missing_dependency('google-auth, google-auth-oauthlib y google-api-python-client')
            raise exc
        return Credentials

    def _get_build_function(self):
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            self._raise_missing_dependency('google-api-python-client')
            raise exc
        return build

    def _get_flow_class(self):
        try:
            from google_auth_oauthlib.flow import Flow
        except ImportError as exc:
            self._raise_missing_dependency('google-auth-oauthlib')
            raise exc
        return Flow

    def _get_installed_app_flow_class(self):
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:
            self._raise_missing_dependency('google-auth-oauthlib')
            raise exc
        return InstalledAppFlow

    def _normalized_client_type(self):
        if self.oauth_client_type in {'installed', 'desktop'}:
            return 'installed'
        return 'web'

    def build_client_config(self):
        client_type = self._normalized_client_type()
        return {
            client_type: {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': self.token_uri,
            }
        }

    def build_authorization_url(self, state=None):
        if not self.client_id or not self.client_secret:
            raise ValueError('GMAIL_API_CLIENT_ID y GMAIL_API_CLIENT_SECRET deben estar configurados.')

        flow_class = self._get_flow_class()
        flow = flow_class.from_client_config(self.build_client_config(), scopes=self.scopes)
        if self.redirect_uri:
            flow.redirect_uri = self.redirect_uri

        auth_url, generated_state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true',
            state=state,
        )
        return auth_url, generated_state, getattr(flow, 'code_verifier', None)

    def exchange_code_for_tokens(self, code, code_verifier=None):
        if not self.client_id or not self.client_secret:
            raise ValueError('GMAIL_API_CLIENT_ID y GMAIL_API_CLIENT_SECRET deben estar configurados.')
        if not code:
            raise ValueError('Se requiere el authorization code para intercambiar tokens.')

        flow_class = self._get_flow_class()
        flow = flow_class.from_client_config(self.build_client_config(), scopes=self.scopes)
        if self.redirect_uri:
            flow.redirect_uri = self.redirect_uri
        if code_verifier:
            flow.code_verifier = code_verifier
        flow.fetch_token(code=code)

        credentials = flow.credentials
        expiry = getattr(credentials, 'expiry', None)
        if isinstance(expiry, datetime):
            expiry = expiry.isoformat()

        return {
            'token': getattr(credentials, 'token', None),
            'refresh_token': getattr(credentials, 'refresh_token', None),
            'scopes': list(getattr(credentials, 'scopes', []) or []),
            'expiry': expiry,
        }

    def run_local_server_oauth(self, host='127.0.0.1', port=0, open_browser=False):
        if not self.client_id or not self.client_secret:
            raise ValueError('GMAIL_API_CLIENT_ID y GMAIL_API_CLIENT_SECRET deben estar configurados.')

        installed_flow_class = self._get_installed_app_flow_class()
        flow = installed_flow_class.from_client_config(self.build_client_config(), scopes=self.scopes)
        credentials = flow.run_local_server(
            host=host,
            port=port,
            open_browser=open_browser,
            access_type='offline',
            prompt='consent',
        )

        expiry = getattr(credentials, 'expiry', None)
        if isinstance(expiry, datetime):
            expiry = expiry.isoformat()

        return {
            'token': getattr(credentials, 'token', None),
            'refresh_token': getattr(credentials, 'refresh_token', None),
            'scopes': list(getattr(credentials, 'scopes', []) or []),
            'expiry': expiry,
        }

    def get_credentials(self):
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise ValueError(
                'GMAIL_API_CLIENT_ID, GMAIL_API_CLIENT_SECRET y GMAIL_API_REFRESH_TOKEN deben estar configurados.'
            )

        Request = self._get_request_class()
        Credentials = self._get_credentials_class()

        credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes,
        )
        credentials.refresh(Request())
        return credentials

    def get_service(self):
        if self._service is not None:
            return self._service

        credentials = self.get_credentials()

        build = self._get_build_function()
        self._service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
        return self._service

    def send_message(self, mime_message):
        payload = {'raw': self.build_raw_message(mime_message)}
        return self.get_service().users().messages().send(userId=self.user_id, body=payload).execute()

    def get_profile(self):
        return self.get_service().users().getProfile(userId=self.user_id).execute()

    def start_watch(self, *, topic_name, label_ids=None, label_filter_action='include'):
        if not topic_name:
            raise ValueError('Se requiere GMAIL_API_PUBSUB_TOPIC para iniciar watch en Gmail API.')

        body = {'topicName': topic_name}
        if label_ids:
            body['labelIds'] = list(label_ids)
        if label_filter_action:
            body['labelFilterAction'] = str(label_filter_action).lower()

        return self.get_service().users().watch(userId=self.user_id, body=body).execute()

    def list_history(self, *, start_history_id, history_types=None, max_results=None, page_token=None):
        if not start_history_id:
            raise ValueError('Se requiere start_history_id para consultar history en Gmail API.')

        kwargs = {
            'userId': self.user_id,
            'startHistoryId': str(start_history_id),
        }
        if history_types:
            kwargs['historyTypes'] = list(history_types)
        if max_results:
            kwargs['maxResults'] = int(max_results)
        if page_token:
            kwargs['pageToken'] = page_token

        try:
            return self.get_service().users().history().list(**kwargs).execute()
        except Exception as exc:
            if is_gmail_rate_limit_error(exc):
                remember_gmail_rate_limit(exc)
            raise

    @staticmethod
    def build_raw_message(mime_message):
        if hasattr(mime_message, 'as_bytes'):
            message_bytes = mime_message.as_bytes()
        elif isinstance(mime_message, str):
            message_bytes = mime_message.encode('utf-8')
        else:
            message_bytes = bytes(mime_message)

        return base64.urlsafe_b64encode(message_bytes).decode('ascii')