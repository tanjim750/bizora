import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    remotePatterns: process.env.IMAGE_REMOTE_HOST
      ? [{ protocol: 'https', hostname: process.env.IMAGE_REMOTE_HOST }]
      : [],
  },
  async rewrites() {
    if (!process.env.API_BASE_URL) return [];
    return {
      beforeFiles: [
        {
          source: '/api/store/:path*',
          destination: `${process.env.API_BASE_URL.replace(/\/+$/, '')}/:path*`,
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
