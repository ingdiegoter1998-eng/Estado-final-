"""
Comando para corregir oficinas productoras asignándolas a procesos correctos y agregando códigos
Uso: python manage.py corregir_oficinas
"""
from django.core.management.base import BaseCommand
from documentos.models import OficinaProductora, Proceso
from django.db import transaction


class Command(BaseCommand):
    help = 'Corrige oficinas productoras asignándolas a procesos correctos y agregando códigos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando corrección de oficinas productoras...'))
        
        # Datos: Macroproceso, No. Proceso, Proceso (Líder), Sigla, Cód. Sub, Subproceso/Servicio
        datos_csv = """
ESTRATÉGICOS,1,DIRECCIONAMIENTO ESTRATÉGICO,DIR,1,Gerencia - Dirección
,1,DIRECCIONAMIENTO ESTRATÉGICO,DIR,2,Planeación
,1,DIRECCIONAMIENTO ESTRATÉGICO,DIR,3,Gestión de mercadeo y venta de servicios
,2,GESTIÓN ESTRATÉGICA DE TALENTO HUMANO,THS,0,Comunicación e imagen corporativa
,2,GESTIÓN ESTRATÉGICA DE TALENTO HUMANO,THS,1,Talento Humano
,2,GESTIÓN ESTRATÉGICA DE TALENTO HUMANO,THS,2,Seguridad y Salud Laboral
,2,GESTIÓN ESTRATÉGICA DE TALENTO HUMANO,THS,3,Gestión de Docencia - Servicio e Investigación
,3,SISTEMA INTEGRADO DE GESTIÓN,SIG,1,Control Disciplinario Interno
,3,SISTEMA INTEGRADO DE GESTIÓN,SIG,2,Gestión de la Calidad
,3,SISTEMA INTEGRADO DE GESTIÓN,SIG,3,Gestión Ambiental
MISIONALES,4,GESTIÓN DE LA SEGURIDAD EN ATENCIÓN,GCL,0,Gestión y administración del riesgo
,4,GESTIÓN DE LA SEGURIDAD EN ATENCIÓN,GCL,1,Gestión de la Seguridad del paciente (Programas)
,4,GESTIÓN DE LA EXPERIENCIA DEL USUARIO,SIC,0,Prevención y control de IAAS
,4,GESTIÓN DE LA EXPERIENCIA DEL USUARIO,SIC,1,Humanización en los servicios de Salud
,4,GESTIÓN DE LA EXPERIENCIA DEL USUARIO,SIC,2,Trabajo Social
,5,GESTIÓN DE ATENCIÓN PRIMARIA EN SALUD,GAP,0,Sistema de atención al Usuario
,6,CONSULTA EXTERNA,CEX,1,Gestión del Riesgo en Salud (Rutas PyM, Vacunación)
,6,CONSULTA EXTERNA,CEX,2,Consulta General (Medicina, Odontología, etc.)
,7,INTERNACIÓN,INT,1,Consulta Especializada y subespecialidades
,7,INTERNACIÓN,INT,2,Internación Adulto
,7,INTERNACIÓN,INT,3,Internación Pediátrico
,7,INTERNACIÓN,INT,4,Internación Neonatal (Básica y UCIM)
,7,INTERNACIÓN,INT,5,Unidad de Cuidado Crítico (UCI/UCE Adulto)
,8,ATENCIÓN INMEDIATA,ATI,1,Obstetricia y Atención del Parto
,8,ATENCIÓN INMEDIATA,ATI,2,Urgencias y Procedimientos
,9,GRUPO QUIRÚRGICO,CIX,1,Referencia y Contra-referencia
,9,GRUPO QUIRÚRGICO,CIX,2,Servicio de Cirugía
,10,APOYO DIAGNÓSTICO,ADG,1,Servicio de Esterilización
,10,APOYO DIAGNÓSTICO,ADG,2,Servicio de Laboratorio Clínico
,11,COMPLEMENTACIÓN TERAPÉUTICA,CTR,1,Servicio de Imágenes Diagnósticas
,11,COMPLEMENTACIÓN TERAPÉUTICA,CTR,2,Banco de Sangre y Gestión pre-transfusional
,11,COMPLEMENTACIÓN TERAPÉUTICA,CTR,3,Servicio Farmacéutico
DE APOYO,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,1,Servicio de Terapias
,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,2,Gestión de la Contabilidad
,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,3,Gestión del Presupuesto
,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,4,Gestión de Tesorería
,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,5,Gestión del Gasto y costo
,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,6,Gestión de Cartera
,12,GESTIÓN FINANCIERA Y ADMINISTRATIVA,GFI,7,Facturación
,13,GESTIÓN JURÍDICA,JUR,1,Cuentas médicas, auditoría y Glosas
,13,GESTIÓN JURÍDICA,JUR,2,Defensa Jurídica
,14,GESTIÓN INTEGRAL DE LA INFORMACIÓN,SIS,1,Contratación
,14,GESTIÓN INTEGRAL DE LA INFORMACIÓN,SIS,2,Gestión de Tecnologías y Sistemas de Información
,14,GESTIÓN INTEGRAL DE LA INFORMACIÓN,SIS,3,Historias Clínicas
,14,GESTIÓN INTEGRAL DE LA INFORMACIÓN,SIS,4,Gestión Documental
,14,GESTIÓN INTEGRAL DE LA INFORMACIÓN,SIS,5,Unidad de vigilancia epidemiológica
,15,ALMACÉN,GCA,1,Unidad de estadísticas y análisis de datos
,16,GESTIÓN Y MANTENIMIENTO,AFT,1,Almacén / Gestión de insumos y suministros
,16,GESTIÓN Y MANTENIMIENTO,AFT,2,Mantenimiento de Infraestructura y Vehículos
,16,GESTIÓN Y MANTENIMIENTO,AFT,3,Gestión Biomédica
,16,GESTIÓN Y MANTENIMIENTO,AFT,4,Servicios Básicos
CONTROL,17,INSTITUCIONAL,SEI,1,Gestión de Redes de tecnología y equipos
"""
        
        # Parsear datos
        lineas = [l.strip() for l in datos_csv.strip().split('\n') if l.strip()]
        
        # Mapeo para normalizar nombres y encontrar coincidencias
        def normalizar_nombre(nombre):
            """Normaliza un nombre para comparación"""
            import re
            # Minúsculas y quitar acentos básicos
            nombre = nombre.lower()
            nombre = nombre.replace('á', 'a').replace('é', 'e').replace('í', 'i')
            nombre = nombre.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
            # Quitar caracteres especiales y espacios extras
            nombre = re.sub(r'[^\w\s]', ' ', nombre)
            nombre = re.sub(r'\s+', ' ', nombre).strip()
            return nombre
        
        def buscar_oficina(nombre_csv):
            """Busca oficina por nombre (coincidencia flexible)"""
            nombre_norm = normalizar_nombre(nombre_csv)
            
            # Buscar todas las oficinas
            oficinas = OficinaProductora.objects.all()
            
            # Búsqueda exacta normalizada
            for o in oficinas:
                if normalizar_nombre(o.nombre) == nombre_norm:
                    return o
            
            # Búsqueda por palabras clave principales
            palabras_clave = [p for p in nombre_norm.split() if len(p) > 3]
            for o in oficinas:
                nombre_oficina_norm = normalizar_nombre(o.nombre)
                coincidencias = sum(1 for p in palabras_clave if p in nombre_oficina_norm)
                if coincidencias >= len(palabras_clave) * 0.6:  # 60% de coincidencia
                    return o
            
            return None
        
        corregidas = 0
        no_encontradas = []
        
        with transaction.atomic():
            self.stdout.write('\nCorrigiendo oficinas...\n')
            
            for linea in lineas:
                partes = [p.strip() for p in linea.split(',')]
                
                sigla = partes[3]
                codigo_sub = partes[4]
                nombre_subproceso = partes[5]
                
                # Buscar proceso por sigla
                try:
                    proceso = Proceso.objects.get(sigla=sigla)
                except Proceso.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  ✗ Proceso {sigla} no encontrado'))
                    continue
                
                # Buscar oficina por nombre
                oficina = buscar_oficina(nombre_subproceso)
                
                if oficina:
                    # Actualizar proceso y código
                    oficina.proceso = proceso
                    oficina.codigo = codigo_sub
                    oficina.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ {oficina.nombre[:40]:40} → {sigla} (código: {codigo_sub})'
                    ))
                    corregidas += 1
                else:
                    no_encontradas.append(nombre_subproceso)
                    self.stdout.write(self.style.WARNING(
                        f'  ? No encontrada: {nombre_subproceso[:50]}'
                    ))
        
        # Resumen
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS(f'✓ Corrección completada'))
        self.stdout.write(f'  Oficinas corregidas: {corregidas}')
        self.stdout.write(f'  No encontradas: {len(no_encontradas)}')
        
        if no_encontradas:
            self.stdout.write('\n📋 Oficinas no encontradas (pueden necesitar crearse):')
            for nombre in no_encontradas:
                self.stdout.write(f'  - {nombre}')
        
        self.stdout.write('='*80)
