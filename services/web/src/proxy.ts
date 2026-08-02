import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = new Set(["/login", "/register", "/setup"]);

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (
    PUBLIC_PATHS.has(path) ||
    path.startsWith("/_next/") ||
    path === "/manifest.webmanifest" ||
    path === "/sw.js" ||
    path === "/icon.svg" ||
    path.startsWith("/api/")
  ) {
    return NextResponse.next();
  }
  if (!request.cookies.get("access_token")?.value) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!favicon.ico).*)"],
};
