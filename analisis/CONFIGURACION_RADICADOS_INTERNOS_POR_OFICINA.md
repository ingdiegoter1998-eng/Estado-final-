# Configuración de Radicados Internos por Oficina

## Regla cerrada

El radicado interno debe salir con este formato:

SIGLA-CODIGO_OFICINA-CONSECUTIVO

Ejemplo:

- DIR-03-005
- SIS-03-005

Donde:

- SIGLA: sigla del proceso.
- CODIGO_OFICINA: código numérico de la oficina en dos dígitos en el radicado interno.
- CONSECUTIVO: consecutivo por oficina, en tres dígitos.

Nota:

- El año del documento sigue guardándose como metadato archivístico, pero ya no hace parte visible del radicado de comunicaciones internas.

La TRD de comunicaciones internas sale desde backend con esta regla:

- TRD = codigo_trd de oficina + codigo_trd de serie + codigo_trd de subserie.

## Oficinas ya definidas

Estas son las configuraciones que ya quedaron definidas como válidas para comunicaciones internas:

| Oficina | Sigla | Proceso | Código oficina | Código dependencia esperado | Código TRD oficina |
| --- | --- | --- | --- | --- | --- |
| Gerencia - Dirección | DIR | 01 | 000 | DIR-01-000 | 300 |
| Planeación | DIR | 01 | 001 | DIR-01-001 | 323 |
| Gestión de Mercadeo y Venta de Servicios | DIR | 01 | 002 | DIR-01-002 | 320.6 |
| Comunicación e Imagen Corporativa | DIR | 01 | 003 | DIR-01-003 | 322.1 |
| Subgerencia Talento Humano | THS | 02 | 000 | THS-02-000 | 321 |
| Gestión de Seguridad y Salud en el Trabajo | THS | 02 | 001 | THS-02-001 | 316 |
| Gestión de Docencia Servicio e Investigación | THS | 02 | 002 | THS-02-002 | 320 |
| Control Disciplinario Interno | THS | 02 | 003 | THS-02-003 | 301 |
| Gestión de la Calidad | SIG | 03 | 001 | SIG-03-001 | 303 |
| Gestión Ambiental | SIG | 03 | 002 | SIG-03-002 | 316 |
| Gestión y Administración del Riesgo | SIG | 03 | 003 | SIG-03-003 | 320 |
| Gestión de la Seguridad del Paciente | GCL | 04 | 000 | GCL-04-000 | 310 |
| Prevención y Control de IAAS | GCL | 04 | 001 | GCL-04-001 | 310 |
| Gestión del Riesgo en Salud, Rutas de Atención Integral PyM. (Vacunación, Mamografías, Toma de Muestras) | GAP | 05 | 000 | GAP-05-000 | 311 |
| Consulta General (Medicina General, Odontología General, Radiología Odontológica) | CEX | 06 | 001 | CEX-06-001 | 311 |
| Consulta Especializada y Subespecialidad (Intramural, Extramural, Telemedicina) | CEX | 06 | 002 | CEX-06-002 | 311 |
| Internación Adulto (Hospitalización Medicina Interna, Hospitalización Quirúrgicos) | INT | 07 | 001 | INT-07-001 | 312 |
| Internación Pediátrico (Hospitalización Pediatría) | INT | 07 | 002 | INT-07-002 | 312 |
| Internación Neonatal (Unidad Básica Neonatal, UCIM y UCI Neonatal) | INT | 07 | 003 | INT-07-003 | 312 |
| Unidad de Cuidado Crítico (Intermedio e Intensivo - Adulto) | INT | 07 | 004 | INT-07-004 | 312 |
| Obstetricia y Atención del Parto (Urgencias Maternas, Atención del Parto y Hospitalización Maternidad) | INT | 07 | 005 | INT-07-005 | 312 |
| Urgencias y Procedimientos | ATI | 08 | 001 | ATI-08-001 | 314 |
| Referencia y Contrarreferencia | ATI | 08 | 002 | ATI-08-002 | 314 |
| Servicio de Cirugía | CIX | 09 | 001 | CIX-09-001 | 315 |
| Servicio de Esterilización | CIX | 09 | 002 | CIX-09-002 | 315 |
| Servicio de Laboratorio Clínico (Toma de Muestra de Laboratorio Clínico) | ADG | 10 | 001 | ADG-10-001 | 313 |
| Servicio de Imágenes Diagnósticas (Tomografía, Radiología, Ecografía) | ADG | 10 | 002 | ADG-10-002 | 313 |
| Banco de Sangre y Servicio de Gestión Pre-Transfusional | CTR | 11 | 001 | CTR-11-001 | 313 |
| Servicio Farmacéutico | CTR | 11 | 002 | CTR-11-002 | 320.2 |
| Servicio de Terapias (Terapia Física, Respiratoria, Ocupacional, Fonoaudiología) | CTR | 11 | 003 | CTR-11-003 | 313 |
| Humanización en los Servicios de Salud | SIC | 12 | 000 | SIC-12-000 | 310 |
| Trabajo Social | SIC | 12 | 001 | SIC-12-001 | 313 |
| Sistema de Atención al Usuario | SIC | 12 | 002 | SIC-12-002 | 313 |
| Gestión de la Contabilidad | GFI | 12 | 001 | GFI-12-001 | 320.5 |
| Gestión del Presupuesto | GFI | 12 | 002 | GFI-12-002 | 320.5 |
| Gestión de Tesorería | GFI | 12 | 003 | GFI-12-003 | 320.4 |
| Gestión del Gasto | GFI | 12 | 004 | GFI-12-004 | 320.8 |
| Gestión de Cartera | GFI | 12 | 005 | GFI-12-005 | 320.6 |
| Facturación | GFI | 12 | 006 | GFI-12-006 | 320.9 |
| Cuentas Médicas y Gestión de Glosas | GFI | 12 | 007 | GFI-12-007 | 320 |
| Defensa Jurídica | JUR | 13 | 001 | JUR-13-001 | 301 |
| Contratación | JUR | 13 | 002 | JUR-13-002 | 320 |
| Gestión de las Tecnologías y Sistemas de Información | SIS | 14 | 001 | SIS-14-001 | 322 |
| Historias Clínicas | SIS | 14 | 002 | SIS-14-002 | 320 |
| Gestión Documental (Archivo Central y Unidad de Correspondencia) | SIS | 14 | 003 | SIS-14-003 | 320.3 |
| Unidad de Vigilancia Epidemiológica | SIS | 14 | 004 | SIS-14-004 | 320 |
| Unidad de Estadísticas y Análisis de Datos | SIS | 14 | 005 | SIS-14-005 | 322.2 |
| Almacén/Gestión de Insumos, Suministros, Inventario y Activos. | GCA | 15 | 001 | GCA-15-001 | 320.1 |
| Gestión del Mantenimiento de la Infraestructura Física Hospitalaria, Equipos Industriales y Vehículos | AFT | 16 | 001 | AFT-16-001 | 323.1 |
| Gestión Biomédica | AFT | 16 | 002 | AFT-16-002 | 320 |
| Servicios Básicos | AFT | 16 | 003 | AFT-16-003 | 321.2 |
| Gestión de Redes de Tecnología y Equipos Informáticos | AFT | 16 | 004 | AFT-16-004 | 320 |
| Control Interno | SEI | 17 | 001 | SEI-17-001 | 302 |

## Oficinas pendientes de definición funcional

Estas oficinas no deben considerarse cerradas todavía para radicación interna:

| Oficina | Problema actual |
| --- | --- |
| Subgerencia administrativa y financiera | Duplica GFI-12-001 con Gestión de la Contabilidad. |
| Subgerencia cientifica | Sin código numérico y sin definición funcional cerrada. |
| COORDINACIÓN ENFERMERIA | Sin código numérico y sin definición funcional cerrada. |
| COORDINACIÓN MÉDICA | Sin código numérico y sin definición funcional cerrada. |
| Consulta Complementaria (Nutrición, Psicología, Trabajo Social) | Duplica CEX-06-001 con Consulta General. |
| Gestión de la Seguridad del paciente | Parece duplicado nominal de Gestión de la Seguridad del Paciente. |
| U.F. SERVICIOS HOSPITALARIOS | Colisiona con otras ATS en ATS-201-001. |
| U.F.SERVICIOS AMBULATORIOS | Colisiona con otras ATS en ATS-201-001. |
| UF.APOYO DIAGNOSTICO Y TERAPEUTICO | Colisiona con otras ATS en ATS-201-001. |
| Of tmp, Of tmp2, Of tmp3, Of tmp4, Of tmp5, Of tmp6, Of tmp7, Of tmp8, Of tmp9 | Temporales, sin configuración archivística válida. |

## Casos ya verificados en base real

- Historias Clínicas: SIS-14-002 y TRD 320.03.11.
- Subgerencia Talento Humano: THS-02-000 y TRD 321.03.11.
- Gestión de la Calidad: SIG-03-001 y TRD 303.13.60.