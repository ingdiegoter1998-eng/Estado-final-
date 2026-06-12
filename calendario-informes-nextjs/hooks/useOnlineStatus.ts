/**
 * useOnlineStatus.ts — Hook para detectar estado de conexión en tiempo real
 * 
 * Combina navigator.onLine con un ping real al servidor para mayor precisión.
 * También expone el conteo de firmas pendientes en cola.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { countPendingFirmas } from '@/lib/offlineDb'

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(true)
  const [pendingCount, setPendingCount] = useState(0)

  // Actualizar conteo de pendientes
  const refreshPendingCount = useCallback(async () => {
    try {
      const count = await countPendingFirmas()
      setPendingCount(count)
    } catch {
      // IndexedDB no disponible
    }
  }, [])

  useEffect(() => {
    // Estado inicial
    setIsOnline(navigator.onLine)
    refreshPendingCount()

    const handleOnline = () => {
      setIsOnline(true)
      refreshPendingCount()
    }

    const handleOffline = () => {
      setIsOnline(false)
      refreshPendingCount()
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Polling: verificar pendientes cada 10s
    const interval = setInterval(refreshPendingCount, 10000)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      clearInterval(interval)
    }
  }, [refreshPendingCount])

  return { isOnline, pendingCount, refreshPendingCount }
}
