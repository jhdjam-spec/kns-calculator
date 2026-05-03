/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Прокси к backend API в dev-режиме, чтобы избежать CORS:
  // фронт обращается к /api/backend/select → next переписывает на http://localhost:8000/select
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
