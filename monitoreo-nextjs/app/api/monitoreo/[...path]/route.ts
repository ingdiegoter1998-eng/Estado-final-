import { NextRequest, NextResponse } from "next/server";

const backendOrigin =
  process.env.NEXT_BACKEND_ORIGIN || "http://127.0.0.1";

type ProxyMethod = "GET" | "POST" | "DELETE";

async function proxyRequest(request: NextRequest, method: ProxyMethod) {
  const path = request.nextUrl.pathname.split("/api/monitoreo/")[1] || "";
  const joinedPath = path.replace(/\/$/, "");
  const search = request.nextUrl.search || "";
  const targetUrl = `${backendOrigin}/registros/correspondencia/api/monitoreo/${joinedPath}/${search}`;

  const headers: Record<string, string> = {
    accept: "application/json",
    cookie: request.headers.get("cookie") || "",
    "x-requested-with": "XMLHttpRequest",
  };

  const csrfToken = request.headers.get("x-csrftoken");
  if (csrfToken) {
    headers["x-csrftoken"] = csrfToken;
  }

  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers["content-type"] = contentType;
  }

  const response = await fetch(targetUrl, {
    method,
    headers,
    body: method === "POST" ? await request.text() : undefined,
    cache: "no-store",
  });

  const text = await response.text();

  return new NextResponse(text, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/json",
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  void context;
  return proxyRequest(request, "GET");
}

export async function POST(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  void context;
  return proxyRequest(request, "POST");
}

export async function DELETE(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  void context;
  return proxyRequest(request, "DELETE");
}