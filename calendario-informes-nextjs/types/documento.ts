export interface DocumentoRemitente {
  nombre: string
  cargo: string
  oficina: string
}

export interface DocumentoDestinatario {
  oficina: string
  usuario: string
}

export interface DocumentoAnexo {
  id: number
  nombre: string
  fecha: string
  content_type: string
  es_previsualizable: boolean
}

export interface DocumentoHistorial {
  evento: string
  fecha: string
  usuario: string
  descripcion: string
}

export interface DocumentoMeta {
  id: number
  radicado: string
  asunto: string
  estado: string
  estado_display: string
  tipo_distribucion: string
  tipo_distribucion_display: string
  fecha_creacion: string
  fecha_documento: string | null
  ciudad: string
  remitente: DocumentoRemitente
  destinatario: DocumentoDestinatario
  cuerpo: string
  tiene_pdf: boolean
  tiene_firmado: boolean
  anexos: DocumentoAnexo[]
  historial: DocumentoHistorial[]
}
