import base64
import email.utils as email_utils
import imaplib
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
from email import message_from_bytes, policy
from functools import partial

from django.conf import settings
from imap_tools import AND, MailBox, MailMessageFlags

from correspondencia.integrations.gmail_client import GmailAPIClient
from correspondencia.utils.gmail_rate_limit import is_gmail_rate_limit_error, remember_gmail_rate_limit


@dataclass
class NormalizedAttachment:
    filename: str
    payload: bytes
    content_type: str = 'application/octet-stream'
    content_id: str = ''


@dataclass
class NormalizedEmailMessage:
    uid: str
    headers: dict = field(default_factory=dict)
    date: datetime | None = None
    from_: str = ''
    subject: str = ''
    attachments: list = field(default_factory=list)
    text: str = ''
    html: str = ''
    obj: object | None = None
    raw_bytes: bytes | None = None


def _normalize_headers(headers):
    normalized = {}
    for key, value in (headers or {}).items():
        header_key = str(key).lower()
        if isinstance(value, list):
            normalized[header_key] = [str(item) for item in value if item is not None]
        elif value is None:
            normalized[header_key] = []
        else:
            normalized[header_key] = [str(value)]
    return normalized


def _parsed_header_datetime(value, fallback=None):
    if not value:
        return fallback
    try:
        parsed = email_utils.parsedate_to_datetime(value)
    except Exception:
        return fallback
    if parsed is None:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt_timezone.utc)
    return parsed


def _extract_text_and_html(email_obj):
    text_parts = []
    html_parts = []
    for part in email_obj.walk():
        if part.is_multipart():
            continue
        if (part.get_content_disposition() or '').lower() == 'attachment':
            continue
        content_type = (part.get_content_type() or '').lower()
        payload = part.get_payload(decode=True)
        if payload is None:
            payload = part.get_payload()
        if isinstance(payload, bytes):
            charset = part.get_content_charset() or 'utf-8'
            try:
                content = payload.decode(charset, errors='replace')
            except LookupError:
                content = payload.decode('utf-8', errors='replace')
        else:
            content = str(payload or '')
        content = content.strip()
        if not content:
            continue
        if content_type == 'text/plain':
            text_parts.append(content)
        elif content_type == 'text/html':
            html_parts.append(content)
    return '\n\n'.join(text_parts), '\n\n'.join(html_parts)


def _extract_attachments(email_obj):
    attachments = []
    for index, part in enumerate(email_obj.walk()):
        if part.is_multipart():
            continue
        filename = part.get_filename() or ''
        disposition = (part.get_content_disposition() or '').lower()
        if disposition != 'attachment' and not filename:
            continue
        payload = part.get_payload(decode=True) or b''
        attachments.append(
            NormalizedAttachment(
                filename=filename or f'adjunto_{index + 1}',
                payload=payload,
                content_type=part.get_content_type() or 'application/octet-stream',
                content_id=part.get('Content-ID', '') or '',
            )
        )
    return attachments


def normalize_imap_message(msg):
    headers = _normalize_headers(getattr(msg, 'headers', {}) or {})
    return NormalizedEmailMessage(
        uid=str(getattr(msg, 'uid', '')),
        headers=headers,
        date=getattr(msg, 'date', None),
        from_=getattr(msg, 'from_', '') or (headers.get('from') or [''])[0],
        subject=getattr(msg, 'subject', '') or (headers.get('subject') or [''])[0],
        attachments=list(getattr(msg, 'attachments', None) or []),
        text=getattr(msg, 'text', '') or '',
        html=getattr(msg, 'html', '') or '',
        obj=getattr(msg, 'obj', None),
        raw_bytes=getattr(msg, 'raw_bytes', None),
    )


def _decode_gmail_raw(raw_value):
    padded = raw_value + '=' * (-len(raw_value) % 4)
    return base64.urlsafe_b64decode(padded.encode('ascii'))


def normalize_gmail_message(message_id, payload, *, raw_bytes=None, internal_date=None):
    email_obj = None
    if raw_bytes:
        email_obj = message_from_bytes(raw_bytes, policy=policy.default)
    headers = {}
    if email_obj is not None:
        for key, value in email_obj.items():
            headers.setdefault(str(key).lower(), []).append(str(value))
    elif payload:
        for item in payload.get('headers', []) or []:
            key = str(item.get('name', '')).lower()
            headers.setdefault(key, []).append(str(item.get('value', '')))

    fallback_date = None
    if internal_date:
        try:
            fallback_date = datetime.fromtimestamp(int(internal_date) / 1000, tz=dt_timezone.utc)
        except Exception:
            fallback_date = None
    parsed_date = _parsed_header_datetime((headers.get('date') or [''])[0] if headers.get('date') else None, fallback=fallback_date)

    attachments = _extract_attachments(email_obj) if email_obj is not None else []
    text_body, html_body = _extract_text_and_html(email_obj) if email_obj is not None else ('', '')

    return NormalizedEmailMessage(
        uid=str(message_id),
        headers=headers,
        date=parsed_date,
        from_=(headers.get('from') or [''])[0],
        subject=(headers.get('subject') or [''])[0],
        attachments=attachments,
        text=text_body,
        html=html_body,
        obj=email_obj,
        raw_bytes=raw_bytes,
    )


class IMAPMailboxProvider:
    """Wrapper mínimo para desacoplar el acceso IMAP del comando de recepción."""

    def __init__(
        self,
        *,
        server,
        port,
        account,
        password,
        initial_folder='INBOX',
        timeout=30,
        mailbox_factory=MailBox,
        imap_factory=imaplib.IMAP4_SSL,
    ):
        self.server = server
        self.port = port
        self.account = account
        self.password = password
        self.initial_folder = initial_folder
        self.timeout = timeout
        self.mailbox_factory = mailbox_factory
        self.imap_factory = imap_factory
        self._mailbox = None

    def connect(self):
        mailbox = self.mailbox_factory(self.server)
        mailbox._factory = partial(self.imap_factory, self.server, self.port, timeout=self.timeout)
        mailbox.login(self.account, self.password, initial_folder=self.initial_folder)
        self._mailbox = mailbox
        return self

    def set_folder(self, folder_name):
        self._require_mailbox().folder.set(folder_name)

    def fetch_headers(self, folder_name, *, date_gte):
        self.set_folder(folder_name)
        return [
            normalize_imap_message(message)
            for message in self.fetch(AND(date_gte=date_gte), mark_seen=False, bulk=True, headers_only=True)
        ]

    def fetch_messages_by_uids(self, folder_name, uids):
        self.set_folder(folder_name)
        if not uids:
            return []
        uid_str = ','.join(str(uid) for uid in uids)
        return [
            normalize_imap_message(message)
            for message in self.fetch(AND(uid=uid_str), mark_seen=False, bulk=True)
        ]

    def mark_seen(self, uid):
        return self.flag(uid, MailMessageFlags.SEEN, True)

    def fetch_message_by_message_id(self, message_id):
        search_mid = f'<{message_id}>' if message_id and not str(message_id).startswith('<') else str(message_id)
        for folder in ['INBOX', '[Gmail]/Todos']:
            try:
                self.set_folder(folder)
                results = list(self.fetch(AND(header=[('Message-ID', search_mid)]), mark_seen=False, bulk=True))
                if results:
                    return normalize_imap_message(results[0])
            except Exception:
                continue
        return None

    def fetch_unread_messages(self, folder_name):
        self.set_folder(folder_name)
        return [
            normalize_imap_message(message)
            for message in self.fetch(AND(seen=False), mark_seen=False, bulk=True)
        ]

    def fetch_messages_since(self, folder_name, *, date_gte):
        self.set_folder(folder_name)
        return [
            normalize_imap_message(message)
            for message in self.fetch(AND(date_gte=date_gte), mark_seen=False, bulk=True)
        ]

    def mark_seen_many(self, uids):
        if not uids:
            return None
        return self.flag(list(uids), [r'\Seen'], True)

    def fetch(self, criteria, *, mark_seen=False, bulk=True, headers_only=False):
        return self._require_mailbox().fetch(
            criteria,
            mark_seen=mark_seen,
            bulk=bulk,
            headers_only=headers_only,
        )

    def flag(self, uid, flag, value):
        return self._require_mailbox().flag(uid, flag, value)

    def list_folders(self):
        return self._require_mailbox().folder.list()

    def logout(self):
        if self._mailbox is not None:
            self._mailbox.logout()

    def _require_mailbox(self):
        if self._mailbox is None:
            raise RuntimeError('El proveedor IMAP aún no está conectado.')
        return self._mailbox


class GmailAPIInboxProvider:
    """Proveedor de recepción usando Gmail API con mensajes normalizados."""

    def __init__(self, *, client, user_id='me', email_account=''):
        self.client = client
        self.user_id = user_id or 'me'
        self.email_account = (email_account or '').lower()
        self._service = None

    def connect(self):
        self._service = self.client.get_service()
        return self

    def _execute(self, request):
        try:
            return request.execute()
        except Exception as exc:
            if is_gmail_rate_limit_error(exc):
                remember_gmail_rate_limit(exc)
            raise

    def fetch_headers(self, folder_name, *, date_gte):
        messages = []
        for message_id in self._list_message_ids(folder_name, query_parts=[f'after:{date_gte.strftime("%Y/%m/%d")}']):
            data = self._execute(self._service.users().messages().get(
                userId=self.user_id,
                id=message_id,
                format='metadata',
                metadataHeaders=['Message-ID', 'Date', 'From', 'Subject'],
            ))
            messages.append(
                normalize_gmail_message(
                    message_id,
                    data.get('payload', {}),
                    internal_date=data.get('internalDate'),
                )
            )
        return messages

    def fetch_messages_by_uids(self, folder_name, uids):
        messages = []
        for uid in uids:
            data = self._execute(self._service.users().messages().get(
                userId=self.user_id,
                id=str(uid),
                format='raw',
            ))
            raw_bytes = _decode_gmail_raw(data.get('raw', ''))
            messages.append(
                normalize_gmail_message(
                    str(uid),
                    data.get('payload', {}),
                    raw_bytes=raw_bytes,
                    internal_date=data.get('internalDate'),
                )
            )
        return messages

    def mark_seen(self, uid):
        return self._execute(self._service.users().messages().modify(
            userId=self.user_id,
            id=str(uid),
            body={'removeLabelIds': ['UNREAD']},
        ))

    def fetch_message_by_message_id(self, message_id):
        response = self._execute(self._service.users().messages().list(
            userId=self.user_id,
            q=f'in:anywhere rfc822msgid:{message_id}',
            includeSpamTrash=False,
        ))
        messages = response.get('messages', []) or []
        if not messages:
            return None
        gmail_message_id = messages[0]['id']
        data = self._execute(self._service.users().messages().get(
            userId=self.user_id,
            id=gmail_message_id,
            format='raw',
        ))
        raw_bytes = _decode_gmail_raw(data.get('raw', ''))
        return normalize_gmail_message(
            gmail_message_id,
            data.get('payload', {}),
            raw_bytes=raw_bytes,
            internal_date=data.get('internalDate'),
        )

    def fetch_unread_messages(self, folder_name):
        message_ids = self._list_message_ids(folder_name, query_parts=['is:unread'])
        return self.fetch_messages_by_uids(folder_name, message_ids)

    def fetch_messages_since(self, folder_name, *, date_gte):
        message_ids = self._list_message_ids(folder_name, query_parts=[f'after:{date_gte.strftime("%Y/%m/%d")}'])
        return self.fetch_messages_by_uids(folder_name, message_ids)

    def mark_seen_many(self, uids):
        for uid in uids or []:
            self.mark_seen(uid)

    def list_folders(self):
        return self._service.users().labels().list(userId=self.user_id).execute().get('labels', [])

    def logout(self):
        return

    def _list_message_ids(self, folder_name, *, query_parts, max_messages=None):
        label_ids = self._label_ids_for_folder(folder_name)
        effective_query_parts = list(query_parts or [])
        if folder_name == '[Gmail]/Todos':
            effective_query_parts.insert(0, 'in:anywhere')
        max_messages = int(max_messages or getattr(settings, 'GMAIL_API_MAX_SCAN_MESSAGES', 300))
        page_token = None
        collected = []
        while True:
            remaining = max_messages - len(collected)
            if remaining <= 0:
                break

            response = self._execute(self._service.users().messages().list(
                userId=self.user_id,
                labelIds=label_ids,
                q=' '.join(effective_query_parts),
                pageToken=page_token,
                maxResults=min(500, remaining),
                includeSpamTrash=False,
            ))
            collected.extend(item['id'] for item in response.get('messages', []) or [])
            if len(collected) >= max_messages:
                break
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        return collected

    def _label_ids_for_folder(self, folder_name):
        if folder_name == 'INBOX':
            return ['INBOX']
        if folder_name == '[Gmail]/Todos':
            return None
        labels = self.list_folders()
        for label in labels:
            if label.get('name') == folder_name:
                return [label.get('id')]
        return ['INBOX']


def build_email_inbox_provider(*, mailbox_factory=MailBox, imap_factory=imaplib.IMAP4_SSL, gmail_client_cls=GmailAPIClient, provider_name=None):
    provider_name = (provider_name or getattr(settings, 'EMAIL_INGESTION_PROVIDER', 'imap')).strip().lower()
    if provider_name == 'gmail_api':
        client = gmail_client_cls(
            client_id=getattr(settings, 'GMAIL_API_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GMAIL_API_CLIENT_SECRET', ''),
            refresh_token=getattr(settings, 'GMAIL_API_REFRESH_TOKEN', ''),
            token_uri=getattr(settings, 'GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            scopes=getattr(settings, 'GMAIL_API_SCOPES', ['https://www.googleapis.com/auth/gmail.modify']),
            user_id=getattr(settings, 'GMAIL_API_USER_ID', 'me'),
            redirect_uri=getattr(settings, 'GMAIL_API_REDIRECT_URI', ''),
            oauth_client_type=getattr(settings, 'GMAIL_API_OAUTH_CLIENT_TYPE', 'web'),
        )
        return GmailAPIInboxProvider(
            client=client,
            user_id=getattr(settings, 'GMAIL_API_USER_ID', 'me'),
            email_account=getattr(settings, 'EMAIL_HOST_USER', ''),
        )

    return IMAPMailboxProvider(
        server=getattr(settings, 'IMAP_SERVER', 'imap.gmail.com'),
        port=getattr(settings, 'IMAP_PORT', 993),
        account=getattr(settings, 'EMAIL_HOST_USER', ''),
        password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
        initial_folder='INBOX',
        timeout=30,
        mailbox_factory=mailbox_factory,
        imap_factory=imap_factory,
    )


def get_email_ingestion_provider_name():
    return getattr(settings, 'EMAIL_INGESTION_PROVIDER', 'imap').strip().lower()


def get_email_ingestion_sync_source():
    return 'GMAIL_API' if get_email_ingestion_provider_name() == 'gmail_api' else 'GMAIL_IMAP'