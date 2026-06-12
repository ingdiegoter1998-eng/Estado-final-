'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { User, Lock, LogIn, AlertCircle, CheckCircle2, Server } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_DJANGO_URL || ''}/registros/correspondencia/api/auth/login/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',  // <-- envía y recibe cookies de sesión Django
          body: JSON.stringify({ username, password }),
        }
      )

      const data = await res.json()

      if (!res.ok) {
        setError(data.error || 'Usuario o contraseña incorrectos')
        setIsLoading(false)
        return
      }

      // Guardar datos de usuario en localStorage para la UI
      localStorage.setItem('user_name', data.user.full_name)
      localStorage.setItem('user_username', data.user.username)
      localStorage.setItem('user_groups', JSON.stringify(data.user.groups))

      router.push('/')
    } catch (err) {
      setError('No se pudo conectar con el servidor. Verifica que Django esté corriendo.')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/20 to-slate-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 shadow-lg mx-auto mb-4">
            <LogIn className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Calendario de Planillas
          </h1>
          <p className="text-slate-600">
            Sistema de gestión de informes diarios de correspondencia
          </p>
        </div>

        {/* Login Card */}
        <Card className="shadow-2xl border-0 overflow-hidden">
          <div className="bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50 p-8 border-b border-slate-200">
            <h2 className="text-xl font-bold text-slate-900">Iniciar Sesión</h2>
            <p className="text-sm text-slate-600 mt-1">Usa tus credenciales del sistema de correspondencia</p>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Username Input */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">
                Usuario
              </label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Nombre de usuario"
                  autoComplete="username"
                  required
                  className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                  className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={isLoading || !username || !password}
              className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-medium py-2 rounded-lg transition-all"
            >
              {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
            </Button>
          </form>

          {/* Footer Info */}
          <div className="bg-blue-50/30 p-4 border-t border-slate-200 flex items-center gap-2">
            <Server className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <p className="text-xs text-slate-600">
              Autenticación contra <span className="font-mono font-semibold text-blue-700">Django :8000</span>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}

