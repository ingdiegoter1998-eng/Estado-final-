"""
Comando para listar oficinas productoras actuales
"""
from django.core.management.base import BaseCommand
from documentos.models import OficinaProductora


class Command(BaseCommand):
    help = 'Lista las oficinas productoras actuales'

    def handle(self, *args, **options):
        oficinas = OficinaProductora.objects.select_related('proceso', 'proceso__macroproceso').order_by('proceso__numero', 'codigo')
        
        self.stdout.write(self.style.SUCCESS(f'\n Total oficinas: {oficinas.count()}\n'))
        self.stdout.write('='*100)
        self.stdout.write(f"{'Cód':>4} | {'Sigla':>4} | {'Nombre Oficina':<50} | {'Proceso'}")
        self.stdout.write('='*100)
        
        for o in oficinas:
            codigo = o.codigo or 'N/A'
            sigla = o.proceso.sigla if o.proceso else 'N/A'
            nombre = o.nombre[:47] + '...' if len(o.nombre) > 50 else o.nombre
            proceso = o.proceso.nombre if o.proceso else 'Sin proceso'
            
            self.stdout.write(f"{codigo:>4} | {sigla:>4} | {nombre:<50} | {proceso}")
        
        self.stdout.write('='*100)
