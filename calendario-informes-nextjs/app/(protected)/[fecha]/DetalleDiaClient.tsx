'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useInformeDia } from '@/lib/hooks/useInformeDia'
import { CardEstadisticas } from '@/components/informes/CardEstadisticas'
import { TablaCorrespondencias } from '@/components/informes/TablaCorrespondencias'
import { SeccionHistorial } from '@/components/informes/SeccionHistorial'
import { SubirArchivo } from '@/components/informes/SubirArchivo'
import { ModalFirma } from '@/components/firma/ModalFirma'
import { ModalFirmaAuxiliar } from '@/components/firma/ModalFirmaAuxiliar'
import { ModalVerFirma } from '@/components/firma/ModalVerFirma'
import { ModalDetalleCorrespondencia } from '@/components/informes/ModalDetalleCorrespondencia'
import { Button } from '@/components/ui/button'
import { Download, ChevronLeft, FileText } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { descargarExcel } from '@/lib/api/informes'
import { Correspondencia } from '@/types/informes'
import { cn } from '@/lib/utils'
import { getAllQueuedFirmas } from '@/lib/offlineDb'

interface DetalleDiaClientProps {
  fecha: string
}

export function DetalleDiaClient({ fecha }: DetalleDiaClientProps) {
  const router = useRouter()
  const { detalle, isLoading, error, refetch } = useInformeDia(fecha)

  const [modalFirmaOpen, setModalFirmaOpen] = useState(false)
  const [modalFirmaAuxiliarOpen, setModalFirmaAuxiliarOpen] = useState(false)
  const [correspondenciaSeleccionada, setCorrespondenciaSeleccionada] = useState<Correspondencia | null>(null)
  const [modalVerFirmaOpen, setModalVerFirmaOpen] = useState(false)
  const [modalDetalleOpen, setModalDetalleOpen] = useState(false)
  const [offlineFirmaIds, setOfflineFirmaIds] = useState<Set<number>>(new Set())

  // Cargar IDs de firmas guardadas offline
  const refreshOfflineIds = useCallback(async () => {
    try {
      const queued = await getAllQueuedFirmas()
      setOfflineFirmaIds(new Set(queued.map(f => f.correspondencia_id)))
    } catch {
      // IndexedDB no disponible
    }
  }, [])

  useEffect(() => {
    refreshOfflineIds()
    // Refrescar cada 5s para detectar cambios por sync
    const interval = setInterval(refreshOfflineIds, 5000)
    return () => clearInterval(interval)
  }, [refreshOfflineIds])

  const handleDescargarExcel = async () => {
    try {
      await descargarExcel(fecha)
      refetch() // Refrescar historial
    } catch (error) {
      console.error('Error descargando Excel:', error)
    }
  }

  const handleFirmar = (correspondencia: Correspondencia) => {
    setCorrespondenciaSeleccionada(correspondencia)
    setModalFirmaOpen(true)
  }

  const handleVerFirma = (correspondencia: Correspondencia) => {
    setCorrespondenciaSeleccionada(correspondencia)
    setModalVerFirmaOpen(true)
  }

  const handleAgregarFirmaAuxiliar = (correspondencia: Correspondencia) => {
    setCorrespondenciaSeleccionada(correspondencia)
    setModalFirmaAuxiliarOpen(true)
  }

  const handleVerDetalle = (correspondencia: Correspondencia) => {
    setCorrespondenciaSeleccionada(correspondencia)
    setModalDetalleOpen(true)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/20 to-slate-100">
        <div className="container mx-auto py-8 px-4 max-w-7xl">
          <div className="animate-pulse space-y-6">
            {/* Header skeleton */}
            <div className="flex items-center gap-4 mb-8">
              <div className="h-10 w-24 bg-slate-200 rounded" />
              <div className="h-12 w-96 bg-slate-200 rounded" />
            </div>
            {/* Stats skeleton */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-32 bg-slate-200 rounded-xl" />
              ))}
            </div>
            {/* Table skeleton */}
            <div className="h-96 bg-slate-200 rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !detalle) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/20 to-slate-100">
        <div className="container mx-auto py-8 px-4 max-w-7xl">
          <Card className="p-12 text-center border-2 border-red-200 bg-gradient-to-br from-red-50 to-orange-50">
            <div className="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-red-100">
              <FileText className="w-8 h-8 text-red-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Error al cargar detalle del día
            </h3>
            <p className="text-gray-600 mb-6">
              No se pudo conectar con el servidor. Por favor, intente nuevamente.
            </p>
            <Button
              onClick={() => window.location.reload()}
              className="bg-red-600 hover:bg-red-700"
            >
              Reintentar
            </Button>
          </Card>
        </div>
      </div>
    )
  }

  const fechaFormateada = new Date(fecha + 'T12:00:00').toLocaleDateString('es-ES', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/20 to-slate-100">
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        {/* Header */}
        <div className="mb-8 animate-in fade-in slide-in-from-top duration-500">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.back()}
                className="hover:bg-white/80 hover:-translate-x-1 transition-all"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Volver
              </Button>
              <div className="h-8 w-px bg-slate-300" />
              <div>
                <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary-custom via-secondary-custom to-primary-custom bg-clip-text text-transparent capitalize">
                  {fechaFormateada}
                </h1>
                <div className="flex items-center gap-2 mt-2">
                  <Badge
                    variant={detalle.informe.estado === 'FIRMADO' ? 'default' : 'secondary'}
                    className={cn(
                      "font-semibold shadow-sm",
                      detalle.informe.estado === 'FIRMADO'
                        ? "bg-success text-white"
                        : "bg-warning text-gray-800"
                    )}
                  >
                    {detalle.informe.estado}
                  </Badge>
                  {detalle.informe.tiene_archivo && (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                      Archivo subido
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={handleDescargarExcel}
              className="bg-white hover:bg-slate-50 border-slate-300 hover:border-secondary-custom transition-all hover:scale-105 shadow-sm"
            >
              <Download className="h-4 w-4 mr-2" />
              Descargar Excel
            </Button>
          </div>
        </div>

        {/* Estadísticas */}
        <CardEstadisticas
          stats={detalle.stats_firmas}
          totalDescargas={detalle.historial_descargas.length}
          fechaFirma={detalle.informe.fecha_subida_firma}
        />

        {/* Subida de archivo firmado */}
        <SubirArchivo
          fecha={fecha}
          informeActual={detalle.informe}
          onUploadSuccess={refetch}
        />

        {/* Tabla de correspondencias */}
        <div className="mb-6 animate-in fade-in slide-in-from-bottom duration-500" style={{ animationDelay: '200ms' }}>
          <TablaCorrespondencias
            correspondencias={detalle.correspondencias}
            onFirmar={handleFirmar}
            onVerFirma={handleVerFirma}
            onAgregarFirmaAuxiliar={handleAgregarFirmaAuxiliar}
            onVerDetalle={handleVerDetalle}
            offlineFirmaIds={offlineFirmaIds}
          />
        </div>

        {/* Historial */}
        <div className="animate-in fade-in slide-in-from-bottom duration-500" style={{ animationDelay: '300ms' }}>
          <SeccionHistorial historial={detalle.historial_descargas} />
        </div>

        {/* Modales de firma */}
        <ModalFirma
          open={modalFirmaOpen}
          onOpenChange={(open) => {
            setModalFirmaOpen(open)
            if (!open) refreshOfflineIds()
          }}
          correspondencia={correspondenciaSeleccionada}
          onSuccess={() => { refetch(); refreshOfflineIds() }}
        />

        <ModalVerFirma
          open={modalVerFirmaOpen}
          onOpenChange={setModalVerFirmaOpen}
          correspondencia={correspondenciaSeleccionada}
        />

        <ModalFirmaAuxiliar
          open={modalFirmaAuxiliarOpen}
          onOpenChange={setModalFirmaAuxiliarOpen}
          correspondencia={correspondenciaSeleccionada}
          onSuccess={refetch}
        />

        <ModalDetalleCorrespondencia
          open={modalDetalleOpen}
          onOpenChange={setModalDetalleOpen}
          correspondencia={correspondenciaSeleccionada}
        />
      </div>
    </div>
  )
}
