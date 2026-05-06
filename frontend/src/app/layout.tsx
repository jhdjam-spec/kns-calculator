import type { Metadata } from "next";
import { Providers } from "./providers";
import { manrope, inter, jetbrainsMono } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "ИНСЕРВО · Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
  description:
    "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций. От ТЗ до спецификации с гидравликой за 60 секунд. Производитель оборудования с 2009 года.",
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
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
