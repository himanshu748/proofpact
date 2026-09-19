import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: false,
  experimental: { proxyTimeout: 840000 },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_ORIGIN || "http://127.0.0.1:8000"}/api/:path*`,
      },
      {
        source: "/fixture/:path*",
        destination: `${process.env.API_ORIGIN || "http://127.0.0.1:8000"}/fixture/:path*`,
      },
    ];
  },
};
export default nextConfig;
