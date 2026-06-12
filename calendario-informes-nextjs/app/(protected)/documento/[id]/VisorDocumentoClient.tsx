'use client'

import { useState } from 'react'
import { useDocumento } from '@/hooks/useDocumento'
import { getDocumentoPdfUrl, getAnexoUrl } from '@/lib/api/documento'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  FileText,
  ArrowLeft,
  Download,
  Paperclip,
  Clock,
  User,
  Building2,
  FileSignature,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  Eye,
  ExternalLink,
  Image as ImageIcon,
} from 'lucide-react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

const ESTADO_COLORS: Record<string, string> = {
  BORRADOR: 'bg-gray-100 text-gray-700 border-gray-300',
  PENDIENTE_APROBACION: 'bg-amber-50 text-amber-700 border-amber-300',
  RECHAZADA: 'bg-red-50 text-red-700 border-red-300',
  APROBADA: 'bg-blue-50 text-blue-700 border-blue-300',
  DISTRIBUIDA: 'bg-emerald-50 text-emerald-700 border-emerald-300',
  RESPONDIDA: 'bg-purple-50 text-purple-700 border-purple-300',
  ANULADA: 'bg-red-100 text-red-800 border-red-400',
}

type ViewerTab = {
  id: string
  label: string
  shortLabel: string
  url: string
  previewable: boolean
  downloadName: string
  icon: 'documento' | 'firmado' | 'anexo' | 'imagen'
}

export default function VisorDocumentoClient({ id }: { id: number }) {
  const { data: doc, isLoading, error } = useDocumento(id)
  const [activeTabId, setActiveTabId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [historialOpen, setHistorialOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-500" />
          <p className="text-sm text-muted-foreground">Cargando documento...</p>
        </div>
      </div>
    )
  }

  if (error || !doc) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center space-y-3">
            <AlertCircle className="h-10 w-10 mx-auto text-red-500" />
            <p className="font-medium">No se pudo cargar el documento</p>
            <p className="text-sm text-muted-foreground">
              {error?.message || 'El documento no existe o no tienes acceso.'}
            </p>
            <Button variant="outline" onClick={() => window.history.back()}>
              <ArrowLeft className="h-4 w-4 mr-2" /> Volver
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const estadoClasses = ESTADO_COLORS[doc.estado] || ESTADO_COLORS.BORRADOR

  const viewerTabs: ViewerTab[] = []

  if (doc.tiene_pdf) {
    viewerTabs.push({
      id: 'generado',
      label: 'Documento principal',
      shortLabel: 'Principal',
      url: getDocumentoPdfUrl(id, 'generado'),
      previewable: true,
      downloadName: `${doc.radicado.replace(/\//g, '_')}.pdf`,
      icon: 'documento',
    })
  }

  if (doc.tiene_firmado) {
    viewerTabs.push({
      id: 'firmado',
      label: 'Documento firmado',
      shortLabel: 'Firmado',
      url: getDocumentoPdfUrl(id, 'firmado'),
      previewable: true,
      downloadName: `${doc.radicado.replace(/\//g, '_')}_firmado.pdf`,
      icon: 'firmado',
    })
  }

  for (const anexo of doc.anexos) {
    const extension = anexo.nombre.includes('.')
      ? anexo.nombre.split('.').pop()?.toLowerCase() || 'archivo'
      : 'archivo'

    viewerTabs.push({
      id: `anexo-${anexo.id}`,
      label: anexo.nombre,
      shortLabel: anexo.nombre,
      url: getAnexoUrl(id, anexo.id),
      previewable: anexo.es_previsualizable,
      downloadName: anexo.nombre || `anexo_${anexo.id}.${extension}`,
      icon: anexo.content_type.startsWith('image/') ? 'imagen' : 'anexo',
    })
  }

  const activeTab = viewerTabs.find((tab) => tab.id === activeTabId) ?? viewerTabs[0] ?? null

  const handleDownload = () => {
    if (activeTab) {
      const a = document.createElement('a')
      a.href = activeTab.url
      a.download = activeTab.downloadName
      a.click()
    }
  }

  const handleOpenExternal = () => {
    if (activeTab) {
      window.open(activeTab.url, '_blank', 'noopener,noreferrer')
    }
  }

  const formatFecha = (iso: string) => {
    try {
      return format(new Date(iso), "d 'de' MMMM yyyy, h:mm a", { locale: es })
    } catch {
      return iso
    }
  }

  const formatFechaCorta = (iso: string) => {
    try {
      return format(new Date(iso), 'dd/MM/yyyy HH:mm', { locale: es })
    } catch {
      return iso
    }
  }

  const renderTabIcon = (tab: ViewerTab) => {
    if (tab.icon === 'firmado') {
      return <FileSignature className="h-3.5 w-3.5" />
    }

    if (tab.icon === 'imagen') {
      return <ImageIcon className="h-3.5 w-3.5" />
    }

    if (tab.icon === 'anexo') {
      return <Paperclip className="h-3.5 w-3.5" />
    }

    return <FileText className="h-3.5 w-3.5" />
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b shrink-0">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.history.back()}
            title="Volver"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-blue-600" />
            <span className="font-semibold text-sm">{doc.radicado}</span>
          </div>
          <Badge className={`text-xs ${estadoClasses}`}>
            {doc.estado_display}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {activeTab && (
            <Badge variant="outline" className="hidden md:inline-flex text-xs">
              {activeTab.label}
            </Badge>
          )}
          {activeTab && (
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-1.5" />
              Descargar
            </Button>
          )}
          {activeTab && !activeTab.previewable && (
            <Button variant="outline" size="sm" onClick={handleOpenExternal}>
              <ExternalLink className="h-4 w-4 mr-1.5" />
              Abrir
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Ocultar detalles' : 'Mostrar detalles'}
          >
            {sidebarOpen ? 'Ocultar info' : 'Info'}
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* PDF Viewer */}
        <div className="flex flex-1 flex-col bg-slate-100 min-w-0">
          {viewerTabs.length > 0 && (
            <div className="border-b bg-white px-3 py-2 shrink-0">
              <div className="flex gap-2 overflow-x-auto pb-1">
                {viewerTabs.map((tab) => {
                  const isActive = activeTab?.id === tab.id

                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveTabId(tab.id)}
                      className={[
                        'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm whitespace-nowrap transition-colors',
                        isActive
                          ? 'border-slate-900 bg-slate-900 text-white shadow-sm'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50',
                      ].join(' ')}
                      title={tab.label}
                    >
                      {renderTabIcon(tab)}
                      <span className="max-w-[220px] truncate">{tab.shortLabel}</span>
                      {!tab.previewable && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                          abrir
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex-1 bg-gray-100">
            {activeTab ? (
              activeTab.previewable ? (
                <iframe
                  key={activeTab.id}
                  src={activeTab.url}
                  className="w-full h-full border-0"
                  title={`${activeTab.label} - ${doc.radicado}`}
                />
              ) : (
                <div className="flex items-center justify-center h-full p-6">
                  <Card className="max-w-lg w-full border-slate-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-lg">Vista previa no disponible</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 text-sm text-muted-foreground">
                      <p>
                        Este adjunto no se puede embeber directamente en el navegador con seguridad.
                        Puedes abrirlo en una pestaña aparte o descargarlo.
                      </p>
                      <div className="flex gap-2">
                        <Button onClick={handleOpenExternal}>
                          <Eye className="h-4 w-4 mr-1.5" />
                          Abrir archivo
                        </Button>
                        <Button variant="outline" onClick={handleDownload}>
                          <Download className="h-4 w-4 mr-1.5" />
                          Descargar
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center space-y-3">
                  <FileText className="h-12 w-12 mx-auto text-gray-400" />
                  <p className="text-muted-foreground">
                    No hay documentos disponibles para esta comunicación
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        {sidebarOpen && (
          <div className="w-80 border-l bg-white overflow-y-auto shrink-0">
            <div className="p-4 space-y-4">
              {/* Asunto */}
              <div>
                <h2 className="font-semibold text-base leading-snug">
                  {doc.asunto}
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  {doc.ciudad} &middot;{' '}
                  {doc.fecha_documento
                    ? formatFecha(doc.fecha_documento)
                    : formatFecha(doc.fecha_creacion)}
                </p>
              </div>

              <Separator />

              {/* Remitente */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  <User className="h-3.5 w-3.5" /> Remitente
                </div>
                <p className="text-sm font-medium">{doc.remitente.nombre}</p>
                {doc.remitente.cargo && (
                  <p className="text-xs text-muted-foreground">{doc.remitente.cargo}</p>
                )}
                {doc.remitente.oficina && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Building2 className="h-3 w-3" />
                    {doc.remitente.oficina}
                  </div>
                )}
              </div>

              <Separator />

              {/* Destinatario */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  <Building2 className="h-3.5 w-3.5" /> Destinatario
                </div>
                {doc.destinatario.usuario && (
                  <p className="text-sm font-medium">{doc.destinatario.usuario}</p>
                )}
                {doc.destinatario.oficina && (
                  <p className="text-xs text-muted-foreground">
                    {doc.destinatario.oficina}
                  </p>
                )}
                {doc.tipo_distribucion_display && (
                  <Badge variant="outline" className="text-xs">
                    {doc.tipo_distribucion_display}
                  </Badge>
                )}
              </div>

              {/* Anexos */}
              {doc.anexos.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      <Paperclip className="h-3.5 w-3.5" /> Anexos ({doc.anexos.length})
                    </div>
                    <div className="space-y-1">
                      {doc.anexos.map((anexo) => (
                        <button
                          key={anexo.id}
                          type="button"
                          onClick={() => setActiveTabId(`anexo-${anexo.id}`)}
                          className="flex w-full items-center gap-2 p-2 rounded-md hover:bg-muted/50 transition-colors text-sm group text-left"
                        >
                          <Paperclip className="h-3.5 w-3.5 text-muted-foreground group-hover:text-blue-500 shrink-0" />
                          <span className="min-w-0 flex-1 truncate group-hover:text-blue-600">
                            {anexo.nombre}
                          </span>
                          {!anexo.es_previsualizable && (
                            <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Historial */}
              {doc.historial.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <button
                      onClick={() => setHistorialOpen(!historialOpen)}
                      className="flex items-center justify-between w-full text-xs font-medium text-muted-foreground uppercase tracking-wide hover:text-foreground transition-colors"
                    >
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" /> Historial
                      </span>
                      {historialOpen ? (
                        <ChevronUp className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" />
                      )}
                    </button>
                    {historialOpen && (
                      <div className="space-y-2 pl-1">
                        {doc.historial.map((h, i) => (
                          <div key={i} className="relative pl-4 pb-2 border-l border-muted">
                            <div className="absolute -left-1 top-0.5 w-2 h-2 rounded-full bg-blue-400" />
                            <p className="text-xs font-medium">{h.evento}</p>
                            <p className="text-[10px] text-muted-foreground">
                              {formatFechaCorta(h.fecha)}
                              {h.usuario && ` — ${h.usuario}`}
                            </p>
                            {h.descripcion && (
                              <p className="text-[10px] text-muted-foreground mt-0.5">
                                {h.descripcion}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
