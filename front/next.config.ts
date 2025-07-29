// next.config.ts (o .mjs)
// VERSIÓN MODIFICADA Y COMPLETA

import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  
  // Su configuración existente para los alias de importación (¡mantenerla!)
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
        pathname: '/static/**', // Permite cualquier imagen dentro de la carpeta /static/ y sus subcarpetas
      },
    ],
  },
};

export default nextConfig;