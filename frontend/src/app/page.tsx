"use client";

import Link from "next/link";
import { WizardL0 } from "@/components/WizardL0";
import { ResultsCards } from "@/components/ResultsCards";
import { HandoffPanel } from "@/components/HandoffPanel";
import { usePumpSelection } from "@/hooks/usePumpSelection";

export default function HomePage() {
  const mutation = usePumpSelection();

  return (
    <main className="container mx-auto px-4 py-8 max-w-5xl space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">
          Подбор насоса для канализационной станции
        </h1>
        <p className="text-gray-700">
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

      {mutation.data && (
        <>
          <ResultsCards result={mutation.data} />
          <HandoffPanel result={mutation.data} />
        </>
      )}
    </main>
  );
}
