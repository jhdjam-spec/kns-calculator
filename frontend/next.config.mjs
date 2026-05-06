/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // На Vercel — `/api/*` обрабатывается Python serverless через vercel.json (vercel.json rewrites).
  // В dev — same-origin, поэтому при VERCEL_ENV=development этот rewrite пробрасывает
  // запросы к локальному uvicorn на 8000 (избегаем CORS).
  async rewrites() {
    // На production Vercel rewrites не нужны (api/index.py обрабатывает /api/* напрямую)
    if (process.env.VERCEL) return [];
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_DEV || "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
