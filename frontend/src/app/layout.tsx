import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";
import { manrope, inter, jetbrainsMono } from "./fonts";
import { BetaBanner } from "@/components/BetaBanner";
import { EncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
import "./globals.css";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://kns-calc-test.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "ИНСЕРВО · Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
  description:
    "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций. От ТЗ до спецификации с гидравликой за минуту. Производитель оборудования с 2009 года.",
  authors: [{ name: "Konstantin Morozov · INSERVO Studio", url: "https://inservo.ru" }],
  creator: "INSERVO Studio",
  publisher: "Серво-Юг",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "ИНСЕРВО · Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
    description:
      "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций. От ТЗ до спецификации с гидравликой за минуту.",
    type: "website",
    locale: "ru_RU",
    siteName: "ИНСЕРВО · Серво-Юг",
    url: SITE_URL,
  },
  twitter: {
    card: "summary_large_image",
    title: "ИНСЕРВО · Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
    description:
      "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

/**
 * Inline-скрипт устанавливает .dark/.light на <html> до первого рендера,
 * чтобы избежать FOUC при переключении темы. Читает localStorage.theme:
 *   "dark"  → принудительно тёмная
 *   "light" → принудительно светлая
 *   "auto"/отсутствует → ничего не ставим, темой управляет CSS prefers-color-scheme.
 */
const themeInitScript = `(function(){try{var t=localStorage.getItem('theme');var r=document.documentElement;if(t==='dark'){r.classList.add('dark');}else if(t==='light'){r.classList.add('light');}}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ru"
      className={`${manrope.variable} ${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:bg-brand-500 focus:text-white focus:px-4 focus:py-2 focus:rounded"
        >
          К содержимому
        </a>
        <BetaBanner />
        <Providers>
          {children}
          <EncyclopediaDrawer />
        </Providers>
      </body>
    </html>
  );
}
