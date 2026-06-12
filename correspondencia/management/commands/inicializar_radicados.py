"""
Management command para inicializar los contadores de radicado.

Uso:
    python manage.py inicializar_radicados
    python manage.py inicializar_radicados --entrante 972 --saliente 672
    python manage.py inicializar_radicados --entrante 1500 --saliente 900

El sistema genera el SIGUIENTE número al último registrado. Por eso
se insertan registros "ancla" con el número ANTERIOR al deseado.
Ejemplos:
    Si quieres empezar en ENTRANTE-2026-00973 → ancla en 00972
    Si quieres empezar en SALIENTE-2026-00673 → ancla en 00672
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction


class Command(BaseCommand):
    help = (
        'Inicializa los contadores de radicado para que arranquen '
        'desde números específicos. Por defecto: entrante=00973, saliente=00673.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--entrante',
            type=int,
            default=973,
            help='Número desde el que arrancará el consecutivo ENTRANTE (por defecto: 973)',
        )
        parser.add_argument(
            '--saliente',
            type=int,
            default=673,
            help='Número desde el que arrancará el consecutivo SALIENTE (por defecto: 673)',
        )
        parser.add_argument(
            '--año',
            dest='anio',
            type=int,
            default=timezone.now().year,
            help=f'Año del consecutivo (por defecto: {timezone.now().year})',
        )
        parser.add_argument(
            '--verificar',
            action='store_true',
            help='Solo muestra el estado actual y el próximo número sin hacer cambios',
        )

    def handle(self, *args, **options):
        from correspondencia.models import Correspondencia, CorrespondenciaSalida, OficinaProductora

        anio = options['anio']
        inicio_entrante = options['entrante']
        inicio_saliente = options['saliente']
        solo_verificar = options['verificar']

        self.stdout.write(self.style.HTTP_INFO(
            f'\n══════════════════════════════════════════'
        ))
        self.stdout.write(self.style.HTTP_INFO(
            f'  Inicializador de Contadores de Radicado'
        ))
        self.stdout.write(self.style.HTTP_INFO(
            f'══════════════════════════════════════════\n'
        ))

        # ── Estado actual ─────────────────────────────────────────────────────
        ultimo_entrante = Correspondencia.objects.filter(
            tipo_radicado='ENTRANTE',
            fecha_radicacion__year=anio
        ).order_by('fecha_radicacion').last()

        ultimo_saliente = CorrespondenciaSalida.objects.filter(
            fecha_creacion__year=anio
        ).order_by('fecha_creacion').last()

        def extraer_consecutivo(numero):
            if not numero:
                return 0
            try:
                return int(numero.split('-')[-1])
            except (ValueError, IndexError):
                return 0

        consecutivo_actual_entrante = extraer_consecutivo(
            ultimo_entrante.numero_radicado if ultimo_entrante else None
        )
        consecutivo_actual_saliente = extraer_consecutivo(
            ultimo_saliente.numero_radicado_salida if ultimo_saliente else None
        )

        self.stdout.write(f'Año objetivo:   {anio}')
        self.stdout.write(
            f'Entrante actual: último={consecutivo_actual_entrante:05d}  '
            f'→  próximo={consecutivo_actual_entrante + 1:05d}'
        )
        self.stdout.write(
            f'Saliente actual: último={consecutivo_actual_saliente:05d}  '
            f'→  próximo={consecutivo_actual_saliente + 1:05d}'
        )

        if solo_verificar:
            self.stdout.write(self.style.WARNING('\n(Modo --verificar: no se realizaron cambios)\n'))
            return

        # ── Validaciones ──────────────────────────────────────────────────────
        if consecutivo_actual_entrante >= inicio_entrante:
            raise CommandError(
                f'El último radicado entrante ({consecutivo_actual_entrante:05d}) ya es '
                f'>= al número deseado ({inicio_entrante:05d}). '
                f'No es posible retroceder el contador.'
            )
        if consecutivo_actual_saliente >= inicio_saliente:
            raise CommandError(
                f'El último radicado saliente ({consecutivo_actual_saliente:05d}) ya es '
                f'>= al número deseado ({inicio_saliente:05d}). '
                f'No es posible retroceder el contador.'
            )

        # El ancla debe tener el número ANTERIOR al deseado
        ancla_entrante = inicio_entrante - 1
        ancla_saliente = inicio_saliente - 1

        self.stdout.write(self.style.WARNING(
            f'\nSe crearán registros ancla con:'
        ))
        self.stdout.write(
            f'  ENTRANTE-{anio}-{ancla_entrante:05d}  '
            f'(el siguiente generado será {inicio_entrante:05d})'
        )
        self.stdout.write(
            f'  SALIENTE-{anio}-{ancla_saliente:05d}  '
            f'(el siguiente generado será {inicio_saliente:05d})'
        )

        # ── Obtener oficina para el ancla entrante ─────────────────────────────
        oficina = OficinaProductora.objects.first()
        if not oficina:
            raise CommandError(
                'No existe ninguna OficinaProductora en la base de datos. '
                'Ejecutá primero: python manage.py poblar_datos_iniciales'
            )

        # ── Crear anclas ──────────────────────────────────────────────────────
        with transaction.atomic():
            # ── Ancla ENTRANTE ─────────────────────────────────────────────────
            numero_ancla_ent = f'ENTRANTE-{anio}-{ancla_entrante:05d}'

            if Correspondencia.objects.filter(numero_radicado=numero_ancla_ent).exists():
                self.stdout.write(self.style.WARNING(
                    f'\n⚠  Ya existe {numero_ancla_ent}, no se crea de nuevo.'
                ))
            else:
                ancla_ent = Correspondencia(
                    tipo_radicado='ENTRANTE',
                    asunto='[ANCLA DE CONTADOR - NO USAR - registro de continuidad del sistema]',
                    oficina_destino=oficina,
                    origen_radicacion='NORMAL',
                    estado='RADICADA',
                )
                # Guardamos con save() para que pase por validaciones básicas,
                # luego sobreescribimos numero_radicado vía update() (bypass editable=False)
                ancla_ent.save()
                Correspondencia.objects.filter(pk=ancla_ent.pk).update(
                    numero_radicado=numero_ancla_ent
                )
                # Ajustamos fecha_radicacion al 1 de enero del año objetivo
                # para que quede ANTES de cualquier radicado real de ese año
                fecha_ancla = timezone.datetime(anio, 1, 1, 0, 0, 1, tzinfo=timezone.get_current_timezone())
                Correspondencia.objects.filter(pk=ancla_ent.pk).update(
                    fecha_radicacion=fecha_ancla
                )
                self.stdout.write(self.style.SUCCESS(
                    f'\n✓  Ancla entrante creada: {numero_ancla_ent}  (id={ancla_ent.pk})'
                ))

            # ── Ancla SALIENTE ─────────────────────────────────────────────────
            numero_ancla_sal = f'SALIENTE-{anio}-{ancla_saliente:05d}'

            if CorrespondenciaSalida.objects.filter(numero_radicado_salida=numero_ancla_sal).exists():
                self.stdout.write(self.style.WARNING(
                    f'⚠  Ya existe {numero_ancla_sal}, no se crea de nuevo.'
                ))
            else:
                ancla_sal = CorrespondenciaSalida(
                    asunto='[ANCLA DE CONTADOR - NO USAR - registro de continuidad del sistema]',
                    cuerpo='Registro de continuidad. No contiene correspondencia real.',
                    estado='BORRADOR',
                )
                ancla_sal.save()
                CorrespondenciaSalida.objects.filter(pk=ancla_sal.pk).update(
                    numero_radicado_salida=numero_ancla_sal
                )
                fecha_ancla = timezone.datetime(anio, 1, 1, 0, 0, 1, tzinfo=timezone.get_current_timezone())
                CorrespondenciaSalida.objects.filter(pk=ancla_sal.pk).update(
                    fecha_creacion=fecha_ancla
                )
                self.stdout.write(self.style.SUCCESS(
                    f'✓  Ancla saliente creada: {numero_ancla_sal}  (id={ancla_sal.pk})'
                ))

        # ── Verificación post-creación ─────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('\n── Verificación final ────────────────────'))

        proximo_ent = Correspondencia.objects.filter(
            tipo_radicado='ENTRANTE',
            fecha_radicacion__year=anio
        ).order_by('fecha_radicacion').last()

        proximo_sal = CorrespondenciaSalida.objects.filter(
            fecha_creacion__year=anio
        ).order_by('fecha_creacion').last()

        consec_ent = extraer_consecutivo(proximo_ent.numero_radicado if proximo_ent else None)
        consec_sal = extraer_consecutivo(proximo_sal.numero_radicado_salida if proximo_sal else None)

        self.stdout.write(
            f'Próximo ENTRANTE :  ENTRANTE-{anio}-{consec_ent + 1:05d}'
        )
        self.stdout.write(
            f'Próximo SALIENTE :  SALIENTE-{anio}-{consec_sal + 1:05d}'
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Contadores inicializados correctamente.\n'
        ))
