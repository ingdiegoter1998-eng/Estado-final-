'use client'

import { useRef, useState } from 'react'
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
import { useToast } from '@/hooks/use-toast'
import { CanvasFirma, type CanvasFirmaRef } from './CanvasFirma'
import { guardarFirmaAuxiliar } from '@/lib/api/firmas'
import { Correspondencia } from '@/types/informes'
import { Briefcase, Loader2, PenTool, PlusCircle, User } from 'lucide-react'

interface ModalFirmaAuxiliarProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  correspondencia: Correspondencia | null
  onSuccess: () => void
}

export function ModalFirmaAuxiliar({
  open,
  onOpenChange,
  correspondencia,
  onSuccess,
}: ModalFirmaAuxiliarProps) {
  const { toast } = useToast()
  const canvasRef = useRef<CanvasFirmaRef>(null)
  const [nombreFirmante, setNombreFirmante] = useState('')
  const [cargoFirmante, setCargoFirmante] = useState('')
  const [saving, setSaving] = useState(false)

  const resetForm = () => {
    setNombreFirmante('')
    setCargoFirmante('')
    canvasRef.current?.clearCanvas()
  }

  const handleClose = () => {
    if (saving) return
    resetForm()
    onOpenChange(false)
  }

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      handleClose()
      return
    }
    onOpenChange(true)
  }

  const handleGuardar = async () => {
    if (!correspondencia) return

    const firmaBase64 = canvasRef.current?.getBase64()
    const nombre = nombreFirmante.trim()
    const cargo = cargoFirmante.trim()

    if (!nombre || !cargo || !firmaBase64) {
      toast({
        variant: 'destructive',
        title: 'Datos incompletos',
        description: 'Debes registrar nombre, cargo y firma auxiliar.',
      })
      return
    }

    setSaving(true)
    try {
      await guardarFirmaAuxiliar({
        correspondencia_id: correspondencia.id,
        firma_base64: firmaBase64,
        nombre_firmante: nombre,
        cargo_firmante: cargo,
      })

      toast({
        title: 'Firma auxiliar registrada',
        description: 'La firma auxiliar quedó asociada a la correspondencia.',
        className: 'bg-success-light border-success',
      })

      resetForm()
      onOpenChange(false)
      onSuccess()
    } catch (error: any) {
      const serverMsg = error?.response?.data?.error || 'No se pudo guardar la firma auxiliar.'
      toast({
        variant: 'destructive',
        title: 'Error al guardar',
        description: serverMsg,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[640px] max-h-[90vh] overflow-y-auto">
        <DialogHeader className="space-y-3 pb-4 border-b-2 border-secondary-custom/20">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-secondary-custom to-primary-custom flex items-center justify-center shadow-lg">
              <PlusCircle className="w-6 h-6 text-white" strokeWidth={2.4} />
            </div>
            <div>
              <DialogTitle className="text-2xl font-bold bg-gradient-to-r from-secondary-custom to-primary-custom bg-clip-text text-transparent">
                Agregar Firma Auxiliar
              </DialogTitle>
              <DialogDescription className="mt-1 text-sm text-slate-600">
                Radicado: <span className="font-semibold text-primary-custom">{correspondencia?.numero_radicado}</span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-5 py-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="aux-nombre" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <User className="w-4 h-4" />
                Nombre
              </Label>
              <Input
                id="aux-nombre"
                value={nombreFirmante}
                onChange={(e) => setNombreFirmante(e.target.value)}
                placeholder="Nombre completo"
                disabled={saving}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="aux-cargo" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Briefcase className="w-4 h-4" />
                Cargo
              </Label>
              <Input
                id="aux-cargo"
                value={cargoFirmante}
                onChange={(e) => setCargoFirmante(e.target.value)}
                placeholder="Cargo o rol"
                disabled={saving}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-bold text-slate-700 flex items-center gap-2">
              <PenTool className="w-4 h-4" />
              Firma auxiliar
            </Label>
            <div className="p-4 bg-slate-50 rounded-lg border-2 border-slate-200">
              <CanvasFirma ref={canvasRef} />
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 pt-4 border-t-2 border-slate-200">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={saving}
            className="border-2 hover:bg-slate-50"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleGuardar}
            disabled={saving}
            className="bg-gradient-to-r from-secondary-custom to-primary-custom hover:opacity-90 font-semibold shadow-md min-w-[170px]"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <PlusCircle className="w-4 h-4 mr-2" />
                Guardar auxiliar
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
