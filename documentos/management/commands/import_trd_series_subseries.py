import csv
import os
import re
import unicodedata
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand, CommandError

from documentos.models import SerieDocumental, SubserieDocumental


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_header(header: str) -> str:
    h = normalize_text(header).lower()
    h = re.sub(r"[^a-z0-9]+", "_", h).strip("_")
    aliases = {
        "entidad_productora": "entidad_productora",
        "nombre_oficina_productora": "oficina_nombre",
        "c_d_oficina_productora": "codigo_oficina",
        "cd_oficina_productora": "codigo_oficina",
        "cod_oficina_productora": "codigo_oficina",
        "cod_serie": "codigo_serie",
        "c_d_serie": "codigo_serie",
        "serie_documental": "serie_documental",
        "cod_sub_serie": "codigo_subserie",
        "c_d_sub_serie": "codigo_subserie",
        "cod_subserie": "codigo_subserie",
        "c_d_subserie": "codigo_subserie",
        "subserie_documental": "subserie_documental",
    }
    return aliases.get(h, h)


def pad_component(comp: str) -> str:
    if comp is None:
        return ""
    comp = comp.strip()
    if not comp:
        return ""
    if comp.isdigit():
        # zero-pad to 2 only for 1-digit numbers
        return str(int(comp)).zfill(2) if int(comp) < 100 else str(int(comp))
    return comp


def extract_components(code: str):
    if code is None:
        return "", "", ""
    raw = code.strip().replace(" ", "")
    parts = raw.split(".")
    oficina = parts[0] if parts else ""
    serie = parts[1] if len(parts) > 1 else ""
    sub = parts[2] if len(parts) > 2 else ""
    return oficina, pad_component(serie), pad_component(sub)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def normalize_for_match(value: str) -> str:
    s = normalize_text(value).lower()
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    return s.strip()


class Command(BaseCommand):
    help = "Actualiza codigo_trd en series y subseries existentes desde SERIES Y SUBSERIES.csv. NO crea registros nuevos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            default="dataUnidad/SERIES Y SUBSERIES.csv",
            help="Ruta al CSV de TRD (por defecto dataUnidad/SERIES Y SUBSERIES.csv)",
        )
        parser.add_argument(
            "--threshold",
            dest="threshold",
            type=float,
            default=0.85,
            help="Umbral de similitud para fuzzy match de subseries (default 0.85)",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Solo mostrar acciones, no guardar",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        dry_run = options["dry_run"]
        threshold = options["threshold"]

        if not os.path.exists(file_path):
            raise CommandError(f"No existe el archivo: {file_path}")

        # Detectar encoding
        encodings = ["utf-8", "latin-1"]
        content = None
        chosen_enc = None
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                    chosen_enc = enc
                    break
            except UnicodeDecodeError:
                continue
        if content is None:
            raise CommandError("No se pudo leer el archivo con UTF-8 ni Latin-1")

        # Detectar delimitador
        try:
            dialect = csv.Sniffer().sniff(content[:2048])
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ";" if ";" in content[:2048] else ","

        rows = list(csv.reader(content.splitlines(), delimiter=delimiter))
        if not rows:
            raise CommandError("El archivo está vacío")

        headers = [normalize_header(h) for h in rows[0]]
        try:
            idx_serie_codigo = headers.index("codigo_serie")
            idx_serie_nombre = headers.index("serie_documental")
            idx_sub_codigo = headers.index("codigo_subserie")
            idx_sub_nombre = headers.index("subserie_documental")
        except ValueError:
            raise CommandError("Faltan columnas requeridas: CÓD. SERIE, SERIE DOCUMENTAL, CÓD. SUB/SERIE, SUBSERIE DOCUMENTAL")

        updated_series = 0
        updated_sub = 0
        not_found_series = 0
        not_found_sub = 0
        fuzzy_matched_sub = 0
        skipped = 0

        for i, row in enumerate(rows[1:], start=2):
            try:
                serie_code_full = normalize_text(row[idx_serie_codigo])
                serie_name = normalize_text(row[idx_serie_nombre])
                sub_code_full = normalize_text(row[idx_sub_codigo])
                sub_name = normalize_text(row[idx_sub_nombre])

                if not serie_code_full or not serie_name:
                    skipped += 1
                    continue

                oficina_part, serie_part, sub_part = extract_components(serie_code_full)
                serie_trd = serie_part

                # Buscar serie existente por codigo o nombre
                serie_obj = None
                try:
                    serie_obj = SerieDocumental.objects.filter(codigo=serie_code_full).first()
                except Exception:
                    pass
                
                if not serie_obj and serie_name:
                    serie_obj = SerieDocumental.objects.filter(nombre__iexact=serie_name).first()
                
                if not serie_obj:
                    not_found_series += 1
                    continue

                # Actualizar codigo_trd de serie si está vacío y tenemos valor
                if serie_trd and not serie_obj.codigo_trd:
                    if dry_run:
                        self.stdout.write(f"[L{i}] DRY-RUN: Actualizar serie '{serie_obj.nombre}' codigo_trd='{serie_trd}'")
                    else:
                        serie_obj.codigo_trd = serie_trd
                        serie_obj.save(update_fields=["codigo_trd"])
                    updated_series += 1

                # Subserie
                if not sub_name or not sub_code_full:
                    continue

                _, _, sub_trd = extract_components(sub_code_full)
                
                # Buscar subserie exacta (por codigo o nombre)
                sub_obj = None
                try:
                    sub_obj = SubserieDocumental.objects.filter(serie=serie_obj, codigo=sub_code_full).first()
                except Exception:
                    pass
                
                if not sub_obj and sub_name:
                    sub_obj = SubserieDocumental.objects.filter(serie=serie_obj, nombre__iexact=sub_name).first()
                
                # Si no encontró exacta, buscar por similitud fuzzy
                if not sub_obj:
                    target_norm = normalize_for_match(sub_name)
                    best_match = None
                    best_score = 0.0
                    
                    for candidate in serie_obj.subseriedocumental_set.all():
                        score = similarity(target_norm, normalize_for_match(candidate.nombre))
                        if score > best_score:
                            best_score = score
                            best_match = candidate
                    
                    if best_match and best_score >= threshold:
                        sub_obj = best_match
                        fuzzy_matched_sub += 1
                
                if not sub_obj:
                    not_found_sub += 1
                    continue

                # Actualizar codigo_trd de subserie si está vacío y tenemos valor
                if sub_trd and not sub_obj.codigo_trd:
                    if dry_run:
                        self.stdout.write(f"[L{i}] DRY-RUN: Actualizar subserie '{sub_obj.nombre}' codigo_trd='{sub_trd}'")
                    else:
                        sub_obj.codigo_trd = sub_trd
                        sub_obj.save(update_fields=["codigo_trd"])
                    updated_sub += 1

            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"[L{i}] Error: {exc}"))
                skipped += 1
                continue

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Series actualizadas:{updated_series}, Subseries actualizadas:{updated_sub}, "
            f"Subseries con fuzzy match:{fuzzy_matched_sub}, Series no encontradas:{not_found_series}, "
            f"Subseries no encontradas:{not_found_sub}, Omitidas:{skipped}."
        ))
