'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { LogOut, WifiOff, Wifi, CloudOff, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useOnlineStatus } from '@/hooks/useOnlineStatus'
import { syncAllPending } from '@/lib/syncManager'

export default function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const router = useRouter()
  const [userName, setUserName] = useState('Usuario')
  const [checked, setChecked] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const { isOnline, pendingCount, refreshPendingCount } = useOnlineStatus()

  useEffect(() => {
    // Verificar sesión activa contra Django (no confiar solo en localStorage)
    fetch('/registros/correspondencia/api/auth/me/', {
      credentials: 'include',
    })
      .then(res => {
        if (!res.ok) {
          // Si estamos offline, usar datos locales
          if (!navigator.onLine) {
            const name = localStorage.getItem('user_name') || 'Usuario'
            setUserName(name)
            setChecked(true)
            return null
          }
          // Sesión caducada o no autenticado → ir a login
          localStorage.removeItem('user_name')
          localStorage.removeItem('user_username')
          localStorage.removeItem('user_groups')
          router.replace('/login')
          return null
        }
        return res.json()
      })
      .then(data => {
        if (!data) return
        const name = data.user?.full_name || localStorage.getItem('user_name') || 'Usuario'
        setUserName(name)
        localStorage.setItem('user_name', name)
        setChecked(true)
      })
      .catch(() => {
        // Si falla por red, intentar modo offline con datos locales
        if (!navigator.onLine) {
          const name = localStorage.getItem('user_name') || 'Usuario'
          setUserName(name)
          setChecked(true)
        } else {
          router.replace('/login')
        }
      })
  }, [router])

  // No renderizar hasta verificar sesión
  if (!checked) return null

  const handleLogout = () => {
    localStorage.removeItem('user_name')
    localStorage.removeItem('user_username')
    localStorage.removeItem('user_groups')
    router.push('/login')
  }

  const handleManualSync = async () => {
    if (!isOnline || syncing) return
    setSyncing(true)
    try {
      await syncAllPending()
      refreshPendingCount()
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Banner offline */}
      {!isOnline && (
        <div className="bg-amber-500 text-white text-center py-2 px-4 text-sm font-medium flex items-center justify-center gap-2">
          <WifiOff className="w-4 h-4" />
          Sin conexión — Las firmas se guardarán localmente
          {pendingCount > 0 && (
            <span className="bg-amber-700 text-white text-xs px-2 py-0.5 rounded-full ml-1">
              {pendingCount} pendiente{pendingCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {/* Header con usuario y logout */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="container mx-auto px-4 max-w-7xl py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
              <span className="text-white font-semibold text-sm">
                {userName.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-medium text-slate-900">Bienvenido</p>
              <p className="text-xs text-slate-600">{userName}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Indicador de conexión dinámico */}
            {isOnline ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-50 border border-green-200">
                <Wifi className="w-3.5 h-3.5 text-green-600" />
                <span className="text-xs text-green-700 font-medium">Conectado</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200">
                <CloudOff className="w-3.5 h-3.5 text-amber-600" />
                <span className="text-xs text-amber-700 font-medium">Sin conexión</span>
              </div>
            )}

            {/* Botón de sincronización grande y visible */}
            {pendingCount > 0 && (
              <Button
                onClick={handleManualSync}
                disabled={syncing || !isOnline}
                size="sm"
                className={`gap-2 font-semibold shadow-md transition-all hover:scale-105 ${
                  isOnline
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                }`}
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                Sincronizar
                <span className="bg-white/20 text-white text-xs px-2 py-0.5 rounded-full font-bold">
                  {pendingCount}
                </span>
              </Button>
            )}

            <Button
              onClick={handleLogout}
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Cerrar Sesión</span>
              <span className="sm:hidden">Salir</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="bg-gradient-to-br from-slate-50 via-blue-50/20 to-slate-100 min-h-[calc(100vh-73px)]">
        {children}
      </main>
    </div>
  )
}
