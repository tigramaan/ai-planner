import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const geist = Geist({ subsets: ["latin", "cyrillic"], variable: "--font-geist" });
export const metadata: Metadata = { title: "UMEC AI Planner", description: "Personal command center", icons: {icon:"/icon-192.png",apple:"/apple-touch-icon.png"}, appleWebApp: { capable: true, title: "AI Planner" } };
export const viewport: Viewport = { themeColor: "#0f6cbd", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body className={geist.variable}><Providers>{children}</Providers><script dangerouslySetInnerHTML={{__html:"if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.register('/sw.js'))}"}} /></body></html>;
}
