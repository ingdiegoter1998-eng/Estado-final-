"""Cola persistente de message IDs pendientes para drenar history de Gmail API por lotes."""

from __future__ import annotations

import json

from django.core.cache import cache

PENDING_IDS_CACHE_KEY = 'correspondencia:gmail_history_pending_ids'
TARGET_HISTORY_CACHE_KEY = 'correspondencia:gmail_history_target_id'
PROCESSED_IDS_CACHE_KEY = 'correspondencia:gmail_history_processed_ids'
CACHE_TIMEOUT = 60 * 60 * 48  # 48 h — suficiente para drenar backlogs grandes


def _load_ids(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    try:
        parsed = json.loads(str(raw))
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if item]


def get_pending_ids() -> list[str]:
    return _load_ids(cache.get(PENDING_IDS_CACHE_KEY))


def get_target_history_id() -> str:
    return str(cache.get(TARGET_HISTORY_CACHE_KEY) or '').strip()


def pending_count() -> int:
    return len(get_pending_ids())


def get_processed_ids() -> set[str]:
    return set(_load_ids(cache.get(PROCESSED_IDS_CACHE_KEY)))


def mark_processed(message_ids: list[str]) -> None:
    processed = get_processed_ids()
    for message_id in message_ids:
        message_id = str(message_id or '').strip()
        if message_id:
            processed.add(message_id)
    cache.set(PROCESSED_IDS_CACHE_KEY, json.dumps(sorted(processed)), timeout=CACHE_TIMEOUT)


def clear_pending() -> None:
    cache.delete(PENDING_IDS_CACHE_KEY)
    cache.delete(TARGET_HISTORY_CACHE_KEY)
    cache.delete(PROCESSED_IDS_CACHE_KEY)


def _save_pending(ids: list[str], target_history_id: str | None = None) -> None:
    cache.set(PENDING_IDS_CACHE_KEY, json.dumps(ids), timeout=CACHE_TIMEOUT)
    if target_history_id is not None:
        cache.set(TARGET_HISTORY_CACHE_KEY, str(target_history_id), timeout=CACHE_TIMEOUT)


def merge_pending_ids(new_ids: list[str], *, target_history_id: str) -> int:
    """Añade IDs nuevos al final de la cola sin duplicar ni reencolar procesados."""
    current = get_pending_ids()
    seen = set(current)
    processed = get_processed_ids()
    for message_id in new_ids:
        message_id = str(message_id or '').strip()
        if message_id and message_id not in seen and message_id not in processed:
            current.append(message_id)
            seen.add(message_id)
    _save_pending(current, target_history_id=target_history_id)
    return len(current)


def take_batch(batch_size: int) -> list[str]:
    """Extrae hasta batch_size IDs del frente de la cola (sin modificar target history)."""
    batch_size = max(1, int(batch_size or 1))
    current = get_pending_ids()
    batch = current[:batch_size]
    _save_pending(current[batch_size:], target_history_id=get_target_history_id())
    return batch


def prepend_pending(ids: list[str]) -> None:
    """Reinserta IDs al frente (p. ej. tras un 429 a mitad de lote)."""
    if not ids:
        return
    current = get_pending_ids()
    _save_pending([*ids, *current], target_history_id=get_target_history_id())


def finalize_if_empty(*, ultimo_history_id: str) -> bool:
    """Si la cola quedó vacía, limpia estado y devuelve True para avanzar historyId."""
    if get_pending_ids():
        return False
    target = get_target_history_id() or ultimo_history_id
    clear_pending()
    return bool(target)
