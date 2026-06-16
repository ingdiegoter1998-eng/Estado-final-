"""
Comando para procesar emails con validación de seguridad para adjuntos
Uso: python manage.py procesar_emails_seguro [--dry-run]
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from correspondencia.utils.email_attachment_validator import EmailAttachmentValidator
from correspondencia.utils.email_provider import build_email_inbox_provider
from correspondencia.utils.email_ingestion import load_known_correo_message_ids, procesar_mensaje_imap
from correspondencia.utils.message_id_utils import normalize_message_id_value
from correspondencia.utils.gmail_rate_limit import (
    get_gmail_rate_limit_until,
    is_gmail_rate_limit_error,
    remember_gmail_rate_limit,
)
from correspondencia.settings.email_config import (
    ALLOWED_FILE_EXTENSIONS,
    BLOCKED_FILE_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    MAX_TOTAL_SIZE_MB,
    MAX_FILES_PER_EMAIL,
)
from correspondencia.models import CorreoEntrante, CorreoProblematico

import imaplib
import time
from imap_tools import MailBox, AND, MailMessageFlags
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa emails con validación de seguridad para adjuntos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular procesamiento sin guardar'
        )
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Mostrar configuración de seguridad'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Días hacia atrás para buscar correos (default: 1 normal, 7 recovery, 60+ para masivo)'
        )
        parser.add_argument(
            '--recovery',
            action='store_true',
            help='Modo recuperación: busca TODOS los correos (incluso ya leídos) y procesa los que faltan en BD'
        )
        parser.add_argument(
            '--since',
            type=str,
            default=None,
            help='Fecha y hora inicial exacta en formato ISO 8601. Ej: 2026-03-12T16:44:00-05:00'
        )
        parser.add_argument(
            '--until',
            type=str,
            default=None,
            help='Fecha y hora final exacta en formato ISO 8601. Ej: 2026-03-13T10:30:00-05:00'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        show_config = options.get('show_config')
        recovery_mode = options.get('recovery', False)
        since_raw = options.get('since')
        until_raw = options.get('until')
        # Default: 2 días para capturar correos de ayer no procesados, 7 en recovery
        days_back = options.get('days') or (7 if recovery_mode else 2)

        since_dt = parse_datetime(since_raw) if since_raw else None
        until_dt = parse_datetime(until_raw) if until_raw else None

        if since_dt and timezone.is_naive(since_dt):
            since_dt = timezone.make_aware(since_dt, timezone.get_current_timezone())
        if until_dt and timezone.is_naive(until_dt):
            until_dt = timezone.make_aware(until_dt, timezone.get_current_timezone())

        if since_dt and until_dt and since_dt > until_dt:
            raise ValueError('El rango exacto es inválido: since no puede ser mayor que until.')

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('PROCESADOR SEGURO DE EMAILS'))
        self.stdout.write('=' * 70)

        if show_config:
            self.show_security_config()

        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('⚠️  MODO SIMULACIÓN (--dry-run activado)'))
            self.stdout.write('No se guardarán cambios en la base de datos.\n')

        correos_guardados = 0
        adjuntos_guardados = 0
        correos_rechazados = 0
        correos_problematicos = 0
        mailbox = None

        EMAIL_ACCOUNT = getattr(settings, 'EMAIL_HOST_USER', '')

        def _connect_mailbox():
            """Crea y retorna un proveedor de recepción autenticado."""
            return build_email_inbox_provider(
                mailbox_factory=MailBox,
                imap_factory=imaplib.IMAP4_SSL,
            ).connect()

        try:
            provider_name = getattr(settings, 'EMAIL_INGESTION_PROVIDER', 'imap').strip().lower()
            if provider_name == 'gmail_api':
                retry_after = get_gmail_rate_limit_until()
                if retry_after:
                    raise CommandError(
                        f'Gmail API en rate limit; reintentar después de {retry_after.isoformat()}'
                    )
                self.stdout.write('Conectando a Gmail API para recepción...')
            else:
                self.stdout.write(f"Conectando a {getattr(settings, 'IMAP_SERVER', 'imap.gmail.com')}:{getattr(settings, 'IMAP_PORT', 993)} con SSL...")
            mailbox = _connect_mailbox()

            # Usar fecha dinámica: últimos N días para rendimiento
            from datetime import timedelta
            fecha_minima = (datetime.now() - timedelta(days=days_back)).date()
            if since_dt or until_dt:
                fecha_referencia = (since_dt or until_dt).astimezone(timezone.get_current_timezone())
                fecha_minima = fecha_referencia.date()
                rango_legible = []
                if since_dt:
                    rango_legible.append(f"desde {timezone.localtime(since_dt).strftime('%d/%m/%Y %H:%M:%S')}")
                if until_dt:
                    rango_legible.append(f"hasta {timezone.localtime(until_dt).strftime('%d/%m/%Y %H:%M:%S')}")
                self.stdout.write(f"Buscando correos en rango exacto {' '.join(rango_legible)}...")
            else:
                self.stdout.write(f"Buscando correos desde {fecha_minima} ({days_back} días atrás)...")

            if recovery_mode:
                self.stdout.write(self.style.WARNING('MODO RECUPERACIÓN: escaneando headers para identificar correos faltantes...'))
            else:
                self.stdout.write(f"Escaneando UNSEEN en INBOX ({days_back} día(s) atrás)...")

            # Obtener message_ids existentes en BD de un solo golpe (canónicos + legacy)
            existing_ids = load_known_correo_message_ids()

            # Criterio IMAP: en modo normal escanea TODOS los headers de INBOX
            # (ya no depende de UNSEEN — correos leídos en Gmail web se capturan).
            # En recovery escanea INBOX + AllMail.
            if recovery_mode:
                imap_criteria = AND(date_gte=fecha_minima)
                folders = ['INBOX', '[Gmail]/Todos']
                self.stdout.write(self.style.WARNING('MODO RECOVERY: escaneando TODOS los correos en INBOX + AllMail'))
            else:
                imap_criteria = AND(date_gte=fecha_minima)
                folders = ['INBOX']
                self.stdout.write('Modo normal: escaneando TODOS los headers en INBOX (dedup por message_id)')

            seen_mids = set()
            all_uids_by_folder = {}

            def esta_en_rango(fecha_valor):
                if not fecha_valor:
                    return False
                fecha_aw = fecha_valor
                if timezone.is_naive(fecha_aw):
                    try:
                        fecha_aw = timezone.make_aware(fecha_aw, timezone.get_current_timezone())
                    except Exception:
                        fecha_aw = timezone.make_aware(fecha_aw, timezone.utc)
                if since_dt and fecha_aw < since_dt:
                    return False
                if until_dt and fecha_aw > until_dt:
                    return False
                return True

            for folder_name in folders:
                self.stdout.write(f"  Escaneando {folder_name}...")
                headers = list(mailbox.fetch_headers(folder_name, date_gte=fecha_minima))
                if since_dt or until_dt:
                    headers = [header for header in headers if esta_en_rango(getattr(header, 'date', None))]
                self.stdout.write(f"    Correos encontrados en {folder_name}: {len(headers)}")

                folder_uids = []
                own_email_lower = EMAIL_ACCOUNT.lower()
                for h in headers:
                    mid = normalize_message_id_value((h.headers.get('message-id') or [''])[0])
                    if not mid or mid in existing_ids or mid in seen_mids:
                        continue
                    # En AllMail: descartar correos enviados por la propia cuenta
                    if folder_name != 'INBOX':
                        from_header = (getattr(h, 'from_', None) or (h.headers.get('from', [''])[0] if h.headers.get('from') else '')).lower()
                        if own_email_lower in from_header:
                            continue
                    folder_uids.append(h.uid)
                    seen_mids.add(mid)

                if folder_uids:
                    all_uids_by_folder[folder_name] = folder_uids
                    self.stdout.write(f"    Correos NUEVOS en {folder_name}: {len(folder_uids)}")
                else:
                    self.stdout.write(f"    Sin correos nuevos en {folder_name}.")

            total_nuevos = sum(len(u) for u in all_uids_by_folder.values())
            self.stdout.write(f"  Total correos NUEVOS a procesar: {total_nuevos}")

            # Descargar y procesar correos por lotes (procesamiento inmediato por lote
            # para no perder correos ya descargados si IMAP falla a medio camino).
            BATCH_SIZE = 15
            BATCH_DELAY = 2  # segundos entre lotes para respetar cuota Gmail
            BATCH_MAX_RETRIES = 1  # reintentos por lote fallido
            processed_count = 0

            for folder_name, uids in all_uids_by_folder.items():
                for batch_start in range(0, len(uids), BATCH_SIZE):
                    batch_uids = uids[batch_start:batch_start + BATCH_SIZE]
                    uid_str = ','.join(batch_uids)
                    batch_num = batch_start // BATCH_SIZE + 1
                    self.stdout.write(f"  Descargando de {folder_name} lote {batch_num} ({len(batch_uids)} correos)...")

                    batch_emails = None
                    for attempt in range(1 + BATCH_MAX_RETRIES):
                        try:
                            batch_emails = list(mailbox.fetch_messages_by_uids(folder_name, batch_uids))
                            break  # fetch exitoso
                        except Exception as e_batch:
                            if attempt < BATCH_MAX_RETRIES:
                                self.stdout.write(self.style.WARNING(f"  Error del proveedor en lote {batch_num} (intento {attempt+1}): {e_batch}. Reconectando..."))
                                time.sleep(3)
                                try:
                                    mailbox.logout()
                                except Exception:
                                    pass
                                try:
                                    mailbox = _connect_mailbox()
                                except Exception as e_reconn:
                                    self.stdout.write(self.style.ERROR(
                                        f"  No se pudo reconectar: {e_reconn}. Saltando lote {batch_num}."
                                    ))
                                    break
                            else:
                                self.stdout.write(self.style.WARNING(
                                    f"  Error IMAP en lote {batch_num} tras {1 + BATCH_MAX_RETRIES} intentos: {e_batch}. "
                                    f"Saltando lote y continuando con el siguiente."
                                ))

                    if batch_emails is None:
                        continue  # saltar este lote, seguir con el próximo

                    for msg in batch_emails:
                        processed_count += 1
                        self.stdout.write(f"--- Procesando email {processed_count}/{total_nuevos}: UID={msg.uid}, Subject='{msg.subject}' ---")
                        try:
                            result = procesar_mensaje_imap(
                                msg,
                                folder_name=folder_name,
                                flow_label='recovery' if recovery_mode else 'normal',
                                persist=not dry_run,
                                fallback_domain=(EMAIL_ACCOUNT.split('@')[-1] if '@' in EMAIL_ACCOUNT else 'local.host'),
                            )

                            if result['status'] == 'duplicate':
                                self.stdout.write("  Ya existe en BD o en bandeja problemática. Marcado como leído.")
                            elif result['status'] == 'skipped_old':
                                self.stdout.write(f"  {result['detail']} Marcado leído y omitido.")
                            elif result['status'] == 'problematic':
                                correos_rechazados += 1
                                correos_problematicos += 1
                                self.stdout.write(self.style.WARNING(
                                    f"  Correo derivado a bandeja problemática: {result['detail']}"
                                ))
                            elif result['status'] == 'dry_run':
                                self.stdout.write(self.style.WARNING("  Dry-run: correo válido detectado, sin guardar en BD."))
                            elif result['status'] == 'saved':
                                correos_guardados += 1
                                adjuntos_guardados += result.get('attachment_count', 0)
                                self.stdout.write(self.style.SUCCESS(
                                    f"  Correo guardado con {result.get('attachment_count', 0)} adjunto(s)."
                                ))

                            if not dry_run:
                                try:
                                    mailbox.mark_seen(msg.uid)
                                    self.stdout.write(self.style.SUCCESS("  Correo procesado y marcado como leído."))
                                except Exception as mark_error:
                                    self.stdout.write(self.style.WARNING(
                                        f"  El resultado fue persistido, pero no se pudo marcar como leído en el proveedor de correo: {mark_error}"
                                    ))
                            else:
                                self.stdout.write(self.style.WARNING("  Dry-run: no se marcó el correo como leído."))

                        except Exception as e_imap:
                            self.stdout.write(self.style.ERROR(f"  Error del proveedor de correo: {e_imap}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"  Error procesando correo: {e}"))

                    # Pausa entre lotes para respetar cuota IMAP de Gmail
                    if batch_start + BATCH_SIZE < len(uids):
                        time.sleep(BATCH_DELAY)

            if processed_count == 0 and total_nuevos == 0:
                self.stdout.write("No se encontraron correos nuevos por procesar.")

        except CommandError:
            raise
        except Exception as e_general:
            if is_gmail_rate_limit_error(e_general):
                retry_after = remember_gmail_rate_limit(e_general)
                raise CommandError(
                    f'Gmail API en rate limit; reintentar después de {retry_after.isoformat()}'
                ) from e_general
            self.stdout.write(self.style.ERROR(f"Error general: {e_general}"))
        finally:
            if mailbox:
                try:
                    mailbox.logout()
                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS("\n--- Procesamiento seguro de emails completado ---"))
        self.stdout.write(f"Correos guardados: {correos_guardados}")
        self.stdout.write(f"Correos rechazados por seguridad: {correos_rechazados}")
        self.stdout.write(f"Correos enviados a bandeja problemática: {correos_problematicos}")
        self.stdout.write(f"Adjuntos guardados: {adjuntos_guardados}")
    
    def show_security_config(self):
        """Muestra la configuración de seguridad"""
        self.stdout.write('\n' + self.style.SUCCESS('✅ EXTENSIONES PERMITIDAS:'))
        ext_list = ', '.join(sorted(ALLOWED_FILE_EXTENSIONS))
        # Dividir en líneas de 70 caracteres
        for i in range(0, len(ext_list), 70):
            self.stdout.write(f'   {ext_list[i:i+70]}')
        
        self.stdout.write('\n' + self.style.ERROR('🚫 EXTENSIONES BLOQUEADAS:'))
        ext_list = ', '.join(sorted(BLOCKED_FILE_EXTENSIONS))
        for i in range(0, len(ext_list), 70):
            self.stdout.write(f'   {ext_list[i:i+70]}')
        
        self.stdout.write('\n' + self.style.WARNING('⚖️  LÍMITES DE TAMAÑO:'))
        self.stdout.write(f'   • Por archivo: {MAX_FILE_SIZE_MB} MB')
        self.stdout.write(f'   • Por email: {MAX_TOTAL_SIZE_MB} MB')
        self.stdout.write(f'   • Máx archivos por email: {MAX_FILES_PER_EMAIL}')
        self.stdout.write('')
