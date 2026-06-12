"""Importa archivos .eml a la bandeja de correos entrantes."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from imap_tools import MailMessage

from correspondencia.utils.email_ingestion import procesar_mensaje_imap


class Command(BaseCommand):
    help = (
        'Importa uno o varios archivos .eml usando el mismo flujo de ingesta de '
        'correos entrantes, sin conectarse a Gmail API ni IMAP.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'paths',
            nargs='+',
            help='Archivos .eml o directorios a importar. Los directorios se recorren de forma recursiva.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Valida y muestra qué se importaría, sin guardar en base de datos.',
        )
        parser.add_argument(
            '--subject-exact',
            action='append',
            default=[],
            help='Importar solo correos cuyo asunto coincida exactamente. Puede repetirse.',
        )

    def handle(self, *args, **options):
        paths = [Path(raw_path).expanduser() for raw_path in options['paths']]
        dry_run = bool(options['dry_run'])
        subject_allowlist = {
            subject.strip()
            for subject in options.get('subject_exact', [])
            if subject and subject.strip()
        }

        eml_files = self._collect_eml_files(paths)
        if not eml_files:
            raise CommandError('No se encontraron archivos .eml en las rutas indicadas.')

        self.stdout.write(f'Archivos .eml encontrados: {len(eml_files)}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: no se guardarán registros.'))
        if subject_allowlist:
            self.stdout.write(f'Filtro de asuntos exactos activo: {len(subject_allowlist)} asunto(s).')

        saved = 0
        duplicates = 0
        problematic = 0
        skipped = 0
        errors = 0
        attachments = 0

        for eml_path in eml_files:
            try:
                raw_bytes = eml_path.read_bytes()
                msg = MailMessage.from_bytes(raw_bytes)
                subject = (getattr(msg, 'subject', '') or '').strip()

                if subject_allowlist and subject not in subject_allowlist:
                    skipped += 1
                    self.stdout.write(f'OMITIDO asunto fuera de filtro: {eml_path} :: {subject}')
                    continue

                result = procesar_mensaje_imap(
                    msg,
                    folder_name='EML_IMPORT',
                    flow_label='manual_eml',
                    persist=not dry_run,
                )
                status = result.get('status')
                attachments += int(result.get('attachment_count') or 0)

                if status == 'saved':
                    saved += 1
                    correo = result.get('correo')
                    correo_id = getattr(correo, 'pk', None)
                    self.stdout.write(self.style.SUCCESS(
                        f'IMPORTADO id={correo_id} adjuntos={result.get("attachment_count", 0)} :: {eml_path} :: {subject}'
                    ))
                elif status == 'duplicate':
                    duplicates += 1
                    self.stdout.write(f'DUPLICADO :: {eml_path} :: {subject}')
                elif status == 'problematic':
                    problematic += 1
                    self.stdout.write(self.style.WARNING(
                        f'PROBLEMATICO adjuntos={result.get("attachment_count", 0)} :: {eml_path} :: {subject} :: {result.get("detail", "")}'
                    ))
                elif status == 'dry_run':
                    self.stdout.write(self.style.WARNING(
                        f'DRY-RUN valido adjuntos={result.get("attachment_count", 0)} :: {eml_path} :: {subject}'
                    ))
                else:
                    skipped += 1
                    self.stdout.write(f'OMITIDO status={status} :: {eml_path} :: {subject} :: {result.get("detail", "")}')
            except Exception as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(f'ERROR :: {eml_path} :: {exc}'))

        self.stdout.write(self.style.SUCCESS('--- Importación .eml finalizada ---'))
        self.stdout.write(f'Guardados: {saved}')
        self.stdout.write(f'Duplicados: {duplicates}')
        self.stdout.write(f'Problemáticos: {problematic}')
        self.stdout.write(f'Omitidos: {skipped}')
        self.stdout.write(f'Errores: {errors}')
        self.stdout.write(f'Adjuntos detectados/guardados: {attachments}')

        if errors:
            raise CommandError(f'La importación terminó con {errors} error(es).')

    def _collect_eml_files(self, paths):
        eml_files = []
        for path in paths:
            if not path.exists():
                raise CommandError(f'La ruta no existe: {path}')
            if path.is_file():
                if path.suffix.lower() != '.eml':
                    raise CommandError(f'El archivo no es .eml: {path}')
                eml_files.append(path)
            elif path.is_dir():
                eml_files.extend(sorted(p for p in path.rglob('*.eml') if p.is_file()))
            else:
                raise CommandError(f'La ruta no es archivo ni directorio: {path}')
        return sorted(set(eml_files))
