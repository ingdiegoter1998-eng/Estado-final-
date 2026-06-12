import csv
import sys
import re
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand, CommandError
from documentos.models import OficinaProductora

class Command(BaseCommand):
    help = 'Importa los códigos TRD de oficinas productoras desde CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='dataUnidad/SERIES Y SUBSERIES.csv',
            help='Ruta del archivo CSV con datos de series y subseries'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.70,
            help='Umbral de similitud para fuzzy matching (0.0-1.0, default 0.70)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular la importación sin hacer cambios en la BD'
        )

    def detect_encoding_and_delimiter(self, file_path):
        """Detecta encoding y delimiter del archivo CSV"""
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    sample = f.read(1024)
                    # Detectar delimiter
                    if ',' in sample:
                        return encoding, ','
                    elif ';' in sample:
                        return encoding, ';'
                    elif '\t' in sample:
                        return encoding, '\t'
                    else:
                        return encoding, ','
            except (UnicodeDecodeError, IOError):
                continue
        
        raise CommandError(f"No se pudo detectar encoding para {file_path}")

    def normalize_text(self, text):
        """Normaliza texto eliminando acentos y espacios extras"""
        if not text:
            return ""
        
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', str(text))
        return ''.join([c for c in nfkd if not unicodedata.combining(c)]).strip()

    def normalize_for_match(self, text):
        """Normaliza para matching: minúsculas, sin acentos, sin puntuación"""
        if not text:
            return ""
        text = self.normalize_text(text).lower()
        # Remover caracteres especiales pero mantener espacios
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Colapsar espacios múltiples
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def similarity(self, a, b):
        """Calcula similitud entre dos strings"""
        a_norm = self.normalize_for_match(a)
        b_norm = self.normalize_for_match(b)
        return SequenceMatcher(None, a_norm, b_norm).ratio()

    def extract_oficina_code(self, codigo_trd_completo):
        """
        Extrae el código de oficina del formato 300.02.03
        Retorna solo 300
        """
        if not codigo_trd_completo:
            return None
        
        # El código de oficina es la primera parte antes del primer punto
        partes = str(codigo_trd_completo).split('.')
        if partes:
            try:
                return partes[0].strip()
            except:
                return None
        return None

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        threshold = options['threshold']

        try:
            encoding, delimiter = self.detect_encoding_and_delimiter(file_path)
            self.stdout.write(f"Detectado: encoding={encoding}, delimiter='{delimiter}'")
        except CommandError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                if not reader.fieldnames:
                    raise CommandError("El archivo CSV está vacío o no tiene encabezados")

                # Mapear columnas exactas disponibles
                nombre_oficina_col = 'NOMBRE OFICINA PRODUCTORA'
                codigo_subserie_col = 'CÓD. SUB/SERIE'

                # Verificar que existan
                if nombre_oficina_col not in reader.fieldnames or codigo_subserie_col not in reader.fieldnames:
                    self.stdout.write(self.style.WARNING(f"Columnas disponibles: {list(reader.fieldnames)}"))
                    raise CommandError(f"No se encontraron columnas requeridas")

                self.stdout.write(f"Usando columnas: Oficina='{nombre_oficina_col}', Código TRD='{codigo_subserie_col}'")
                self.stdout.write(f"Threshold de similitud: {threshold}")

                # Cargar todas las oficinas para referencia
                todas_oficinas = list(OficinaProductora.objects.all())
                self.stdout.write(f"Total de oficinas en BD: {len(todas_oficinas)}")

                oficinas_actualizadas = 0
                oficinas_fuzzy = 0
                codigos_vistos = set()
                no_encontradas = []

                for row_num, row in enumerate(reader, start=2):
                    nombre_oficina = row.get(nombre_oficina_col, '').strip()
                    codigo_trd_completo = row.get(codigo_subserie_col, '').strip()

                    if not nombre_oficina or not codigo_trd_completo:
                        continue

                    # Extrae código de oficina (primera parte del TRD)
                    codigo_oficina = self.extract_oficina_code(codigo_trd_completo)

                    if not codigo_oficina:
                        continue

                    # Evitar duplicados (por si hay múltiples subseries de la misma oficina)
                    if codigo_oficina in codigos_vistos:
                        continue

                    codigos_vistos.add(codigo_oficina)

                    # Intento 1: Búsqueda exacta
                    oficina = OficinaProductora.objects.filter(
                        nombre__iexact=nombre_oficina
                    ).first()

                    best_score = 1.0  # Para tracking de fuzzy match
                    
                    # Intento 2: Si ya tiene codigo_trd, skip
                    if oficina and oficina.codigo_trd:
                        continue

                    # Intento 3: Fuzzy matching
                    if not oficina:
                        best_match = None
                        best_score = 0.0

                        for candidate in todas_oficinas:
                            if candidate.codigo_trd:  # Skip si ya tiene código
                                continue
                            
                            score = self.similarity(nombre_oficina, candidate.nombre)
                            if score > best_score:
                                best_score = score
                                best_match = candidate

                        if best_match and best_score >= threshold:
                            oficina = best_match

                    # Actualizar si encontró
                    if oficina:
                        if dry_run:
                            self.stdout.write(
                                f"DRY-RUN: Actualizar oficina '{nombre_oficina}' → '{oficina.nombre}' codigo_trd='{codigo_oficina}'"
                            )
                            if best_score < 1.0 and best_score >= threshold:
                                self.stdout.write(f"         (fuzzy match: {best_score:.2f})")
                        else:
                            oficina.codigo_trd = codigo_oficina
                            oficina.save()
                            if best_score < 1.0 and best_score >= threshold:
                                self.stdout.write(
                                    f"✓ Oficina fuzzy '{nombre_oficina}' → '{oficina.nombre}' codigo_trd='{codigo_oficina}' ({best_score:.2f})"
                                )
                                oficinas_fuzzy += 1
                            else:
                                self.stdout.write(
                                    f"✓ Oficina exacta '{nombre_oficina}' codigo_trd='{codigo_oficina}'"
                                )
                                oficinas_actualizadas += 1
                    else:
                        no_encontradas.append((nombre_oficina, codigo_oficina))

                self.stdout.write(self.style.SUCCESS(
                    f"\nListo. Oficinas exactas:{oficinas_actualizadas}, "
                    f"Oficinas fuzzy:{oficinas_fuzzy}, "
                    f"Oficinas no encontradas:{len(no_encontradas)}."
                ))

                if no_encontradas:
                    self.stdout.write(self.style.WARNING("\nOficinas no encontradas:"))
                    for nombre, codigo in no_encontradas:
                        self.stdout.write(f"  • {nombre} (TRD: {codigo})")

        except FileNotFoundError:
            raise CommandError(f"Archivo no encontrado: {file_path}")
        except Exception as e:
            raise CommandError(f"Error al procesar el archivo: {str(e)}")

