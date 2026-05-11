import type { Metadata } from "next";
import { Providers } from "./providers";
import { manrope, inter, jetbrainsMono } from "./fonts";
import { BetaBanner } from "@/components/BetaBanner";
import { EncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
import "./globals.css";

export const metadata: Metadata = {
  title: "ИНСЕРВО · Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
  description:
    "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций. От ТЗ до спецификации с гидравликой за минуту. Производитель оборудования с 2009 года.",
  authors: [{ name: "Konstantin Morozov · INSERVO Studio", url: "https://inservo.ru" }],
  creator: "INSERVO Studio",
  publisher: "Серво-Юг",
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
        <BetaBanner />
        <Providers>
          {children}
          <EncyclopediaDrawer />
        </Providers>
      </body>
    </html>
  );
}
