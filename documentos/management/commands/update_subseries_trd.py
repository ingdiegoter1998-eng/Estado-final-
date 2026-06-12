from django.core.management.base import BaseCommand, CommandError
from documentos.models import SerieDocumental, SubserieDocumental
import csv
import os
import unicodedata
import re


def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return s


def normalize_header(h: str) -> str:
    """Normaliza nombres de columnas para mapear más fácilmente."""
    h = normalize_text(h).lower()
    h = re.sub(r"[^a-z0-9]+", "_", h)
    h = h.strip('_')
    # Mapeos comunes del dataset proporcionado
    aliases = {
        'entidad_productora': 'entidad_productora',
        'nombre_oficina_productora': 'oficina_nombre',
        'cod_oficina_productora': 'codigo_oficina',
        'cod_serie': 'codigo_serie',
        'serie_documental': 'serie_documental',
        'cod_sub_serie': 'codigo_subserie',
        'subserie_documental': 'subserie_documental',
    }
    return aliases.get(h, h)


def normalize_trd_code(code: str) -> str:
    """
    Normaliza el código TRD de subserie:
    - Quita espacios
    - Elimina ceros u otros caracteres antes del primer '3'
    - Asegura que comience con '3'
    - Quita puntos al inicio/fin
    Ej: "0300.02.03" -> "300.02.03"
    """
    if code is None:
        return ""
    s = str(code).strip().replace(' ', '')
    # Buscar la primera ocurrencia de '3' y cortar desde allí
    m = re.search(r"3[0-9.]*", s)
    if m:
        s = m.group(0)
    # Remover puntos iniciales/finales accidentales
    s = s.strip('.')
    return s


class Command(BaseCommand):
    help = "Actualiza/crea SubserieDocumental asignando codigo_trd desde un archivo CSV/TSV (dataset TRD). Normaliza códigos que empiezan en 0 para que inicien en 3."

    def add_arguments(self, parser):
        parser.add_argument('--file', dest='file', required=True, help='Ruta del archivo CSV/TSV con columnas: CÓD. SERIE, SERIE DOCUMENTAL, CÓD. SUB/SERIE, SUBSERIE DOCUMENTAL')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true', help='Solo muestra cambios sin escribir en BD')

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options.get('dry_run', False)

        if not os.path.exists(file_path):
            raise CommandError(f"No existe el archivo: {file_path}")

        # Detectar delimitador automáticamente
        with open(file_path, 'r', encoding='utf-8') as f:
            sample = f.read(2048)
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                # Por defecto, tablero (TSV) o coma si no hay tabs
                delimiter = '\t' if '\t' in sample else ','

        created = 0
        updated = 0
        skipped = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
            if not rows:
                raise CommandError('El archivo está vacío')

            headers = [normalize_header(h) for h in rows[0]]
            # Construir índice de columnas
            try:
                idx_serie_codigo = headers.index('codigo_serie')
                idx_serie_nombre = headers.index('serie_documental')
                idx_sub_codigo = headers.index('codigo_subserie')
                idx_sub_nombre = headers.index('subserie_documental')
            except ValueError:
                raise CommandError('El archivo no contiene las columnas necesarias: CÓD. SERIE, SERIE DOCUMENTAL, CÓD. SUB/SERIE, SUBSERIE DOCUMENTAL')

            for i, row in enumerate(rows[1:], start=2):
                try:
                    serie_codigo_raw = normalize_text(row[idx_serie_codigo])
                    serie_nombre = normalize_text(row[idx_serie_nombre])
                    sub_codigo_raw = normalize_text(row[idx_sub_codigo])
                    sub_nombre = normalize_text(row[idx_sub_nombre])

                    if not sub_nombre:
                        skipped += 1
                        continue

                    sub_codigo_trd = normalize_trd_code(sub_codigo_raw)
                    if not sub_codigo_trd or not sub_codigo_trd.startswith('3'):
                        # Si después de normalizar no comienza con '3', descartar
                        self.stdout.write(self.style.WARNING(f"[L{i}] Código subserie inválido tras normalizar: '{sub_codigo_raw}' -> '{sub_codigo_trd}'. Se omite."))
                        skipped += 1
                        continue

                    # Serie: asegurar existencia por código; si no hay código, por nombre
                    serie_obj = None
                    if serie_codigo_raw:
                        try:
                            serie_obj, _ = SerieDocumental.objects.get_or_create(
                                codigo=serie_codigo_raw,
                                defaults={'nombre': serie_nombre or serie_codigo_raw}
                            )
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"[L{i}] Error creando/obteniendo serie '{serie_codigo_raw}': {e}"))
                    if serie_obj is None:
                        # fallback por nombre
                        if serie_nombre:
                            serie_obj, _ = SerieDocumental.objects.get_or_create(
                                nombre=serie_nombre,
                                defaults={'codigo': serie_codigo_raw or ''}
                            )
                        else:
                            self.stdout.write(self.style.WARNING(f"[L{i}] Sin datos de serie. Se omite fila."))
                            skipped += 1
                            continue

                    # Subserie: buscar por (serie, nombre)
                    try:
                        sub_obj, created_flag = SubserieDocumental.objects.get_or_create(
                            serie=serie_obj,
                            nombre=sub_nombre,
                            defaults={'codigo_trd': sub_codigo_trd}
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"[L{i}] Error creando subserie '{sub_nombre}': {e}"))
                        skipped += 1
                        continue

                    if created_flag:
                        created += 1
                        action = 'CREATED'
                    else:
                        action = 'UNCHANGED'

                    # Actualizar codigo_trd si difiere
                    if sub_obj.codigo_trd != sub_codigo_trd:
                        if dry_run:
                            updated += 1
                            self.stdout.write(f"[L{i}] DRY-RUN: actualizar codigo_trd de '{sub_nombre}' -> '{sub_codigo_trd}'")
                        else:
                            sub_obj.codigo_trd = sub_codigo_trd
                            sub_obj.save(update_fields=['codigo_trd'])
                            updated += 1
                            action = 'UPDATED'

                    self.stdout.write(f"[L{i}] {action}: Serie='{serie_obj.codigo or serie_obj.nombre}' Subserie='{sub_nombre}' codigo_trd='{sub_codigo_trd}'")

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"[L{i}] Error procesando fila: {e}"))
                    skipped += 1
                    continue

        self.stdout.write(self.style.SUCCESS(f"Finalizado. Creadas: {created}, Actualizadas: {updated}, Omitidas: {skipped}"))
