"""Prepara usuarios y datos aislados para flujos E2E de ventanilla."""

import json
import os

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from correspondencia.models import (
    Contacto,
    Correspondencia,
    CorrespondenciaSalida,
    EntidadExterna,
    SalidaDestinatario,
)
from documentos.models import OficinaProductora, PerfilUsuario


E2E_PREFIX = '[E2E]'


class Command(BaseCommand):
    help = 'Prepara datos seguros para Playwright E2E de ventanilla/radicación/respuesta.'

    def add_arguments(self, parser):
        parser.add_argument('--stdout-json', action='store_true')
        parser.add_argument('--cleanup', action='store_true')
        parser.add_argument('--ventanilla-user', default=os.getenv('E2E_VENTANILLA_USER', 'e2e_ventanilla'))
        parser.add_argument('--redactor-user', default=os.getenv('E2E_REDACTOR_USER', 'e2e_redactor'))
        parser.add_argument('--password', default=os.getenv('E2E_TEST_PASSWORD', 'test123'))
        parser.add_argument('--destinatario-email', default=os.getenv('E2E_MAIL_TO', 'e2e.destino@maildemo.co'))

    def _require_allow_mutations(self):
        if os.getenv('E2E_ALLOW_MUTATIONS', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
            raise CommandError(
                'Este comando crea datos E2E. Define E2E_ALLOW_MUTATIONS=1 para ejecutarlo.'
            )

    @transaction.atomic
    def handle(self, *args, **options):
        self._require_allow_mutations()

        if options['cleanup']:
            deleted_salidas, _ = CorrespondenciaSalida.objects.filter(asunto__startswith=E2E_PREFIX).delete()
            deleted_entradas, _ = Correspondencia.objects.filter(asunto__startswith=E2E_PREFIX).delete()
            payload = {'deleted_salidas': deleted_salidas, 'deleted_entradas': deleted_entradas}
            self._emit(payload, options['stdout_json'])
            return

        oficina = OficinaProductora.objects.order_by('id').first()
        if not oficina:
            raise CommandError('No hay OficinaProductora disponible para preparar usuarios E2E.')

        ventanilla = self._ensure_user(
            username=options['ventanilla_user'],
            password=options['password'],
            first_name='Ventanilla',
            last_name='E2E',
            oficina=oficina,
            groups=['Ventanilla'],
        )
        redactor = self._ensure_user(
            username=options['redactor_user'],
            password=options['password'],
            first_name='Redactor',
            last_name='E2E',
            oficina=oficina,
            groups=[],
        )

        entidad = EntidadExterna.get_entidad_por_defecto()
        contacto, _ = Contacto.objects.get_or_create(
            correo_electronico=options['destinatario_email'].strip().lower(),
            defaults={
                'entidad_externa': entidad,
                'nombres': 'Destinatario',
                'apellidos': 'Playwright E2E',
                'cargo': 'Pruebas automatizadas',
            },
        )

        stamp = timezone.now().strftime('%Y%m%d%H%M%S')
        entrada = Correspondencia.objects.create(
            numero_radicado=f'E2E-ENTRANTE-{stamp}',
            usuario_radicador=ventanilla,
            remitente=contacto,
            asunto=f'{E2E_PREFIX} Entrada Playwright {stamp}',
            medio_recepcion='ELECTRONICO',
            requiere_respuesta=True,
            tiempo_respuesta='NORMAL',
            oficina_destino=oficina,
            usuario_destino_inicial=redactor,
            origen_radicacion='NORMAL',
        )

        salida = CorrespondenciaSalida.objects.create(
            numero_radicado_salida=f'E2E-SALIDA-{stamp}',
            respuesta_a=entrada,
            usuario_redactor=redactor,
            oficina_emisora=oficina,
            destinatario_contacto=contacto,
            destinatario_email=contacto.correo_electronico,
            asunto=f'{E2E_PREFIX} Respuesta Playwright {stamp}',
            cuerpo='Respuesta generada por e2e_prepare_ventanilla_flow para validar aprobación y envío.',
            estado='PENDIENTE_APROBACION',
        )
        SalidaDestinatario.objects.create(
            correspondencia_salida=salida,
            contacto=contacto,
            email_snapshot=contacto.correo_electronico,
            nombre_snapshot=contacto.nombre_completo or 'Destinatario E2E',
            estado='PENDIENTE',
        )

        payload = {
            'ventanilla_user': ventanilla.username,
            'redactor_user': redactor.username,
            'password': options['password'],
            'entrada_id': entrada.pk,
            'numero_radicado': entrada.numero_radicado,
            'salida_id': salida.pk,
            'numero_radicado_salida': salida.numero_radicado_salida,
            'dashboard_path': '/registros/correspondencia/ventanilla/dashboard/',
            'entrada_path': f'/registros/correspondencia/correspondencia/{entrada.pk}/',
            'revisar_path': f'/registros/correspondencia/ventanilla/respuesta/{salida.pk}/revisar/',
            'respuestas_path': '/registros/correspondencia/ventanilla/respuestas-pendientes/',
        }
        self._emit(payload, options['stdout_json'])

    def _ensure_user(self, *, username, password, first_name, last_name, oficina, groups):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'email': f'{username}@e2e.local',
                'is_active': True,
            },
        )
        if created or not user.has_usable_password():
            user.set_password(password)
        user.is_active = True
        user.first_name = first_name
        user.last_name = last_name
        user.email = f'{username}@e2e.local'
        user.save()

        perfil, _ = PerfilUsuario.objects.get_or_create(
            user=user,
            defaults={
                'oficina': oficina,
                'cargo': 'Usuario E2E',
                'numero_documento': f'E2E-{user.username}',
            },
        )
        perfil.oficina = oficina
        perfil.cargo = 'Usuario E2E'
        if not perfil.numero_documento:
            perfil.numero_documento = f'E2E-{user.username}'
        perfil.save()

        for group_name in groups:
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user

    def _emit(self, payload, stdout_json):
        if stdout_json:
            self.stdout.write(json.dumps(payload, ensure_ascii=False))
        else:
            self.stdout.write(self.style.SUCCESS(json.dumps(payload, ensure_ascii=False, indent=2)))
