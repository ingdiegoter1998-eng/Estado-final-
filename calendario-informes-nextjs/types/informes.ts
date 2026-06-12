export interface InformeDiario {
  id: number
  fecha: string // ISO format YYYY-MM-DD
  estado: 'PENDIENTE' | 'FIRMADO'
  total_correspondencias: number
  archivo_firmado?: string
  tiene_archivo: boolean
  fecha_subida_firma?: string
}

export interface DiaCalendario {
  fecha: string
  es_mes_actual: boolean
  es_hoy: boolean
  es_futuro: boolean
  total_correspondencias: number
  tiene_correspondencias: boolean
  informe: InformeDiario | null
}

export interface CalendarioData {
  year: number
  month: number
  month_name: string
  prev_month: number
  prev_year: number
  next_month: number
  next_year: number
  dias: DiaCalendario[]
}

export interface FirmaCorrespondencia {
  id: number
  firma_imagen: string
  fecha_firma: string
  nombre_firmante: string
  cargo_firmante?: string
  observaciones?: string
}

export interface Correspondencia {
  id: number
  numero_radicado: string
  fecha_radicacion: string
  asunto: string
  remitente_nombre: string
  destinatario_nombre: string
  funcionario_responsable: string
  oficina_destino_nombre: string
  requiere_respuesta: boolean
  tiene_firma: boolean
  firma?: FirmaCorrespondencia
  firmas_auxiliares?: FirmaCorrespondencia[]
  total_firmas_auxiliares?: number
  cuerpo_correo?: string
  medio_recepcion?: string
  clasificacion_comunicacion?: string
  numero_folios?: number
  estado?: string
}

export interface HistorialDescarga {
  usuario: string
  fecha_descarga: string
  ip_address?: string
}

export interface EstadisticasFirmas {
  total: number
  firmadas: number
  pendientes: number
  porcentaje: number
}

export interface DetalleDia {
  fecha: string
  informe: InformeDiario
  correspondencias: Correspondencia[]
  historial_descargas: HistorialDescarga[]
  stats_firmas: EstadisticasFirmas
}
