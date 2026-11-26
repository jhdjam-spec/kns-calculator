import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Справочник по СП и ГОСТ — Энциклопедия инженера ВК · Серво-Юг",
  description:
    "Справочник проектировщика: гидравлика, NPSH, кавитация, СП 32 канализация, СП 30 ВК, СП 22 геотехника, ПУЭ электрика, ЛОС биология. Цитаты норм, ссылки на cntd.ru.",
  alternates: { canonical: "/teach/" },
  openGraph: {
    title: "Справочник по СП и ГОСТ — Энциклопедия инженера ВК",
    description:
      "7 разделов с цитатами из СП и ГОСТ для проектировщиков водоснабжения и водоотведения.",
    type: "website",
    locale: "ru_RU",
  },
};

export default function TeachLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
