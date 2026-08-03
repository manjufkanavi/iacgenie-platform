import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3071";

async function proxyRequest(request: NextRequest, method: string) {
  try {
    const url = new URL(request.url);
    const backendPath = url.searchParams.get("path") || "";

    if (!backendPath) {
      return NextResponse.json(
        { error: "Missing backend path" },
        { status: 400 }
      );
    }

    // Build backend URL with remaining query params (exclude 'path' which is the router)
    const backendUrlObj = new URL(`${API_BASE}${backendPath}`);
    for (const [key, value] of url.searchParams) {
      if (key !== "path") {
        backendUrlObj.searchParams.set(key, value);
      }
    }
    const backendUrl = backendUrlObj.toString();

    const headers: Record<string, string> = {};
    if (method === "POST") {
      headers["Content-Type"] = "application/json";
    }

    const apiKey = request.headers.get("x-api-key");
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const authHeader = request.headers.get("authorization");
    if (authHeader) {
      headers["Authorization"] = authHeader;
    }

    const fetchInit: Record<string, unknown> = {
      method,
      headers,
      signal: AbortSignal.timeout(30000),
    };
    if (method === "POST" && request.body) {
      fetchInit["body"] = request.body;
      (fetchInit as { duplex?: string }).duplex = "half";
    }

    const response = await fetch(backendUrl, fetchInit as RequestInit);

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Proxy error";
    return NextResponse.json(
      { error: `Backend proxy failed: ${message}` },
      { status: 502 }
    );
  }
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, "POST");
}

export async function GET(request: NextRequest) {
  return proxyRequest(request, "GET");
}
