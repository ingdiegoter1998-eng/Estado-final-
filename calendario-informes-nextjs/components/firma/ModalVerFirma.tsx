'use client'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Correspondencia, FirmaCorrespondencia } from '@/types/informes'
import { CheckCircle2, User, Briefcase, Calendar, FileText, MessageSquare, Layers3 } from 'lucide-react'

interface ModalVerFirmaProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  correspondencia: Correspondencia | null
}

export function ModalVerFirma({ open, onOpenChange, correspondencia }: ModalVerFirmaProps) {
  const firmaPrincipal = correspondencia?.firma
  const firmasAuxiliares = correspondencia?.firmas_auxiliares ?? []

  if (!firmaPrincipal && firmasAuxiliares.length === 0) return null

  const renderFirmaCard = (
    firma: FirmaCorrespondencia,
    titulo: string,
    tone: 'success' | 'secondary' = 'success'
  ) => (
    <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={tone === 'success'
              ? 'bg-success/10 text-success border-success/20 font-semibold'
              : 'bg-secondary-custom/10 text-secondary-custom border-secondary-custom/20 font-semibold'}
          >
            {titulo}
          </Badge>
        </div>
      </div>

      <div className="relative rounded-xl border-3 border-slate-200 p-6 bg-gradient-to-br from-white to-slate-50 shadow-inner">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={firma.firma_imagen}
          alt={titulo}
          className="w-full h-auto max-h-[200px] object-contain"
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <div className="w-10 h-10 rounded-lg bg-primary-custom/10 flex items-center justify-center flex-shrink-0">
            <User className="w-5 h-5 text-primary-custom" strokeWidth={2.5} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              Nombre del Firmante
            </p>
            <p className="text-base font-bold text-slate-800">
              {firma.nombre_firmante || 'Sin nombre registrado'}
            </p>
          </div>
        </div>

        {firma.cargo_firmante && (
          <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="w-10 h-10 rounded-lg bg-secondary-custom/10 flex items-center justify-center flex-shrink-0">
              <Briefcase className="w-5 h-5 text-secondary-custom" strokeWidth={2.5} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                Cargo
              </p>
              <p className="text-base font-semibold text-slate-700">
                {firma.cargo_firmante}
              </p>
            </div>
          </div>
        )}

        <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center flex-shrink-0">
            <Calendar className="w-5 h-5 text-success" strokeWidth={2.5} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              Fecha y Hora de Firma
            </p>
            <p className="text-base font-semibold text-slate-700">
              {new Date(firma.fecha_firma).toLocaleString('es-ES', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
              })}
            </p>
          </div>
        </div>

        {firma.observaciones && (
          <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
              <MessageSquare className="w-5 h-5 text-blue-600" strokeWidth={2.5} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">
                Observaciones
              </p>
              <p className="text-sm text-slate-700 leading-relaxed">
                {firma.observaciones}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[720px] max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <DialogHeader className="space-y-3 pb-4 border-b-2 border-success/20">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-success to-emerald-500 flex items-center justify-center shadow-lg">
              <CheckCircle2 className="w-6 h-6 text-white" strokeWidth={2.5} />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-2xl font-bold text-success">
                Firmas Registradas
              </DialogTitle>
              <p className="text-sm font-medium text-slate-600 flex items-center gap-2 mt-1">
                <FileText className="w-4 h-4" />
                Radicado: <span className="font-bold text-primary-custom">{correspondencia?.numero_radicado}</span>
              </p>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {firmaPrincipal && renderFirmaCard(firmaPrincipal, 'Firma principal', 'success')}

          {firmasAuxiliares.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Layers3 className="w-4 h-4 text-secondary-custom" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-secondary-custom">
                  Firmas auxiliares
                </h3>
                <Badge variant="outline" className="bg-secondary-custom/10 text-secondary-custom border-secondary-custom/20">
                  {firmasAuxiliares.length}
                </Badge>
              </div>
              <div className="space-y-4">
                {firmasAuxiliares.map((firmaAuxiliar, index) => (
                  <div key={firmaAuxiliar.id}>
                    {renderFirmaCard(firmaAuxiliar, `Auxiliar ${index + 1}`, 'secondary')}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer info */}
          <div className="p-3 bg-gradient-to-r from-slate-50 to-blue-50/30 rounded-lg border border-slate-200">
            <p className="text-xs text-slate-500 text-center">
              Esta firma digital es válida y está vinculada permanentemente al documento.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
