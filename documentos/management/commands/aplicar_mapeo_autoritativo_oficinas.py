from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from documentos.models import OficinaProductora, Proceso
from documentos.oficinas_autoritativas import MAPPINGS, normalizar


class Command(BaseCommand):
    help = 'Aplica mapeo autoritativo de sigla, código SIS y código TRD a oficinas productoras.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Aplica cambios en la base de datos. Sin este flag, solo simula.')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        alias_map = {}
        for mapping in MAPPINGS:
            for alias in mapping['aliases']:
                alias_map[normalizar(alias)] = mapping

        procesos = {proceso.sigla: proceso for proceso in Proceso.objects.all()}
        actualizaciones = []
        no_mapeadas = []

        oficinas = OficinaProductora.objects.select_related('proceso').annotate(total_usuarios=Count('perfilusuario'))
        for oficina in oficinas:
            mapping = alias_map.get(normalizar(oficina.nombre))
            if not mapping:
                no_mapeadas.append(oficina)
                continue

            proceso_destino = procesos.get(mapping['sigla'])
            if not proceso_destino:
                self.stdout.write(self.style.ERROR(f"No existe el proceso con sigla {mapping['sigla']} para {oficina.nombre}"))
                continue

            cambios = {}
            if oficina.proceso_id != proceso_destino.id:
                cambios['proceso'] = (oficina.proceso.sigla if oficina.proceso_id else None, proceso_destino.sigla)
                oficina.proceso = proceso_destino
            if str(oficina.codigo or '') != mapping['codigo']:
                cambios['codigo'] = (oficina.codigo, mapping['codigo'])
                oficina.codigo = mapping['codigo']
            if str(oficina.codigo_trd or '') != mapping['codigo_trd']:
                cambios['codigo_trd'] = (oficina.codigo_trd, mapping['codigo_trd'])
                oficina.codigo_trd = mapping['codigo_trd']

            if cambios:
                actualizaciones.append((oficina, cambios))

        self.stdout.write(self.style.WARNING('SIMULACION' if not apply_changes else 'APLICACION REAL'))
        self.stdout.write(f'Oficinas con cambios detectados: {len(actualizaciones)}')
        for oficina, cambios in actualizaciones:
            resumen = ', '.join(f"{campo}: {antes} -> {despues}" for campo, (antes, despues) in cambios.items())
            self.stdout.write(f"- {oficina.id} | {oficina.nombre} | usuarios={getattr(oficina, 'total_usuarios', 0)} | {resumen}")

        self.stdout.write(f'Oficinas sin mapeo autoritativo: {len(no_mapeadas)}')
        for oficina in sorted(no_mapeadas, key=lambda item: (-(getattr(item, 'total_usuarios', 0)), item.nombre))[:20]:
            self.stdout.write(f"  ? {oficina.id} | {oficina.nombre} | sigla={oficina.proceso.sigla if oficina.proceso_id else 'SIN'} | codigo={oficina.codigo} | trd={oficina.codigo_trd} | usuarios={getattr(oficina, 'total_usuarios', 0)}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING('No se aplicaron cambios. Use --apply para persistir.'))
            return

        with transaction.atomic():
            for oficina, _cambios in actualizaciones:
                oficina.save(update_fields=['proceso', 'codigo', 'codigo_trd'])

        self.stdout.write(self.style.SUCCESS(f'Se aplicaron {len(actualizaciones)} actualizaciones.'))