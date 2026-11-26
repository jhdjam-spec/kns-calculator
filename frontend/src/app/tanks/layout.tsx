import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Подбор ёмкости и корпуса КНС — ПП и стеклопластик · Серво-Юг",
  description:
    "Подбор полипропиленовых ёмкостей и корпусов КНС: горизонтальные ПП, вертикальные ПП-КНС, стеклопластик. Расчёт объёма по СП 32.13330 за минуту.",
  alternates: { canonical: "/tanks" },
  openGraph: {
    title: "Подбор ёмкости и корпуса КНС — ПП и стеклопластик · Серво-Юг",
    description:
      "Подбор ёмкостей и корпусов КНС: ПП, стеклопластик. Расчёт по СП 32.13330.",
    url: "/tanks",
    type: "website",
  },
};

export default function TanksLayout({ children }: { children: React.ReactNode }) {
  return children;
}
