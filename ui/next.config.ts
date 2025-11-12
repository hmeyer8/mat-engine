import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    turbopack: {
      root: __dirname, // pin workspace root to /ui
    },
  },
};

export default nextConfig;
