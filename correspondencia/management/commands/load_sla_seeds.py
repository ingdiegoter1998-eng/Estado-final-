"""Comando para cargar/actualizar seeds relacionados con los plazos legales (SLA)."""

import csv
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from correspondencia.modelos_minimos_sla import TramiteTipo, CalendarioLaboral


class Command(BaseCommand):
    help = (
        "Carga datos iniciales para los modelos de SLA, incluyendo tipos de "
        "trámite predefinidos y, opcionalmente, un calendario laboral "
        "proveniente de un archivo CSV (YYYY-MM-DD,es_habil)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--feriados-csv",
            dest="feriados_csv",
            type=str,
            help="Ruta al CSV con feriados/calendario laboral.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Tipos de trámite"))
        seeds = [
            ("DP_INFO", "Derecho de Petición - Información", 10, "Ley 1755/2015 art. 14"),
            ("DP_GENERAL", "Derecho de Petición - General", 15, "Ley 1755/2015 art. 14"),
            ("DP_CONSULTA", "Derecho de Petición - Consulta", 30, "Ley 1755/2015 art. 14"),
        ]

        for codigo, nombre, plazo, fundamento in seeds:
            obj, created = TramiteTipo.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "plazo_dias_habiles": plazo,
                    "fundamento_normativo": fundamento,
                    "activo": True,
                },
            )
            action = "CREADO" if created else "ACTUALIZADO"
            self.stdout.write(f" - {action}: {obj}")

        csv_path = options.get("feriados_csv")
        if csv_path:
            if not os.path.isfile(csv_path):
                raise CommandError(f"Archivo CSV no encontrado: {csv_path}")

            self.stdout.write(self.style.MIGRATE_HEADING("Calendario laboral"))
            with open(csv_path, newline="", encoding="utf-8") as fh:
                reader = csv.reader(fh)
                for row in reader:
                    if not row or row[0].startswith("#"):
                        continue
                    fecha_str = row[0].strip()
                    if not fecha_str:
                        continue
                    try:
                        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    except ValueError as exc:
                        self.stdout.write(self.style.WARNING(f"Fecha inválida '{fecha_str}': {exc}"))
                        continue

                    es_habil = True
                    if len(row) > 1:
                        es_habil = row[1].strip().lower() in {"1", "true", "si", "sí"}

                    CalendarioLaboral.objects.update_or_create(
                        fecha=fecha, defaults={"es_habil": es_habil}
                    )
            self.stdout.write(self.style.SUCCESS("Calendario laboral procesado satisfactoriamente."))

        self.stdout.write(self.style.SUCCESS("Seeds de SLA cargados con éxito."))
