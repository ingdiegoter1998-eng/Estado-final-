"""
Depura duplicados en CorreoEntrante (message_id legacy, doble ingesta y reenvíos Fwd).

Por defecto dry-run. Con --apply envía copias sobrantes a papelera y corrige message_id
del registro que se conserva. Respeta registros que ya están en papelera (no los restaura).
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from correspondencia.models import CorreoEntrante
from correspondencia.utils.blocked_recipients import normalizar_email_destinatario
from correspondencia.utils.message_id_utils import normalize_message_id_value
from correspondencia.utils.subject_dedup import (
    es_asunto_reenvio,
    es_remitente_institucional,
    normalize_subject_key,
)


def _normalize_asunto(asunto: str) -> str:
    return normalize_subject_key(asunto)


def _duplicate_group_key(correo: CorreoEntrante) -> tuple | None:
    canonical_mid = normalize_message_id_value(correo.message_id)
    remitente = normalizar_email_destinatario(correo.remitente) or (correo.remitente or '').strip().lower()
    asunto = _normalize_asunto(correo.asunto)
    fecha = correo.fecha_recibida_gmail

    if not fecha:
        return None
    if canonical_mid:
        return ('mid', canonical_mid, fecha.isoformat())
    if remitente and asunto:
        return ('meta', remitente, asunto, fecha.isoformat())
    return None


def _content_group_key(correo: CorreoEntrante) -> tuple | None:
    if correo.en_papelera:
        return None
    subject_key = normalize_subject_key(correo.asunto)
    if not subject_key:
        return None
    fecha = correo.fecha_recibida_gmail or correo.fecha_lectura_imap
    if not fecha:
        return None
    return ('contenido', subject_key, fecha.date().isoformat())


def _keeper_score(correo: CorreoEntrante) -> tuple:
    canonical = normalize_message_id_value(correo.message_id)
    stored = (correo.message_id or '').strip()
    if stored == canonical and canonical:
        id_quality = 0
    elif stored.startswith('('):
        id_quality = 2
    else:
        id_quality = 1

    institutional = es_remitente_institucional(correo.remitente)
    institutional_fwd = institutional and es_asunto_reenvio(correo.asunto or '')

    return (
        0 if correo.radicado_asociado_id else 1,
        0 if institutional_fwd else 1,
        0 if not institutional else 1,
        id_quality,
        0 if not correo.en_papelera else 1,
        correo.id,
    )


def _should_use_content_group(members: list[CorreoEntrante]) -> bool:
    """Agrupa por asunto solo si hay reenvío Fwd del buzón institucional en el grupo."""
    if len(members) <= 1:
        return False
    return any(
        es_remitente_institucional(c.remitente) and es_asunto_reenvio(c.asunto or '')
        for c in members
    )


def _collect_duplicate_actions(qs):
    groups: dict[tuple, list[CorreoEntrante]] = defaultdict(list)
    content_groups: dict[tuple, list[CorreoEntrante]] = defaultdict(list)

    for correo in qs.iterator():
        key = _duplicate_group_key(correo)
        if key:
            groups[key].append(correo)
        content_key = _content_group_key(correo)
        if content_key:
            content_groups[content_key].append(correo)

    duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
    duplicate_groups.update({
        k: v for k, v in content_groups.items()
        if _should_use_content_group(v)
    })

    to_papelera = []
    to_fix_mid = []
    seen_papelera_ids: set[int] = set()

    for members in duplicate_groups.values():
        keeper = min(members, key=_keeper_score)
        canonical = normalize_message_id_value(keeper.message_id)
        if canonical and keeper.message_id != canonical:
            to_fix_mid.append((keeper, canonical))

        for correo in members:
            if correo.id == keeper.id:
                continue
            if correo.en_papelera:
                continue
            if correo.id in seen_papelera_ids:
                continue
            to_papelera.append((correo, keeper))
            seen_papelera_ids.add(correo.id)

    return duplicate_groups, to_papelera, to_fix_mid


class Command(BaseCommand):
    help = (
        'Detecta duplicados en bandeja entrante (message_id legacy, doble ingesta, '
        'reenvíos Fwd institucionales) y envía copias sobrantes a papelera.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Ventana hacia atrás (default 30).')
        parser.add_argument('--apply', action='store_true', help='Aplicar cambios (default: simulación).')
        parser.add_argument(
            '--include-papelera',
            action='store_true',
            help='Incluir registros ya en papelera al agrupar duplicados por message_id.',
        )

    def handle(self, *args, **options):
        days = max(1, int(options['days']))
        apply_changes = bool(options['apply'])
        since = timezone.now() - timedelta(days=days)

        qs = CorreoEntrante.objects.filter(fecha_lectura_imap__gte=since).order_by('id')
        duplicate_groups, to_papelera, to_fix_mid = _collect_duplicate_actions(qs)

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('DEPURACIÓN DE DUPLICADOS — CorreoEntrante'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Ventana: últimos {days} días ({since.date()} → hoy)')
        self.stdout.write(f'Modo: {"APLICAR" if apply_changes else "SIMULACIÓN (dry-run)"}')
        self.stdout.write(f'Grupos duplicados: {len(duplicate_groups)}')
        self.stdout.write(f'A enviar a papelera: {len(to_papelera)}')
        self.stdout.write(f'Message-ID a corregir en conservados: {len(to_fix_mid)}')
        self.stdout.write('')

        for correo, keeper in to_papelera[:50]:
            self.stdout.write(
                f'  PAPELERA id={correo.id} | conservar id={keeper.id} | '
                f'{correo.remitente[:45]} | {(correo.asunto or "")[:50]}'
            )
        if len(to_papelera) > 50:
            self.stdout.write(f'  ... y {len(to_papelera) - 50} más')

        if not apply_changes:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Dry-run: re-ejecute con --apply para aplicar.'))
            return

        papelera_count = 0
        fixed_count = 0
        with transaction.atomic():
            for correo, keeper in to_papelera:
                correo.en_papelera = True
                correo.motivo_papelera = 'NOTIFICACION_AUTOMATICA'
                correo.fecha_papelera = timezone.now()
                correo.save(update_fields=['en_papelera', 'motivo_papelera', 'fecha_papelera'])
                papelera_count += 1

            for keeper, canonical in to_fix_mid:
                if keeper.message_id == canonical:
                    continue
                if CorreoEntrante.objects.filter(message_id=canonical).exclude(pk=keeper.pk).exists():
                    continue
                keeper.message_id = canonical
                keeper.save(update_fields=['message_id'])
                fixed_count += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Listo: {papelera_count} a papelera, {fixed_count} message_id corregidos.'))
