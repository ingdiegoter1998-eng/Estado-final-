import base64
import json
from email.mime.base import MIMEBase
from urllib import error, request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from correspondencia.integrations.gmail_client import GmailAPIClient


class GmailAPIEmailBackend(BaseEmailBackend):
    """Envía correos salientes usando Gmail API mediante OAuth 2.0."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.client_id = kwargs.get('client_id') or getattr(settings, 'GMAIL_API_CLIENT_ID', '')
        self.client_secret = kwargs.get('client_secret') or getattr(settings, 'GMAIL_API_CLIENT_SECRET', '')
        self.refresh_token = kwargs.get('refresh_token') or getattr(settings, 'GMAIL_API_REFRESH_TOKEN', '')
        self.token_uri = kwargs.get('token_uri') or getattr(settings, 'GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token')
        self.user_id = kwargs.get('user_id') or getattr(settings, 'GMAIL_API_USER_ID', 'me')
        self.scopes = kwargs.get('scopes') or getattr(settings, 'GMAIL_API_SCOPES', ['https://www.googleapis.com/auth/gmail.send'])
        self.client = kwargs.get('client')

    def open(self):
        if self.client is None:
            self.client = self._build_client()
        return True

    def close(self):
        return

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        self.open()
        sent_count = 0
        for message in email_messages:
            try:
                self._send(message)
                sent_count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent_count

    def _build_client(self):
        return GmailAPIClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            scopes=self.scopes,
            user_id=self.user_id,
        )

    def _send(self, message):
        mime_message = self._build_mime_message(message)
        response = self.client.send_message(mime_message)
        message.gmail_api_response = response
        return True

    def _build_mime_message(self, message):
        mime_message = message.message()
        if getattr(message, 'bcc', None) and 'Bcc' not in mime_message:
            mime_message['Bcc'] = ', '.join(message.bcc)
        return mime_message


class PostmarkEmailBackend(BaseEmailBackend):
    """Envía correos usando la API de Postmark sin tocar el flujo IMAP existente."""

    api_url = 'https://api.postmarkapp.com/email'

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.server_token = kwargs.get('server_token') or getattr(settings, 'POSTMARK_SERVER_TOKEN', '')
        self.message_stream = kwargs.get('message_stream') or getattr(settings, 'POSTMARK_MESSAGE_STREAM', 'outbound')
        self.api_url = kwargs.get('api_url') or getattr(settings, 'POSTMARK_API_URL', self.api_url)

    def open(self):
        return True

    def close(self):
        return

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.server_token:
            if self.fail_silently:
                return 0
            raise ValueError('POSTMARK_SERVER_TOKEN no está configurado.')

        sent_count = 0
        for message in email_messages:
            try:
                self._send(message)
                sent_count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent_count

    def _send(self, message):
        payload = self._build_payload(message)
        req = request.Request(
            self.api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.server_token,
            },
            method='POST',
        )

        try:
            with request.urlopen(req) as response:
                response_body = response.read().decode('utf-8')
        except error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace') if hasattr(exc, 'read') else str(exc)
            raise RuntimeError(f'Postmark rechazó el envío: {body}') from exc
        except error.URLError as exc:
            raise RuntimeError(f'No fue posible conectar con Postmark: {exc.reason}') from exc

        parsed = json.loads(response_body or '{}')
        if parsed.get('ErrorCode') not in (None, 0):
            raise RuntimeError(f"Postmark devolvió error {parsed.get('ErrorCode')}: {parsed.get('Message')}")

        message.postmark_response = parsed
        return True

    def _build_payload(self, message):
        headers = dict(getattr(message, 'extra_headers', {}) or {})
        stream = headers.pop('X-PM-Message-Stream', None) or self.message_stream

        text_body = None
        html_body = None
        if getattr(message, 'content_subtype', 'plain') == 'html':
            html_body = message.body
        else:
            text_body = message.body

        alternatives = getattr(message, 'alternatives', None) or []
        for alternative in alternatives:
            if len(alternative) >= 2 and alternative[1] == 'text/html':
                html_body = alternative[0]
            elif len(alternative) >= 2 and alternative[1] == 'text/plain':
                text_body = alternative[0]

        payload = {
            'From': message.from_email,
            'To': ','.join(message.to or []),
            'Cc': ','.join(message.cc or []),
            'Bcc': ','.join(message.bcc or []),
            'Subject': message.subject,
            'MessageStream': stream,
        }

        if text_body:
            payload['TextBody'] = text_body
        if html_body:
            payload['HtmlBody'] = html_body
        if getattr(message, 'reply_to', None):
            payload['ReplyTo'] = ','.join(message.reply_to)
        if headers:
            # Postmark rechaza explícitamente el header "To" dentro de Headers.
            # El campo 'To' del payload lo maneja Postmark por separado.
            headers_filtered = {
                name: value
                for name, value in headers.items()
                if name.lower() != 'to'
            }
            if headers_filtered:
                payload['Headers'] = [
                    {'Name': name, 'Value': value}
                    for name, value in headers_filtered.items()
                ]

        attachments = self._serialize_attachments(getattr(message, 'attachments', None) or [])
        if attachments:
            payload['Attachments'] = attachments

        return payload

    def _serialize_attachments(self, attachments):
        serialized = []
        for attachment in attachments:
            if isinstance(attachment, MIMEBase):
                content = attachment.get_payload(decode=True) or b''
                name = attachment.get_filename() or 'adjunto'
                content_type = attachment.get_content_type() or 'application/octet-stream'
            else:
                name, content, content_type = attachment
                if isinstance(content, str):
                    content = content.encode('utf-8')
                content_type = content_type or 'application/octet-stream'

            serialized.append({
                'Name': name,
                'Content': base64.b64encode(content).decode('ascii'),
                'ContentType': content_type,
            })
        return serialized


class E2ECaptureEmailBackend(BaseEmailBackend):
    """
    Backend para Playwright E2E: ejecuta el flujo Django mail sin llamar Gmail/Postmark.
    Deja atributos gmail_api_response/postmark_response para trazabilidad en aprobacion_envio.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._messages = []

    def open(self):
        return True

    def close(self):
        return

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            try:
                self._capture(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _capture(self, message):
        from email.utils import make_msgid

        fake_id = make_msgid(domain='e2e.capture.local')
        message.gmail_api_response = {'id': fake_id, 'threadId': 'e2e-capture'}
        message.postmark_response = {'MessageID': fake_id}
        self._messages.append(message)