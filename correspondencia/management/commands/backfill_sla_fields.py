from django.core.management.base import BaseCommand
from django.db import transaction

from correspondencia.models import Correspondencia


class Command(BaseCommand):
    help = "Calcula y persiste campos SLA (plazo_respuesta_dias, fecha_limite_respuesta_persist, plazo_origen, tramite_aplicado) para correspondencias existentes."

    def add_arguments(self, parser):
        parser.add_argument('--ids', nargs='+', type=int, help='IDs específicos a recalcular (opcional)')

    @transaction.atomic
    def handle(self, *args, **options):
        qs = Correspondencia.objects.all()
        if options.get('ids'):
            qs = qs.filter(id__in=options['ids'])

        total = qs.count()
        procesados = 0
        self.stdout.write(self.style.NOTICE(f"Procesando {total} correspondencias..."))

        for c in qs.iterator():
            # Reutilizamos la lógica del modelo
            c._recalcular_sla_persistido()
            c.save(update_fields=[
                'tiempo_respuesta',
                'plazo_respuesta_dias',
                'fecha_limite_respuesta_persist',
                'plazo_origen',
                'tramite_aplicado',
            ])
            procesados += 1
            if procesados % 100 == 0:
                self.stdout.write(self.style.SUCCESS(f"{procesados}/{total}..."))

        self.stdout.write(self.style.SUCCESS(f"Listo. Recalculados {procesados} registros."))


