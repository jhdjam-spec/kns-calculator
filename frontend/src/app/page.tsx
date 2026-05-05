"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { WizardL0 } from "@/components/WizardL0";
import { ResultsCards } from "@/components/ResultsCards";
import { HandoffPanel } from "@/components/HandoffPanel";
import { QuizUploader } from "@/components/QuizUploader";
import { usePumpSelection } from "@/hooks/usePumpSelection";
import type { SelectionResult } from "@/schemas/result";

export default function HomePage() {
  const mutation = usePumpSelection();
  // Результат может прийти из 2 источников: WizardL0 (mutation) или QuizUploader (file).
  // Держим единое состояние, чтобы ResultsCards/HandoffPanel показывали последний.
  const [latest, setLatest] = useState<SelectionResult | null>(null);
  useEffect(() => {
    if (mutation.data) setLatest(mutation.data);
  }, [mutation.data]);

  return (
    <main className="container mx-auto px-4 py-6 md:py-8 max-w-5xl space-y-6 md:space-y-8">
      {/* Брендинг Серво-Юг */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-gray-200">
        <div>
          <p className="text-base md:text-lg font-bold text-blue-900 leading-tight">
            ИНСЕРВО · Серво-Юг
          </p>
          <p className="text-xs text-gray-600">
            Производство КНС, ЛОС и резервуаров с 2009 года · Адыгея, аул Хатукай
          </p>
        </div>
        <div className="text-sm">
          <a href="tel:+78002224457" className="block font-semibold text-blue-900 hover:underline">
            8 (800) 222-44-57
          </a>
          <a href="mailto:zakaz@inservo.ru" className="text-xs text-gray-600 hover:underline">
            zakaz@inservo.ru
          </a>
        </div>
      </div>

      <header className="space-y-2">
        <h1 className="text-2xl md:text-3xl font-bold">
          Подбор насоса для канализационной станции
        </h1>
        <p className="text-sm md:text-base text-gray-700">
          Введите параметры объекта — получите 3 варианта комплекта с ориентировочной ценой.
          Подходит для гостиниц, коттеджей, небольших производств.
        </p>
        <nav className="text-sm flex gap-3 mt-2">
          <span className="font-semibold border-b-2 border-blue-600 pb-0.5">
            Подбор насоса
          </span>
          <Link href="/tanks" className="text-blue-600 hover:underline">
            Калькуляторы ёмкостей →
          </Link>
        </nav>
      </header>

      <section>
        <h2 className="text-xl font-semibold mb-3">Параметры</h2>
        <WizardL0
          onSubmit={(input) => mutation.mutate(input)}
          isPending={mutation.isPending}
        />
      </section>

      <section>
        <QuizUploader onResult={(r) => setLatest(r)} />
      </section>

      {mutation.isError && (
        <div
          role="alert"
          className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-900"
        >
          <strong>Ошибка вызова backend:</strong>{" "}
          {mutation.error?.message ?? "неизвестная ошибка"}
          <p className="text-xs mt-1 text-red-700">
            Убедитесь, что backend запущен на http://localhost:8000 (см. README).
          </p>
        </div>
      )}

      {latest && (
        <>
          <ResultsCards result={latest} />
          <HandoffPanel result={latest} />
        </>
      )}
    </main>
  );
}
