'use client'

import { DiaCalendario } from '@/types/informes'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, Mail } from 'lucide-react'
import Link from 'next/link'

interface DiaCeldaProps {
  dia: DiaCalendario
}

export function DiaCelda({ dia }: DiaCeldaProps) {
  const {
    fecha,
    es_mes_actual,
    es_hoy,
    es_futuro,
    total_correspondencias,
    tiene_correspondencias,
    informe
  } = dia

  // Extraer partes de la fecha del string ISO para evitar bug de timezone
  // new Date('YYYY-MM-DD') se parsea como UTC y al convertir a local (UTC-5) retrocede un día
  const [anio, mesStr, diaStr] = fecha.split('-')
  const diaNum = parseInt(diaStr, 10)

  // Determinar color de fondo según estado
  const getBackgroundClasses = () => {
    if (!es_mes_actual) return 'bg-slate-50/50'
    if (!tiene_correspondencias) return 'bg-gray-light/80'
    if (informe?.estado === 'FIRMADO') return 'bg-success-light/90'
    if (tiene_correspondencias) return 'bg-warning-light/90'
    return 'bg-white'
  }

  // Determinar clases de hover según estado
  const getHoverClasses = () => {
    if (!isClickeable) return ''
    return 'hover:shadow-lg hover:scale-[1.02] hover:brightness-95 hover:-translate-y-0.5'
  }

  // Determinar si es clickeable
  const isClickeable = es_mes_actual && tiene_correspondencias && !es_futuro

  const cellContent = (
    <div
      className={cn(
        // Base structure
        'relative min-h-[120px] p-3',
        'rounded-xl border-2 transition-all duration-300 ease-out',
        'flex flex-col justify-between',

        // Background colors
        getBackgroundClasses(),

        // Border styling
        es_hoy
          ? 'border-secondary-custom ring-4 ring-secondary-custom/20 shadow-md'
          : 'border-gray-200/60',

        // Interactive states
        isClickeable
          ? cn('cursor-pointer', getHoverClasses())
          : 'cursor-default opacity-70',

        // Disabled appearance
        !es_mes_actual && 'saturate-50'
      )}
      aria-label={`${new Date(fecha + 'T12:00:00').toLocaleDateString('es-ES', { day: 'numeric', month: 'long' })}: ${
        informe?.estado === 'FIRMADO'
          ? 'Firmado'
          : tiene_correspondencias
            ? `${total_correspondencias} correspondencias pendientes`
            : 'Sin correspondencias'
      }`}
    >
      {/* Header: Día del mes */}
      <div className="flex items-start justify-between">
        <div className={cn(
          'text-base font-semibold tabular-nums tracking-tight',
          es_hoy
            ? 'text-secondary-custom font-bold text-lg'
            : es_mes_actual
              ? 'text-gray-800'
              : 'text-gray-400'
        )}>
          {diaNum}
        </div>

        {/* Check icon para firmado */}
        {informe?.estado === 'FIRMADO' && (
          <div className="animate-in fade-in zoom-in duration-300">
            <CheckCircle2
              className="text-success drop-shadow-sm"
              size={22}
              strokeWidth={2.5}
            />
          </div>
        )}
      </div>

      {/* Footer: Badge de cantidad */}
      {tiene_correspondencias && (
        <div className="flex items-end justify-between mt-auto pt-2">
          <Badge
            variant="secondary"
            className={cn(
              'shadow-sm backdrop-blur-sm font-medium tabular-nums',
              'transition-all duration-200',
              isClickeable && 'group-hover:scale-105',
              informe?.estado === 'FIRMADO'
                ? 'bg-success/90 text-white hover:bg-success'
                : 'bg-white/90 text-gray-700 hover:bg-white'
            )}
          >
            <Mail className="w-3 h-3 mr-1" />
            {total_correspondencias}
          </Badge>

          {/* Indicador de "hoy" alternativo si no es el borde */}
          {es_hoy && (
            <div className="flex items-center gap-1">
              <span className="text-xs font-bold text-secondary-custom uppercase tracking-wider">
                Hoy
              </span>
              <div className="w-2 h-2 rounded-full bg-secondary-custom animate-pulse" />
            </div>
          )}
        </div>
      )}

      {/* Efecto de brillo sutil en hover */}
      {isClickeable && (
        <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/0 to-white/0 hover:from-white/20 hover:to-transparent transition-all duration-300 pointer-events-none" />
      )}
    </div>
  )

  if (isClickeable) {
    return (
      <Link
        href={`/${fecha}`}
        className="block focus:outline-none focus:ring-2 focus:ring-primary-custom focus:ring-offset-2 rounded-xl"
      >
        {cellContent}
      </Link>
    )
  }

  return cellContent
}
