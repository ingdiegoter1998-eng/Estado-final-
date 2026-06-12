def normalizar(valor):
    reemplazos = str.maketrans({
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n',
        'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u', 'Ü': 'u', 'Ñ': 'n',
    })
    texto = (valor or '').translate(reemplazos).lower().strip()
    limpio = []
    for caracter in texto:
        if caracter.isalnum() or caracter.isspace():
            limpio.append(caracter)
        else:
            limpio.append(' ')
    return ' '.join(''.join(limpio).split())


PROCESO_NUMEROS_AUTORITATIVOS = {
    'DIR': 1,
    'THS': 2,
    'SIG': 3,
    'GCL': 4,
    'GAP': 5,
    'CEX': 6,
    'INT': 7,
    'ATI': 8,
    'CIX': 9,
    'ADG': 10,
    'CTR': 11,
    'SIC': 12,
    'GFI': 12,
    'JUR': 13,
    'SIS': 14,
    'GCA': 15,
    'AFT': 16,
    'SEI': 17,
}


MAPPINGS = [
    {'nombre': 'Gerencia - Dirección', 'sigla': 'DIR', 'codigo': '0', 'codigo_trd': '300', 'aliases': ['gerencia direccion', 'gerencia direccion.']},
    {'nombre': 'Planeación', 'sigla': 'DIR', 'codigo': '1', 'codigo_trd': '323', 'aliases': ['planeacion']},
    {'nombre': 'Gestión de Mercadeo y Venta de Servicios', 'sigla': 'DIR', 'codigo': '2', 'codigo_trd': '320.6', 'aliases': ['gestion de mercadeo y venta de servicios']},
    {'nombre': 'Comunicación e Imagen Corporativa', 'sigla': 'DIR', 'codigo': '3', 'codigo_trd': '322.1', 'aliases': ['comunicacion e imagen corporativa']},
    {'nombre': 'Subgerencia Talento Humano', 'sigla': 'THS', 'codigo': '0', 'codigo_trd': '321', 'aliases': ['talento humano', 'subgerencia talento humano']},
    {'nombre': 'Gestión de Seguridad y Salud en el Trabajo', 'sigla': 'THS', 'codigo': '1', 'codigo_trd': '316', 'aliases': ['seguridad y salud laboral', 'gestion de seguridad y salud en el trabajo']},
    {'nombre': 'Gestión de Docencia Servicio e Investigación', 'sigla': 'THS', 'codigo': '2', 'codigo_trd': '320', 'aliases': ['gestion de docencia servicio e investigacion', 'gestion de docencia servicio e investigacion.']},
    {'nombre': 'Control Disciplinario Interno', 'sigla': 'THS', 'codigo': '3', 'codigo_trd': '301', 'aliases': ['control disciplinario interno']},
    {'nombre': 'Gestión de la Calidad', 'sigla': 'SIG', 'codigo': '1', 'codigo_trd': '303', 'aliases': ['gestion de la calidad']},
    {'nombre': 'Gestión Ambiental', 'sigla': 'SIG', 'codigo': '2', 'codigo_trd': '316', 'aliases': ['gestion ambiental']},
    {'nombre': 'Gestión y Administración del Riesgo', 'sigla': 'SIG', 'codigo': '3', 'codigo_trd': '320', 'aliases': ['gestion y administracion del riesgo']},
    {'nombre': 'Gestión de la Seguridad del Paciente', 'sigla': 'GCL', 'codigo': '0', 'codigo_trd': '310', 'aliases': ['gestion de la seguridad del paciente', 'gestion de la seguridad del paciente programas']},
    {'nombre': 'Prevención y Control de IAAS', 'sigla': 'GCL', 'codigo': '1', 'codigo_trd': '310', 'aliases': ['prevencion y control de iaas']},
    {'nombre': 'Humanización en los Servicios de Salud', 'sigla': 'SIC', 'codigo': '0', 'codigo_trd': '310', 'aliases': ['humanizacion en los servicios de salud']},
    {'nombre': 'Trabajo Social', 'sigla': 'SIC', 'codigo': '1', 'codigo_trd': '313', 'aliases': ['trabajo social']},
    {'nombre': 'Sistema de Atención al Usuario', 'sigla': 'SIC', 'codigo': '2', 'codigo_trd': '313', 'aliases': ['sistema de atencion al usuario']},
    {'nombre': 'Gestión del Riesgo en Salud, Rutas de Atención Integral PyM. (Vacunación, Mamografías, Toma de Muestras)', 'sigla': 'GAP', 'codigo': '0', 'codigo_trd': '311', 'aliases': ['gestion del riesgo en salud', 'gestion del riesgo en salud rutas de atencion integral pym vacunacion mamografias toma de muestras']},
    {'nombre': 'Consulta General (Medicina General, Odontología General, Radiología Odontológica)', 'sigla': 'CEX', 'codigo': '1', 'codigo_trd': '311', 'aliases': ['consulta general', 'consulta general medicina general odontologia general radiologia odontologica']},
    {'nombre': 'Consulta Especializada y Subespecialidad (Intramural, Extramural, Telemedicina)', 'sigla': 'CEX', 'codigo': '2', 'codigo_trd': '311', 'aliases': ['consulta especializada y subespecialidad', 'consulta especializada y subespecialidad intramural extramural telemedicina']},
    {'nombre': 'Internación Adulto (Hospitalización Medicina Interna, Hospitalización Quirúrgicos)', 'sigla': 'INT', 'codigo': '1', 'codigo_trd': '312', 'aliases': ['internacion adulto', 'internacion adulto hospitalizacion medicina interna hospitalizacion quirurgicos']},
    {'nombre': 'Internación Pediátrico (Hospitalización Pediatría)', 'sigla': 'INT', 'codigo': '2', 'codigo_trd': '312', 'aliases': ['internacion pediatrico', 'internacion pediatrico hospitalizacion pediatria']},
    {'nombre': 'Internación Neonatal (Unidad Básica Neonatal, UCIM y UCI Neonatal)', 'sigla': 'INT', 'codigo': '3', 'codigo_trd': '312', 'aliases': ['internacion neonatal', 'internacion neonatal unidad basica neonatal ucim y uci neonatal']},
    {'nombre': 'Unidad de Cuidado Crítico (Intermedio e Intensivo - Adulto)', 'sigla': 'INT', 'codigo': '4', 'codigo_trd': '312', 'aliases': ['unidad de cuidado critico', 'unidad de cuidado critico intermedio e intensivo adulto']},
    {'nombre': 'Obstetricia y Atención del Parto (Urgencias Maternas, Atención del Parto y Hospitalización Maternidad)', 'sigla': 'INT', 'codigo': '5', 'codigo_trd': '312', 'aliases': ['obstetricia y atencion del parto', 'obstetricia y atencion del parto urgencias maternas atencion del parto y hospitalizacion maternidad']},
    {'nombre': 'Urgencias y Procedimientos', 'sigla': 'ATI', 'codigo': '1', 'codigo_trd': '314', 'aliases': ['urgencias y procedimientos']},
    {'nombre': 'Referencia y Contrarreferencia', 'sigla': 'ATI', 'codigo': '2', 'codigo_trd': '314', 'aliases': ['referencia y contrarreferencia', 'referencia y contra referencia']},
    {'nombre': 'Servicio de Cirugía', 'sigla': 'CIX', 'codigo': '1', 'codigo_trd': '315', 'aliases': ['servicio de cirugia']},
    {'nombre': 'Servicio de Esterilización', 'sigla': 'CIX', 'codigo': '2', 'codigo_trd': '315', 'aliases': ['servicio de esterilizacion']},
    {'nombre': 'Servicio de Laboratorio Clínico (Toma de Muestra de Laboratorio Clínico)', 'sigla': 'ADG', 'codigo': '1', 'codigo_trd': '313', 'aliases': ['servicio de laboratorio clinico', 'servicio de laboratorio clinico toma de muestra de laboratorio clinico']},
    {'nombre': 'Servicio de Imágenes Diagnósticas (Tomografía, Radiología, Ecografía)', 'sigla': 'ADG', 'codigo': '2', 'codigo_trd': '313', 'aliases': ['servicio de imagenes diagnosticas', 'servicio de imagenes diagnosticas tomografia radiologia ecografia']},
    {'nombre': 'Banco de Sangre y Servicio de Gestión Pre-Transfusional', 'sigla': 'CTR', 'codigo': '1', 'codigo_trd': '313', 'aliases': ['banco de sangre y servicio de gestion pre transfusional', 'banco de sangre y servicio de gestion pretransfusional']},
    {'nombre': 'Servicio Farmacéutico', 'sigla': 'CTR', 'codigo': '2', 'codigo_trd': '320.2', 'aliases': ['servicio farmaceutico']},
    {'nombre': 'Servicio de Terapias (Terapia Física, Respiratoria, Ocupacional, Fonoaudiología)', 'sigla': 'CTR', 'codigo': '3', 'codigo_trd': '313', 'aliases': ['servicio de terapias', 'servicio de terapias terapia fisica respiratoria ocupacional fonoaudiologia']},
    {'nombre': 'Gestión de la Contabilidad', 'sigla': 'GFI', 'codigo': '1', 'codigo_trd': '320.5', 'aliases': ['gestion de la contabilidad']},
    {'nombre': 'Gestión del Presupuesto', 'sigla': 'GFI', 'codigo': '2', 'codigo_trd': '320.5', 'aliases': ['gestion del presupuesto']},
    {'nombre': 'Gestión de Tesorería', 'sigla': 'GFI', 'codigo': '3', 'codigo_trd': '320.4', 'aliases': ['gestion de tesoreria']},
    {'nombre': 'Gestión del Gasto', 'sigla': 'GFI', 'codigo': '4', 'codigo_trd': '320.8', 'aliases': ['gestion del gasto y costo', 'gestion del gasto']},
    {'nombre': 'Gestión de Cartera', 'sigla': 'GFI', 'codigo': '5', 'codigo_trd': '320.6', 'aliases': ['gestion de cartera']},
    {'nombre': 'Facturación', 'sigla': 'GFI', 'codigo': '6', 'codigo_trd': '320.9', 'aliases': ['facturacion']},
    {'nombre': 'Cuentas Médicas y Gestión de Glosas', 'sigla': 'GFI', 'codigo': '7', 'codigo_trd': '320', 'aliases': ['cuentas medicas auditoria y gestion de glosas', 'cuentas medicas y gestion de glosas']},
    {'nombre': 'Defensa Jurídica', 'sigla': 'JUR', 'codigo': '1', 'codigo_trd': '301', 'aliases': ['defensa juridica']},
    {'nombre': 'Contratación', 'sigla': 'JUR', 'codigo': '2', 'codigo_trd': '320', 'aliases': ['contratacion']},
    {'nombre': 'Gestión de las Tecnologías y Sistemas de Información', 'sigla': 'SIS', 'codigo': '1', 'codigo_trd': '322', 'aliases': ['gestion de las tecnologias y sistemas de informacion', 'gestion de tecnologias y sistemas de informacion']},
    {'nombre': 'Historias Clínicas', 'sigla': 'SIS', 'codigo': '2', 'codigo_trd': '320', 'aliases': ['historias clinicas', 'historias clinica']},
    {'nombre': 'Gestión Documental (Archivo Central y Unidad de Correspondencia)', 'sigla': 'SIS', 'codigo': '3', 'codigo_trd': '320.3', 'aliases': ['gestion documental archivo central y unidad de correspondencia', 'gestion documental']},
    {'nombre': 'Unidad de Vigilancia Epidemiológica', 'sigla': 'SIS', 'codigo': '4', 'codigo_trd': '320', 'aliases': ['unidad de vigilancia epidemiologica']},
    {'nombre': 'Unidad de Estadísticas y Análisis de Datos', 'sigla': 'SIS', 'codigo': '5', 'codigo_trd': '322.2', 'aliases': ['unidad de estadisticas y analisis de datos']},
    {'nombre': 'Almacén/Gestión de Insumos, Suministros, Inventario y Activos.', 'sigla': 'GCA', 'codigo': '1', 'codigo_trd': '320.1', 'aliases': ['almacen gestion de insumos y suministros', 'almacen gestion de insumos suministros inventario y activos']},
    {'nombre': 'Gestión del Mantenimiento de la Infraestructura Física Hospitalaria, Equipos Industriales y Vehículos', 'sigla': 'AFT', 'codigo': '1', 'codigo_trd': '323.1', 'aliases': ['gestion del mantenimiento de la infraestructura fisica hospitalaria equipos industriales y vehiculos']},
    {'nombre': 'Gestión Biomédica', 'sigla': 'AFT', 'codigo': '2', 'codigo_trd': '320', 'aliases': ['gestion biomedica']},
    {'nombre': 'Servicios Básicos', 'sigla': 'AFT', 'codigo': '3', 'codigo_trd': '321.2', 'aliases': ['servicios basicos']},
    {'nombre': 'Gestión de Redes de Tecnología y Equipos Informáticos', 'sigla': 'AFT', 'codigo': '4', 'codigo_trd': '320', 'aliases': ['gestion de redes de tecnologia y equipos informaticos']},
    {'nombre': 'Control Interno', 'sigla': 'SEI', 'codigo': '1', 'codigo_trd': '302', 'aliases': ['control interno']},
]


def codigo_dependencia_esperado(sigla, proceso_numero, codigo_oficina):
    return f"{sigla}-{int(proceso_numero):02d}-{int(str(codigo_oficina).strip()):03d}"


OFICINAS_RADICADO_DEFINIDAS = tuple(
    {
        **mapping,
        'proceso_numero': PROCESO_NUMEROS_AUTORITATIVOS[mapping['sigla']],
        'codigo_dependencia': codigo_dependencia_esperado(
            mapping['sigla'],
            PROCESO_NUMEROS_AUTORITATIVOS[mapping['sigla']],
            mapping['codigo'],
        ),
    }
    for mapping in MAPPINGS
)


OFICINAS_RADICADO_PENDIENTES = (
    {
        'nombre': 'Subgerencia administrativa y financiera',
        'motivo': 'Duplica el prefijo GFI-12-001 con Gestión de la Contabilidad. Requiere código propio o exclusión del flujo.',
    },
    {
        'nombre': 'COORDINACIÓN ENFERMERIA',
        'motivo': 'No tiene código numérico ni definición autoritativa cerrada.',
    },
    {
        'nombre': 'COORDINACIÓN MÉDICA',
        'motivo': 'No tiene código numérico ni definición autoritativa cerrada.',
    },
    {
        'nombre': 'Consulta Complementaria (Nutrición, Psicología, Trabajo Social)',
        'motivo': 'Hoy duplica el prefijo CEX-06-001 con Consulta General; requiere código propio o integración funcional.',
    },
    {
        'nombre': 'Gestión de la Seguridad del paciente',
        'motivo': 'Parece duplicado nominal de Gestión de la Seguridad del Paciente; requiere depuración de maestro.',
    },
    {
        'nombre': 'U.F. SERVICIOS HOSPITALARIOS',
        'motivo': 'Las unidades ATS usan el mismo proceso y código 1; requieren definición separada si van a radicar internas.',
    },
    {
        'nombre': 'U.F.SERVICIOS AMBULATORIOS',
        'motivo': 'Las unidades ATS usan el mismo proceso y código 1; requieren definición separada si van a radicar internas.',
    },
    {
        'nombre': 'UF.APOYO DIAGNOSTICO Y TERAPEUTICO',
        'motivo': 'Las unidades ATS usan el mismo proceso y código 1; requieren definición separada si van a radicar internas.',
    },
    {
        'nombre': 'Of tmp, Of tmp2, Of tmp3, Of tmp4, Of tmp5, Of tmp6, Of tmp7, Of tmp8, Of tmp9',
        'motivo': 'Oficinas temporales sin código numérico ni definición archivística válida.',
    },
)