import type { NextConfig } from "next";
import path from "path";

function ensureHttpsPublicHost(url: string): string {
  const t = (url || "").trim();
  if (!t) {
    return t;
  }
  const lower = t.toLowerCase();
  if (
    lower.startsWith("http://localhost") ||
    lower.startsWith("http://127.0.0.1") ||
    lower.startsWith("http://[::1]")
  ) {
    return t;
  }
  if (t.startsWith("http://")) {
    return `https://${t.slice("http://".length)}`;
  }
  return t.replace(/\/+$/, "");
}

const API_HOST = ensureHttpsPublicHost(
  process.env.NEXT_PUBLIC_API_URL || "https://sistema-ima.sistemataup.online",
);

const nextConfig: NextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_HOST}/api/:path*`,
      },
    ];
  },
  webpack: (config) => {
    config.resolve.alias["@"] = path.resolve(__dirname, "src");
    return config;
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "sistema-ima.sistemataup.online",
        port: "",
        pathname: "/api/static/**",
      },
    ],
  },
};

export default nextConfig;
