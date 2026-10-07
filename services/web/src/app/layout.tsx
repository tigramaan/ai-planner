import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import { Geist } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { resolveAcceptLanguage } from "@/lib/locale";

const geist = Geist({ subsets: ["latin", "cyrillic"], variable: "--font-geist" });
export const metadata: Metadata = {
  title: "UMEC AI Planner",
  description: "Personal command center",
  icons: {
    icon: [
      { url: "/icon.svg?v=calendar-ai-1", type: "image/svg+xml" },
      { url: "/icon-192.png?v=calendar-ai-1", type: "image/png", sizes: "192x192" },
    ],
    apple: "/apple-touch-icon.png?v=calendar-ai-1",
  },
  appleWebApp: { capable: true, title: "AI Planner" },
};
export const viewport: Viewport = { themeColor: "#0f6cbd", width: "device-width", initialScale: 1 };

export default async function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  const initialLocale = resolveAcceptLanguage((await headers()).get("accept-language"));
  return <html lang={initialLocale}><body className={geist.variable}>
    <Providers initialLocale={initialLocale}>{children}</Providers>
    <script dangerouslySetInnerHTML={{__html:"if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.register('/sw.js'))}"}} />
  </body></html>;
}
