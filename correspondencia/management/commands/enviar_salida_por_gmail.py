"""
Envía una correspondencia salida concreta por Gmail API (OAuth), sin cambiar
EMAIL_PROVIDER global (p. ej. Postmark sigue activo para el resto).

Uso operativo:
  python manage.py enviar_salida_por_gmail --radicado SALIENTE-2026-02329
  python manage.py enviar_salida_por_gmail --salida-id 1661
  python manage.py enviar_salida_por_gmail --radicado SALIENTE-2026-02329 --dry-run
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from correspondencia.aprobacion_envio import aprobar_y_enviar_una_respuesta
from correspondencia.models import CorrespondenciaSalida
from correspondencia.utils.outbound_gmail_api import get_outbound_gmail_api_mail_connection


class Command(BaseCommand):
    help = (
        'Aprueba y envía una salida puntual por Gmail API (no Postmark). '
        'No modifica EMAIL_PROVIDER del entorno.'
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--salida-id', type=int, dest='salida_id')
        group.add_argument('--radicado', type=str, dest='radicado')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo valida salida, credenciales y destinatarios pendientes; no envía.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Permite reintento aunque la salida ya esté ENVIADA (solo destinos PENDIENTE/FALLO).',
        )

    def handle(self, *args, **options):
        salida = self._resolver_salida(options)
        self._validar_credenciales_gmail()

        destinos = list(salida.destinatarios.all())
        pendientes = [d for d in destinos if d.estado in {'PENDIENTE', 'FALLO'}]
        ya_enviados = [d for d in destinos if d.estado == 'ENVIADO']

        if salida.estado == 'ENVIADA' and not pendientes and not options['force']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'{salida.numero_radicado_salida} (id={salida.pk}) ya está ENVIADA; '
                    f'{len(ya_enviados)} destinatario(s) ENVIADO. Nada que hacer.'
                )
            )
            return

        if not pendientes:
            raise CommandError(
                f'Sin destinatarios PENDIENTE/FALLO en {salida.numero_radicado_salida}. '
                f'Estados: {[f"{d.email_snapshot}:{d.estado}" for d in destinos]}'
            )

        self.stdout.write(
            f'Salida {salida.numero_radicado_salida} (id={salida.pk}) estado={salida.estado}; '
            f'pendientes={len(pendientes)} de {len(destinos)}'
        )
        for d in pendientes:
            self.stdout.write(f'  → {d.email_snapshot} ({d.estado})')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run: no se envió correo.'))
            return

        connection = get_outbound_gmail_api_mail_connection()
        enviados, total = aprobar_y_enviar_una_respuesta(
            salida,
            usuario_aprobador=None,
            mail_connection=connection,
            proveedor_envio='gmail_api',
        )
        salida.refresh_from_db()

        if enviados == total and total > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Enviado por Gmail API: {enviados}/{total}. '
                    f'Estado salida={salida.estado}. '
                    f'id_mensaje={salida.id_mensaje_enviado or "-"}'
                )
            )
            return

        if enviados > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Envío parcial Gmail API: {enviados}/{total}. Estado salida={salida.estado}'
                )
            )
            return

        raise CommandError(
            f'No se envió a ningún destinatario ({enviados}/{total}). '
            f'Estado salida={salida.estado}. Revise HistorialSalida y logs.'
        )

    def _resolver_salida(self, options):
        if options.get('salida_id'):
            salida = CorrespondenciaSalida.objects.filter(pk=options['salida_id']).first()
        else:
            radicado = (options.get('radicado') or '').strip()
            salida = CorrespondenciaSalida.objects.filter(numero_radicado_salida=radicado).first()
        if not salida:
            raise CommandError('No se encontró la correspondencia salida indicada.')
        return salida

    def _validar_credenciales_gmail(self):
        missing = []
        if not getattr(settings, 'GMAIL_API_CLIENT_ID', '').strip():
            missing.append('GMAIL_API_CLIENT_ID')
        if not getattr(settings, 'GMAIL_API_CLIENT_SECRET', '').strip():
            missing.append('GMAIL_API_CLIENT_SECRET')
        if not getattr(settings, 'GMAIL_API_REFRESH_TOKEN', '').strip():
            missing.append('GMAIL_API_REFRESH_TOKEN')
        if missing:
            raise CommandError(
                'Faltan credenciales OAuth Gmail: ' + ', '.join(missing) + '. '
                'Ejecute gmail_oauth_desktop_start / gmail_oauth_exchange y configure .env.'
            )
        addr = (getattr(settings, 'OUTBOUND_EMAIL_ADDRESS', '') or '').strip()
        if not addr or '@' not in addr:
            raise CommandError(
                'Configure OUTBOUND_EMAIL_ADDRESS (buzón autorizado en Gmail API) antes de enviar.'
            )
