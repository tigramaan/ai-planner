import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "UMEC AI Planner",
    short_name: "AI Planner",
    description: "Personal command center",
    start_url: "/",
    id: "/",
    display: "standalone",
    background_color: "#f6f8fb",
    theme_color: "#0f6cbd",
    icons: [
      { src: "/apple-touch-icon.png?v=calendar-ai-1", sizes: "180x180", type: "image/png" },
      { src: "/icon-192.png?v=calendar-ai-1", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png?v=calendar-ai-1", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
