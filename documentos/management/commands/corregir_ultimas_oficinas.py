"""
Comando para corregir las 2 últimas oficinas que faltaban
Uso: python manage.py corregir_ultimas_oficinas
"""
from django.core.management.base import BaseCommand
from documentos.models import OficinaProductora, Proceso
from django.db import transaction


class Command(BaseCommand):
    help = 'Corrige las 2 últimas oficinas: Control Interno y Subgerencia administrativa'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Corrigiendo últimas 2 oficinas...'))
        
        with transaction.atomic():
            correcciones = [
                {
                    'nombre_actual': 'Control Interno',
                    'proceso_sigla': 'DIR',  # Parte del direccionamiento estratégico
                    'codigo': '0'
                },
                {
                    'nombre_actual': 'Subgerencia administrativa y financiera',
                    'proceso_sigla': 'GFI',  # Gestión Financiera y Administrativa
                    'codigo': '0'
                },
            ]
            
            oficinas_corregidas = 0
            
            for correccion in correcciones:
                nombre_actual = correccion['nombre_actual']
                proceso_sigla = correccion['proceso_sigla']
                codigo = correccion['codigo']
                
                try:
                    proceso = Proceso.objects.get(sigla=proceso_sigla)
                    oficina = OficinaProductora.objects.get(nombre=nombre_actual)
                    
                    oficina.proceso = proceso
                    oficina.codigo = codigo
                    oficina.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {nombre_actual:<45} → {proceso_sigla} (código: {codigo})'
                        )
                    )
                    oficinas_corregidas += 1
                    
                except Proceso.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Proceso {proceso_sigla} no encontrado')
                    )
                except OficinaProductora.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'? No encontrada: {nombre_actual}')
                    )
        
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'✓ Corrección completada'))
        self.stdout.write(f'  Oficinas corregidas: {oficinas_corregidas}')
        self.stdout.write('=' * 80)
