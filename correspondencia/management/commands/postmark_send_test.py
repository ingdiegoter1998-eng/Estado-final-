"""Envío mínimo por Postmark para validar From + token en producción."""

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.core.management.base import BaseCommand, CommandError

from correspondencia.aprobacion_envio import _direccion_remitente_visible
from correspondencia.utils.postmark_outbound import build_postmark_outbound_status


class Command(BaseCommand):
    help = 'Envía un correo de prueba por Postmark (valida remitente y token).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            default='',
            help='Destinatario (default: OUTBOUND_EMAIL_ADDRESS, envío a sí mismo).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo validar configuración, sin llamar a la API.',
        )

    def handle(self, *args, **options):
        status = build_postmark_outbound_status()
        if not status.get('postmark_outbound_ready'):
            for issue in status.get('postmark_outbound_issues') or []:
                self.stderr.write(self.style.ERROR(issue))
            raise CommandError('Configuración Postmark incompleta o From no verificado.')

        to_addr = (options['to'] or '').strip() or (settings.OUTBOUND_EMAIL_ADDRESS or '').strip()
        if not to_addr or '@' not in to_addr:
            raise CommandError('Indique --to o configure OUTBOUND_EMAIL_ADDRESS.')

        from_email = _direccion_remitente_visible()
        if not from_email:
            raise CommandError('No se pudo construir From (OUTBOUND_EMAIL_ADDRESS).')

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'OK (dry-run): enviaría desde {from_email} hacia {to_addr}'
            ))
            return

        connection = get_connection()
        msg = EmailMessage(
            subject='[Correspondencia] Prueba Postmark saliente',
            body='Mensaje de prueba generado por manage.py postmark_send_test.',
            from_email=from_email,
            to=[to_addr],
            connection=connection,
        )
        try:
            msg.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f'Postmark rechazó el envío: {exc}') from exc

        response = getattr(msg, 'postmark_response', {}) or {}
        message_id = (response.get('MessageID') or '').strip()
        if not message_id:
            raise CommandError(f'Postmark no devolvió MessageID: {response}')

        self.stdout.write(self.style.SUCCESS(
            f'Enviado OK — MessageID={message_id} → {to_addr}'
        ))
