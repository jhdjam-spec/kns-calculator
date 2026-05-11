/** @type {import('next').NextConfig} */
//
// Production target: Yandex Cloud Object Storage (static hosting).
//
// Логика режимов:
//   `next dev`  → IS_DEV → SSR + rewrite /api/backend/* → localhost:8000
//   `next build` → static export (output:'export') для YC Object Storage.
//                  Frontend ходит напрямую в backend по NEXT_PUBLIC_API_BASE
//                  (https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net)
//
// При static-export Next.js rewrites не применяются — поэтому src/lib/api.ts
// формирует абсолютный URL через `NEXT_PUBLIC_API_BASE`.
const IS_DEV =
  process.env.NEXT_PHASE === "phase-development-server" ||
  process.env.NODE_ENV === "development";

/** @type {import('next').NextConfig} */
const prodConfig = {
  reactStrictMode: true,
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

/** @type {import('next').NextConfig} */
const devConfig = {
  reactStrictMode: true,
  async rewrites() {
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_DEV || "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

export default IS_DEV ? devConfig : prodConfig;
