import json
import re
import socket
from datetime import timedelta
from io import StringIO

from celery import current_app
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import Count, Max
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from .models import CorreoEntrante, EstadoSincronizacionCorreos
from .tasks import _EMAIL_LOCK_KEY, procesar_emails_periodico
from .utils.email_provider import build_email_inbox_provider, get_email_ingestion_provider_name, get_email_ingestion_sync_source


def dumps_payload(payload):
    return json.dumps(payload or {}, ensure_ascii=False, default=str, indent=2)


def loads_payload(payload, default=None):
    if not payload:
        return {} if default is None else default
    try:
        return json.loads(payload)
    except Exception:
        return {} if default is None else default


def parse_procesar_emails_output(output):
    summary = {
        'folders': {},
        'total_encontrados': 0,
        'total_nuevos': 0,
        'total_guardados': 0,
        'total_rechazados': 0,
        'total_adjuntos': 0,
        'errores': [],
    }

    found_pattern = re.compile(r'Correos encontrados en (?P<folder>.+?): (?P<count>\d+)')
    new_pattern = re.compile(r'Correos NUEVOS en (?P<folder>.+?): (?P<count>\d+)')
    total_new_pattern = re.compile(r'Total correos NUEVOS a procesar: (?P<count>\d+)')
    saved_pattern = re.compile(r'Correos guardados: (?P<count>\d+)')
    rejected_pattern = re.compile(r'Correos rechazados por seguridad: (?P<count>\d+)')
    attachments_pattern = re.compile(r'Adjuntos guardados: (?P<count>\d+)')

    for line in output.splitlines():
        found_match = found_pattern.search(line)
        if found_match:
            folder = found_match.group('folder')
            count = int(found_match.group('count'))
            summary['folders'].setdefault(folder, {})['encontrados'] = count
            summary['total_encontrados'] += count
            continue

        new_match = new_pattern.search(line)
        if new_match:
            folder = new_match.group('folder')
            count = int(new_match.group('count'))
            summary['folders'].setdefault(folder, {})['nuevos'] = count
            continue

        total_new_match = total_new_pattern.search(line)
        if total_new_match:
            summary['total_nuevos'] = int(total_new_match.group('count'))
            continue

        saved_match = saved_pattern.search(line)
        if saved_match:
            summary['total_guardados'] = int(saved_match.group('count'))
            continue

        rejected_match = rejected_pattern.search(line)
        if rejected_match:
            summary['total_rechazados'] = int(rejected_match.group('count'))
            continue

        attachments_match = attachments_pattern.search(line)
        if attachments_match:
            summary['total_adjuntos'] = int(attachments_match.group('count'))
            continue

        if 'Error ' in line or 'ERROR' in line or 'Error:' in line:
            summary['errores'].append(line.strip())

    return summary


def _normalize_range_parameters(parameters):
    since_raw = parameters.get('since')
    until_raw = parameters.get('until')

    since_dt = parse_datetime(since_raw) if since_raw else None
    until_dt = parse_datetime(until_raw) if until_raw else None

    if since_dt and timezone.is_naive(since_dt):
        since_dt = timezone.make_aware(since_dt, timezone.get_current_timezone())
    if until_dt and timezone.is_naive(until_dt):
        until_dt = timezone.make_aware(until_dt, timezone.get_current_timezone())

    return since_dt, until_dt


def run_verify_or_recovery(days, recover=False, since_dt=None, until_dt=None):
    buffer = StringIO()
    command_kwargs = {
        'recovery': True,
        'dry_run': not recover,
        'days': days,
        'stdout': buffer,
    }
    if since_dt:
        command_kwargs['since'] = since_dt.isoformat()
    if until_dt:
        command_kwargs['until'] = until_dt.isoformat()

    call_command(
        'procesar_emails_seguro',
        **command_kwargs,
    )
    output = buffer.getvalue()
    summary = parse_procesar_emails_output(output)
    summary['days'] = days
    summary['mode'] = 'recovery' if recover else 'verify'
    summary['since'] = since_dt
    summary['until'] = until_dt
    status = 'WARN' if summary['errores'] else 'SUCCESS'
    return {
        'status': status,
        'summary': summary,
        'output': output,
        'metrics': {
            'total_encontrados': summary['total_encontrados'],
            'total_nuevos': summary['total_nuevos'],
            'total_guardados': summary['total_guardados'],
            'total_rechazados': summary['total_rechazados'],
            'total_adjuntos': summary['total_adjuntos'],
            'total_errores': len(summary['errores']),
        },
    }


def run_duplicate_check(days, since_dt=None, until_dt=None):
    queryset = CorreoEntrante.objects.all()
    output_lines = []
    if since_dt or until_dt:
        if since_dt:
            queryset = queryset.filter(fecha_lectura_imap__gte=since_dt)
        if until_dt:
            queryset = queryset.filter(fecha_lectura_imap__lte=until_dt)
        output_lines.append(
            'Verificación de duplicados en rango exacto: '
            f"desde {timezone.localtime(since_dt).strftime('%d/%m/%Y %H:%M:%S') if since_dt else 'inicio abierto'} "
            f"hasta {timezone.localtime(until_dt).strftime('%d/%m/%Y %H:%M:%S') if until_dt else 'fin abierto'}."
        )
    elif days:
        since = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(fecha_lectura_imap__gte=since)
        output_lines.append(f'Verificación de duplicados en los últimos {days} día(s).')
    else:
        output_lines.append('Verificación de duplicados sobre toda la bandeja almacenada.')

    total = queryset.count()
    exact_dups = list(
        queryset.values('message_id')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
        .order_by('-c', 'message_id')[:20]
    )
    suspect_dups = list(
        queryset.values('remitente', 'asunto', 'fecha_recibida_gmail')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
        .order_by('-c', 'remitente', 'asunto')[:20]
    )

    output_lines.append(f'Total correos revisados: {total}')
    output_lines.append(f'Duplicados reales por message_id: {len(exact_dups)} grupo(s)')
    for item in exact_dups:
        output_lines.append(f"  - {item['message_id']}: {item['c']} registros")

    output_lines.append(f'Sospechosos por remitente/asunto/fecha: {len(suspect_dups)} grupo(s)')
    for item in suspect_dups:
        asunto = (item['asunto'] or '(Sin asunto)')[:120]
        output_lines.append(
            f"  - {item['remitente']} | {asunto} | {item['fecha_recibida_gmail']}: {item['c']} registros"
        )

    status = 'WARN' if exact_dups else 'SUCCESS'
    summary = {
        'total_revisados': total,
        'duplicados_reales': exact_dups,
        'sospechosos': suspect_dups,
    }
    return {
        'status': status,
        'summary': summary,
        'output': '\n'.join(output_lines),
        'metrics': {
            'total_duplicados': len(exact_dups),
            'total_sospechosos': len(suspect_dups),
            'total_errores': 0,
        },
    }


def run_pipeline_diagnosis():
    output_lines = []
    inspect = current_app.control.inspect(timeout=5)

    stats = inspect.stats() or {}
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}

    sync_state = EstadoSincronizacionCorreos.objects.filter(fuente=get_email_ingestion_sync_source()).first()
    ultimo_fetch = CorreoEntrante.objects.aggregate(ultima=Max('fecha_lectura_imap'))['ultima']
    lock_value = cache.get(_EMAIL_LOCK_KEY)

    output_lines.append(f'Nodos Celery disponibles: {len(stats)}')
    output_lines.append(f'Tareas activas reportadas: {sum(len(items) for items in active.values())}')
    output_lines.append(f'Tareas reservadas reportadas: {sum(len(items) for items in reserved.values())}')

    if sync_state:
        output_lines.append(
            f"Estado sincronización: {sync_state.estado} | inicio={sync_state.ultimo_inicio} | fin={sync_state.ultimo_fin}"
        )
        if sync_state.ultimo_error:
            output_lines.append(f'Último error: {sync_state.ultimo_error}')
    else:
        output_lines.append('Estado sincronización: sin registro en BD')

    output_lines.append(f'Último correo guardado en BD: {ultimo_fetch}')
    output_lines.append(f'Lock de procesamiento activo: {'sí' if lock_value else 'no'}')

    warnings = []
    if not stats:
        warnings.append('Celery no respondió al inspect')
    if sync_state and sync_state.estado == 'RUNNING' and sync_state.ultimo_inicio:
        delta = timezone.now() - sync_state.ultimo_inicio
        if delta.total_seconds() > 600:
            warnings.append('Sincronización marcada RUNNING por más de 10 minutos')
    if lock_value:
        warnings.append('Lock de correos sigue activo')

    if warnings:
        output_lines.append('Advertencias detectadas:')
        output_lines.extend(f'  - {warning}' for warning in warnings)

    return {
        'status': 'WARN' if warnings else 'SUCCESS',
        'summary': {
            'nodos_celery': len(stats),
            'tareas_activas': sum(len(items) for items in active.values()),
            'tareas_reservadas': sum(len(items) for items in reserved.values()),
            'estado_sincronizacion': sync_state.estado if sync_state else 'SIN_REGISTRO',
            'ultimo_fetch': ultimo_fetch,
            'lock_activo': bool(lock_value),
            'warnings': warnings,
        },
        'output': '\n'.join(output_lines),
        'metrics': {
            'total_errores': len(warnings),
        },
    }


def run_sync_now():
    async_result = procesar_emails_periodico.delay()
    summary = {
        'mensaje': 'Sincronización inmediata encolada',
        'task_id': async_result.id,
    }
    return {
        'status': 'SUCCESS',
        'summary': summary,
        'output': f"Sincronización de correos encolada en Celery con task_id={async_result.id}",
        'metrics': {
            'total_errores': 0,
        },
    }


def run_gmail_pubsub_pull_operation():
    from .utils.gmail_pipeline import run_pubsub_pull

    result = run_pubsub_pull()
    return result.as_control_payload()


def run_gmail_watch_renew_operation():
    from .utils.gmail_pipeline import renew_watch_if_needed

    result = renew_watch_if_needed(force=True)
    return result.as_control_payload()


def run_gmail_history_sync_operation():
    from .utils.gmail_pipeline import run_history_sync

    result = run_history_sync()
    return result.as_control_payload()


def run_gmail_pipeline_tick_operation():
    from .utils.gmail_pipeline import run_pipeline_tick

    result = run_pipeline_tick()
    return result.as_control_payload()


def run_gmail_status_operation():
    from .utils.gmail_pipeline import build_operational_status

    payload = build_operational_status()
    lines = [f'{key}: {value}' for key, value in payload.items()]
    warnings = []
    if payload.get('watch_missing'):
        warnings.append('Watch no inicializado')
    if payload.get('watch_expires_soon'):
        warnings.append('Watch expira en menos de 24 horas')
    if warnings:
        lines.extend(['Advertencias:'] + [f'  - {item}' for item in warnings])
    return {
        'status': 'WARN' if warnings else 'SUCCESS',
        'summary': payload,
        'output': '\n'.join(lines),
        'metrics': {'total_errores': len(warnings)},
    }


def run_imap_smoke_test():
    started = timezone.now()
    mailbox = None
    output_lines = []
    previous_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(30)
        provider_name = get_email_ingestion_provider_name()
        mailbox = build_email_inbox_provider().connect()
        raw_folders = list(mailbox.list_folders())[:10]
        folders = [getattr(folder, 'name', None) or folder.get('name', str(folder)) for folder in raw_folders]
        elapsed = (timezone.now() - started).total_seconds()
        output_lines.append(f'Conexión {provider_name} exitosa en {elapsed:.2f}s')
        output_lines.append(f'Orígenes visibles: {", ".join(folders)}')
        return {
            'status': 'SUCCESS',
            'summary': {
                'provider': provider_name,
                'tiempo_respuesta_segundos': round(elapsed, 2),
                'carpetas': folders,
            },
            'output': '\n'.join(output_lines),
            'metrics': {'total_errores': 0},
        }
    finally:
        socket.setdefaulttimeout(previous_timeout)
        if mailbox:
            try:
                mailbox.logout()
            except Exception:
                pass


def execute_control_operation(operation_type, parameters):
    days = int(parameters.get('days') or 1)
    since_dt, until_dt = _normalize_range_parameters(parameters)

    if operation_type == 'VERIFY':
        return run_verify_or_recovery(days=days, recover=False, since_dt=since_dt, until_dt=until_dt)
    if operation_type == 'RECOVER':
        return run_verify_or_recovery(days=days, recover=True, since_dt=since_dt, until_dt=until_dt)
    if operation_type == 'DUPLICATES':
        return run_duplicate_check(days=days, since_dt=since_dt, until_dt=until_dt)
    if operation_type == 'DIAGNOSE':
        return run_pipeline_diagnosis()
    if operation_type == 'SYNC_NOW':
        return run_sync_now()
    if operation_type == 'IMAP_TEST':
        return run_imap_smoke_test()
    if operation_type == 'GMAIL_PUBSUB_PULL':
        return run_gmail_pubsub_pull_operation()
    if operation_type == 'GMAIL_WATCH_RENEW':
        return run_gmail_watch_renew_operation()
    if operation_type == 'GMAIL_HISTORY_SYNC':
        return run_gmail_history_sync_operation()
    if operation_type == 'GMAIL_PIPELINE_TICK':
        return run_gmail_pipeline_tick_operation()
    if operation_type == 'GMAIL_STATUS':
        return run_gmail_status_operation()

    raise ValueError(f'Operación no soportada: {operation_type}')