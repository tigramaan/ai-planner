import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "UMEC AI Planner",
    short_name: "AI Planner",
    description: "Personal command center",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f8fb",
    theme_color: "#0f6cbd",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
