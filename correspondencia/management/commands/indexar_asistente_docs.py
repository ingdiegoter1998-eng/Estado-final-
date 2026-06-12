from django.core.management.base import BaseCommand

from correspondencia.services_chatbot import index_documents


class Command(BaseCommand):
    help = 'Indexa documentación markdown/txt para el asistente documental MVP.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            action='append',
            dest='paths',
            help='Ruta relativa o absoluta a indexar. Puede repetirse varias veces.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpia documentos y chunks existentes antes de indexar.',
        )

    def handle(self, *args, **options):
        result = index_documents(
            custom_paths=options.get('paths'),
            clear_existing=options.get('clear', False),
        )
        self.stdout.write(self.style.SUCCESS(
            'Indexación completada. '
            f"Archivos encontrados: {result['files_found']} | "
            f"Indexados: {result['indexed']} | "
            f"Sin cambios: {result['skipped']}"
        ))