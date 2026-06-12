'use client'

import { Correspondencia } from '@/types/informes'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CheckCircle2, Edit3, FileText, CloudOff, PlusCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TablaCorrespondenciasProps {
  correspondencias: Correspondencia[]
  onFirmar: (correspondencia: Correspondencia) => void
  onVerFirma: (correspondencia: Correspondencia) => void
  onAgregarFirmaAuxiliar: (correspondencia: Correspondencia) => void
  onVerDetalle: (correspondencia: Correspondencia) => void
  offlineFirmaIds?: Set<number>
}

export function TablaCorrespondencias({
  correspondencias,
  onFirmar,
  onVerFirma,
  onAgregarFirmaAuxiliar,
  onVerDetalle,
  offlineFirmaIds = new Set()
}: TablaCorrespondenciasProps) {
  return (
    <div className="relative rounded-xl border-2 border-slate-200 overflow-hidden shadow-lg bg-white">
      {/* Decorative top border - medical accent */}
      <div className="h-1.5 bg-gradient-to-r from-primary-custom via-secondary-custom to-primary-custom" />

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-gradient-to-r from-primary-custom to-[#1e5f8a] hover:from-primary-custom hover:to-[#1e5f8a] border-b-2 border-slate-300">
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider">
                Radicado
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider">
                Hora
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider">
                Remitente
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider min-w-[200px]">
                Asunto
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider">
                Func. Responsable
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider">
                Oficina
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider text-center">
                ¿Respuesta?
              </TableHead>
              <TableHead className="text-white font-bold text-xs uppercase tracking-wider text-center">
                Estado Firma
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {correspondencias.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="h-48">
                  <div className="flex flex-col items-center justify-center py-12 animate-in fade-in duration-500">
                    <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                      <FileText className="w-8 h-8 text-slate-400" strokeWidth={1.5} />
                    </div>
                    <p className="text-slate-500 font-medium text-lg">
                      No hay correspondencias para este día
                    </p>
                    <p className="text-slate-400 text-sm mt-1">
                      Los registros aparecerán aquí cuando estén disponibles
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              correspondencias.map((corr, index) => (
                <TableRow
                  key={corr.id}
                  className={cn(
                    "transition-all duration-200 border-b border-slate-100",
                    "hover:bg-slate-50/80 hover:shadow-sm",
                    "animate-in fade-in slide-in-from-bottom-2 duration-300"
                  )}
                  style={{
                    animationDelay: `${index * 40}ms`,
                    animationFillMode: 'backwards'
                  }}
                >
                  {/* Radicado (clickable → abre detalle) */}
                  <TableCell>
                    <button
                      onClick={() => onVerDetalle(corr)}
                      className="font-semibold text-primary-custom tabular-nums hover:text-blue-700 hover:underline underline-offset-2 transition-colors cursor-pointer text-left"
                      title="Ver detalle de la comunicación"
                    >
                      {corr.numero_radicado}
                    </button>
                  </TableCell>

                  {/* Hora */}
                  <TableCell className="text-slate-600 font-medium tabular-nums">
                    {new Date(corr.fecha_radicacion).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </TableCell>

                  {/* Remitente */}
                  <TableCell className="text-slate-700 font-medium max-w-[180px]">
                    <div className="truncate" title={corr.remitente_nombre}>
                      {corr.remitente_nombre}
                    </div>
                  </TableCell>

                  {/* Asunto */}
                  <TableCell className="text-slate-600 min-w-[200px] max-w-[300px]">
                    <div className="truncate" title={corr.asunto}>
                      {corr.asunto}
                    </div>
                  </TableCell>

                  {/* Funcionario responsable */}
                  <TableCell className="text-slate-700 font-medium max-w-[160px]">
                    <div className="truncate" title={corr.funcionario_responsable || corr.destinatario_nombre}>
                      {corr.funcionario_responsable || corr.destinatario_nombre || "—"}
                    </div>
                  </TableCell>

                  {/* Oficina destino */}
                  <TableCell className="text-slate-600 max-w-[160px]">
                    <div className="truncate" title={corr.oficina_destino_nombre}>
                      {corr.oficina_destino_nombre || "—"}
                    </div>
                  </TableCell>

                  {/* ¿Requiere respuesta? */}
                  <TableCell className="text-center">
                    {corr.requiere_respuesta ? (
                      <Badge
                        variant="outline"
                        className="bg-blue-50 text-blue-700 border-blue-200 font-semibold shadow-sm"
                      >
                        Sí
                      </Badge>
                    ) : (
                      <Badge
                        variant="secondary"
                        className="bg-slate-100 text-slate-600 font-semibold shadow-sm"
                      >
                        No
                      </Badge>
                    )}
                  </TableCell>

                  {/* Estado de firma */}
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      {corr.tiene_firma || (corr.total_firmas_auxiliares ?? 0) > 0 ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className={cn(
                            "h-9 w-9 p-0 bg-blue-50 hover:bg-blue-100 border-blue-300",
                            "text-blue-700 shadow-sm",
                            "transition-all duration-200 hover:scale-105 hover:shadow-md"
                          )}
                          onClick={() => onVerFirma(corr)}
                          title="Ver firmas"
                          aria-label="Ver firmas"
                        >
                          <CheckCircle2 className="h-4 w-4" strokeWidth={2.5} />
                          <span className="sr-only">Ver firmas</span>
                        </Button>
                      ) : offlineFirmaIds.has(corr.id) ? (
                        <div
                          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-amber-50 border border-amber-300 text-amber-800 shadow-sm"
                          title="Firma pendiente offline"
                          aria-label="Firma pendiente offline"
                        >
                          <CloudOff className="h-4 w-4 text-amber-600" strokeWidth={2.5} />
                        </div>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className={cn(
                            "h-9 w-9 p-0 bg-white hover:bg-primary-custom/5 border-slate-300",
                            "text-slate-700 hover:text-primary-custom",
                            "transition-all duration-200 hover:scale-105 hover:shadow-md hover:border-primary-custom"
                          )}
                          onClick={() => onFirmar(corr)}
                          title="Firmar"
                          aria-label="Firmar"
                        >
                          <Edit3 className="h-4 w-4" />
                          <span className="sr-only">Firmar</span>
                        </Button>
                      )}

                      <Button
                        size="sm"
                        variant="outline"
                        className={cn(
                          "h-9 w-9 p-0 bg-secondary-custom/5 hover:bg-secondary-custom/10 border-secondary-custom/30",
                          "text-secondary-custom shadow-sm",
                          "transition-all duration-200 hover:scale-105 hover:shadow-md"
                        )}
                        onClick={() => onAgregarFirmaAuxiliar(corr)}
                        title="Agregar firma auxiliar"
                        aria-label="Agregar firma auxiliar"
                      >
                        <PlusCircle className="h-4 w-4" />
                        <span className="sr-only">Agregar firma auxiliar</span>
                      </Button>

                      {(corr.total_firmas_auxiliares ?? 0) > 0 && (
                        <Badge
                          variant="outline"
                          className="h-7 min-w-7 justify-center px-2 bg-secondary-custom/10 text-secondary-custom border-secondary-custom/20 font-semibold"
                          title={`${corr.total_firmas_auxiliares ?? 0} firmas auxiliares`}
                        >
                          {(corr.total_firmas_auxiliares ?? 0)}
                        </Badge>
                      )}
                    </div>
                  </TableCell>

                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Footer info */}
      {correspondencias.length > 0 && (
        <div className="bg-slate-50/80 border-t border-slate-200 px-6 py-3 flex items-center justify-between">
          <p className="text-sm text-slate-600 font-medium">
            Total de registros: <span className="font-bold text-primary-custom tabular-nums">{correspondencias.length}</span>
          </p>
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-blue-100 border-2 border-blue-500" />
              <span>Con firmas</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-amber-100 border-2 border-amber-400" />
              <span>Offline</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-white border-2 border-slate-300" />
              <span>Pendiente</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
