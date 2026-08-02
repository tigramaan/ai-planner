import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const geist = Geist({ subsets: ["latin", "cyrillic"], variable: "--font-geist" });
export const metadata: Metadata = { title: "UMEC AI Planner", description: "Персональный командный центр", appleWebApp: { capable: true, title: "AI Planner" } };
export const viewport: Viewport = { themeColor: "#0f6cbd", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  return <html lang="ru"><body className={geist.variable}><Providers>{children}</Providers><script dangerouslySetInnerHTML={{__html:"if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.register('/sw.js'))}"}} /></body></html>;
}
