"""
Comando para actualizar las fechas de lectura de las distribuciones internas
que ya estaban marcadas como leídas pero no tienen fecha_lectura.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from correspondencia.models import DistribucionInternaUsuario


class Command(BaseCommand):
    help = 'Actualiza las fechas de lectura para distribuciones ya marcadas como leídas'

    def handle(self, *args, **options):
        # Buscar distribuciones marcadas como leídas pero sin fecha_lectura
        distribuciones_sin_fecha = DistribucionInternaUsuario.objects.filter(
            leido=True,
            fecha_lectura__isnull=True
        )
        
        total = distribuciones_sin_fecha.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ No hay distribuciones por actualizar'))
            return
        
        self.stdout.write(f'Encontradas {total} distribuciones sin fecha de lectura...')
        
        actualizadas = 0
        for dist in distribuciones_sin_fecha:
            # Usar la fecha de asignación como fecha de lectura aproximada
            # (asumimos que se leyó poco después de ser asignada)
            dist.fecha_lectura = dist.fecha_asignacion
            dist.save(update_fields=['fecha_lectura'])
            actualizadas += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Actualizadas {actualizadas} distribuciones con fecha de lectura')
        )

