/**
 * ServiceWorkerProvider.tsx — Registra el Service Worker y maneja sincronización
 */

'use client'

import { useEffect, useCallback } from 'react'
import { setupOnlineSync, setupSyncListener, syncAllPending } from '@/lib/syncManager'
import { useToast } from '@/hooks/use-toast'

export function ServiceWorkerProvider({ children }: { children: React.ReactNode }) {
  const { toast } = useToast()

  const handleSync = useCallback(async () => {
    const { synced, failed } = await syncAllPending()
    if (synced > 0) {
      toast({
        title: `✅ ${synced} firma${synced > 1 ? 's' : ''} sincronizada${synced > 1 ? 's' : ''}`,
        description: 'Las firmas guardadas localmente se enviaron al servidor',
        className: 'bg-green-50 border-green-300 text-green-900',
      })
    }
    if (failed > 0) {
      toast({
        variant: 'destructive',
        title: `${failed} firma${failed > 1 ? 's' : ''} no se pudo sincronizar`,
        description: 'Se reintentará automáticamente',
      })
    }
  }, [toast])

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return

    const basePath = process.env.NODE_ENV === 'production' ? '/calendario' : ''

    navigator.serviceWorker
      .register(`${basePath}/sw.js`, { scope: `${basePath}/` })
      .then((reg) => {
        console.log('[PWA] Service Worker registrado:', reg.scope)
        setInterval(() => reg.update(), 60 * 60 * 1000)
      })
      .catch((err) => {
        console.warn('[PWA] Error registrando Service Worker:', err)
      })

    // Setup sync: escuchar online event y mensajes del SW
    const onOnline = async () => {
      console.log('[Sync] Conexión recuperada, sincronizando...')
      await new Promise(r => setTimeout(r, 2000))
      await handleSync()
    }

    window.addEventListener('online', onOnline)
    setupSyncListener()

    // Sincronizar al cargar (por si hay pendientes de sesión anterior)
    handleSync()

    return () => {
      window.removeEventListener('online', onOnline)
    }
  }, [handleSync])

  return <>{children}</>
}
