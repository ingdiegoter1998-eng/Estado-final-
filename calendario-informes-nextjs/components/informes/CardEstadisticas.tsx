import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EstadisticasFirmas } from '@/types/informes'
import { FileText, Download, PenTool, Calendar } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CardEstadisticasProps {
  stats: EstadisticasFirmas
  totalDescargas: number
  fechaFirma?: string
}

export function CardEstadisticas({ stats, totalDescargas, fechaFirma }: CardEstadisticasProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Total Correspondencias */}
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300",
          "hover:shadow-lg hover:-translate-y-1",
          "border-l-4 border-l-primary-custom",
          "bg-gradient-to-br from-white to-slate-50/50",
          "animate-in fade-in slide-in-from-bottom-4 duration-500"
        )}
        style={{ animationDelay: '0ms' }}
      >
        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Total Correspondencias
          </CardTitle>
          <div className="w-10 h-10 rounded-lg bg-primary-custom/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-primary-custom" strokeWidth={2.5} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <div className="text-4xl font-bold tabular-nums tracking-tight text-primary-custom">
              {stats.total}
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Radicados del día
            </p>
          </div>
        </CardContent>
        {/* Decorative corner accent */}
        <div className="absolute -right-8 -bottom-8 w-24 h-24 rounded-full bg-primary-custom/5" />
      </Card>

      {/* Total Descargas */}
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300",
          "hover:shadow-lg hover:-translate-y-1",
          "border-l-4 border-l-secondary-custom",
          "bg-gradient-to-br from-white to-blue-50/30",
          "animate-in fade-in slide-in-from-bottom-4 duration-500"
        )}
        style={{ animationDelay: '100ms' }}
      >
        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Descargas
          </CardTitle>
          <div className="w-10 h-10 rounded-lg bg-secondary-custom/10 flex items-center justify-center">
            <Download className="w-5 h-5 text-secondary-custom" strokeWidth={2.5} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <div className="text-4xl font-bold tabular-nums tracking-tight text-secondary-custom">
              {totalDescargas}
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Informes generados
            </p>
          </div>
        </CardContent>
        <div className="absolute -right-8 -bottom-8 w-24 h-24 rounded-full bg-secondary-custom/5" />
      </Card>

      {/* Firmas - Card más elaborada */}
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300",
          "hover:shadow-lg hover:-translate-y-1",
          "border-l-4 border-l-success",
          "bg-gradient-to-br from-white to-emerald-50/30",
          "animate-in fade-in slide-in-from-bottom-4 duration-500"
        )}
        style={{ animationDelay: '200ms' }}
      >
        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Estado de Firmas
          </CardTitle>
          <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
            <PenTool className="w-5 h-5 text-success" strokeWidth={2.5} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {/* Ratio de firmas */}
            <div className="flex items-baseline gap-2">
              <div className="text-4xl font-bold tabular-nums tracking-tight text-success">
                {stats.firmadas}
              </div>
              <div className="text-2xl font-semibold text-slate-400">/</div>
              <div className="text-2xl font-semibold tabular-nums text-slate-600">
                {stats.total}
              </div>
            </div>

            {/* Barra de progreso con diseño médico */}
            <div className="space-y-1.5">
              <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                <div
                  className={cn(
                    "absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out",
                    "bg-gradient-to-r from-success to-emerald-400",
                    "shadow-sm"
                  )}
                  style={{
                    width: `${stats.porcentaje}%`,
                    transitionDelay: '400ms'
                  }}
                >
                  {/* Animated shine effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-success">
                  {stats.porcentaje.toFixed(1)}% completado
                </span>
                <span className="text-slate-500">
                  {stats.pendientes} pendientes
                </span>
              </div>
            </div>
          </div>
        </CardContent>
        <div className="absolute -right-8 -bottom-8 w-24 h-24 rounded-full bg-success/5" />
      </Card>

      {/* Fecha de Firma */}
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300",
          "hover:shadow-lg hover:-translate-y-1",
          fechaFirma
            ? "border-l-4 border-l-success bg-gradient-to-br from-white to-emerald-50/30"
            : "border-l-4 border-l-warning bg-gradient-to-br from-white to-amber-50/30",
          "animate-in fade-in slide-in-from-bottom-4 duration-500"
        )}
        style={{ animationDelay: '300ms' }}
      >
        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Fecha de Firma
          </CardTitle>
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center",
            fechaFirma ? "bg-success/10" : "bg-warning/10"
          )}>
            <Calendar className={cn(
              "w-5 h-5",
              fechaFirma ? "text-success" : "text-warning"
            )} strokeWidth={2.5} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {fechaFirma ? (
              <>
                <div className="text-2xl font-bold text-success leading-tight">
                  {new Date(fechaFirma).toLocaleDateString('es-ES', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric'
                  })}
                </div>
                <div className="text-sm font-semibold text-slate-500">
                  {new Date(fechaFirma).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </>
            ) : (
              <>
                <div className="text-2xl font-bold text-warning">
                  Pendiente
                </div>
                <p className="text-xs text-slate-500 font-medium">
                  Sin firma registrada
                </p>
              </>
            )}
          </div>
        </CardContent>
        <div className={cn(
          "absolute -right-8 -bottom-8 w-24 h-24 rounded-full",
          fechaFirma ? "bg-success/5" : "bg-warning/5"
        )} />
      </Card>
    </div>
  )
}
