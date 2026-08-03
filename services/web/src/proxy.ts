import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = new Set(["/login", "/register", "/setup"]);
const PUBLIC_PWA_ASSETS = new Set([
  "/manifest.webmanifest", "/sw.js", "/icon.svg", "/icon-192.png",
  "/icon-512.png", "/apple-touch-icon.png",
]);

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (
    PUBLIC_PATHS.has(path) ||
    path.startsWith("/_next/") ||
    PUBLIC_PWA_ASSETS.has(path) ||
    path.startsWith("/api/")
  ) {
    return NextResponse.next();
  }
  if (!request.cookies.get("access_token")?.value && !request.cookies.get("refresh_token")?.value) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!favicon.ico).*)"],
};
