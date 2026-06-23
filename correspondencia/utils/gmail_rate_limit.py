"""Helpers para respetar cooldowns de Gmail API cuando devuelve 429."""

from __future__ import annotations

import re
from datetime import timedelta, timezone as dt_timezone

from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime


GMAIL_API_RATE_LIMIT_CACHE_KEY = 'correspondencia:gmail_api_rate_limit_until'
GMAIL_API_RATE_LIMIT_CACHE_KEY_READ = 'correspondencia:gmail_api_rate_limit_until:read'
GMAIL_API_RATE_LIMIT_CACHE_KEY_SEND = 'correspondencia:gmail_api_rate_limit_until:send'
_VALID_SCOPES = frozenset({'read', 'send'})
_RETRY_AFTER_RE = re.compile(r'Retry after\s+([0-9T:\.\-+Z]+)', re.IGNORECASE)
# Margen extra tras el Retry-After de Google (cache expiraba antes que el bloqueo real).
DEFAULT_COOLDOWN_BUFFER_SECONDS = 120


def _cooldown_buffer_seconds() -> int:
    from django.conf import settings

    return int(getattr(settings, 'GMAIL_API_RATE_LIMIT_COOLDOWN_BUFFER_SECONDS', DEFAULT_COOLDOWN_BUFFER_SECONDS))


def _cache_key_for_scope(scope: str) -> str:
    if scope not in _VALID_SCOPES:
        raise ValueError(f'scope Gmail API inválido: {scope!r}')
    if scope == 'send':
        return GMAIL_API_RATE_LIMIT_CACHE_KEY_SEND
    return GMAIL_API_RATE_LIMIT_CACHE_KEY_READ


def _as_aware(dt):
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt, dt_timezone.utc)
    return dt


def parse_gmail_retry_after(value) -> timezone.datetime | None:
    """Extrae el timestamp `Retry after` del error textual de Gmail API."""
    if not value:
        return None
    match = _RETRY_AFTER_RE.search(str(value))
    if not match:
        return None
    raw = match.group(1).replace('Z', '+00:00')
    return _as_aware(parse_datetime(raw))


def remember_gmail_rate_limit(exc_or_text, *, fallback_seconds: int = 900, scope: str = 'read'):
    """Guarda en cache hasta cuándo se debe evitar llamar Gmail API para un scope."""
    now = timezone.now()
    retry_after = parse_gmail_retry_after(exc_or_text) or (now + timedelta(seconds=fallback_seconds))
    if retry_after <= now:
        retry_after = now + timedelta(seconds=fallback_seconds)
    retry_after = retry_after + timedelta(seconds=_cooldown_buffer_seconds())

    timeout = max(1, int((retry_after - now).total_seconds()))
    cache_key = _cache_key_for_scope(scope)
    cache.set(cache_key, retry_after.isoformat(), timeout=timeout)
    # Compatibilidad: lectura también en la clave legacy usada antes del desacople.
    if scope == 'read':
        cache.set(GMAIL_API_RATE_LIMIT_CACHE_KEY, retry_after.isoformat(), timeout=timeout)
    return retry_after


def get_gmail_rate_limit_until(scope: str = 'read'):
    cache_key = _cache_key_for_scope(scope)
    value = cache.get(cache_key)
    if not value and scope == 'read':
        value = cache.get(GMAIL_API_RATE_LIMIT_CACHE_KEY)
    if not value:
        return None
    retry_after = _as_aware(parse_datetime(str(value)))
    if not retry_after or retry_after <= timezone.now():
        cache.delete(cache_key)
        if scope == 'read':
            cache.delete(GMAIL_API_RATE_LIMIT_CACHE_KEY)
        return None
    return retry_after


def gmail_rate_limit_message(prefix='Gmail API en rate limit', scope: str = 'read'):
    retry_after = get_gmail_rate_limit_until(scope)
    if not retry_after:
        return ''
    return f'{prefix}; reintentar después de {retry_after.isoformat()}'


def is_gmail_rate_limit_error(exc) -> bool:
    status = getattr(getattr(exc, 'resp', None), 'status', None)
    if status == 429:
        return True
    text = str(exc)
    return 'rateLimitExceeded' in text or 'User-rate limit exceeded' in text


def celery_gmail_api_tasks_paused() -> bool:
    """True si Celery debe omitir tareas pesadas que consumen cuota Gmail API."""
    from django.conf import settings

    return getattr(settings, 'CELERY_PAUSE_GMAIL_API_TASKS', False)


def should_skip_gmail_api_celery_task(task_name: str, *, logger=None, scope: str = 'read') -> bool:
    """
    Omite tareas Celery que golpean Gmail API si hay pausa operativa explícita
    o cooldown activo por 429 en el scope indicado (evita alargar el bloqueo).
    """
    if celery_gmail_api_tasks_paused():
        if logger is not None:
            logger.info('%s: omitido (CELERY_PAUSE_GMAIL_API_TASKS=true)', task_name)
        return True
    retry_after = get_gmail_rate_limit_until(scope)
    if retry_after:
        if logger is not None:
            logger.info(
                '%s: omitido (Gmail API rate limit %s hasta %s)',
                task_name,
                scope,
                retry_after.isoformat(),
            )
        return True
    return False
