import os
import sys
import django
from difflib import SequenceMatcher

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_document_management.settings')
sys.path.insert(0, '/home/devdiego/Correspondencia-diciembre-1.0')
django.setup()

from documentos.models import OficinaProductora
import csv

def similitud_string(a, b):
    """
    Calcula similitud entre dos strings normalizando ambos.
    Retorna un valor entre 0 y 1 (1 = idénticos).
    """
    # Normalizar: minúsculas, sin espacios extra, sin acentos
    def normalizar(s):
        s = s.lower().strip()
        # Remover caracteres especiales
        s = ''.join(c for c in s if c.isalnum() or c.isspace())
        return s
    
    a_norm = normalizar(a)
    b_norm = normalizar(b)
    
    return SequenceMatcher(None, a_norm, b_norm).ratio()

def cargar_datos_csv(ruta_csv):
    """Carga los datos del CSV con código y nombre de subproceso."""
    datos = {}
    with open(ruta_csv, 'r', encoding='utf-8') as f:
        # Leer sin DictReader para evitar problemas con encabezados
        lines = f.readlines()
    
    # Procesar líneas manualmente (saltando el encabezado)
    for line in lines[3:]:  # Saltar las primeras 3 líneas del encabezado
        line = line.strip()
        if not line:
            continue
        
        # Dividir por primera coma
        parts = line.split(',', 1)
        if len(parts) == 2:
            codigo = parts[0].strip()
            nombre = parts[1].strip().strip('"')
            if codigo and nombre:
                # Limpiar el nombre (remover saltos de línea internos)
                nombre = ' '.join(nombre.split())
                datos[nombre] = codigo
    
    return datos

def actualizar_codigos_oficinas(ruta_csv, tolerancia=0.85):
    """
    Actualiza los códigos de las oficinas usando matching flexible.
    
    Args:
        ruta_csv: Ruta al archivo CSV
        tolerancia: Umbral de similitud (0.85 = 85% de similitud)
    """
    print("🔄 Iniciando actualización de códigos de oficinas...\n")
    
    # Cargar datos del CSV
    datos_csv = cargar_datos_csv(ruta_csv)
    print(f"✓ Cargados {len(datos_csv)} registros del CSV\n")
    
    # Obtener todas las oficinas
    oficinas = OficinaProductora.objects.all()
    print(f"✓ Encontradas {oficinas.count()} oficinas en la base de datos\n")
    
    actualizadas = 0
    no_coincidentes = []
    
    for oficina in oficinas:
        nombre_oficina = oficina.nombre
        mejor_match = None
        mejor_similitud = 0
        mejor_codigo = None
        
        # Buscar el mejor match en los datos del CSV
        for nombre_csv, codigo_csv in datos_csv.items():
            similitud = similitud_string(nombre_oficina, nombre_csv)
            
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_match = nombre_csv
                mejor_codigo = codigo_csv
        
        # Si la similitud supera el umbral, actualizar
        if mejor_similitud >= tolerancia:
            codigo_anterior = oficina.codigo
            oficina.codigo = mejor_codigo
            oficina.save(update_fields=['codigo'])
            
            print(f"✅ {oficina.nombre}")
            print(f"   Similitud: {mejor_similitud:.1%}")
            print(f"   Código anterior: {codigo_anterior or 'sin asignar'}")
            print(f"   Código nuevo: {mejor_codigo}")
            print(f"   Match: {mejor_match}\n")
            
            actualizadas += 1
        else:
            print(f"⚠️  {oficina.nombre}")
            print(f"   Similitud: {mejor_similitud:.1%} (umbral: {tolerancia:.1%})")
            print(f"   Mejor match encontrado: {mejor_match} (código: {mejor_codigo})\n")
            
            no_coincidentes.append({
                'nombre': nombre_oficina,
                'similitud': mejor_similitud,
                'match_csv': mejor_match,
                'codigo_csv': mejor_codigo
            })
    
    # Resumen
    print("\n" + "="*70)
    print(f"📊 RESUMEN")
    print("="*70)
    print(f"✓ Oficinas actualizadas: {actualizadas}")
    print(f"⚠️  Oficinas sin match confiable: {len(no_coincidentes)}\n")
    
    if no_coincidentes:
        print("Oficinas que requieren revisión manual:\n")
        for item in no_coincidentes:
            print(f"  • {item['nombre']}")
            print(f"    Similitud: {item['similitud']:.1%}")
            print(f"    Sugerencia: {item['match_csv']} (código: {item['codigo_csv']})\n")

if __name__ == '__main__':
    # Ruta al archivo CSV (ajustar si es necesario)
    csv_path = '/home/devdiego/Correspondencia-diciembre-1.0/mapa_procesos.csv'
    
    # Crear el archivo CSV si no existe (para descargar el archivo adjunto)
    if not os.path.exists(csv_path):
        print(f"⚠️  El archivo CSV no se encontró en {csv_path}")
        print("Por favor, descarga el archivo adjunto y colócalo en esa ruta.\n")
        sys.exit(1)
    
    actualizar_codigos_oficinas(csv_path, tolerancia=0.85)
