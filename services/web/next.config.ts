import type { NextConfig } from "next";
import path from "node:path";

const config: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
  async rewrites() {
    const api = process.env.API_INTERNAL_URL ?? "http://api:8000";
    return [
      { source: "/booking/v1/:path*", destination: `${api}/booking/v1/:path*` },
      { source: "/api/health/:path*", destination: `${api}/health/:path*` },
      { source: "/api/:path*", destination: `${api}/api/:path*` },
    ];
  },
};

export default config;
