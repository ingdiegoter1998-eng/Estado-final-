import { CalendarioMensual } from '@/components/calendario/CalendarioMensual'
import { FileText } from 'lucide-react'

export const metadata = {
  title: 'Calendario de Planillas | Sistema de Correspondencia',
  description: 'Vista calendario de informes diarios de correspondencia',
}

export default function CalendarioPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/20 to-slate-100">
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        {/* Header de la página */}
        <div className="mb-8 animate-in fade-in slide-in-from-top duration-500">
          <div className="flex items-center gap-4 mb-3">
            <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-custom to-secondary-custom shadow-lg">
              <FileText className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-primary-custom via-secondary-custom to-primary-custom bg-clip-text text-transparent">
                Calendario de Planillas
              </h1>
              <p className="text-slate-600 mt-1">
                Sistema de gestión de informes diarios de correspondencia
              </p>
            </div>
          </div>
        </div>

        {/* Calendario */}
        <CalendarioMensual />
      </div>
    </main>
  )
}
