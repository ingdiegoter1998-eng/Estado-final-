import { NextRequest, NextResponse } from 'next/server'

// En producción, Next.js corre bajo basePath=/calendario
// El middleware recibe la ruta SIN el basePath (Next.js lo elimina internamente)
export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname

  // Rutas públicas (sin protección)
  const publicRoutes = ['/login', '/api/login']
  if (publicRoutes.some(route => pathname.startsWith(route))) {
    return NextResponse.next()
  }

  // Verificar cookie de sesión Django (sessionid)
  const sessionId = request.cookies.get('sessionid')?.value

  if (!sessionId) {
    const forwardedProto = request.headers.get('x-forwarded-proto') || request.nextUrl.protocol.replace(':', '') || 'http'
    const forwardedHost = request.headers.get('x-forwarded-host') || request.headers.get('host') || request.nextUrl.host
    const basePath = request.nextUrl.basePath || ''
    const loginUrl = new URL(`${basePath}/login`, `${forwardedProto}://${forwardedHost}`)
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
