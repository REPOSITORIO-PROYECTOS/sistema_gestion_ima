import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  webpack: (config) => {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src');
    return config;
  },

  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'sistema-ima.sistemataup.online',
        port: '', 
        pathname: '/api/static/**', // esto permite cualquier ruta, no solo /static/
      },
    ],
  },
};

export default nextConfig;