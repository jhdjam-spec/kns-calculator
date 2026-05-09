/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // YC Object Storage static hosting:
  //   BUILD_TARGET=yc-static → static export (output:'export')
  //   trailingSlash=true для красивых URL /project/, /tanks/, /teach/fire/
  //   images.unoptimized — на static нет Next.js Image Optimization
  // Для Vercel и dev — обычный SSR режим.
  ...(process.env.BUILD_TARGET === "yc-static"
    ? {
        output: "export",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {}),

  // Dev/Vercel rewrites — не применяется при output:'export'
  async rewrites() {
    if (process.env.BUILD_TARGET === "yc-static") return [];
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
