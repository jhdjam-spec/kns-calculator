"use client";

import { useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { HorizontalTankForm } from "@/components/HorizontalTankForm";
import { KnsCorpusForm } from "@/components/KnsCorpusForm";

type Tab = "pp" | "fiberglass" | "kns";

const TABS: { id: Tab; label: string; subtitle: string }[] = [
  { id: "pp", label: "ПП-ёмкости", subtitle: "Горизонтальные, первичный полипропилен" },
  { id: "fiberglass", label: "Стеклопластик", subtitle: "В разработке" },
  { id: "kns", label: "Корпус КНС", subtitle: "Вертикальный ПП" },
];

export default function TanksPage() {
  const [tab, setTab] = useState<Tab>("pp");

  return (
    <main className="container mx-auto px-4 py-8 max-w-5xl space-y-6">
      <header className="space-y-2">
        <nav className="text-sm">
          <Link href="/" className="text-blue-600 underline">
            ← Подбор насоса
          </Link>
        </nav>
        <h1 className="text-3xl font-bold">Калькуляторы ёмкостей</h1>
        <p className="text-gray-600">
          Расчёт массы и стоимости горизонтальных ПП-ёмкостей и корпусов КНС.
          Источник формул:{" "}
          <code className="text-xs">02_dataset/tanks/tank_calculator_models.json</code>{" "}
          (на основе ODS-калькулятора Серво-Юг).
        </p>
      </header>

      <div role="tablist" className="flex border-b border-gray-200 gap-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 transition",
              tab === t.id
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-gray-600 hover:text-gray-900"
            )}
          >
            {t.label}
            <span className="block text-xs font-normal text-gray-500">{t.subtitle}</span>
          </button>
        ))}
      </div>

      <section>
        {tab === "pp" && <HorizontalTankForm />}
        {tab === "kns" && <KnsCorpusForm />}
        {tab === "fiberglass" && (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
            <h3 className="text-lg font-semibold mb-2">Калькулятор стеклопластиковых ёмкостей</h3>
            <p className="text-gray-600 max-w-lg mx-auto">
              В разработке. Принципиально использует ту же геометрию, что ПП-калькулятор,
              но с другими константами плотности (1700–2000 кг/м³ для стеклопластика vs
              ~920 кг/м³ для ПП) и удельной стоимости.
            </p>
            <p className="text-sm text-gray-500 mt-3">
              Если у вас есть прайс или модель Серво-Юг по стеклопластику — добавьте в{" "}
              <code>02_dataset/tanks/tank_calculator_models.json::fiberglass_tank</code>.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
