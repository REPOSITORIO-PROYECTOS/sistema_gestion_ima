/** @type {import('next').NextConfig} */
const API_HOST = process.env.NEXT_PUBLIC_API_URL || 'https://sistema-ima.sistemataup.online';

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_HOST}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

