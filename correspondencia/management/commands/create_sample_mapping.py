import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from datetime import datetime
from correspondencia.modelos_minimos_sla import TramiteTipo, CalendarioLaboral, SubserieTramite

class Command(BaseCommand):
    help = 'Crea un mapeo de ejemplo entre una subserie y un tipo de trámite para pruebas SLA.'

    def add_arguments(self, parser):
        parser.add_argument('--subserie-id', type=int, help='ID de la subserie a mapear')
        parser.add_argument('--tramite-codigo', type=str, default='DP_GENERAL', 
                           help='Código del tipo de trámite (default: DP_GENERAL)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creando mapeo de ejemplo...'))

        subserie_id = options['subserie_id']
        tramite_codigo = options['tramite_codigo']

        if not subserie_id:
            self.stdout.write(self.style.WARNING(
                'No se especificó subserie_id. Use --subserie-id <ID> para crear un mapeo.'
            ))
            return

        try:
            with transaction.atomic():
                # Obtener el tipo de trámite
                try:
                    tramite = TramiteTipo.objects.get(codigo=tramite_codigo)
                except TramiteTipo.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f'No se encontró el tipo de trámite con código: {tramite_codigo}'
                    ))
                    return

                # Verificar si ya existe un mapeo para esta subserie
                existing_mapping = SubserieTramite.objects.filter(subserie_id=subserie_id).first()
                
                if existing_mapping:
                    # Actualizar el mapeo existente
                    existing_mapping.tramite = tramite
                    existing_mapping.save()
                    self.stdout.write(self.style.SUCCESS(
                        f'ACTUALIZADO: Subserie {subserie_id} -> {tramite.codigo} ({tramite.nombre})'
                    ))
                else:
                    # Crear nuevo mapeo
                    # Necesitamos importar SubserieDocumental
                    try:
                        from documentos.models import SubserieDocumental
                        subserie = SubserieDocumental.objects.get(id=subserie_id)
                        
                        mapping = SubserieTramite.objects.create(
                            subserie=subserie,
                            tramite=tramite
                        )
                        
                        self.stdout.write(self.style.SUCCESS(
                            f'CREADO: Subserie {subserie_id} ({subserie.nombre}) -> {tramite.codigo} ({tramite.nombre})'
                        ))
                        
                    except ImportError:
                        self.stdout.write(self.style.ERROR(
                            'No se pudo importar SubserieDocumental. Asegúrese de que la app documentos esté disponible.'
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f'Error al crear mapeo: {e}'
                        ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
