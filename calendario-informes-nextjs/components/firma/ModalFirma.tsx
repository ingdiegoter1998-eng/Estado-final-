'use client'

import { useState, useRef } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import { CanvasFirma, type CanvasFirmaRef } from './CanvasFirma'
import { Correspondencia } from '@/types/informes'
import { guardarFirma } from '@/lib/api/firmas'
import { addPendingFirma } from '@/lib/offlineDb'
import { PenTool, FileText, Loader2, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModalFirmaProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  correspondencia: Correspondencia | null
  onSuccess: () => void
}

export function ModalFirma({
  open,
  onOpenChange,
  correspondencia,
  onSuccess
}: ModalFirmaProps) {
  const [nombreFirmante, setNombreFirmante] = useState('')
  const [cargoFirmante, setCargoFirmante] = useState('')
  const [observaciones, setObservaciones] = useState('')
  const [saving, setSaving] = useState(false)
  const [showExtraFields, setShowExtraFields] = useState(false)
  const { toast } = useToast()
  const canvasRef = useRef<CanvasFirmaRef>(null)

  const handleGuardar = async () => {
    if (!correspondencia) return

    // Validaciones
    const firmaBase64 = canvasRef.current?.getBase64()
    if (!firmaBase64) {
      toast({
        variant: 'destructive',
        title: 'Firma requerida',
        description: 'Debes dibujar la firma en el canvas',
      })
      return
    }

    setSaving(true)

    const firmaData = {
      correspondencia_id: correspondencia.id,
      numero_radicado: correspondencia.numero_radicado,
      firma_base64: firmaBase64,
      nombre_firmante: nombreFirmante.trim() || undefined,
      cargo_firmante: cargoFirmante.trim() || undefined,
      observaciones: observaciones.trim() || undefined,
    }

    // DETECTAR OFFLINE INMEDIATAMENTE
    if (!navigator.onLine) {
      try {
        await addPendingFirma(firmaData)

        toast({
          title: '✉️ Firma guardada localmente',
          description: 'Se sincronizará automáticamente cuando haya conexión',
          className: 'bg-amber-50 border-amber-300 text-amber-900',
        })

        handleReset()
        onOpenChange(false)
        // NO llamar onSuccess() offline - evita refetch que causa error de página
      } catch {
        toast({
          variant: 'destructive',
          title: 'Error al guardar',
          description: 'No se pudo guardar la firma localmente.',
        })
      } finally {
        setSaving(false)
      }
      return
    }

    // Si hay conexión, intentar enviar al servidor
    try {
      await guardarFirma({
        correspondencia_id: firmaData.correspondencia_id,
        firma_base64: firmaData.firma_base64,
        nombre_firmante: firmaData.nombre_firmante,
        cargo_firmante: firmaData.cargo_firmante,
        observaciones: firmaData.observaciones,
      })

      toast({
        title: 'Firma guardada exitosamente',
        description: 'La firma digital se registró correctamente',
        className: 'bg-success-light border-success',
      })

      handleReset()
      onOpenChange(false)
      onSuccess()
    } catch (error: any) {
      const isNetworkError =
        error?.code === 'ERR_NETWORK' ||
        error?.code === 'ECONNABORTED' ||
        error?.message === 'Network Error' ||
        !error?.response

      if (isNetworkError) {
        try {
          await addPendingFirma(firmaData)

          toast({
            title: '✉️ Firma guardada localmente',
            description: 'Se sincronizará automáticamente cuando haya conexión',
            className: 'bg-amber-50 border-amber-300 text-amber-900',
          })

          handleReset()
          onOpenChange(false)
          // NO llamar onSuccess() - evita refetch que causa error
        } catch {
          toast({
            variant: 'destructive',
            title: 'Error al guardar',
            description: 'No se pudo guardar la firma localmente.',
          })
        }
      } else {
        const serverMsg = error?.response?.data?.error || 'No se pudo registrar la firma.'
        toast({
          variant: 'destructive',
          title: 'Error al guardar firma',
          description: serverMsg,
        })
      }
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    handleReset()
    onOpenChange(false)
  }

  const handleReset = () => {
    setNombreFirmante('')
    setCargoFirmante('')
    setObservaciones('')
    setShowExtraFields(false)
    canvasRef.current?.clearCanvas()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[650px] max-h-[90vh] overflow-y-auto">
        {/* Header con diseño médico */}
        <DialogHeader className="space-y-3 pb-4 border-b-2 border-primary-custom/20">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-custom to-secondary-custom flex items-center justify-center shadow-lg">
              <PenTool className="w-6 h-6 text-white" strokeWidth={2.5} />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-2xl font-bold bg-gradient-to-r from-primary-custom to-secondary-custom bg-clip-text text-transparent">
                Recolectar Firma Digital
              </DialogTitle>
              <DialogDescription className="text-sm font-medium text-slate-600 flex items-center gap-2 mt-1">
                <FileText className="w-4 h-4" />
                Radicado: <span className="font-bold text-primary-custom">{correspondencia?.numero_radicado}</span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Formulario */}
        <div className="space-y-5 py-4">
          {/* Información del documento */}
          <div className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50/50 rounded-lg border border-blue-200">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-slate-500 font-medium">Remitente:</span>
                <p className="font-semibold text-slate-800 mt-0.5">{correspondencia?.remitente_nombre}</p>
              </div>
              <div>
                <span className="text-slate-500 font-medium">Fecha:</span>
                <p className="font-semibold text-slate-800 mt-0.5">
                  {correspondencia && new Date(correspondencia.fecha_radicacion).toLocaleString('es-ES', {
                    day: '2-digit',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
            </div>
          </div>

          {/* Canvas Firma - PRIMERO, es lo principal */}
          <div className="space-y-2">
            <Label className="text-sm font-bold text-slate-700 flex items-center gap-1">
              Firma Digital
              <span className="text-red-500 text-base">*</span>
            </Label>
            <div className="p-4 bg-slate-50 rounded-lg border-2 border-slate-200">
              <CanvasFirma ref={canvasRef} />
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              La firma será almacenada de forma segura y vinculada al documento
            </p>
          </div>

          {/* Datos adicionales del firmante - colapsados por defecto */}
          <div className="border rounded-lg border-slate-200 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowExtraFields(!showExtraFields)}
              className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
            >
              <span className="text-sm font-medium text-slate-600">
                Datos adicionales (opcional)
              </span>
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-slate-400 transition-transform duration-200",
                  showExtraFields && "rotate-180"
                )}
              />
            </button>
            {showExtraFields && (
              <div className="px-4 py-3 space-y-4 border-t border-slate-200 bg-white">
                <div className="space-y-1.5">
                  <Label htmlFor="nombre" className="text-sm text-slate-600">
                    Nombre del Firmante
                  </Label>
                  <Input
                    id="nombre"
                    value={nombreFirmante}
                    onChange={(e) => setNombreFirmante(e.target.value)}
                    placeholder="Ej: Juan Pérez García"
                    className="border focus:border-primary-custom transition-colors"
                    disabled={saving}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="cargo" className="text-sm text-slate-600">
                    Cargo o Posición
                  </Label>
                  <Input
                    id="cargo"
                    value={cargoFirmante}
                    onChange={(e) => setCargoFirmante(e.target.value)}
                    placeholder="Ej: Director Administrativo"
                    className="border focus:border-primary-custom transition-colors"
                    disabled={saving}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="obs" className="text-sm text-slate-600">
                    Observaciones
                  </Label>
                  <Textarea
                    id="obs"
                    value={observaciones}
                    onChange={(e) => setObservaciones(e.target.value)}
                    placeholder="Notas adicionales sobre la firma (opcional)..."
                    rows={2}
                    className="border focus:border-primary-custom transition-colors resize-none"
                    disabled={saving}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <DialogFooter className="gap-2 pt-4 border-t-2 border-slate-200">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={saving}
            className="border-2 hover:bg-slate-50"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleGuardar}
            disabled={saving}
            className="bg-gradient-to-r from-primary-custom to-secondary-custom hover:opacity-90 font-semibold shadow-md min-w-[140px]"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <PenTool className="w-4 h-4 mr-2" />
                Guardar Firma
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
