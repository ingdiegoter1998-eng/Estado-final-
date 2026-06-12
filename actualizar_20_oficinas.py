import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_document_management.settings')
sys.path.insert(0, '/home/devdiego/Correspondencia-diciembre-1.0')
django.setup()

from documentos.models import OficinaProductora

# Mapeo manual de las 20 oficinas
actualizaciones = [
    ("Subgerencia Talento Humano", "0"),
    ("Gerencia - Dirección", "0"),
    ("Gestión de Seguridad y Salud en el Trabajo", "1"),
    ("Gestión del Gasto", "4"),
    ("Almacén/Gestión de Insumos, Suministros, Inventario y Activos.", "1"),
    ("Gestión del Riesgo en Salud, Rutas de Atención Integral PyM. (Vacunación, Mamografías, Toma de Muestras)", "0"),
    ("Consulta General (Medicina General, Odontología General, Radiología Odontológica)", "1"),
    ("Consulta Complementaria (Nutrición, Psicología, Trabajo Social)", "1"),
    ("Consulta Especializada y Subespecialidad (Intramural, Extramural, Telemedicina)", "2"),
    ("Internación Adulto (Hospitalización Medicina Interna, Hospitalización Quirúrgicos)", "1"),
    ("Internación Pediátrico (Hospitalización Pediatría)", "2"),
    ("Internación Neonatal (Unidad Básica Neonatal, UCIM y UCI Neonatal)", "3"),
    ("Obstetricia y Atención del Parto (Urgencias Maternas, Atención del Parto y Hospitalización Maternidad)", "5"),
    ("Servicio de Laboratorio Clínico (Toma de Muestra de Laboratorio Clínico)", "1"),
    ("Servicio de Imágenes Diagnósticas (Tomografía, Radiología, Ecografía)", "2"),
    ("Servicio de Terapias (Terapia Física, Respiratoria, Ocupacional, Fonoaudiología)", "3"),
    ("Subgerencia administrativa y financiera", "1"),
    ("U.F. SERVICIOS HOSPITALARIOS", "1"),
    ("U.F.SERVICIOS AMBULATORIOS", "1"),
    ("UF.APOYO DIAGNOSTICO Y TERAPEUTICO", "1"),
]

print("🔄 Actualizando manualmente 20 oficinas...\n")

actualizadas = 0
no_encontradas = []

for nombre_oficina, codigo in actualizaciones:
    try:
        oficina = OficinaProductora.objects.get(nombre=nombre_oficina)
        codigo_anterior = oficina.codigo
        oficina.codigo = codigo
        oficina.save(update_fields=['codigo'])
        
        print(f"✅ {nombre_oficina}")
        print(f"   Código anterior: {codigo_anterior or 'sin asignar'}")
        print(f"   Código nuevo: {codigo}\n")
        
        actualizadas += 1
    except OficinaProductora.DoesNotExist:
        print(f"❌ NO ENCONTRADA: {nombre_oficina}")
        print(f"   Código sugerido: {codigo}\n")
        no_encontradas.append((nombre_oficina, codigo))

print("\n" + "="*70)
print(f"📊 RESUMEN ACTUALIZACIÓN MANUAL")
print("="*70)
print(f"✓ Oficinas actualizadas: {actualizadas}")
print(f"❌ Oficinas no encontradas: {len(no_encontradas)}\n")

if no_encontradas:
    print("Oficinas que no se encontraron en la BD:\n")
    for nombre, codigo in no_encontradas:
        print(f"  • {nombre} (código sugerido: {codigo})")
