'use client'

import { useState, useMemo } from 'react'
import { useCalendario } from '@/lib/hooks/useCalendario'
import { DiaCelda } from './DiaCelda'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ChevronLeft, ChevronRight, Calendar, CheckCircle2, Clock, FileX, Loader2, Download } from 'lucide-react'
import { cn } from '@/lib/utils'
import { descargarExcelMensual } from '@/lib/api/informes'

export function CalendarioMensual() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [isDownloadingExcel, setIsDownloadingExcel] = useState(false)

  const nombreMes = new Date(year, month - 1, 1).toLocaleDateString('es-ES', {
    month: 'long'
  })

  const { calendario, isLoading, error } = useCalendario(year, month)

  // Calcular "hoy" en el cliente para no depender de cache del API/SW
  const todayStr = useMemo(() => {
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }, [])

  const navMesAnterior = () => {
    if (month === 1) {
      setMonth(12)
      setYear(year - 1)
    } else {
      setMonth(month - 1)
    }
  }

  const navMesSiguiente = () => {
    if (month === 12) {
      setMonth(1)
      setYear(year + 1)
    } else {
      setMonth(month + 1)
    }
  }

  const handleDescargarExcelMensual = async () => {
    try {
      setIsDownloadingExcel(true)
      await descargarExcelMensual(year, month)
    } catch (error) {
      console.error('Error descargando Excel mensual:', error)
    } finally {
      setIsDownloadingExcel(false)
    }
  }

  if (isLoading) {
    return (
      <Card className="shadow-2xl border-0 overflow-hidden">
        {/* Header Skeleton */}
        <div className="bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50 p-8 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <div className="h-10 w-32 bg-slate-200 rounded-lg animate-pulse" />
            <div className="h-10 w-64 bg-slate-200 rounded-lg animate-pulse" />
            <div className="h-10 w-32 bg-slate-200 rounded-lg animate-pulse" />
          </div>
        </div>

        {/* Calendar Grid Skeleton */}
        <div className="p-6 bg-white">
          {/* Week days header */}
          <div className="grid grid-cols-7 gap-2 mb-4">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="h-8 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>

          {/* Days grid */}
          <div className="grid grid-cols-7 gap-3">
            {Array.from({ length: 35 }).map((_, i) => (
              <div
                key={i}
                className="h-32 bg-slate-100 rounded-xl animate-pulse"
                style={{ animationDelay: `${i * 20}ms` }}
              />
            ))}
          </div>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="shadow-2xl border-0 overflow-hidden">
        <div className="p-12 text-center bg-gradient-to-br from-blue-50 to-cyan-50">
          <div className="inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-blue-100">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">
            Modo Demo Activado
          </h3>
          <p className="text-gray-600 mb-6">
            El servidor de desarrollo no está disponible. Se están mostrando datos de demostración.
          </p>
          <div className="bg-white rounded-lg p-4 mb-6 border border-blue-200 text-sm text-left">
            <p className="font-semibold text-blue-900 mb-2">💡 Para usar datos reales:</p>
            <p className="text-blue-700 text-xs">
              Asegúrate de que Django esté ejecutándose en <code className="bg-blue-50 px-1 rounded">http://localhost:8001</code>
            </p>
          </div>
          <p className="text-sm text-gray-500">
            El calendario cargará datos de demostración automáticamente
          </p>
        </div>
      </Card>
    )
  }

  if (!calendario) return null

  const diasSemana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

  return (
    <Card className="shadow-2xl border-0 overflow-hidden animate-in fade-in duration-500">
      {/* Header con navegación */}
      <div className="relative bg-gradient-to-br from-slate-100 via-blue-50/40 to-slate-100 p-8 border-b border-slate-200/80">
        {/* Efecto decorativo superior */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-custom via-secondary-custom to-primary-custom" />

        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <Button
            variant="outline"
            size="lg"
            onClick={navMesAnterior}
            className={cn(
              'group shadow-sm hover:shadow-md transition-all duration-300',
              'border-slate-300 hover:border-primary-custom',
              'hover:-translate-x-1 hover:scale-105'
            )}
          >
            <ChevronLeft className="h-5 w-5 mr-2 transition-transform group-hover:-translate-x-1" />
            <span className="font-medium">Anterior</span>
          </Button>

          <div className="flex flex-col items-center">
            <div className="flex items-center gap-3 mb-1">
              <Calendar className="w-6 h-6 text-primary-custom" />
              <h2 className="text-3xl font-bold bg-gradient-to-r from-primary-custom to-secondary-custom bg-clip-text text-transparent">
                {nombreMes.charAt(0).toUpperCase() + nombreMes.slice(1)}
              </h2>
            </div>
            <span className="text-2xl font-semibold text-slate-600 tabular-nums">
              {calendario.year}
            </span>
          </div>

          <div className="flex items-center justify-center gap-3">
            <Button
              variant="outline"
              onClick={handleDescargarExcelMensual}
              disabled={isDownloadingExcel}
              className="bg-white hover:bg-slate-50 border-slate-300 hover:border-secondary-custom transition-all hover:scale-105 shadow-sm"
            >
              <Download className="h-4 w-4 mr-2" />
              {isDownloadingExcel ? 'Descargando...' : 'Excel mensual'}
            </Button>

            <Button
              variant="outline"
              size="lg"
              onClick={navMesSiguiente}
              className={cn(
                'group shadow-sm hover:shadow-md transition-all duration-300',
                'border-slate-300 hover:border-primary-custom',
                'hover:translate-x-1 hover:scale-105'
              )}
            >
              <span className="font-medium">Siguiente</span>
              <ChevronRight className="h-5 w-5 ml-2 transition-transform group-hover:translate-x-1" />
            </Button>
          </div>
        </div>
      </div>

      {/* Grid del calendario */}
      <div className="p-6 bg-gradient-to-br from-white to-slate-50/30">
        {/* Encabezados días de la semana */}
        <div className="grid grid-cols-7 gap-3 mb-4">
          {diasSemana.map((dia, index) => (
            <div
              key={dia}
              className={cn(
                'text-center text-sm font-bold uppercase tracking-wider py-3 rounded-lg',
                'bg-gradient-to-br from-slate-100 to-slate-50',
                'border border-slate-200',
                'text-slate-700',
                'animate-in fade-in slide-in-from-top duration-300'
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              {dia}
            </div>
          ))}
        </div>

        {/* Días del mes */}
        <div className="grid grid-cols-7 gap-3">
          {calendario.dias.map((dia, index) => {
            // Sobreescribir es_hoy y es_futuro con la fecha local del cliente
            const diaActualizado = {
              ...dia,
              es_hoy: dia.fecha === todayStr,
              es_futuro: dia.fecha > todayStr,
            }
            return (
              <div
                key={index}
                className="animate-in fade-in zoom-in-50 duration-300"
                style={{ animationDelay: `${index * 15}ms` }}
              >
                <DiaCelda dia={diaActualizado} />
              </div>
            )
          })}
        </div>

        {/* Leyenda */}
        <div className="mt-8 pt-6 border-t border-slate-200">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-1 w-12 bg-gradient-to-r from-primary-custom to-transparent rounded-full" />
            <span className="text-sm font-bold text-slate-600 uppercase tracking-wide">
              Leyenda
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Firmado */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-success-light/50 border border-success/20 transition-all hover:shadow-md hover:scale-105">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-success-light border-2 border-success rounded-lg flex items-center justify-center shadow-sm">
                  <CheckCircle2 className="w-5 h-5 text-success" strokeWidth={2.5} />
                </div>
              </div>
              <span className="text-sm font-semibold text-gray-800">Firmado</span>
            </div>

            {/* Pendiente */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-warning-light/50 border border-warning/20 transition-all hover:shadow-md hover:scale-105">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-warning-light border-2 border-warning rounded-lg flex items-center justify-center shadow-sm">
                  <Clock className="w-5 h-5 text-warning" strokeWidth={2.5} />
                </div>
              </div>
              <span className="text-sm font-semibold text-gray-800">Pendiente</span>
            </div>

            {/* Sin registros */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-light/80 border border-gray-300/30 transition-all hover:shadow-md hover:scale-105">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-gray-light border-2 border-gray-300 rounded-lg flex items-center justify-center shadow-sm">
                  <FileX className="w-5 h-5 text-gray-500" strokeWidth={2.5} />
                </div>
              </div>
              <span className="text-sm font-semibold text-gray-800">Sin registros</span>
            </div>

            {/* Hoy */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 border border-secondary-custom/30 transition-all hover:shadow-md hover:scale-105">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-white border-2 border-secondary-custom rounded-lg flex items-center justify-center shadow-sm relative">
                  <div className="w-2 h-2 rounded-full bg-secondary-custom animate-pulse" />
                </div>
              </div>
              <span className="text-sm font-semibold text-gray-800">Hoy</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}
