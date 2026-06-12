"""Helpers para respetar cooldowns de Gmail API cuando devuelve 429."""

from __future__ import annotations

import re
from datetime import timedelta, timezone as dt_timezone

from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime


GMAIL_API_RATE_LIMIT_CACHE_KEY = 'correspondencia:gmail_api_rate_limit_until'
_RETRY_AFTER_RE = re.compile(r'Retry after\s+([0-9T:\.\-+Z]+)', re.IGNORECASE)


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


def remember_gmail_rate_limit(exc_or_text, *, fallback_seconds: int = 900):
    """Guarda en cache hasta cuándo se debe evitar llamar Gmail API."""
    now = timezone.now()
    retry_after = parse_gmail_retry_after(exc_or_text) or (now + timedelta(seconds=fallback_seconds))
    if retry_after <= now:
        retry_after = now + timedelta(seconds=fallback_seconds)

    timeout = max(1, int((retry_after - now).total_seconds()))
    cache.set(GMAIL_API_RATE_LIMIT_CACHE_KEY, retry_after.isoformat(), timeout=timeout)
    return retry_after


def get_gmail_rate_limit_until():
    value = cache.get(GMAIL_API_RATE_LIMIT_CACHE_KEY)
    if not value:
        return None
    retry_after = _as_aware(parse_datetime(str(value)))
    if not retry_after or retry_after <= timezone.now():
        cache.delete(GMAIL_API_RATE_LIMIT_CACHE_KEY)
        return None
    return retry_after


def gmail_rate_limit_message(prefix='Gmail API en rate limit'):
    retry_after = get_gmail_rate_limit_until()
    if not retry_after:
        return ''
    return f'{prefix}; reintentar después de {retry_after.isoformat()}'


def is_gmail_rate_limit_error(exc) -> bool:
    status = getattr(getattr(exc, 'resp', None), 'status', None)
    if status == 429:
        return True
    text = str(exc)
    return 'rateLimitExceeded' in text or 'User-rate limit exceeded' in text
