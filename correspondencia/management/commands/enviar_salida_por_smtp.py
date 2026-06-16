"""
Envía una correspondencia salida concreta por SMTP, sin Gmail API.

Uso operativo (p. ej. durante rate limit 429 de Gmail API):
  python manage.py enviar_salida_por_smtp --radicado SALIENTE-2026-02504
  python manage.py enviar_salida_por_smtp --salida-id 1843
  python manage.py enviar_salida_por_smtp --radicado SALIENTE-2026-02504 --dry-run
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from correspondencia.aprobacion_envio import aprobar_y_enviar_una_respuesta
from correspondencia.models import CorrespondenciaSalida
from correspondencia.utils.outbound_smtp import get_outbound_smtp_mail_connection, smtp_outbound_disponible


class Command(BaseCommand):
    help = (
        'Aprueba y envía una salida puntual por SMTP (Workspace). '
        'No usa Gmail API ni modifica EMAIL_PROVIDER del entorno.'
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
        self._validar_credenciales_smtp()

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

        connection = get_outbound_smtp_mail_connection()
        enviados, total = aprobar_y_enviar_una_respuesta(
            salida,
            usuario_aprobador=None,
            mail_connection=connection,
            proveedor_envio='smtp',
        )
        salida.refresh_from_db()

        if enviados == total and total > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Enviado por SMTP: {enviados}/{total}. '
                    f'Estado salida={salida.estado}. '
                    f'id_mensaje={salida.id_mensaje_enviado or "-"}'
                )
            )
            return

        if enviados > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Envío parcial SMTP: {enviados}/{total}. Estado salida={salida.estado}'
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

    def _validar_credenciales_smtp(self):
        if smtp_outbound_disponible():
            return
        addr = (getattr(settings, 'OUTBOUND_EMAIL_ADDRESS', '') or getattr(settings, 'EMAIL_HOST_USER', '')).strip()
        raise CommandError(
            'Faltan credenciales SMTP. Configure EMAIL_HOST_PASSWORD o '
            'IMAP_MANUAL_EMAIL_PASSWORD (app password de Google Workspace). '
            f'Remitente esperado: {addr or "(sin configurar)"}'
        )
