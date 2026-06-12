"""
Prueba E2E de rebotes Postmark usando el dominio bounce-testing.postmarkapp.com.

Crea una salida clonada en PENDIENTE_APROBACION, envía por Postmark y espera el webhook Bounce.
Requiere: EMAIL_PROVIDER=postmark, webhook activo (ngrok o producción).
"""

import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from correspondencia.aprobacion_envio import aprobar_y_enviar_una_respuesta
from correspondencia.models import (
    CorrespondenciaSalida,
    PostmarkWebhookEvento,
    SalidaDestinatario,
)

BOUNCE_TARGETS = {
    'soft': 'SoftBounce@bounce-testing.postmarkapp.com',
    'hard': 'HardBounce@bounce-testing.postmarkapp.com',
    'transient': 'Transient@bounce-testing.postmarkapp.com',
}

SALIDA_CLONE_FIELDS = (
    'respuesta_a_id',
    'respuesta_a_urgencia_id',
    'usuario_redactor_id',
    'oficina_emisora_id',
    'oficina_emisora_nombre',
    'redactor_nombre',
    'redactor_cargo',
    'destinatario_contacto_id',
    'tipo_respuesta',
    'motivo_respuesta_discrecional',
    'funcionario_envia',
)


class Command(BaseCommand):
    help = (
        'Prueba rebotes Postmark: clona una salida, envía a bounce-testing.postmarkapp.com '
        'y verifica webhook + estado REBOTE en BD.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'bounce_type',
            choices=sorted(BOUNCE_TARGETS.keys()),
            help='Tipo de rebote simulado (soft, hard, transient).',
        )
        parser.add_argument(
            '--from-salida-id',
            type=int,
            default=1595,
            help='Salida plantilla para clonar (default: 1595).',
        )
        parser.add_argument(
            '--send-only',
            type=int,
            metavar='SALIDA_ID',
            help='Solo enviar/aprobar una salida existente (sin clonar).',
        )
        parser.add_argument(
            '--usuario',
            default='superprueba',
            help='Usuario aprobador (default: superprueba).',
        )
        parser.add_argument(
            '--wait-seconds',
            type=int,
            default=45,
            help='Segundos máximos esperando webhook Bounce (default: 45).',
        )
        parser.add_argument(
            '--no-send',
            action='store_true',
            help='Solo crear la salida pendiente, sin enviar.',
        )

    def handle(self, *args, **options):
        bounce_type = options['bounce_type']
        target_email = BOUNCE_TARGETS[bounce_type]
        User = get_user_model()

        try:
            usuario = User.objects.get(username=options['usuario'])
        except User.DoesNotExist as exc:
            raise CommandError(f"Usuario '{options['usuario']}' no existe.") from exc

        if options['send_only']:
            salida = CorrespondenciaSalida.objects.get(pk=options['send_only'])
            self.stdout.write(f'Usando salida existente {salida.numero_radicado_salida} (id={salida.pk})')
        else:
            salida = self._clonar_salida_prueba(
                template_id=options['from_salida_id'],
                bounce_type=bounce_type,
                target_email=target_email,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Salida creada: {salida.numero_radicado_salida} (id={salida.pk}) → {target_email}'
                )
            )
            self.stdout.write(
                f'UI: /registros/correspondencia/ventanilla/respuesta/{salida.pk}/revisar/'
            )

        if options['no_send']:
            return

        if salida.estado not in ('PENDIENTE_APROBACION', 'ERROR_ENVIO'):
            self._preparar_reintento(salida)

        dest = SalidaDestinatario.objects.filter(correspondencia_salida=salida).first()
        if not dest:
            raise CommandError('La salida no tiene destinatarios.')

        self.stdout.write('Enviando por Postmark (aprobar_y_enviar)...')
        enviados, total = aprobar_y_enviar_una_respuesta(salida, usuario)
        salida.refresh_from_db()
        dest.refresh_from_db()

        self.stdout.write(
            f'  Envío: {enviados}/{total} | salida={salida.estado} | '
            f'postmark_message_id={salida.postmark_message_id or "-"}'
        )
        self.stdout.write(f'  Destinatario: {dest.estado} | {dest.email_snapshot}')

        if not salida.postmark_message_id:
            raise CommandError('No se obtuvo postmark_message_id; revise logs y POSTMARK_SERVER_TOKEN.')

        message_id = salida.postmark_message_id
        self.stdout.write(f'Esperando webhook Bounce (hasta {options["wait_seconds"]}s)...')

        bounce_ok = False
        deadline = time.time() + options['wait_seconds']
        while time.time() < deadline:
            dest.refresh_from_db()
            evento = PostmarkWebhookEvento.objects.filter(
                record_type='Bounce',
                postmark_message_id=message_id,
            ).order_by('-recibido_at').first()

            if dest.estado == 'REBOTE' and evento and evento.procesado:
                bounce_ok = True
                break
            time.sleep(2)

        dest.refresh_from_db()
        salida.refresh_from_db()
        evento = PostmarkWebhookEvento.objects.filter(
            record_type='Bounce',
            postmark_message_id=message_id,
        ).order_by('-recibido_at').first()

        self.stdout.write('')
        self.stdout.write('--- Resultado ---')
        self.stdout.write(f'  Destinatario: {dest.estado} (esperado: REBOTE)')
        self.stdout.write(f'  Salida:       {salida.estado}')
        if evento:
            self.stdout.write(
                f'  Webhook:      {evento.record_type} proc={evento.procesado} '
                f'resultado={evento.resultado} recipient={evento.recipient}'
            )
        else:
            self.stdout.write(self.style.WARNING('  Webhook:      no recibido aún'))
            self.stdout.write(
                '  Verifique ngrok/producción y stream outbound en Postmark.'
            )

        if bounce_ok:
            self.stdout.write(self.style.SUCCESS('OK: rebote procesado correctamente.'))
        else:
            raise CommandError(
                'Rebote no confirmado en tiempo. Ejecute: python manage.py postmark_webhook_status'
            )

    @transaction.atomic
    def _clonar_salida_prueba(self, *, template_id: int, bounce_type: str, target_email: str):
        plantilla = CorrespondenciaSalida.objects.get(pk=template_id)
        origen_dest = SalidaDestinatario.objects.filter(correspondencia_salida=plantilla).first()
        if not origen_dest:
            raise CommandError(f'Salida {template_id} sin destinatarios.')

        data = {f: getattr(plantilla, f) for f in SALIDA_CLONE_FIELDS}
        salida = CorrespondenciaSalida(
            **data,
            asunto=f'[PRUEBA REBOTE {bounce_type.upper()}] {plantilla.asunto}'[:255],
            cuerpo=(
                f'Prueba automática Postmark ({bounce_type}).\n\n'
                f'{plantilla.cuerpo or ""}'
            )[:4000],
            estado='PENDIENTE_APROBACION',
            destinatario_email='',
        )
        salida.save()

        SalidaDestinatario.objects.create(
            correspondencia_salida=salida,
            contacto=origen_dest.contacto,
            email_snapshot=target_email,
            nombre_snapshot=f'Postmark test {bounce_type}',
            estado='PENDIENTE',
        )
        return salida

    def _preparar_reintento(self, salida: CorrespondenciaSalida):
        salida.estado = 'PENDIENTE_APROBACION'
        salida.fecha_envio = None
        salida.postmark_message_id = None
        salida.id_mensaje_enviado = None
        salida.save(update_fields=['estado', 'fecha_envio', 'postmark_message_id', 'id_mensaje_enviado'])
        SalidaDestinatario.objects.filter(correspondencia_salida=salida).update(
            estado='PENDIENTE',
            fecha_envio=None,
            id_mensaje_enviado=None,
            postmark_message_id=None,
            detalle_error=None,
            smtp_code=None,
            dsn_status=None,
            ultimo_evento_at=None,
        )
