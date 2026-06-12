'use client'

import { Correspondencia } from '@/types/informes'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  FileText,
  Clock,
  User,
  Building2,
  Mail,
  CheckCircle2,
  AlertCircle,
  Hash,
  Layers,
  MessageSquareText,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModalDetalleCorrespondenciaProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  correspondencia: Correspondencia | null
}

function InfoRow({ icon: Icon, label, value, className }: {
  icon: React.ElementType
  label: string
  value: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex items-start gap-3 py-2.5", className)}>
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center mt-0.5">
        <Icon className="w-4 h-4 text-slate-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
        <div className="text-sm font-medium text-slate-900 mt-0.5 break-words">{value || '—'}</div>
      </div>
    </div>
  )
}

export function ModalDetalleCorrespondencia({
  open,
  onOpenChange,
  correspondencia
}: ModalDetalleCorrespondenciaProps) {
  if (!correspondencia) return null

  const fecha = new Date(correspondencia.fecha_radicacion)
  const fechaFormateada = fecha.toLocaleDateString('es-ES', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  const horaFormateada = fecha.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="pb-2">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-md">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold text-slate-900">
                {correspondencia.numero_radicado}
              </DialogTitle>
              <p className="text-xs text-slate-500 capitalize">{fechaFormateada} — {horaFormateada}</p>
            </div>
          </div>
        </DialogHeader>

        <Separator />

        {/* Info principal */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
          <InfoRow
            icon={User}
            label="Remitente"
            value={correspondencia.remitente_nombre}
          />
          <InfoRow
            icon={Building2}
            label="Oficina destino"
            value={correspondencia.oficina_destino_nombre}
          />
          <InfoRow
            icon={User}
            label="Funcionario responsable"
            value={correspondencia.funcionario_responsable || correspondencia.destinatario_nombre}
          />
          <InfoRow
            icon={Mail}
            label="Medio de recepción"
            value={
              correspondencia.medio_recepcion === 'ELECTRONICO' ? 'Electrónico' :
              correspondencia.medio_recepcion === 'FISICO' ? 'Físico' :
              correspondencia.medio_recepcion || '—'
            }
          />
          {correspondencia.clasificacion_comunicacion && (
            <InfoRow
              icon={Layers}
              label="Clasificación"
              value={correspondencia.clasificacion_comunicacion}
            />
          )}
          {correspondencia.numero_folios != null && (
            <InfoRow
              icon={Hash}
              label="Número de folios"
              value={correspondencia.numero_folios}
            />
          )}
          <InfoRow
            icon={AlertCircle}
            label="¿Requiere respuesta?"
            value={
              <Badge
                variant="outline"
                className={cn(
                  "font-semibold text-xs",
                  correspondencia.requiere_respuesta
                    ? "bg-blue-50 text-blue-700 border-blue-200"
                    : "bg-slate-100 text-slate-600 border-slate-200"
                )}
              >
                {correspondencia.requiere_respuesta ? 'Sí' : 'No'}
              </Badge>
            }
          />
          <InfoRow
            icon={CheckCircle2}
            label="Estado firma"
            value={
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant="outline"
                  className={cn(
                    "font-semibold text-xs",
                    correspondencia.tiene_firma
                      ? "bg-green-50 text-green-700 border-green-200"
                      : "bg-amber-50 text-amber-700 border-amber-200"
                  )}
                >
                  {correspondencia.tiene_firma ? 'Principal registrada' : 'Principal pendiente'}
                </Badge>
                {(correspondencia.total_firmas_auxiliares ?? 0) > 0 && (
                  <Badge
                    variant="outline"
                    className="font-semibold text-xs bg-secondary-custom/10 text-secondary-custom border-secondary-custom/20"
                  >
                    {correspondencia.total_firmas_auxiliares} auxiliar{(correspondencia.total_firmas_auxiliares ?? 0) === 1 ? '' : 'es'}
                  </Badge>
                )}
              </div>
            }
          />
        </div>

        <Separator />

        {/* Asunto */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <MessageSquareText className="w-4 h-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Asunto</h3>
          </div>
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
            <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
              {correspondencia.asunto}
            </p>
          </div>
        </div>

        {/* Cuerpo del correo */}
        {correspondencia.cuerpo_correo && correspondencia.cuerpo_correo.trim() !== '' && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Mail className="w-4 h-4 text-slate-600" />
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Contenido del correo</h3>
            </div>
            <div className="bg-blue-50/50 rounded-lg p-4 border border-blue-100 max-h-80 overflow-y-auto">
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap font-mono">
                {correspondencia.cuerpo_correo}
              </p>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
