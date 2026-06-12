import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const basePath = process.env.NEXT_BASE_PATH || "";

function getPublicOrigin(request: NextRequest) {
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const forwardedHost = request.headers.get("x-forwarded-host");
  const host = forwardedHost || request.headers.get("host") || request.nextUrl.host;
  const protocol = forwardedProto || request.nextUrl.protocol.replace(":", "");

  return `${protocol}://${host}`;
}

export function middleware(request: NextRequest) {
  const requestPath = new URL(request.url).pathname;

  // Next.js + basePath: /monitoreo/ responde 200 vacío; /monitoreo sirve el dashboard.
  if (basePath && requestPath === `${basePath}/`) {
    const redirectUrl = new URL(request.url);
    redirectUrl.pathname = basePath;
    return NextResponse.redirect(redirectUrl, 308);
  }

  const sessionId = request.cookies.get("sessionid");

  if (!sessionId) {
    const publicOrigin = getPublicOrigin(request);
    const loginUrl = new URL("/registros/login/", publicOrigin);
    const pathname = request.nextUrl.pathname.startsWith(basePath)
      ? request.nextUrl.pathname
      : `${basePath}${request.nextUrl.pathname}`;
    const nextUrl = new URL(pathname + request.nextUrl.search, publicOrigin);

    loginUrl.searchParams.set("next", nextUrl.toString());
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/|registros|static|media).*)"],
};
