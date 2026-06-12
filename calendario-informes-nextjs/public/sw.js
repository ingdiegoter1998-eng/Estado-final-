// Service Worker para modo offline del Calendario de Correspondencia
// Estrategias: Cache-first para assets, Network-first para API, Queue para POSTs
// IMPORTANTE: Incrementar versión al hacer deploy para invalidar cache anterior

const CACHE_VERSION = 3
const CACHE_NAME = `calendario-v${CACHE_VERSION}`
const API_CACHE = `calendario-api-v${CACHE_VERSION}`

// Assets estáticos que se pre-cachean al instalar
const PRECACHE_URLS = [
  '/calendario/',
  '/calendario/login',
]

// ─── INSTALL ─────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
      .catch(err => {
        console.warn('[SW] Error precaching:', err)
        return self.skipWaiting()
      })
  )
})

// ─── ACTIVATE ────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME && key !== API_CACHE)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  )
})

// ─── FETCH ───────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Solo interceptamos GET requests (los POST van por la cola IndexedDB)
  if (request.method !== 'GET') return

  // Rutas API (GET): Network-first con fallback a cache
  if (url.pathname.includes('/api/')) {
    event.respondWith(networkFirstWithCache(request))
    return
  }

  // Assets estáticos de Next.js (_next/): Cache-first
  if (url.pathname.includes('/_next/')) {
    event.respondWith(cacheFirst(request))
    return
  }

  // Páginas de navegación: Network-first con fallback
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstWithCache(request))
    return
  }

  // Todo lo demás: Cache-first
  event.respondWith(cacheFirst(request))
})

// ─── ESTRATEGIAS ─────────────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request)
  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    return new Response('Offline', { status: 503 })
  }
}

async function networkFirstWithCache(request) {
  const cacheName = request.url.includes('/api/') ? API_CACHE : CACHE_NAME

  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(cacheName)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    if (cached) return cached
    return new Response(
      JSON.stringify({ error: 'Sin conexión', offline: true }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    )
  }
}

// ─── SYNC EVENT (Background Sync API) ────────────────────────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-firmas') {
    event.waitUntil(syncPendingFirmas())
  }
})

async function syncPendingFirmas() {
  // Notificar al cliente para que ejecute la sincronización desde IndexedDB
  const clients = await self.clients.matchAll()
  clients.forEach(client => {
    client.postMessage({ type: 'SYNC_FIRMAS' })
  })
}

// ─── MENSAJES DESDE EL CLIENTE ───────────────────────────────────────────────
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})
