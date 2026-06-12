import { NextRequest, NextResponse } from "next/server";

const backendOrigin =
  process.env.NEXT_BACKEND_ORIGIN || "http://127.0.0.1:8004";

async function proxyToBackend(
  request: NextRequest,
  context: { params: { path: string[] } },
  method: string
) {
  const joinedPath = context.params.path.join("/");
  const search = request.nextUrl.search || "";
  const targetUrl = `${backendOrigin}/registros/correspondencia/api/chat/${joinedPath}/${search}`;

  const headers: Record<string, string> = {
    accept: "application/json",
    cookie: request.headers.get("cookie") || "",
    "x-requested-with": "XMLHttpRequest",
  };

  const csrfToken = request.cookies.get("csrftoken")?.value;
  if (csrfToken) headers["x-csrftoken"] = csrfToken;

  let body: BodyInit | undefined;

  if (method === "POST") {
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("multipart/form-data")) {
      // Reenviar multipart tal cual (con boundary)
      headers["content-type"] = contentType;
      body = await request.arrayBuffer();
    } else {
      headers["content-type"] = "application/json";
      body = await request.text();
    }
  }

  const init: RequestInit = { method, headers, cache: "no-store", body };

  const response = await fetch(targetUrl, init);
  const text = await response.text();

  return new NextResponse(text, {
    status: response.status,
    headers: {
      "content-type":
        response.headers.get("content-type") || "application/json",
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyToBackend(request, context, "GET");
}

export async function POST(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyToBackend(request, context, "POST");
}
