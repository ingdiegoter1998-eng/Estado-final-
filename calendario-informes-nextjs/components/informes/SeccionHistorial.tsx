'use client'

import { useState } from 'react'
import { HistorialDescarga } from '@/types/informes'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronDown, ChevronUp, Clock, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { cn } from '@/lib/utils'

interface SeccionHistorialProps {
  historial: HistorialDescarga[]
}

export function SeccionHistorial({ historial }: SeccionHistorialProps) {
  const [collapsed, setCollapsed] = useState(true)

  if (historial.length === 0) return null

  return (
    <Card className="shadow-lg border-2 border-slate-200 overflow-hidden">
      <CardHeader
        className={cn(
          "cursor-pointer transition-all duration-200",
          "bg-gradient-to-r from-slate-50 to-blue-50/30 hover:from-slate-100 hover:to-blue-50/50",
          "border-b border-slate-200"
        )}
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-secondary-custom/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-secondary-custom" strokeWidth={2.5} />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-slate-800">
                Historial de Descargas
              </CardTitle>
              <p className="text-sm text-slate-600 font-medium mt-0.5">
                {historial.length} {historial.length === 1 ? 'descarga registrada' : 'descargas registradas'}
              </p>
            </div>
          </div>
          <div className={cn(
            "w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center",
            "transition-transform duration-300",
            !collapsed && "rotate-180"
          )}>
            <ChevronDown className="w-5 h-5 text-slate-600" />
          </div>
        </div>
      </CardHeader>

      <div
        className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          collapsed ? "max-h-0" : "max-h-[600px]"
        )}
      >
        <CardContent className="pt-6 pb-4">
          <ul className="space-y-3">
            {historial.map((h, index) => (
              <li
                key={index}
                className={cn(
                  "flex items-start gap-4 p-4 rounded-lg",
                  "bg-gradient-to-r from-slate-50 to-transparent",
                  "border border-slate-200 hover:border-secondary-custom/40",
                  "transition-all duration-200 hover:shadow-sm",
                  "animate-in fade-in slide-in-from-left-2 duration-300"
                )}
                style={{
                  animationDelay: `${index * 60}ms`,
                  animationFillMode: collapsed ? 'none' : 'backwards'
                }}
              >
                {/* Avatar circle */}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-secondary-custom to-blue-600 flex items-center justify-center shadow-md">
                  <User className="w-5 h-5 text-white" strokeWidth={2.5} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="font-semibold text-slate-800 text-sm">
                        {h.usuario}
                      </p>
                      <p className="text-sm text-slate-600 mt-0.5">
                        <span className="text-slate-500">Descargó el informe</span>
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xs font-medium text-secondary-custom">
                        {formatDistanceToNow(new Date(h.fecha_descarga), {
                          addSuffix: true,
                          locale: es
                        })}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5 tabular-nums">
                        {new Date(h.fecha_descarga).toLocaleString('es-ES', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                  {h.ip_address && (
                    <p className="text-xs text-slate-400 mt-1 font-mono">
                      IP: {h.ip_address}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </div>
    </Card>
  )
}
