"""Normalización canónica de Message-ID RFC822 para deduplicación en ingesta."""

from __future__ import annotations

import ast
import re

_MESSAGE_ID_IN_BRACKETS_RE = re.compile(r'<([^>]+@[^>]+)>')


def normalize_message_id_value(raw) -> str:
    """
    Devuelve un Message-ID canónico (sin <> ni basura de headers mal parseados).

    Tolera valores legacy guardados como repr de tupla Python, saltos de línea
    y encabezados metadata vs raw de Gmail API.
    """
    if raw is None:
        return ''

    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else ''

    text = str(raw).strip()
    if not text:
        return ''

    if text.startswith('(') and text.endswith(')'):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)) and parsed:
                return normalize_message_id_value(parsed[0])
        except (ValueError, SyntaxError):
            pass

    bracket_match = _MESSAGE_ID_IN_BRACKETS_RE.search(text)
    if bracket_match:
        return bracket_match.group(1).strip()

    text = text.strip('<>').strip().strip("'\"")
    text = re.sub(r'^[\r\n\s]+', '', text)
    return text.strip('<>').strip()


def build_known_message_id_set(stored_ids) -> set[str]:
    """Construye un set con IDs almacenados y su forma canónica para dedup."""
    known: set[str] = set()
    for stored in stored_ids:
        stored_text = str(stored or '').strip()
        if not stored_text:
            continue
        known.add(stored_text)
        canonical = normalize_message_id_value(stored_text)
        if canonical:
            known.add(canonical)
    return known


def message_id_matches_stored(canonical_id: str, stored_id: str) -> bool:
    if not canonical_id or not stored_id:
        return False
    stored_text = str(stored_id).strip()
    if stored_text == canonical_id:
        return True
    return normalize_message_id_value(stored_text) == canonical_id
