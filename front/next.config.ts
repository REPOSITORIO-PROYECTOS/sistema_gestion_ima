import path from "path";
import type { NextConfig } from "next/types";

/** Primer argumento del hook `webpack` según el tipo oficial de Next. */
type NextWebpackConfigArg = Parameters<NonNullable<NextConfig["webpack"]>>[0];

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

function hostnameFromApiHost(url: string): string {
  const trimmed = (url || "").trim();
  if (!trimmed) {
    return "sistema-ima.sistemataup.online";
  }
  try {
    const normalized = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    return new URL(normalized).hostname;
  } catch {
    return "sistema-ima.sistemataup.online";
  }
}

const apiImageHostname = hostnameFromApiHost(API_HOST);

const nextConfig: NextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/static/:path*",
        destination: `${API_HOST}/api/static/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${API_HOST}/:path*`,
      },
    ];
  },
  webpack: (config: NextWebpackConfigArg) => {
    config.resolve.alias["@"] = path.resolve(__dirname, "src");
    return config;
  },

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: apiImageHostname,
        port: "",
        pathname: "/api/static/**",
      },
    ],
  },
};

export default nextConfig;
