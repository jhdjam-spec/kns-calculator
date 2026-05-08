import type { Metadata } from "next";
import { Providers } from "./providers";
import { manrope, inter, jetbrainsMono } from "./fonts";
import { BetaBanner } from "@/components/BetaBanner";
import { EncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
import "./globals.css";

export const metadata: Metadata = {
  title: "ИНСЕРВО · Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
  description:
    "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций. От ТЗ до спецификации с гидравликой за 60 секунд. Производитель оборудования с 2009 года.",
  authors: [{ name: "Konstantin Morozov · INSERVO Studio", url: "https://inservo.ru" }],
  creator: "INSERVO Studio",
  publisher: "Серво-Юг",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ru"
      className={`${manrope.variable} ${inter.variable} ${jetbrainsMono.variable}`}
    >
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
