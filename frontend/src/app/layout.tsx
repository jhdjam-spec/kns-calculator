import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "kns-calculator — подбор насоса для КНС/НС/СПД",
  description:
    "Открытый калькулятор первичного подбора насоса. Введите 4 поля — получите топ-3 насоса в трёх ценовых сегментах.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
