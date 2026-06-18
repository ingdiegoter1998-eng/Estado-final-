# Diccionario de Datos - Sistema de Gestión de Correspondencia
## Hospital del Sarare E.S.E.

**Versión:** 1.1
**Fecha:** Junio 2026
**Base de Datos:** SQL Server `GestionDocumental` (producción) / SQLite solo para desarrollo local explícito

**Fuente de verdad técnica:** modelos Django en `documentos.models`, `correspondencia.models`, `correspondencia.modelos_minimos_sla` y `correspondencia.chat_models`.
**Criterio de conteo:** se cuentan modelos de dominio y tablas estándar documentadas; las tablas intermedias Many-to-Many se describen dentro de la tabla propietaria y no incrementan el total salvo que tengan modelo explícito.

---

## 📋 Índice

1. [Módulo: Autenticación y Usuarios](#módulo-autenticación-y-usuarios)
2. [Módulo: Documentos - Estructura Organizacional](#módulo-documentos---estructura-organizacional)
3. [Módulo: Documentos - Series y Subseries (TRD)](#módulo-documentos---series-y-subseries-trd)
4. [Módulo: Documentos - FUID y Registros](#módulo-documentos---fuid-y-registros)
5. [Módulo: Documentos - Perfiles y Permisos](#módulo-documentos---perfiles-y-permisos)
6. [Módulo: Documentos - Pacientes](#módulo-documentos---pacientes)
7. [Módulo: Documentos - Préstamos Documentales](#módulo-documentos---préstamos-documentales)
8. [Módulo: Correspondencia - Entidades y Contactos](#módulo-correspondencia---entidades-y-contactos)
9. [Módulo: Correspondencia - Correspondencia Entrante](#módulo-correspondencia---correspondencia-entrante)
10. [Módulo: Correspondencia - Correos Entrantes (IMAP)](#módulo-correspondencia---correos-entrantes-imap)
11. [Módulo: Correspondencia - Distribución y Accesos](#módulo-correspondencia---distribución-y-accesos)
12. [Módulo: Correspondencia - Correspondencia Saliente](#módulo-correspondencia---correspondencia-saliente)
13. [Módulo: Correspondencia - Comunicaciones Masivas](#módulo-correspondencia---comunicaciones-masivas)
14. [Módulo: Correspondencia - Informes Diarios](#módulo-correspondencia---informes-diarios)
15. [Módulo: Correspondencia - Firmas](#módulo-correspondencia---firmas)
16. [Módulo: Correspondencia - Comunicaciones Internas](#módulo-correspondencia---comunicaciones-internas)
17. [Módulo: Correspondencia - SLA y Calendario Laboral](#módulo-correspondencia---sla-y-calendario-laboral)
18. [Módulo: Correspondencia - Operativa de Correos](#módulo-correspondencia---operativa-de-correos)
19. [Módulo: Correspondencia - Urgencias](#módulo-correspondencia---urgencias)
20. [Módulo: Correspondencia - Asistente IA Documental](#módulo-correspondencia---asistente-ia-documental)
21. [Módulo: Correspondencia - Chat de Soporte](#módulo-correspondencia---chat-de-soporte)
22. [Módulo: Correspondencia - Notificaciones](#módulo-correspondencia---notificaciones)

---

## Módulo: Autenticación y Usuarios

### Tabla: `auth_user`

**Descripción:** Usuarios del sistema (tabla estándar de Django)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único del usuario |
| `username` | Varchar(150) | UNIQUE, NOT NULL | Nombre de usuario para login |
| `first_name` | Varchar(150) | NULL | Primer nombre |
| `last_name` | Varchar(150) | NULL | Apellido |
| `email` | Varchar(254) | NULL | Correo electrónico |
| `password` | Varchar(128) | NOT NULL | Contraseña hasheada |
| `is_staff` | Boolean | DEFAULT: False | Acceso al admin de Django |
| `is_active` | Boolean | DEFAULT: True | Usuario activo |
| `is_superuser` | Boolean | DEFAULT: False | Superusuario (todos los permisos) |
| `date_joined` | DateTime | NOT NULL | Fecha de registro |
| `last_login` | DateTime | NULL | Último inicio de sesión |

**Índices:**
- PRIMARY KEY: `id`
- UNIQUE: `username`

---

### Tabla: `auth_group`

**Descripción:** Grupos de usuarios (roles del sistema)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único del grupo |
| `name` | Varchar(150) | UNIQUE, NOT NULL | Nombre del grupo (ej: "Ventanilla", "Lider de Oficina") |

**Grupos estándar:**
- `Ventanilla`: Radicar, imprimir sellos, aprobar respuestas
- `Lider de Oficina`: Aprobar comunicaciones, gestionar oficina
- `Usuario`: Leer, responder correspondencia asignada

---

### Tabla: `auth_permission`

**Descripción:** Permisos estándar de Django asociados a modelos y acciones (`add`, `change`, `delete`, `view`) más permisos personalizados.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único del permiso |
| `name` | Varchar(255) | NOT NULL | Nombre legible del permiso |
| `content_type_id` | Integer | FK, NOT NULL | Modelo al que pertenece el permiso |
| `codename` | Varchar(100) | NOT NULL | Código técnico del permiso |

**Restricciones:**
- UNIQUE: `(content_type_id, codename)`

**Relaciones:**
- `content_type_id` → `django_content_type.id`

---

## Módulo: Documentos - Estructura Organizacional

### Tabla: `documentos_entidadproductora`

**Descripción:** Entidad productora de documentos (ej: Hospital del Sarare E.S.E.)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(255) | UNIQUE, NOT NULL | Nombre completo de la entidad |

---

### Tabla: `documentos_macroproceso`

**Descripción:** Macroprocesos organizacionales (Estratégicos, Misionales, de Apoyo, etc.)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `numero` | Integer | UNIQUE, NOT NULL | Número secuencial (1, 2, 3...) |
| `nombre` | Varchar(255) | NOT NULL | Nombre del macroproceso |

**Ejemplos:**
- `1 - ESTRATEGICOS`
- `2 - MISIONALES`
- `3 - DE APOYO`
- `4 - DE CONTROL Y SEGUIMIENTO`

---

### Tabla: `documentos_proceso`

**Descripción:** Procesos organizacionales que pertenecen a un macroproceso

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `numero` | Integer | NOT NULL | Número del proceso |
| `nombre` | Varchar(255) | NOT NULL | Nombre del proceso |
| `sigla` | Varchar(20) | NOT NULL | Sigla del proceso (ej: DIR, THS, SIG) |
| `macroproceso_id` | Integer | FK, NOT NULL | Macroproceso al que pertenece |

**Restricciones:**
- UNIQUE: `(numero, macroproceso_id)`

**Relaciones:**
- `macroproceso_id` → `documentos_macroproceso.id`

---

### Tabla: `documentos_unidadadministrativa`

**Descripción:** Unidades administrativas de la entidad

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(255) | NOT NULL | Nombre de la unidad |
| `entidad_productora_id` | Integer | FK, NOT NULL | Entidad a la que pertenece |

**Relaciones:**
- `entidad_productora_id` → `documentos_entidadproductora.id`

---

### Tabla: `documentos_oficinaproductora`

**Descripción:** Oficinas productoras de documentos (Subprocesos)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(255) | NOT NULL | Nombre de la oficina |
| `codigo` | Varchar(50) | NULL | Código de la oficina (opcional) |
| `codigo_trd` | Varchar(255) | UNIQUE, NULL | Código TRD de la oficina |
| `unidad_administrativa_id` | Integer | FK, NOT NULL | Unidad administrativa |
| `proceso_id` | Integer | FK, NOT NULL | Proceso (Subproceso) |

**Relaciones:**
- `unidad_administrativa_id` → `documentos_unidadadministrativa.id`
- `proceso_id` → `documentos_proceso.id`

---

## Módulo: Documentos - Series y Subseries (TRD)

### Tabla: `documentos_seriedocumental`

**Descripción:** Series documentales según Tabla de Retención Documental (TRD)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `codigo` | Varchar(50) | NOT NULL | Código de la serie |
| `nombre` | Varchar(255) | NOT NULL | Nombre de la serie |
| `codigo_trd` | Varchar(255) | UNIQUE, NULL | Código TRD de la serie |

**Ejemplos:**
- `1.0 - ADMINISTRATIVA`
- `2.0 - HISTORIA CLINICA`
- `3.0 - TALENTO HUMANO`

---

### Tabla: `documentos_subseriedocumental`

**Descripción:** Subseries documentales (pertenecen a una serie)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `codigo` | Varchar(50) | NOT NULL | Código de la subserie |
| `nombre` | Varchar(255) | NOT NULL | Nombre de la subserie |
| `codigo_trd` | Varchar(255) | UNIQUE, NULL | Código TRD de la subserie |
| `serie_id` | Integer | FK, NOT NULL | Serie a la que pertenece |

**Relaciones:**
- `serie_id` → `documentos_seriedocumental.id`

**Ejemplos:**
- `1.1 - CORRESPONDENCIA` (pertenece a serie 1.0)
- `2.1 - HISTORIA CLINICA INDIVIDUAL` (pertenece a serie 2.0)

---

## Módulo: Documentos - FUID y Registros

### Tabla: `documentos_objeto`

**Descripción:** Tipos de objetos documentales

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(255) | UNIQUE, NOT NULL | Nombre del objeto |

---

### Tabla: `documentos_fuid`

**Descripción:** Formato Único de Inventario Documental (FUID)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `entidad_productora_id` | Integer | FK, NULL | Entidad productora |
| `unidad_administrativa_id` | Integer | FK, NULL | Unidad administrativa |
| `oficina_productora_id` | Integer | FK, NULL | Oficina productora |
| `objeto_id` | Integer | FK, NULL | Objeto documental |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `creado_por_id` | Integer | FK, NULL | Usuario creador |
| `notas` | Varchar(245) | NULL | Notas adicionales |
| `elaborado_por_nombre` | Varchar(255) | NULL | Nombre de quien elaboró |
| `elaborado_por_cargo` | Varchar(255) | NULL | Cargo de quien elaboró |
| `elaborado_por_lugar` | Varchar(255) | NULL | Lugar de elaboración |
| `elaborado_por_fecha` | Date | NULL | Fecha de elaboración |
| `entregado_por_nombre` | Varchar(255) | NULL | Nombre de quien entregó |
| `entregado_por_cargo` | Varchar(255) | NULL | Cargo de quien entregó |
| `entregado_por_lugar` | Varchar(255) | NULL | Lugar de entrega |
| `entregado_por_fecha` | Date | NULL | Fecha de entrega |
| `recibido_por_nombre` | Varchar(255) | NULL | Nombre de quien recibió |
| `recibido_por_cargo` | Varchar(255) | NULL | Cargo de quien recibió |
| `recibido_por_lugar` | Varchar(255) | NULL | Lugar de recepción |
| `recibido_por_fecha` | Date | NULL | Fecha de recepción |

**Relaciones:**
- `entidad_productora_id` → `documentos_entidadproductora.id`
- `unidad_administrativa_id` → `documentos_unidadadministrativa.id`
- `oficina_productora_id` → `documentos_oficinaproductora.id`
- `objeto_id` → `documentos_objeto.id`
- `creado_por_id` → `auth_user.id`

**Tabla intermedia:** `documentos_fuid_registros` (Many-to-Many)
- `fuid_id` → `documentos_fuid.id`
- `registrodearchivo_id` → `documentos_registrodearchivo.id`

---

### Tabla: `documentos_registrodearchivo`

**Descripción:** Registros individuales de archivo (unidades documentales)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `Estado_archivo` | Boolean | DEFAULT: True | Estado activo/inactivo |
| `numero_orden` | Integer | NOT NULL, DEFAULT: 0 | Número de orden único |
| `codigo` | Varchar(50) | NULL | Código del registro |
| `codigo_serie_id` | Integer | FK, NOT NULL | Serie documental |
| `codigo_subserie_id` | Integer | FK, NULL | Subserie documental |
| `unidad_documental` | Varchar(255) | NOT NULL | Nombre de la unidad documental |
| `fecha_archivo` | Date | NULL | Fecha del archivo |
| `fecha_inicial` | Date | NULL | Fecha inicial del rango |
| `fecha_final` | Date | NULL | Fecha final del rango |
| `soporte_fisico` | Boolean | DEFAULT: False | Tiene soporte físico |
| `soporte_electronico` | Boolean | DEFAULT: False | Tiene soporte electrónico |
| `caja` | Integer | NULL | Número de caja (físico) |
| `carpeta` | Integer | NULL | Número de carpeta (físico) |
| `tomo_legajo_libro` | Varchar(50) | NULL | Tomo, legajo o libro |
| `numero_folios` | Integer | NULL | Número de folios |
| `tipo` | Varchar(100) | NULL | Tipo de documento |
| `cantidad` | Integer | NULL | Cantidad de documentos |
| `ubicacion` | Varchar(255) | NULL | Ubicación física |
| `cantidad_documentos_electronicos` | Integer | NULL | Cantidad de documentos electrónicos |
| `tamano_documentos_electronicos` | Varchar(50) | NULL | Tamaño de documentos electrónicos |
| `identificador_documento` | Varchar(150) | NULL | Identificador específico (ej: número HC) |
| `notas` | Text(250) | NULL | Notas adicionales |
| `creado_por_id` | Integer | FK, NULL | Usuario creador |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |

**Relaciones:**
- `codigo_serie_id` → `documentos_seriedocumental.id`
- `codigo_subserie_id` → `documentos_subseriedocumental.id`
- `creado_por_id` → `auth_user.id`

---

### Tabla: `documentos_documento`

**Descripción:** Archivos adjuntos a registros (máximo 3 por registro)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `registro_id` | Integer | FK, NOT NULL | Registro al que pertenece |
| `archivo` | Varchar(300) | NOT NULL | Ruta del archivo (PDF, Word, Excel) |
| `uploaded_at` | DateTime | NOT NULL | Fecha de carga |

**Restricciones:**
- Máximo 3 archivos por registro
- Formatos permitidos: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`
- Tamaño máximo: 2 MB por archivo

**Relaciones:**
- `registro_id` → `documentos_registrodearchivo.id`

---

## Módulo: Documentos - Perfiles y Permisos

### Tabla: `documentos_perfilusuario`

**Descripción:** Perfil extendido de usuario con información adicional

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `user_id` | Integer | FK, UNIQUE, NOT NULL | Usuario (OneToOne) |
| `oficina_id` | Integer | FK, NOT NULL | Oficina a la que pertenece |
| `cargo` | Varchar(150) | NULL | Cargo del usuario |
| `tipo_documento` | Varchar(3) | DEFAULT: 'CC' | Tipo de documento (CC, CE, TI, PA, etc.) |
| `numero_documento` | Varchar(20) | UNIQUE, NULL | Número de documento |
| `fecha_nacimiento` | Date | NULL | Fecha de nacimiento |
| `direccion` | Varchar(200) | NULL | Dirección de residencia |
| `telefono` | Varchar(20) | NULL | Número de teléfono |
| `firma_digital` | Varchar(255) | NULL | Ruta de imagen de firma manuscrita |
| `fecha_firma_creada` | DateTime | NULL | Fecha de creación de la firma |
| `fecha_registro` | DateTime | NULL | Fecha de registro |
| `solicita_lider` | Boolean | DEFAULT: False | Solicita ser líder de oficina |

**Relaciones:**
- `user_id` → `auth_user.id` (OneToOne)
- `oficina_id` → `documentos_oficinaproductora.id`

---

### Tabla: `documentos_permisousuarioserie`

**Descripción:** Permisos de usuario sobre series documentales

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `usuario_id` | Integer | FK, NOT NULL | Usuario |
| `serie_id` | Integer | FK, NOT NULL | Serie documental |
| `permiso_crear` | Boolean | DEFAULT: False | Puede crear registros |
| `permiso_editar` | Boolean | DEFAULT: False | Puede editar registros |
| `permiso_consultar` | Boolean | DEFAULT: True | Puede consultar registros |
| `permiso_eliminar` | Boolean | DEFAULT: False | Puede eliminar registros |

**Relaciones:**
- `usuario_id` → `auth_user.id`
- `serie_id` → `documentos_seriedocumental.id`

---

### Tabla: `documentos_despliegueoficina`

**Descripción:** Seguimiento manual del despliegue/capacitación por oficina para monitoreo operativo.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `oficina_id` | Integer | FK, UNIQUE, NOT NULL | Oficina monitoreada |
| `estado_visita` | Varchar(20) | DEFAULT: 'pendiente' | pendiente, visitada, capacitada, no_aplica |
| `fecha_visita` | Date | NULL | Fecha de visita o capacitación |
| `notas` | Text | DEFAULT: '' | Observaciones del despliegue |
| `actualizado_por_id` | Integer | FK, NULL | Usuario que actualizó el registro |
| `actualizado_en` | DateTime | NOT NULL | Última actualización |

**Relaciones:**
- `oficina_id` → `documentos_oficinaproductora.id` (OneToOne)
- `actualizado_por_id` → `auth_user.id`

---

## Módulo: Documentos - Pacientes

### Tabla: `documentos_tipodocumento`

**Descripción:** Tipos de documento de identificación

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(50) | UNIQUE, NOT NULL | Nombre del tipo (CC, CE, TI, PA, etc.) |

---

### Tabla: `documentos_nacionalidad`

**Descripción:** Nacionalidades

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(100) | UNIQUE, NOT NULL, INDEX | Nombre de la nacionalidad |

---

### Tabla: `documentos_fichapaciente`

**Descripción:** Fichas de pacientes (Historias Clínicas)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `consecutivo` | Integer | PK, Auto | Identificador único |
| `primer_nombre` | Varchar(50) | NOT NULL, INDEX | Primer nombre |
| `segundo_nombre` | Varchar(50) | NULL, INDEX | Segundo nombre |
| `primer_apellido` | Varchar(50) | NOT NULL, INDEX | Primer apellido |
| `segundo_apellido` | Varchar(50) | NULL, INDEX | Segundo apellido |
| `num_identificacion` | Varchar(50) | NULL, INDEX | Número de identificación |
| `tipo_identificacion_id` | Integer | FK, NULL, INDEX | Tipo de identificación |
| `num_identificacion_secundario` | Varchar(50) | NULL, INDEX | Número secundario |
| `tipo_identificacion_secundario_id` | Integer | FK, NULL, INDEX | Tipo secundario |
| `fecha_nacimiento` | Date | NULL, INDEX | Fecha de nacimiento |
| `primer_nombre_padre` | Varchar(50) | NULL, INDEX | Nombre del padre |
| `segundo_nombre_padre` | Varchar(50) | NULL, INDEX | Segundo nombre del padre |
| `primer_apellido_padre` | Varchar(50) | NULL, INDEX | Apellido del padre |
| `segundo_apellido_padre` | Varchar(50) | NULL, INDEX | Segundo apellido del padre |
| `Numero_historia_clinica` | BigInt | UNIQUE, NOT NULL, INDEX | Número de historia clínica |
| `caja` | Varchar(20) | NULL, INDEX | Número de caja |
| `carpeta` | Varchar(20) | NULL, INDEX | Número de carpeta |
| `gabeta` | Integer | NULL, INDEX | Número de gaveta |
| `sexo` | Varchar(10) | DEFAULT: 'Masculino', INDEX | Sexo |
| `activo` | Boolean | DEFAULT: True, INDEX | Paciente activo |
| `estado_de_migracion` | Boolean | DEFAULT: False, INDEX | Estado de migración |
| `Fecha_de_visita_de_la_tarjeta` | Date | NULL, INDEX | Fecha de última visita |
| `ultimo_registro_de_visita_en_la_base_de_datos` | Date | NULL, INDEX | Último registro en BD |
| `año_de_registro` | Integer | NULL, INDEX | Año de registro |
| `nacionalidad_id` | Integer | FK, NULL, INDEX | Nacionalidad |

**Restricciones:**
- UNIQUE: `(num_identificacion, tipo_identificacion_id)`

**Relaciones:**
- `tipo_identificacion_id` → `documentos_tipodocumento.id`
- `tipo_identificacion_secundario_id` → `documentos_tipodocumento.id`
- `nacionalidad_id` → `documentos_nacionalidad.id`

---

## Módulo: Documentos - Préstamos Documentales

### Tabla: `documentos_prestamodocumental`

**Descripción:** Préstamos de documentos (físicos o virtuales)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `registro_id` | Integer | FK, NULL | Registro solicitado |
| `fuid_id` | Integer | FK, NULL | FUID asociado |
| `solicitante_id` | Integer | FK, NOT NULL | Usuario solicitante |
| `oficina_solicitante_id` | Integer | FK, NULL | Oficina del solicitante |
| `oficina_responsable_id` | Integer | FK, NULL | Oficina a la que se dirige la solicitud |
| `subproceso_solicitante` | Varchar(255) | NULL | Subproceso solicitante |
| `codigo_trd` | Varchar(50) | NULL | Código TRD |
| `serie_id` | Integer | FK, NULL | Serie documental |
| `subserie_id` | Integer | FK, NULL | Subserie documental |
| `descripcion_documento` | Text | NULL | Descripción del documento |
| `tipo_prestamo` | Varchar(10) | NOT NULL | FISICO o VIRTUAL |
| `estado` | Varchar(25) | NOT NULL, DEFAULT: 'SOLICITADO' | SOLICITADO, ENTREGADO, PRESTAMO_ACTIVO, DEVOLUCION_SOLICITADA, DEVUELTO, REINTEGRADO, RECHAZADO, RECHAZADO_USUARIO, VENCIDO |
| `fecha_solicitud` | DateTime | NOT NULL | Fecha de solicitud |
| `fecha_aprobacion` | DateTime | NULL | Fecha de aprobación |
| `fecha_entrega` | DateTime | NULL | Fecha de entrega |
| `fecha_vencimiento` | Date | NULL | Fecha de vencimiento (10 días HC, 20 días otros) |
| `fecha_devolucion` | DateTime | NULL | Fecha de devolución |
| `fecha_reintegracion` | DateTime | NULL | Fecha de reintegración |
| `aprobado_por_id` | Integer | FK, NULL | Usuario que aprobó |
| `procesado_por_id` | Integer | FK, NULL | Usuario que procesó |
| `vobo_jefe_nombre` | Varchar(255) | DEFAULT: 'Eliana Gelves' | Nombre del jefe que aprueba |
| `vobo_jefe_cargo` | Varchar(255) | NULL | Cargo del jefe |
| `vobo_jefe_fecha` | Date | NULL | Fecha de Vo.Bo. |
| `documento_escaneado` | Varchar(255) | NULL | PDF escaneado |
| `documento_virtual` | Varchar(255) | NULL | PDF para préstamo virtual |
| `motivo_rechazo` | Text | NULL | Motivo de rechazo |
| `motivo_rechazo_usuario` | Text | NULL | Motivo si usuario rechaza |
| `documento_rechazo` | Varchar(255) | NULL | Documento de rechazo |
| `documento_devuelto` | Boolean | DEFAULT: False | Documento devuelto |
| `documento_danado` | Boolean | DEFAULT: False | Documento dañado |
| `observaciones_dano` | Text | NULL | Observaciones sobre daños |
| `confirmado_por_usuario` | Boolean | DEFAULT: False | Confirmado por usuario |
| `fecha_confirmacion` | DateTime | NULL | Fecha de confirmación |
| `notas` | Text | NULL | Notas adicionales |

**Índices:**
- `(estado, fecha_solicitud DESC)`
- `(solicitante_id, fecha_solicitud DESC)`
- `(tipo_prestamo, estado)`

**Relaciones:**
- `registro_id` → `documentos_registrodearchivo.id`
- `fuid_id` → `documentos_fuid.id`
- `solicitante_id` → `auth_user.id`
- `oficina_solicitante_id` → `documentos_oficinaproductora.id`
- `oficina_responsable_id` → `documentos_oficinaproductora.id`
- `serie_id` → `documentos_seriedocumental.id`
- `subserie_id` → `documentos_subseriedocumental.id`
- `aprobado_por_id` → `auth_user.id`
- `procesado_por_id` → `auth_user.id`

---

### Tabla: `documentos_documentoescaneadoprestamo`

**Descripción:** Documentos escaneados adjuntos a préstamos (múltiples)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `prestamo_id` | Integer | FK, NOT NULL | Préstamo asociado |
| `archivo` | Varchar(300) | NOT NULL | Ruta del archivo (PDF, Word, Excel) |
| `uploaded_at` | DateTime | NOT NULL | Fecha de carga |
| `nombre_archivo_original` | Varchar(255) | NULL | Nombre original |
| `confirmado` | Boolean | DEFAULT: False | Confirmado |
| `fecha_confirmacion` | DateTime | NULL | Fecha de confirmación |
| `uploaded_by_id` | Integer | FK, NULL | Usuario que subió |

**Relaciones:**
- `prestamo_id` → `documentos_prestamodocumental.id`
- `uploaded_by_id` → `auth_user.id`

---

### Tabla: `documentos_notificacionavisoprestamo`

**Descripción:** Notificaciones de aviso por retrasos en préstamos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `prestamo_id` | Integer | FK, NOT NULL | Préstamo asociado |
| `documento_oficio` | Varchar(255) | NOT NULL | Archivo oficio de notificación |
| `observaciones` | Text | NULL | Observaciones |
| `fecha_notificacion` | DateTime | NOT NULL | Fecha de notificación |
| `notificado_por_id` | Integer | FK, NULL | Usuario que notificó |
| `oficina_notificada_id` | Integer | FK, NULL | Oficina notificada |

**Relaciones:**
- `prestamo_id` → `documentos_prestamodocumental.id`
- `notificado_por_id` → `auth_user.id`
- `oficina_notificada_id` → `documentos_oficinaproductora.id`

---

### Tabla: `documentos_historialprestamo`

**Descripción:** Historial de eventos de préstamos (trazabilidad)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `prestamo_id` | Integer | FK, NOT NULL | Préstamo asociado |
| `usuario_id` | Integer | FK, NULL | Usuario que realizó el evento |
| `evento` | Varchar(100) | NOT NULL | Tipo de evento |
| `descripcion` | Text | NULL | Descripción del evento |
| `fecha` | DateTime | NOT NULL | Fecha del evento |

**Relaciones:**
- `prestamo_id` → `documentos_prestamodocumental.id`
- `usuario_id` → `auth_user.id`

---

### Tabla: `documentos_historialdescargaprestamo`

**Descripción:** Auditoría de descargas de reportes mensuales de préstamos documentales.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `usuario_id` | Integer | FK, NULL | Usuario que descargó el reporte |
| `fecha_descarga` | DateTime | NOT NULL | Fecha y hora de descarga |
| `anio` | Integer | NOT NULL | Año reportado |
| `mes` | SmallInteger | NOT NULL | Mes reportado |
| `nombre_archivo` | Varchar(255) | NOT NULL | Nombre del archivo generado |
| `total_registros` | Integer | DEFAULT: 0 | Total de préstamos exportados |
| `filtro_estado` | Varchar(25) | NULL | Estado filtrado |
| `filtro_tipo` | Varchar(10) | NULL | Tipo de préstamo filtrado |
| `filtro_alerta` | Varchar(40) | NULL | Alerta filtrada |
| `filtro_tipo_archivo` | Varchar(40) | NULL | Tipo de archivo filtrado |
| `filtro_oficina` | Varchar(255) | NULL | Oficina filtrada |
| `busqueda` | Varchar(255) | NULL | Texto de búsqueda aplicado |
| `ip_address` | Varchar(39) | NULL | Dirección IP |

**Índices:**
- `(anio, mes, fecha_descarga)`
- `(usuario_id, fecha_descarga)`

**Relaciones:**
- `usuario_id` → `auth_user.id`

---

## Módulo: Correspondencia - Entidades y Contactos

### Tabla: `correspondencia_entidadexterna`

**Descripción:** Entidades externas (empresas, instituciones)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `nombre` | Varchar(255) | UNIQUE, NOT NULL | Nombre completo de la entidad |
| `nit` | Varchar(20) | NULL | NIT o identificador fiscal |
| `direccion` | Varchar(255) | NULL | Dirección |
| `telefono` | Varchar(50) | NULL | Teléfono |
| `dominio` | Varchar(100) | UNIQUE, NULL | Dominio de correo asociado |

---

### Tabla: `correspondencia_contacto`

**Descripción:** Contactos externos (personas) asociados a entidades

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `entidad_externa_id` | Integer | FK, NOT NULL | Entidad a la que pertenece |
| `nombres` | Varchar(150) | NOT NULL | Nombres del contacto |
| `apellidos` | Varchar(150) | NULL | Apellidos del contacto |
| `cargo` | Varchar(150) | NULL | Cargo dentro de la entidad |
| `correo_electronico` | Varchar(254) | UNIQUE, NOT NULL | Correo electrónico |
| `telefono_contacto` | Varchar(50) | NULL | Teléfono del contacto |
| `numero_documento` | Varchar(50) | NULL | Número de documento (CC, CE, etc.) |

**Relaciones:**
- `entidad_externa_id` → `correspondencia_entidadexterna.id`

---

### Tabla: `correspondencia_entidadexternadominio`

**Descripción:** Dominios secundarios autorizados para una entidad externa, usados para reconocer remitentes institucionales sin duplicar entidades.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `entidad_externa_id` | Integer | FK, NOT NULL | Entidad propietaria del dominio |
| `dominio` | Varchar(120) | UNIQUE, NOT NULL | Dominio normalizado |
| `activo` | Boolean | DEFAULT: True | Dominio habilitado para clasificación |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |

**Relaciones:**
- `entidad_externa_id` → `correspondencia_entidadexterna.id`

---

### Tabla: `correspondencia_auditoriacontacto`

**Descripción:** Bitácora de creación, edición y eliminación de contactos externos.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `contacto_id` | Integer | FK, NULL | Contacto afectado |
| `usuario_id` | Integer | FK, NULL | Usuario que realizó el cambio |
| `tipo_cambio` | Varchar | NOT NULL | CREACION, EDICION o ELIMINACION |
| `fecha_cambio` | DateTime | NOT NULL | Fecha del evento |
| `campos_modificados` | JSON | DEFAULT: {} | Diccionario `{campo: {antes, despues}}` |
| `contacto_nombre_snapshot` | Varchar(300) | NULL | Nombre del contacto al momento del cambio |
| `ip_address` | Varchar(39) | NULL | Dirección IP |

**Relaciones:**
- `contacto_id` → `correspondencia_contacto.id`
- `usuario_id` → `auth_user.id`

---

## Módulo: Correspondencia - SLA y Calendario Laboral

### Tabla: `correspondencia_tipotramite`

**Descripción:** Catálogo administrativo de tipos de trámite para radicación rápida, con días hábiles configurables desde el sistema.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `codigo` | Varchar(20) | UNIQUE, NOT NULL | Código del trámite (PT, PTA, PQRSF, etc.) |
| `nombre` | Varchar(100) | NOT NULL | Nombre descriptivo |
| `descripcion` | Text | NULL | Descripción operativa |
| `dias_respuesta` | Integer | NULL | Días hábiles; NULL si no aplica plazo |
| `activo` | Boolean | DEFAULT: True | Disponible en formularios |
| `orden` | Integer | DEFAULT: 0 | Orden de presentación |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `fecha_modificacion` | DateTime | NOT NULL | Última modificación |

---

### Tabla: `correspondencia_tramitetipo`

**Descripción:** Catálogo de trámites legales asociados a plazos de respuesta de la TRD.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `codigo` | Varchar(50) | UNIQUE, NOT NULL | Código legal/operativo |
| `nombre` | Varchar(255) | NOT NULL | Nombre del trámite |
| `plazo_dias_habiles` | SmallInteger | NOT NULL | Plazo legal en días hábiles |
| `fundamento_normativo` | Varchar(255) | NULL | Norma o sustento del plazo |
| `activo` | Boolean | DEFAULT: True | Trámite disponible |

---

### Tabla: `correspondencia_subserietramite`

**Descripción:** Mapeo uno a uno entre subseries documentales y trámites legales de SLA.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `subserie_id` | Integer | FK, UNIQUE, NOT NULL | Subserie documental |
| `tramite_id` | Integer | FK, NOT NULL | Trámite legal aplicado |

**Relaciones:**
- `subserie_id` → `documentos_subseriedocumental.id`
- `tramite_id` → `correspondencia_tramitetipo.id`

---

### Tabla: `correspondencia_calendariolaboral`

**Descripción:** Calendario de días hábiles/feriados usado por el cálculo de SLA. Si está vacío, el sistema cae al cálculo por lunes-viernes.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `fecha` | Date | UNIQUE, NOT NULL, INDEX | Fecha evaluada |
| `es_habil` | Boolean | DEFAULT: True | Indica si la fecha cuenta como hábil |

---

## Módulo: Correspondencia - Correspondencia Entrante

### Tabla: `correspondencia_correspondencia`

**Descripción:** Correspondencia entrante (documento principal)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `numero_radicado` | Varchar(50) | UNIQUE, NOT NULL | Número de radicado (ENTRANTE-2026-00001) |
| `tipo_radicado` | Varchar(20) | NOT NULL, DEFAULT: 'ENTRANTE' | Tipo de radicado |
| `fecha_radicacion` | DateTime | NOT NULL | Fecha y hora de radicación |
| `usuario_radicador_id` | Integer | FK, NULL | Usuario que radicó |
| `remitente_id` | Integer | FK, NULL | Contacto remitente |
| `asunto` | Text | NOT NULL | Asunto de la correspondencia |
| `serie_id` | Integer | FK, NULL | Serie documental |
| `subserie_id` | Integer | FK, NULL | Subserie documental |
| `medio_recepcion` | Varchar(50) | NOT NULL, DEFAULT: 'FISICO' | FISICO o ELECTRONICO |
| `requiere_respuesta` | Boolean | DEFAULT: False | Requiere respuesta |
| `tiempo_respuesta` | Varchar(20) | NULL | NORMAL, URGENTE, MUY_URGENTE |
| `dias_personalizados` | Integer | NULL | Días personalizados (1-15) con prioridad sobre TRD/fallback |
| `plazo_respuesta_dias` | Integer | NULL | Días hábiles persistidos |
| `fecha_limite_respuesta_persist` | DateTime | NULL | Fecha límite persistida |
| `plazo_origen` | Varchar(20) | DEFAULT: 'NONE' | TRD, TIPO_TRAMITE, PERSONALIZADO, MANUAL, FALLBACK, NONE |
| `tramite_aplicado_id` | Integer | FK, NULL | Trámite aplicado (si TRD) |
| `estado` | Varchar(50) | NOT NULL, DEFAULT: 'RADICADA' | RADICADA, ASIGNADA_USUARIO, LEIDA, RESPONDIDA |
| `leido_por_oficina` | Boolean | DEFAULT: False | Leído por oficina |
| `resumen_ia` | Text | NULL | Resumen generado por IA |
| `sellado` | Boolean | DEFAULT: False, INDEX | Documento sellado |
| `fecha_sellado` | DateTime | NULL | Fecha de sellado |
| `en_planilla` | Boolean | DEFAULT: False, INDEX | Incluido en planilla |
| `oficina_destino_id` | Integer | FK, NOT NULL | Oficina destino |
| `usuario_destino_inicial_id` | Integer | FK, NULL | Usuario destino inicial |
| `origen_radicacion` | Varchar(20) | DEFAULT: 'NORMAL', INDEX | NORMAL, RAPIDA o CORREO |
| `fecha_recepcion_documento` | Date | NULL | Fecha de recepción física/documental |
| `tipo_tramite` | Varchar(50) | NULL | Código de trámite para radicación rápida |
| `entidad_persona_remitente` | Varchar(255) | NULL | Remitente textual en radicación rápida |
| `funcionario_responsable_tramite` | Varchar(255) | NULL | Funcionario responsable informado |
| `email_funcionario_responsable` | Varchar(254) | NULL | Email del funcionario responsable |
| `clasificacion_comunicacion` | Varchar(255) | NULL | Clasificación operativa de comunicación |
| `numero_folios` | Integer | NULL | Número de folios |
| `anexos` | Varchar(500) | NULL | Descripción de anexos |
| `medio_recibido` | Varchar(50) | NULL | EMAIL, CORREO_CERTIFICADO o PERSONAL |
| `direccion_correo_remitente` | Varchar(254) | NULL | Email remitente capturado |
| `empresa_transportadora` | Varchar(255) | NULL | Transportadora si aplica |
| `numero_guia` | Varchar(100) | NULL | Número de guía si aplica |
| `fecha_limite_respuesta_manual` | Date | NULL | Fecha límite manual |
| `fecha_primer_seguimiento` | Date | NULL | Primer seguimiento |
| `fecha_segundo_seguimiento` | Date | NULL | Segundo seguimiento |
| `fecha_notificacion_vencimiento` | Date | NULL | Notificación de vencimiento |
| `fecha_respuesta` | Date | NULL | Fecha de respuesta final |
| `estado_respuesta` | Varchar(20) | NULL | PENDIENTE, RESPONDIDA o VENCIDA |
| `radicado_enviado_respuesta` | Varchar(100) | NULL | Radicado de respuesta enviado |

**Relaciones:**
- `usuario_radicador_id` → `auth_user.id`
- `remitente_id` → `correspondencia_contacto.id`
- `serie_id` → `documentos_seriedocumental.id`
- `subserie_id` → `documentos_subseriedocumental.id`
- `oficina_destino_id` → `documentos_oficinaproductora.id`
- `usuario_destino_inicial_id` → `auth_user.id`
- `tramite_aplicado_id` → `correspondencia_tramitetipo.id`

---

### Tabla: `correspondencia_historialcorrespondencia`

**Descripción:** Historial de eventos de correspondencia (trazabilidad)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, NOT NULL | Correspondencia asociada |
| `fecha_hora` | DateTime | NOT NULL | Fecha y hora del evento |
| `evento` | Varchar(30) | NOT NULL | RADICADA, ASIGNADA_USUARIO, LEIDA, RESPONDIDA, SELLO_IMPRESO, REDISTRIBUIDA_INTERNA, COMPARTIDA_OFICINA |
| `usuario_id` | Integer | FK, NULL | Usuario que realizó el evento |
| `descripcion` | Text | NULL | Descripción del evento |

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id`
- `usuario_id` → `auth_user.id`

---

### Tabla: `correspondencia_adjuntocorreo`

**Descripción:** Archivos adjuntos de correspondencia electrónica

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, NOT NULL | Correspondencia asociada |
| `archivo` | Varchar(255) | NOT NULL | Ruta del archivo |
| `nombre_original` | Varchar(255) | NULL | Nombre original |
| `tipo_mime` | Varchar(100) | NULL | Tipo MIME |
| `fecha_carga` | DateTime | NOT NULL | Fecha de carga |

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id`

---

### Tabla: `correspondencia_adjuntocorrespondenciarapida`

**Descripción:** Escaneos o documentos adjuntos capturados durante radicación rápida.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, NOT NULL | Correspondencia asociada |
| `archivo` | Varchar(255) | NOT NULL | Ruta del archivo |
| `nombre_original` | Varchar(255) | NULL | Nombre original del archivo |
| `tipo_mime` | Varchar(100) | NULL | Tipo MIME |
| `fecha_carga` | DateTime | NOT NULL | Fecha de carga |

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id`

---

## Módulo: Correspondencia - Correos Entrantes (IMAP)

### Tabla: `correspondencia_correoentrante`

**Descripción:** Correos electrónicos leídos de IMAP (pendientes de radicar)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `message_id` | Varchar(255) | UNIQUE, NOT NULL | Message-ID único del correo |
| `remitente` | Varchar(254) | NOT NULL | Email del remitente |
| `asunto` | Varchar(500) | NULL | Asunto del correo |
| `cuerpo_texto` | Text | NULL | Cuerpo en texto plano |
| `cuerpo_html` | Text | NULL | Cuerpo en HTML |
| `fecha_recepcion_original` | DateTime | NULL | Fecha del encabezado Date |
| `fecha_recibida_gmail` | DateTime | NULL | INTERNALDATE registrada por Gmail/IMAP |
| `fecha_lectura_imap` | DateTime | NOT NULL | Fecha de lectura desde IMAP |
| `procesado` | Boolean | DEFAULT: False, INDEX | Ya procesado por IA |
| `radicado_asociado_id` | Integer | FK, NULL | Correspondencia creada |
| `urgencia_asociada_id` | Integer | FK, NULL | Urgencia creada desde el correo |
| `requiere_revision_manual` | Boolean | DEFAULT: False | Requiere revisión manual |
| `en_papelera` | Boolean | DEFAULT: False, INDEX | Excluido de bandeja activa sin borrarlo |
| `motivo_papelera` | Varchar(32) | NULL | Motivo operativo de papelera |
| `fecha_papelera` | DateTime | NULL | Fecha de envío a papelera |
| `usuario_papelera_id` | Integer | FK, NULL | Usuario que envió a papelera |
| `oficina_clasificada_id` | Integer | FK, NULL | Oficina predicha por IA |
| `serie_clasificada_id` | Integer | FK, NULL | Serie predicha por IA |
| `subserie_clasificada_id` | Integer | FK, NULL | Subserie predicha por IA |
| `fecha_clasificacion` | DateTime | NULL | Fecha de clasificación IA |

**Relaciones:**
- `radicado_asociado_id` → `correspondencia_correspondencia.id`
- `urgencia_asociada_id` → `correspondencia_urgencia.id`
- `usuario_papelera_id` → `auth_user.id`
- `oficina_clasificada_id` → `documentos_oficinaproductora.id`
- `serie_clasificada_id` → `documentos_seriedocumental.id`
- `subserie_clasificada_id` → `documentos_subseriedocumental.id`

---

### Tabla: `correspondencia_adjuntocorreoentrante`

**Descripción:** Archivos adjuntos de correos entrantes

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correo_entrante_id` | Integer | FK, NOT NULL | Correo asociado |
| `archivo` | Varchar(255) | NOT NULL | Ruta del archivo |
| `nombre_original` | Varchar(255) | NULL | Nombre original |
| `tipo_mime` | Varchar(100) | NULL | Tipo MIME |
| `content_id` | Varchar(255) | NULL, INDEX | Content-ID para imágenes inline referenciadas por HTML |
| `fecha_carga` | DateTime | NOT NULL | Fecha de carga |

**Relaciones:**
- `correo_entrante_id` → `correspondencia_correoentrante.id`

---

## Módulo: Correspondencia - Operativa de Correos

### Tabla: `correspondencia_correoproblematico`

**Descripción:** Correos detectados por IMAP/Gmail que no entraron al flujo normal y requieren revisión o admisión manual.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `message_id` | Varchar(255) | UNIQUE, NOT NULL | Message-ID del correo problemático |
| `remitente` | Varchar(254) | NULL | Email remitente |
| `asunto` | Varchar(500) | NULL | Asunto |
| `cuerpo_texto` | Text | NULL | Cuerpo texto para revisión |
| `cuerpo_html` | Text | NULL | HTML para revisión |
| `fecha_recepcion_original` | DateTime | NULL | Fecha del encabezado Date |
| `fecha_recibida_gmail` | DateTime | NULL | INTERNALDATE Gmail/IMAP |
| `fecha_lectura_imap` | DateTime | NOT NULL | Fecha de detección |
| `carpeta_origen` | Varchar(128) | NULL | Carpeta IMAP/Gmail de origen |
| `flujo_origen` | Varchar(32) | NULL | Flujo que detectó el incidente |
| `motivo_problema` | Varchar(64) | DEFAULT: 'VALIDACION_ADJUNTO' | Motivo técnico |
| `detalle_problema` | Text | NULL | Detalle operativo |
| `adjuntos_resumen` | Text | DEFAULT: '[]' | Resumen JSON de adjuntos |
| `respaldo_eml` | Varchar(255) | NULL | Respaldo RFC822/.eml |
| `resuelto` | Boolean | DEFAULT: False, INDEX | Incidente resuelto |
| `fecha_resuelto` | DateTime | NULL | Fecha de resolución |
| `correo_entrante_asociado_id` | Integer | FK, NULL | Correo creado al resolver |

**Relaciones:**
- `correo_entrante_asociado_id` → `correspondencia_correoentrante.id`

---

### Tabla: `correspondencia_estadosincronizacioncorreos`

**Descripción:** Estado resumido de la última sincronización de correos y de la vigencia del watch Gmail.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `fuente` | Varchar(32) | DEFAULT: 'GMAIL_IMAP' | Fuente de sincronización |
| `ultimo_inicio` | DateTime | NULL | Último inicio |
| `ultimo_fin` | DateTime | NULL | Último fin |
| `estado` | Varchar(16) | DEFAULT: 'SUCCESS' | RUNNING, SUCCESS o FAIL |
| `ultimo_error` | Text | NULL | Último error registrado |
| `ultimo_history_id` | Varchar(64) | NULL | History ID Gmail |
| `ultima_renovacion_watch` | DateTime | NULL | Última renovación del watch |
| `watch_expira_en` | DateTime | NULL | Expiración del watch |
| `watch_topic` | Varchar(255) | NULL | Topic Pub/Sub asociado |
| `actualizado_en` | DateTime | NOT NULL | Última actualización |

---

### Tabla: `correspondencia_ejecucioncontrolcorreos`

**Descripción:** Bitácora de verificaciones, recuperaciones, diagnósticos y ciclos operativos de Gmail/IMAP.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `tipo_operacion` | Varchar(24) | NOT NULL | VERIFY, RECOVER, DIAGNOSE, SYNC_NOW, GMAIL_STATUS, etc. |
| `estado` | Varchar(16) | DEFAULT: 'PENDING' | PENDING, RUNNING, SUCCESS, WARN o FAIL |
| `ejecutado_por_id` | Integer | FK, NULL | Usuario que lanzó la operación |
| `task_id` | Varchar(255) | NULL | ID Celery si aplica |
| `parametros` | Text | DEFAULT: '{}' | Parámetros JSON serializados |
| `resumen` | Text | DEFAULT: '{}' | Resumen JSON serializado |
| `salida` | Text | NULL | Salida del comando/proceso |
| `error` | Text | NULL | Error capturado |
| `total_encontrados` | Integer | NULL | Métrica operativa |
| `total_nuevos` | Integer | NULL | Métrica operativa |
| `total_guardados` | Integer | NULL | Métrica operativa |
| `total_rechazados` | Integer | NULL | Métrica operativa |
| `total_adjuntos` | Integer | NULL | Métrica operativa |
| `total_duplicados` | Integer | NULL | Métrica operativa |
| `total_sospechosos` | Integer | NULL | Métrica operativa |
| `total_errores` | Integer | NULL | Métrica operativa |
| `creado_en` | DateTime | NOT NULL | Fecha de creación |
| `iniciado_en` | DateTime | NULL | Inicio real |
| `finalizado_en` | DateTime | NULL | Fin real |

**Relaciones:**
- `ejecutado_por_id` → `auth_user.id`

---

## Módulo: Correspondencia - Distribución y Accesos

### Tabla: `correspondencia_distribucioninternausuario`

**Descripción:** Redistribución de correspondencia a usuarios específicos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, NOT NULL | Correspondencia |
| `usuario_asignado_id` | Integer | FK, NOT NULL | Usuario asignado |
| `fecha_asignacion` | DateTime | NOT NULL | Fecha de asignación |
| `asignado_por_id` | Integer | FK, NULL | Usuario que asignó |
| `leido` | Boolean | DEFAULT: False | Leído por usuario |
| `fecha_lectura` | DateTime | NULL | Fecha de lectura |
| `observaciones` | Text | NULL | Observaciones |

**Restricciones:**
- UNIQUE: `(correspondencia_id, usuario_asignado_id)`

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id`
- `usuario_asignado_id` → `auth_user.id`
- `asignado_por_id` → `auth_user.id`

---

### Tabla: `correspondencia_accesocorrespondenciaoficina`

**Descripción:** Accesos de solo lectura para oficinas distintas a la destino

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, NOT NULL | Correspondencia |
| `oficina_id` | Integer | FK, NOT NULL | Oficina con acceso |
| `compartido_por_id` | Integer | FK, NULL | Usuario que compartió |
| `fecha_compartido` | DateTime | NOT NULL | Fecha de compartido |
| `observaciones` | Text | NULL | Observaciones |
| `leido` | Boolean | DEFAULT: False | Leído por oficina |
| `fecha_lectura` | DateTime | NULL | Fecha de lectura |
| `solo_lider` | Boolean | DEFAULT: True | Solo líderes pueden ver |
| `puede_responder` | Boolean | DEFAULT: False | Puede generar respuestas |

**Restricciones:**
- UNIQUE: `(correspondencia_id, oficina_id)`

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id`
- `oficina_id` → `documentos_oficinaproductora.id`
- `compartido_por_id` → `auth_user.id`

---

## Módulo: Correspondencia - Correspondencia Saliente

### Tabla: `correspondencia_correspondenciasalida`

**Descripción:** Respuestas y comunicaciones salientes

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `respuesta_a_id` | Integer | FK, NULL | Correspondencia entrante a la que responde |
| `respuesta_a_urgencia_id` | Integer | FK, NULL | Urgencia a la que responde |
| `numero_radicado_salida` | Varchar(50) | UNIQUE, NOT NULL | SALIENTE-2026-00001 |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `usuario_redactor_id` | Integer | FK, NULL | Usuario redactor |
| `fecha_ultima_modificacion` | DateTime | NOT NULL | Última modificación |
| `oficina_emisora_id` | Integer | FK, NULL | Oficina emisora |
| `oficina_emisora_nombre` | Varchar(255) | NULL | Snapshot nombre oficina |
| `redactor_nombre` | Varchar(255) | NULL | Snapshot nombre redactor |
| `redactor_cargo` | Varchar(255) | NULL | Snapshot cargo redactor |
| `destinatario_contacto_id` | Integer | FK, NOT NULL | Contacto destinatario |
| `destinatario_email` | Varchar(254) | NOT NULL | Snapshot email destinatario |
| `asunto` | Varchar(255) | NOT NULL | Asunto |
| `cuerpo` | Text | NOT NULL | Cuerpo del mensaje |
| `tipo_respuesta` | Varchar(20) | DEFAULT: 'OBLIGATORIA' | OBLIGATORIA o DISCRECIONAL |
| `motivo_respuesta_discrecional` | Text | NULL | Motivo cuando la respuesta es discrecional |
| `estado` | Varchar(50) | NOT NULL, DEFAULT: 'BORRADOR' | BORRADOR, PENDIENTE_APROBACION, APROBADA, RECHAZADA, ENVIADA, ERROR_ENVIO |
| `usuario_aprobador_id` | Integer | FK, NULL | Usuario aprobador |
| `fecha_aprobacion` | DateTime | NULL | Fecha de aprobación |
| `motivo_rechazo` | Text | NULL | Motivo de rechazo |
| `fecha_envio` | DateTime | NULL | Fecha de envío |
| `id_mensaje_enviado` | Varchar(255) | NULL | Message-ID para seguimiento |
| `postmark_message_id` | Varchar(64) | NULL, INDEX | MessageID devuelto por Postmark |
| `envio_tipo` | Varchar(20) | NULL | INDIVIDUAL, GRUPO, MULTIPLE_SELECTIVO |
| `envio_grupo_id` | Integer | FK, NULL | Grupo utilizado |
| `envio_total_destinatarios` | Integer | NULL | Total destinatarios |
| `envio_detalle_snapshot` | Varchar(255) | NULL | Detalle snapshot |
| `funcionario_envia` | Varchar(255) | DEFAULT: '' | Funcionario que envía (texto libre) |
| `fue_respondida` | Boolean | DEFAULT: False | Marca de respuesta efectiva |
| `evidencia_respuesta` | Varchar(255) | NULL | Evidencia documental de respuesta |

**Relaciones:**
- `respuesta_a_id` → `correspondencia_correspondencia.id`
- `respuesta_a_urgencia_id` → `correspondencia_urgencia.id`
- `usuario_redactor_id` → `auth_user.id`
- `oficina_emisora_id` → `documentos_oficinaproductora.id`
- `destinatario_contacto_id` → `correspondencia_contacto.id`
- `usuario_aprobador_id` → `auth_user.id`
- `envio_grupo_id` → `correspondencia_grupoagenda.id`

---

### Tabla: `correspondencia_adjuntosalida`

**Descripción:** Archivos adjuntos de correspondencia saliente

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_salida_id` | Integer | FK, NOT NULL | Correspondencia saliente |
| `archivo` | Varchar(255) | NOT NULL | Ruta del archivo |
| `nombre_original` | Varchar(255) | NULL | Nombre original |
| `tipo_mime` | Varchar(100) | NULL | Tipo MIME |
| `fecha_carga` | DateTime | NOT NULL | Fecha de carga |

**Relaciones:**
- `correspondencia_salida_id` → `correspondencia_correspondenciasalida.id`

---

### Tabla: `correspondencia_historialsalida`

**Descripción:** Historial de eventos de correspondencia saliente

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_salida_id` | Integer | FK, NOT NULL | Correspondencia saliente |
| `fecha_hora` | DateTime | NOT NULL | Fecha y hora |
| `tipo_evento` | Varchar(30) | NOT NULL | CREACION, RESPUESTA_DISCRECIONAL, MODIFICACION, ENVIO_APROBACION, APROBACION, RECHAZO, INTENTO_ENVIO, ENVIO_EXITOSO, ENVIO_FALLIDO, ENTREGA_CONFIRMADA |
| `usuario_id` | Integer | FK, NULL | Usuario |
| `descripcion` | Text | NULL | Descripción |

**Relaciones:**
- `correspondencia_salida_id` → `correspondencia_correspondenciasalida.id`
- `usuario_id` → `auth_user.id`

---

### Tabla: `correspondencia_salidadestinatario`

**Descripción:** Destinatarios individuales de correspondencia saliente

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_salida_id` | Integer | FK, NOT NULL | Correspondencia saliente |
| `contacto_id` | Integer | FK, NOT NULL | Contacto destinatario |
| `email_snapshot` | Varchar(254) | NOT NULL | Snapshot email |
| `nombre_snapshot` | Varchar(255) | NULL | Snapshot nombre |
| `estado` | Varchar(20) | NOT NULL, DEFAULT: 'PENDIENTE' | PENDIENTE, ENVIADO, FALLO, REBOTE |
| `fecha_envio` | DateTime | NULL | Fecha de envío |
| `id_mensaje_enviado` | Varchar(255) | NULL | Message-ID |
| `postmark_message_id` | Varchar(64) | NULL, INDEX | MessageID devuelto por Postmark |
| `detalle_error` | Text | NULL | Detalle de error |
| `smtp_code` | Varchar(20) | NULL | Código SMTP |
| `dsn_status` | Varchar(20) | NULL | Estado DSN |
| `ultimo_evento_at` | DateTime | NULL | Último evento |

**Relaciones:**
- `correspondencia_salida_id` → `correspondencia_correspondenciasalida.id`
- `contacto_id` → `correspondencia_contacto.id`

---

### Tabla: `correspondencia_postmarkwebhookevento`

**Descripción:** Bitácora idempotente de webhooks de Postmark para seguimiento de entregas, rebotes y eventos de envío.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `record_type` | Varchar(32) | NOT NULL | Tipo de evento reportado por Postmark |
| `postmark_message_id` | Varchar(64) | NOT NULL, INDEX | MessageID de Postmark |
| `recipient` | Varchar(254) | DEFAULT: '' | Destinatario del evento |
| `payload` | JSON | DEFAULT: {} | Cuerpo completo del webhook |
| `recibido_at` | DateTime | NOT NULL | Fecha de recepción |
| `procesado` | Boolean | DEFAULT: False | Indica si ya fue aplicado |
| `resultado` | Varchar(64) | DEFAULT: '' | Resultado del procesamiento |

**Restricciones:**
- UNIQUE: `(record_type, postmark_message_id, recipient)`

---

## Módulo: Correspondencia - Comunicaciones Masivas

### Tabla: `correspondencia_grupoagenda`

**Descripción:** Grupos de contactos para envíos masivos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `oficina_propietaria_id` | Integer | FK, NOT NULL | Oficina propietaria |
| `nombre` | Varchar(150) | NOT NULL | Nombre del grupo |
| `descripcion` | Text | NULL | Descripción |
| `creado_por_id` | Integer | FK, NULL | Usuario creador |
| `activo` | Boolean | DEFAULT: True | Grupo activo |
| `created_at` | DateTime | NOT NULL | Fecha de creación |
| `updated_at` | DateTime | NOT NULL | Fecha de actualización |

**Restricciones:**
- UNIQUE: `(oficina_propietaria_id, nombre)`

**Relaciones:**
- `oficina_propietaria_id` → `documentos_oficinaproductora.id`
- `creado_por_id` → `auth_user.id`

**Tabla intermedia:** `correspondencia_grupoagenda_contactos` (Many-to-Many)
- `grupoagenda_id` → `correspondencia_grupoagenda.id`
- `contacto_id` → `correspondencia_contacto.id`

---

### Tabla: `correspondencia_comunicacionmasiva`

**Descripción:** Comunicaciones masivas independientes

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `oficina_emisora_id` | Integer | FK, NOT NULL | Oficina emisora |
| `usuario_creador_id` | Integer | FK, NULL | Usuario creador |
| `asunto` | Varchar(255) | NOT NULL | Asunto |
| `cuerpo` | Text | NOT NULL | Cuerpo |
| `estado` | Varchar(20) | NOT NULL, DEFAULT: 'BORRADOR' | BORRADOR, ENVIADA, PARCIAL, ERROR |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `fecha_envio` | DateTime | NULL | Fecha de envío |

**Relaciones:**
- `oficina_emisora_id` → `documentos_oficinaproductora.id`
- `usuario_creador_id` → `auth_user.id`

---

### Tabla: `correspondencia_comunicaciondestinatario`

**Descripción:** Destinatarios individuales de comunicaciones masivas

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `comunicacion_id` | Integer | FK, NOT NULL | Comunicación masiva |
| `contacto_id` | Integer | FK, NOT NULL | Contacto destinatario |
| `email_snapshot` | Varchar(254) | NOT NULL | Snapshot email |
| `nombre_snapshot` | Varchar(255) | NULL | Snapshot nombre |
| `estado` | Varchar(20) | NOT NULL, DEFAULT: 'PENDIENTE' | PENDIENTE, ENVIADO, FALLO, REBOTE |
| `fecha_envio` | DateTime | NULL | Fecha de envío |
| `id_mensaje_enviado` | Varchar(255) | NULL | Message-ID |
| `detalle_error` | Text | NULL | Detalle de error |

**Restricciones:**
- UNIQUE: `(comunicacion_id, contacto_id)`

**Relaciones:**
- `comunicacion_id` → `correspondencia_comunicacionmasiva.id`
- `contacto_id` → `correspondencia_contacto.id`

---

## Módulo: Correspondencia - Informes Diarios

### Tabla: `correspondencia_informediariocorrespondencia`

**Descripción:** Informes diarios de correspondencia con archivo firmado

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `fecha` | Date | UNIQUE, NOT NULL | Fecha del informe |
| `archivo_firmado` | Varchar(255) | NULL | Archivo escaneado con firmas |
| `estado` | Varchar(20) | NOT NULL, DEFAULT: 'PENDIENTE' | PENDIENTE, FIRMADO |
| `total_correspondencias` | Integer | DEFAULT: 0 | Total de correspondencias del día |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `fecha_subida_firma` | DateTime | NULL | Fecha de subida de firma |
| `subido_por_id` | Integer | FK, NULL | Usuario que subió |

**Relaciones:**
- `subido_por_id` → `auth_user.id`

---

### Tabla: `correspondencia_historialdescargainforme`

**Descripción:** Historial de descargas de informes

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `informe_id` | Integer | FK, NOT NULL | Informe descargado |
| `usuario_id` | Integer | FK, NULL | Usuario que descargó |
| `fecha_descarga` | DateTime | NOT NULL | Fecha de descarga |
| `ip_address` | Varchar(39) | NULL | Dirección IP |

**Relaciones:**
- `informe_id` → `correspondencia_informediariocorrespondencia.id`
- `usuario_id` → `auth_user.id`

---

## Módulo: Correspondencia - Firmas

### Tabla: `correspondencia_firmacorrespondencia`

**Descripción:** Firmas digitales de correspondencia recibida

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, UNIQUE, NOT NULL | Correspondencia |
| `firma_imagen` | Varchar(255) | NOT NULL | Imagen de la firma |
| `fecha_firma` | DateTime | NOT NULL | Fecha de firma |
| `firmado_por_id` | Integer | FK, NULL | Usuario que firmó |
| `nombre_firmante` | Varchar(255) | NOT NULL | Snapshot nombre |
| `cargo_firmante` | Varchar(255) | NULL | Snapshot cargo |
| `oficina_firmante_id` | Integer | FK, NULL | Oficina del firmante |
| `recolector_id` | Integer | FK, NULL | Usuario que recolectó |
| `ip_address` | Varchar(39) | NULL | Dirección IP |
| `observaciones` | Text | NULL | Observaciones |

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id` (OneToOne)
- `firmado_por_id` → `auth_user.id`
- `oficina_firmante_id` → `documentos_oficinaproductora.id`
- `recolector_id` → `auth_user.id`

---

### Tabla: `correspondencia_firmaauxiliarcorrespondencia`

**Descripción:** Firmas auxiliares adicionales asociadas a una correspondencia recibida sin reemplazar la firma principal.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correspondencia_id` | Integer | FK, NOT NULL | Correspondencia firmada |
| `firma_imagen` | Varchar(255) | NOT NULL | Imagen de la firma auxiliar |
| `fecha_firma` | DateTime | NOT NULL | Fecha de firma |
| `nombre_firmante` | Varchar(255) | NOT NULL | Nombre del firmante auxiliar |
| `cargo_firmante` | Varchar(255) | NOT NULL | Cargo del firmante auxiliar |
| `recolector_id` | Integer | FK, NULL | Usuario que recolectó |
| `ip_address` | Varchar(39) | NULL | Dirección IP |

**Relaciones:**
- `correspondencia_id` → `correspondencia_correspondencia.id`
- `recolector_id` → `auth_user.id`

---

## Módulo: Correspondencia - Comunicaciones Internas

### Tabla: `correspondencia_comunicacioninterna`

**Descripción:** Comunicaciones internas (Oficios entre oficinas)

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `radicado` | Varchar(50) | UNIQUE, NULL | Formato: SIGLA-XX-XXX |
| `trd` | Varchar(100) | NULL | Código TRD |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `ciudad` | Varchar(100) | DEFAULT: 'Saravena' | Ciudad |
| `fecha_documento` | Date | NOT NULL | Fecha del documento |
| `tipo_distribucion` | Varchar(20) | NULL | USUARIO, OFICINA, PROCESO, ENTIDAD |
| `es_a_toda_entidad` | Boolean | DEFAULT: False | DEPRECADO |
| `remitente_usuario_id` | Integer | FK, NOT NULL | Usuario remitente |
| `remitente_nombre` | Varchar(255) | NOT NULL | Snapshot nombre |
| `remitente_cargo` | Varchar(255) | NULL | Snapshot cargo |
| `remitente_oficina_id` | Integer | FK, NOT NULL | Oficina remitente |
| `destinatario_oficina_id` | Integer | FK, NULL | Oficina destino |
| `destinatario_usuario_id` | Integer | FK, NULL | Usuario destino |
| `destinatario_proceso_id` | Integer | FK, NULL | Proceso destino |
| `asunto` | Varchar(255) | NOT NULL | Asunto |
| `cuerpo` | Text | NOT NULL | Cuerpo |
| `archivo_generado` | Varchar(255) | NULL | Documento Word generado |
| `archivo_firmado` | Varchar(255) | NULL | PDF firmado digitalmente |
| `fecha_firma` | DateTime | NULL | Fecha de firma |
| `revisado_por_id` | Integer | FK, NULL | Líder que revisó |
| `revisado_nombre` | Varchar(255) | NULL | Snapshot nombre revisor |
| `revisado_cargo` | Varchar(255) | NULL | Snapshot cargo revisor |
| `fecha_revision` | DateTime | NULL | Fecha de revisión |
| `motivo_rechazo` | Text | NULL | Motivo de rechazo |
| `comunicacion_origen_id` | Integer | FK, UNIQUE, NULL | Comunicación a la que responde |
| `fecha_distribucion` | DateTime | NULL | Fecha de distribución |
| `estado` | Varchar(25) | NOT NULL, DEFAULT: 'BORRADOR' | BORRADOR, PENDIENTE_APROBACION, RECHAZADA, APROBADA, DISTRIBUIDA, RESPONDIDA, ANULADA |

**Restricciones:**
- UNIQUE: `comunicacion_origen_id` (solo 1 respuesta por comunicación)

**Relaciones:**
- `remitente_usuario_id` → `auth_user.id`
- `remitente_oficina_id` → `documentos_oficinaproductora.id`
- `destinatario_oficina_id` → `documentos_oficinaproductora.id`
- `destinatario_usuario_id` → `auth_user.id`
- `destinatario_proceso_id` → `documentos_proceso.id`
- `revisado_por_id` → `auth_user.id`
- `comunicacion_origen_id` → `correspondencia_comunicacioninterna.id` (self-reference)

---

### Tabla: `correspondencia_comunicacioninternadestinatario`

**Descripción:** Destinatarios múltiples de comunicaciones internas

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `comunicacion_id` | Integer | FK, NOT NULL | Comunicación |
| `tipo` | Varchar(10) | NOT NULL | USUARIO u OFICINA |
| `usuario_id` | Integer | FK, NULL | Usuario (si tipo=USUARIO) |
| `oficina_id` | Integer | FK, NULL | Oficina (si tipo=OFICINA) |

**Restricciones:**
- CHECK: Si tipo='USUARIO' entonces usuario_id NOT NULL y oficina_id NULL
- CHECK: Si tipo='OFICINA' entonces oficina_id NOT NULL y usuario_id NULL
- UNIQUE: `(comunicacion_id, usuario_id)`
- UNIQUE: `(comunicacion_id, oficina_id)`

**Relaciones:**
- `comunicacion_id` → `correspondencia_comunicacioninterna.id`
- `usuario_id` → `auth_user.id`
- `oficina_id` → `documentos_oficinaproductora.id`

---

### Tabla: `correspondencia_comunicacioninternadistribucion`

**Descripción:** Distribución de comunicaciones a usuarios específicos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `comunicacion_id` | Integer | FK, NOT NULL | Comunicación |
| `usuario_id` | Integer | FK, NOT NULL | Usuario que recibió |
| `fecha_distribucion` | DateTime | NOT NULL | Fecha de distribución |
| `leido` | Boolean | DEFAULT: False | Leído por usuario |
| `fecha_lectura` | DateTime | NULL | Fecha de lectura |

**Restricciones:**
- UNIQUE: `(comunicacion_id, usuario_id)`

**Relaciones:**
- `comunicacion_id` → `correspondencia_comunicacioninterna.id`
- `usuario_id` → `auth_user.id`

---

### Tabla: `correspondencia_historialcomunicacioninterna`

**Descripción:** Historial de eventos de comunicaciones internas

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `comunicacion_id` | Integer | FK, NOT NULL | Comunicación |
| `evento` | Varchar(30) | NOT NULL | CREADA, EDITADA, ENVIADA_APROBACION, APROBADA, RECHAZADA, FIRMA_SUBIDA, DISTRIBUIDA, LEIDA, RESPUESTA_CREADA, ANULADA |
| `fecha` | DateTime | NOT NULL | Fecha del evento |
| `usuario_id` | Integer | FK, NULL | Usuario |
| `descripcion` | Text | NULL | Descripción |

**Relaciones:**
- `comunicacion_id` → `correspondencia_comunicacioninterna.id`
- `usuario_id` → `auth_user.id`

---

### Tabla: `correspondencia_anexocomunicacioninterna`

**Descripción:** Anexos adjuntos a comunicaciones internas

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `comunicacion_id` | Integer | FK, NOT NULL | Comunicación |
| `archivo` | Varchar(300) | NOT NULL | Ruta del archivo (PDF, Word, Excel) |
| `nombre_original` | Varchar(255) | NULL | Nombre original |
| `fecha_carga` | DateTime | NOT NULL | Fecha de carga |
| `subido_por_id` | Integer | FK, NULL | Usuario que subió |

**Restricciones:**
- Máximo 10 anexos por comunicación
- Tamaño máximo: 2 MB por archivo
- Tamaño total máximo: 10 MB por comunicación
- Formatos permitidos: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`

**Relaciones:**
- `comunicacion_id` → `correspondencia_comunicacioninterna.id`
- `subido_por_id` → `auth_user.id`

---

## Módulo: Correspondencia - Urgencias

### Tabla: `correspondencia_urgencia`

**Descripción:** Correspondencia urgente con SLA en horas laborales. Comparte secuencia de radicado con correspondencia entrante.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `correo_entrante_id` | Integer | FK, NOT NULL | Correo que origina la urgencia |
| `numero_radicado` | Integer | UNIQUE, NOT NULL, INDEX | Consecutivo compartido con entrantes |
| `radicado` | Varchar(50) | UNIQUE, NOT NULL | Formato `ENTRANTE-YYYY-NNNNN` |
| `fecha_radicacion` | DateTime | NOT NULL | Fecha de radicación |
| `usuario_radica_id` | Integer | FK, NOT NULL | Usuario de ventanilla que radica |
| `serie_id` | Integer | FK, NOT NULL | Serie documental |
| `subserie_id` | Integer | FK, NULL | Subserie documental |
| `oficina_destino_id` | Integer | FK, NOT NULL | Oficina completa que recibe la urgencia |
| `horas_limite` | SmallInteger | DEFAULT: 24 | Horas laborales para responder |
| `fecha_limite` | DateTime | NOT NULL | Fecha límite calculada |
| `estado` | Varchar(20) | DEFAULT: 'PENDIENTE', INDEX | PENDIENTE, EN_PROCESO, RESPONDIDA, VENCIDA |
| `usuario_asignado_id` | Integer | FK, NULL | Usuario que tomó la urgencia |
| `fecha_asignacion` | DateTime | NULL | Fecha de toma |
| `usuario_responde_id` | Integer | FK, NULL | Usuario que respondió |
| `fecha_respuesta` | DateTime | NULL | Fecha de respuesta |
| `respuesta` | Text | NULL | Texto de respuesta |
| `prioridad` | Varchar(10) | DEFAULT: 'ALTA', INDEX | ALTA o CRITICA |
| `observaciones` | Text | NULL | Observaciones internas |
| `motivo_urgencia` | Text | NOT NULL | Justificación de urgencia |
| `horas_transcurridas` | Decimal(6,2) | DEFAULT: 0 | Horas laborales consumidas |

**Índices:**
- `(estado, oficina_destino_id)`
- `(prioridad, estado)`
- `fecha_limite`

**Relaciones:**
- `correo_entrante_id` → `correspondencia_correoentrante.id`
- `usuario_radica_id` → `auth_user.id`
- `serie_id` → `documentos_seriedocumental.id`
- `subserie_id` → `documentos_subseriedocumental.id`
- `oficina_destino_id` → `documentos_oficinaproductora.id`
- `usuario_asignado_id` → `auth_user.id`
- `usuario_responde_id` → `auth_user.id`

---

### Tabla: `adjuntos_urgencia`

**Descripción:** Adjuntos de respuestas de urgencias.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `urgencia_id` | Integer | FK, NOT NULL | Urgencia asociada |
| `archivo` | Varchar(255) | NOT NULL | Ruta del archivo |
| `nombre_original` | Varchar(255) | NOT NULL | Nombre original |
| `tipo_mime` | Varchar(100) | NULL | Tipo MIME |
| `tamaño_bytes` | Integer | DEFAULT: 0 | Tamaño en bytes |
| `fecha_carga` | DateTime | NOT NULL | Fecha de carga |
| `subido_por_id` | Integer | FK, NULL | Usuario que subió |

**Relaciones:**
- `urgencia_id` → `correspondencia_urgencia.id`
- `subido_por_id` → `auth_user.id`

---

## Módulo: Correspondencia - Asistente IA Documental

### Tabla: `asistente_conversacion`

**Descripción:** Sesiones de conversación del asistente documental por usuario.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `usuario_id` | Integer | FK, NOT NULL | Usuario dueño de la conversación |
| `titulo` | Varchar(160) | DEFAULT: 'Nueva conversación' | Título visible |
| `estado` | Varchar(20) | DEFAULT: 'ACTIVA' | ACTIVA o ARCHIVADA |
| `ultima_pregunta_at` | DateTime | NULL | Última pregunta del usuario |
| `creado_en` | DateTime | NOT NULL | Fecha de creación |
| `actualizado_en` | DateTime | NOT NULL | Última actualización |

**Relaciones:**
- `usuario_id` → `auth_user.id`

---

### Tabla: `asistente_documento`

**Descripción:** Documento fuente indexado para recuperación documental.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `ruta_relativa` | Varchar(500) | UNIQUE, NOT NULL | Ruta del documento fuente |
| `titulo` | Varchar(255) | NOT NULL | Título del documento |
| `checksum` | Varchar(64) | NOT NULL | Huella del archivo indexado |
| `tipo_fuente` | Varchar(40) | DEFAULT: 'archivo' | Tipo de fuente |
| `activo` | Boolean | DEFAULT: True | Disponible para búsqueda |
| `metadata` | JSON | DEFAULT: {} | Metadatos del documento |
| `indexado_en` | DateTime | NOT NULL | Fecha de indexación/actualización |

---

### Tabla: `asistente_chunk`

**Descripción:** Fragmentos indexados de documentos fuente para recuperación semántica/textual.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `documento_id` | Integer | FK, NOT NULL | Documento fuente |
| `orden` | Integer | NOT NULL | Orden del fragmento dentro del documento |
| `heading` | Varchar(255) | NULL | Encabezado asociado |
| `contenido` | Text | NOT NULL | Contenido del fragmento |
| `search_text` | Text | NULL | Texto normalizado para búsqueda |
| `metadata` | JSON | DEFAULT: {} | Metadatos del fragmento |

**Restricciones:**
- UNIQUE: `(documento_id, orden)`

**Relaciones:**
- `documento_id` → `asistente_documento.id`

---

### Tabla: `asistente_mensaje`

**Descripción:** Mensajes intercambiados en una conversación del asistente documental.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `conversacion_id` | Integer | FK, NOT NULL | Conversación asociada |
| `rol` | Varchar(20) | NOT NULL | user, assistant o system |
| `contenido` | Text | NOT NULL | Contenido del mensaje |
| `citas` | JSON | DEFAULT: [] | Citas/documentos usados |
| `metadata` | JSON | DEFAULT: {} | Metadatos de generación |
| `creado_en` | DateTime | NOT NULL | Fecha de creación |

**Relaciones:**
- `conversacion_id` → `asistente_conversacion.id`

---

## Módulo: Correspondencia - Chat de Soporte

### Tabla: `correspondencia_chatconversation`

**Descripción:** Hilos de soporte interno abiertos por usuarios.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `usuario_id` | Integer | FK, NOT NULL | Usuario que abre el hilo |
| `asunto` | Varchar(200) | NOT NULL | Asunto del reporte |
| `estado` | Varchar(10) | DEFAULT: 'abierta', INDEX | abierta o cerrada |
| `prioridad` | Varchar(10) | DEFAULT: 'normal' | normal o urgente |
| `creado` | DateTime | NOT NULL | Fecha de creación |
| `actualizado` | DateTime | NOT NULL | Última actualización |

**Relaciones:**
- `usuario_id` → `auth_user.id`

---

### Tabla: `correspondencia_chatmessage`

**Descripción:** Mensajes individuales dentro de un hilo de soporte.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `conversacion_id` | Integer | FK, NOT NULL | Conversación de soporte |
| `autor_id` | Integer | FK, NULL | Usuario autor |
| `texto` | Text | NOT NULL | Mensaje |
| `es_admin` | Boolean | DEFAULT: False | Indica si lo envió un admin/superusuario |
| `leido` | Boolean | DEFAULT: False | Mensaje leído |
| `creado` | DateTime | NOT NULL | Fecha de creación |

**Relaciones:**
- `conversacion_id` → `correspondencia_chatconversation.id`
- `autor_id` → `auth_user.id`

---

### Tabla: `correspondencia_chatadjunto`

**Descripción:** Imágenes o capturas adjuntas a mensajes de soporte.

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `mensaje_id` | Integer | FK, NOT NULL | Mensaje asociado |
| `archivo` | Varchar(255) | NOT NULL | Ruta de la imagen |
| `nombre_original` | Varchar(255) | NOT NULL | Nombre original |
| `creado` | DateTime | NOT NULL | Fecha de creación |

**Relaciones:**
- `mensaje_id` → `correspondencia_chatmessage.id`

---

## Módulo: Correspondencia - Notificaciones

### Tabla: `correspondencia_notificacion`

**Descripción:** Notificaciones del sistema para usuarios

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `id` | Integer | PK, Auto | Identificador único |
| `usuario_id` | Integer | FK, NOT NULL | Usuario destinatario |
| `tipo` | Varchar(25) | NOT NULL, DEFAULT: 'asignacion' | asignacion, compartido, respuesta, vencimiento, acceso_oficina, comunicacion_interna, aprobacion_pendiente, urgencia, rebote, otro |
| `titulo` | Varchar(200) | NOT NULL | Título de la notificación |
| `mensaje` | Text | NOT NULL | Mensaje |
| `correspondencia_id` | Integer | FK, NULL | Correspondencia asociada |
| `comunicacion_interna_id` | Integer | FK, NULL | Comunicación interna asociada |
| `leida` | Boolean | DEFAULT: False | Notificación leída |
| `fecha_creacion` | DateTime | NOT NULL | Fecha de creación |
| `fecha_lectura` | DateTime | NULL | Fecha de lectura |
| `url` | Varchar(500) | NULL | URL de destino |

**Índices:**
- `(usuario_id, leida, fecha_creacion DESC)`

**Relaciones:**
- `usuario_id` → `auth_user.id`
- `correspondencia_id` → `correspondencia_correspondencia.id`
- `comunicacion_interna_id` → `correspondencia_comunicacioninterna.id`

---

## 📊 Resumen de Tablas

| Módulo | Número de Tablas |
|--------|------------------|
| Autenticación | 3 |
| Documentos - Estructura | 5 |
| Documentos - TRD | 2 |
| Documentos - FUID | 4 |
| Documentos - Perfiles / Despliegue | 3 |
| Documentos - Pacientes | 3 |
| Documentos - Préstamos | 5 |
| Correspondencia - Contactos | 4 |
| Correspondencia - SLA y Calendario | 4 |
| Correspondencia - Entrante | 4 |
| Correspondencia - IMAP | 2 |
| Correspondencia - Operativa de Correos | 3 |
| Correspondencia - Distribución | 2 |
| Correspondencia - Saliente | 5 |
| Correspondencia - Masivo | 3 |
| Correspondencia - Informes | 2 |
| Correspondencia - Firmas | 2 |
| Correspondencia - Internas | 5 |
| Correspondencia - Urgencias | 2 |
| Correspondencia - Asistente IA | 4 |
| Correspondencia - Chat de Soporte | 3 |
| Correspondencia - Notificaciones | 1 |
| **TOTAL** | **71 tablas documentadas** |

---

## 🔗 Convenciones de Nomenclatura

- **Prefijos de tabla:** `documentos_` o `correspondencia_` según el módulo
- **Campos FK:** Terminan en `_id` (ej: `usuario_id`, `oficina_id`)
- **Campos booleanos:** Prefijo `is_` o `puede_` o nombre descriptivo (ej: `activo`, `leido`)
- **Campos de fecha:** Prefijo `fecha_` o `_at` para timestamps
- **Snapshots:** Campos que congelan datos históricos (ej: `redactor_nombre`, `oficina_emisora_nombre`)

---

**Última actualización:** Junio 2026
**Mantenido por:** Equipo de Desarrollo - Hospital del Sarare E.S.E.
