import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/", "/login", "/signup", "/privacy", "/terms", "/auth/callback"];
const PROTECTED_PATHS = ["/dashboard", "/settings", "/playground"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if path is public
  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();
  }

  // Check if path is protected
  if (PROTECTED_PATHS.some((p) => pathname.startsWith(p))) {
    const token = request.cookies.get("lightsERP_token");
    if (!token) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  // Pass through for all other routes
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - api (API routes)
     */
    "/((?!_next/static|_next/image|favicon.ico|api).*)",
  ],
};
