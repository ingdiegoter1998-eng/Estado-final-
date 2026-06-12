"""
Comando IMAP legacy — DESHABILITADO.

Antes contenía credenciales en código fuente. La recepción oficial usa Gmail API vía
`procesar_emails_seguro` y la tarea Celery `procesar_emails_periodico`.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'DEPRECADO y deshabilitado por seguridad. '
        'Use: python manage.py procesar_emails_seguro'
    )

    def handle(self, *args, **options):
        raise CommandError(
            'El comando «procesar_emails» (IMAP legacy) está deshabilitado: contenía credenciales '
            'en el repositorio y ya no se usa en producción.\n'
            'Use en su lugar:\n'
            '  python manage.py procesar_emails_seguro\n'
            'o la sincronización periódica Celery (procesar_emails_periodico).'
        )
