"""
Comando para corregir las oficinas faltantes y crear proceso SIC
Uso: python manage.py corregir_oficinas_faltantes
"""
from django.core.management.base import BaseCommand
from documentos.models import OficinaProductora, Proceso, MacroProceso
from django.db import transaction
from django.db.models import Max


class Command(BaseCommand):
    help = 'Corrige las 8 oficinas faltantes creando proceso SIC y asignándolas correctamente'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando corrección de oficinas faltantes...'))
        
        with transaction.atomic():
            # Primero crear el proceso SIC que faltaba
            macroproceso_misionales = MacroProceso.objects.get(nombre='MISIONALES')
            
            # Intentar obtener el proceso SIC si existe
            try:
                proceso_sic = Proceso.objects.get(sigla='SIC')
                created = False
            except Proceso.DoesNotExist:
                # Obtener el siguiente número disponible en MISIONALES
                ultimo_numero = Proceso.objects.filter(
                    macroproceso=macroproceso_misionales
                ).aggregate(Max('numero'))['numero__max'] or 0
                
                proceso_sic = Proceso.objects.create(
                    numero=ultimo_numero + 1,
                    nombre='GESTIÓN DE LA EXPERIENCIA DEL USUARIO',
                    sigla='SIC',
                    macroproceso=macroproceso_misionales
                )
                created = True
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Proceso SIC creado'))
            else:
                self.stdout.write(self.style.WARNING(f'✓ Proceso SIC ya existía'))
            
            # Ahora corregir las oficinas faltantes
            correcciones = [
                # Proceso SIC
                {
                    'nombre_actual': 'Prevención y Control de IAAS',
                    'proceso_sigla': 'SIC',
                    'codigo': '0'
                },
                {
                    'nombre_actual': 'Humanización en los Servicios de Salud',
                    'proceso_sigla': 'SIC',
                    'codigo': '1'
                },
                {
                    'nombre_actual': 'Trabajo Social',
                    'proceso_sigla': 'SIC',
                    'codigo': '2'
                },
                # Proceso SIS
                {
                    'nombre_actual': 'Historia Clínica',
                    'nombre_nuevo': 'Historias Clínicas',
                    'proceso_sigla': 'SIS',
                    'codigo': '3'
                },
                {
                    'nombre_actual': 'Estadísticas',
                    'nombre_nuevo': 'Unidad de Estadísticas y Análisis de Datos',
                    'proceso_sigla': 'GCA',
                    'codigo': '1'
                },
                # Proceso DIR - Consulta Complementaria
                {
                    'nombre_actual': 'Consulta Complementaria (Nutrición, Psicología,...',
                    'nombre_nuevo': 'Consulta Complementaria (Nutrición, Psicología, Trabajo Social)',
                    'proceso_sigla': 'CEX',
                    'codigo': '3'
                },
                # Control Interno y Subgerencia administrativa quedan en DIR
                # ya que no aparecen en el CSV
            ]
            
            oficinas_corregidas = 0
            
            for correccion in correcciones:
                nombre_actual = correccion['nombre_actual']
                proceso_sigla = correccion['proceso_sigla']
                codigo = correccion['codigo']
                nombre_nuevo = correccion.get('nombre_nuevo', nombre_actual)
                
                try:
                    proceso = Proceso.objects.get(sigla=proceso_sigla)
                    oficina = OficinaProductora.objects.get(nombre__icontains=nombre_actual[:30])
                    
                    oficina.proceso = proceso
                    oficina.codigo = codigo
                    oficina.nombre = nombre_nuevo
                    oficina.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {nombre_actual[:40]:<40} → {proceso_sigla} (código: {codigo})'
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
                except OficinaProductora.MultipleObjectsReturned:
                    self.stdout.write(
                        self.style.WARNING(f'? Múltiples coincidencias para: {nombre_actual}')
                    )
        
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'✓ Corrección completada'))
        self.stdout.write(f'  Oficinas corregidas: {oficinas_corregidas}')
        self.stdout.write('=' * 80)
