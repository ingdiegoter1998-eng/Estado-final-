"""Utilidades compartidas para la tubería operativa Gmail API (watch, Pub/Sub, history)."""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from correspondencia.models import EstadoSincronizacionCorreos
from correspondencia.utils.email_sync_helpers import get_email_ingestion_sync_source
from correspondencia.utils.gmail_rate_limit import (
    celery_gmail_api_tasks_paused,
    get_gmail_rate_limit_until,
    gmail_rate_limit_message,
    is_gmail_rate_limit_error,
    remember_gmail_rate_limit,
)
from correspondencia.utils.postmark_outbound import build_postmark_outbound_status


@dataclass
class GmailPipelineResult:
    status: str
    summary: dict
    output: str

    def as_control_payload(self):
        return {
            'status': self.status,
            'summary': self.summary,
            'output': self.output,
            'metrics': {'total_errores': 0 if self.status != 'FAIL' else 1},
        }


def _capture_command_output(command: str, **kwargs) -> str:
    buffer = StringIO()
    call_command(command, stdout=buffer, **kwargs)
    return buffer.getvalue().strip()


def get_sync_state():
    return EstadoSincronizacionCorreos.objects.filter(fuente=get_email_ingestion_sync_source()).first()


def _runtime_database_info() -> dict:
    db = settings.DATABASES['default']
    engine = db.get('ENGINE', '')
    is_sqlite = 'sqlite' in engine.lower()
    return {
        'database_engine': engine.rsplit('.', 1)[-1] if engine else '',
        'database_name': str(db.get('NAME', '')),
        'database_host': str(db.get('HOST', '') or ''),
        'is_production_database': not is_sqlite,
        'django_settings_module': os.environ.get('DJANGO_SETTINGS_MODULE', ''),
        'django_debug': settings.DEBUG,
    }


def _gmail_profile_email() -> tuple[str, str]:
    """Devuelve (email_vinculado, error)."""
    if not getattr(settings, 'GMAIL_API_REFRESH_TOKEN', ''):
        return '', 'GMAIL_API_REFRESH_TOKEN no configurado'
    cooldown_message = gmail_rate_limit_message('Consulta de perfil omitida por rate limit Gmail API')
    if cooldown_message:
        return '', cooldown_message
    try:
        from correspondencia.integrations.gmail_client import GmailAPIClient

        client = GmailAPIClient(
            client_id=getattr(settings, 'GMAIL_API_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GMAIL_API_CLIENT_SECRET', ''),
            refresh_token=getattr(settings, 'GMAIL_API_REFRESH_TOKEN', ''),
            token_uri=getattr(settings, 'GMAIL_API_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            scopes=getattr(settings, 'GMAIL_API_SCOPES', []),
        )
        profile = client.get_service().users().getProfile(userId='me').execute()
        return profile.get('emailAddress', '') or '', ''
    except Exception as exc:
        if is_gmail_rate_limit_error(exc):
            remember_gmail_rate_limit(exc)
        return '', str(exc)


def build_operational_status() -> dict:
    sync = get_sync_state()
    now = timezone.now()
    rate_limit_until = get_gmail_rate_limit_until()
    watch_expires_soon = False
    watch_missing = False
    if sync:
        if not sync.watch_topic or not sync.ultimo_history_id:
            watch_missing = True
        if sync.watch_expira_en and sync.watch_expira_en <= now + timedelta(hours=24):
            watch_expires_soon = True
    project_id = getattr(settings, 'GCP_PROJECT_ID', '')
    client_id = getattr(settings, 'GMAIL_API_CLIENT_ID', '')
    outbound_address = getattr(settings, 'OUTBOUND_EMAIL_ADDRESS', '')
    cuenta_institucional_pendiente = not (
        project_id == 'correspondencia-django'
        and client_id.startswith('454105653873-')
        and outbound_address == 'correspondencia@esehospitaldelsarare.gov.co'
    )
    gmail_profile_email, gmail_profile_error = _gmail_profile_email()
    runtime = _runtime_database_info()
    postmark = build_postmark_outbound_status()
    return {
        'ingestion_provider': getattr(settings, 'EMAIL_INGESTION_PROVIDER', 'imap'),
        'email_provider': getattr(settings, 'EMAIL_PROVIDER', 'smtp'),
        'postmark_outbound_ready': postmark.get('postmark_outbound_ready'),
        'postmark_outbound_issues': postmark.get('postmark_outbound_issues'),
        'outbound_matches_verified_sender': postmark.get('outbound_matches_verified_sender'),
        'sync_fuente': get_email_ingestion_sync_source(),
        'ultimo_history_id': sync.ultimo_history_id if sync else '',
        'watch_topic': sync.watch_topic if sync else '',
        'watch_expira_en': sync.watch_expira_en.isoformat() if sync and sync.watch_expira_en else '',
        'ultima_renovacion_watch': sync.ultima_renovacion_watch.isoformat() if sync and sync.ultima_renovacion_watch else '',
        'sync_estado': sync.estado if sync else 'SIN_REGISTRO',
        'sync_ultimo_error': sync.ultimo_error if sync else '',
        'watch_expires_soon': watch_expires_soon,
        'watch_missing': watch_missing,
        'pubsub_subscription': getattr(settings, 'GMAIL_API_PUBSUB_SUBSCRIPTION', ''),
        'pubsub_credentials_file': getattr(settings, 'GMAIL_API_PUBSUB_CREDENTIALS_FILE', ''),
        'cuenta_institucional_pendiente': cuenta_institucional_pendiente,
        'outbound_email_address': outbound_address,
        'gmail_profile_email': gmail_profile_email,
        'gmail_profile_error': gmail_profile_error,
        'gmail_rate_limit_until': rate_limit_until.isoformat() if rate_limit_until else '',
        'celery_gmail_api_tasks_paused': celery_gmail_api_tasks_paused(),
        **runtime,
    }


def renew_watch_if_needed(*, force: bool = False, hours_before: int | None = None) -> GmailPipelineResult:
    hours_before = hours_before or int(getattr(settings, 'GMAIL_API_WATCH_RENEW_HOURS_BEFORE', 24))
    sync = get_sync_state()
    now = timezone.now()

    should_renew = force
    if not should_renew and sync and sync.watch_expira_en:
        should_renew = sync.watch_expira_en <= now + timedelta(hours=hours_before)
    elif not should_renew and (not sync or not sync.watch_topic or not sync.ultimo_history_id):
        should_renew = True

    if not should_renew:
        return GmailPipelineResult(
            status='SUCCESS',
            summary={'renovado': False, 'motivo': 'watch_vigente'},
            output='Watch vigente; no se requiere renovación.',
        )

    output = _capture_command_output('gmail_watch_start')
    sync = get_sync_state()
    summary = {
        'renovado': True,
        'history_id': sync.ultimo_history_id if sync else '',
        'watch_expira_en': sync.watch_expira_en.isoformat() if sync and sync.watch_expira_en else '',
    }
    return GmailPipelineResult(status='SUCCESS', summary=summary, output=output)


def run_pubsub_pull(*, max_messages: int | None = None) -> GmailPipelineResult:
    max_messages = max_messages or int(getattr(settings, 'GMAIL_API_PUBSUB_PULL_MAX_MESSAGES', 10))
    cooldown_message = gmail_rate_limit_message()
    if cooldown_message:
        return GmailPipelineResult(
            status='WARN',
            summary={'history_ids': [], 'max_messages': max_messages, 'rate_limited': True},
            output=cooldown_message,
        )
    output = _capture_command_output('gmail_pubsub_pull', max_messages=max_messages)
    history_ids = []
    for line in output.splitlines():
        if line.startswith('history_ids='):
            try:
                history_ids = ast.literal_eval(line.split('=', 1)[1].strip())
            except Exception:
                history_ids = []
    rate_limited = 'rate_limited=True' in output or 'no se hace ack' in output
    status = 'SUCCESS' if (
        'Consumo Pub/Sub completado' in output
        or 'Sin mensajes Pub/Sub pendientes' in output
    ) else 'WARN'
    if rate_limited:
        status = 'WARN'
    return GmailPipelineResult(
        status=status,
        summary={'history_ids': history_ids, 'max_messages': max_messages, 'rate_limited': rate_limited},
        output=output,
    )


def run_history_sync(*, dry_run: bool = False) -> GmailPipelineResult:
    cooldown_message = gmail_rate_limit_message()
    if cooldown_message:
        return GmailPipelineResult(
            status='WARN',
            summary={'dry_run': dry_run, 'rate_limited': True},
            output=cooldown_message,
        )
    kwargs = {'dry_run': True} if dry_run else {}
    output = _capture_command_output('gmail_history_sync', **kwargs)
    status = 'SUCCESS' if 'Sincronización por history completada' in output else 'FAIL'
    return GmailPipelineResult(status=status, summary={'dry_run': dry_run}, output=output)


def run_pipeline_tick(*, renew_watch: bool = True, pubsub_pull: bool = True) -> GmailPipelineResult:
    lines = []
    summaries = {}
    status = 'SUCCESS'

    if renew_watch:
        renew_result = renew_watch_if_needed()
        lines.append('[watch]')
        lines.append(renew_result.output)
        summaries['watch'] = renew_result.summary
        if renew_result.status == 'FAIL':
            status = 'FAIL'

    if pubsub_pull and status != 'FAIL':
        pull_result = run_pubsub_pull()
        lines.append('[pubsub_pull]')
        lines.append(pull_result.output)
        summaries['pubsub_pull'] = pull_result.summary
        if pull_result.status == 'FAIL':
            status = 'FAIL'
        elif pull_result.status == 'WARN' and status == 'SUCCESS':
            status = 'WARN'

    return GmailPipelineResult(status=status, summary=summaries, output='\n'.join(lines))
