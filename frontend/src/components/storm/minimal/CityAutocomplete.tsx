// ╭───────────────────────────────────────────────────────────────────────╮
// │ INSERVO Studio — Калькулятор подбора КНС/НС/ЛОС                       │
// │ Автор: Константин Морозов · https://inservo.ru                        │
// │ Лицензия: MIT (см. LICENSE и NOTICE)                                  │
// │ Просьба сохранять авторство при использовании производных работ       │
// ╰───────────────────────────────────────────────────────────────────────╯
"use client";

import { useState, useMemo } from "react";

interface Props {
  selected: string | null;
  onSelect: (city: string | null) => void;
}

// 36 городов из БД 02_climate_db_36_cities.json
const CITIES = [
  "Краснодар", "Ростов-на-Дону", "Сочи", "Анапа", "Геленджик", "Новороссийск",
  "Ставрополь", "Махачкала", "Грозный", "Симферополь", "Севастополь", "Ялта",
  "Керчь", "Евпатория", "Донецк", "Луганск", "Мариуполь", "Москва",
  "Санкт-Петербург", "Воронеж", "Волгоград", "Казань", "Самара",
  "Нижний Новгород", "Екатеринбург", "Челябинск", "Уфа", "Новосибирск",
  "Омск", "Красноярск", "Тюмень", "Мурманск", "Архангельск", "Якутск",
  "Хабаровск", "Владивосток",
] as const;

const DEFAULT_CITY = "Москва";

export function CityAutocomplete({ selected, onSelect }: Props) {
  const [query, setQuery] = useState(selected ?? "");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filtered = useMemo(() => {
    if (!query.trim()) return CITIES.slice(0, 6);
    const q = query.toLowerCase();
    return CITIES.filter((c) => c.toLowerCase().includes(q)).slice(0, 8);
  }, [query]);

  const handleSelect = (city: string) => {
    setQuery(city);
    onSelect(city);
    setShowSuggestions(false);
  };

  const handleDontKnow = () => {
    setQuery(DEFAULT_CITY);
    onSelect(DEFAULT_CITY);
    setShowSuggestions(false);
  };

  return (
    <div className="space-y-2 relative">
      <label className="block text-sm font-medium text-ink-800 dark:text-ink-200">
        3. В каком городе объект?{" "}
        <span className="text-ink-600 dark:text-ink-500" title="Город нужен для климатических параметров (количество дождей, интенсивность). Если ваш город не в списке — выберите ближайший крупный.">
          ❓
        </span>
      </label>
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setShowSuggestions(true);
          if (!CITIES.includes(e.target.value as (typeof CITIES)[number])) {
            onSelect(null);
          }
        }}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
        placeholder="Начните печатать название..."
        className="w-full px-3 py-2 rounded-md bg-white border border-ink-200 text-ink-900 dark:bg-white/[0.04] dark:border-white/10 dark:text-ink-100 focus:border-brand-500 dark:focus:border-accent-500 focus:outline-none"
      />
      {showSuggestions && filtered.length > 0 && (
        <ul className="absolute z-10 w-full mt-1 bg-white border border-ink-200 dark:bg-ink-900 dark:border-white/10 rounded-md shadow-premium-md max-h-60 overflow-auto">
          {filtered.map((city) => (
            <li key={city}>
              <button
                type="button"
                onClick={() => handleSelect(city)}
                className="w-full text-left px-3 py-2 text-sm text-ink-800 dark:text-ink-200 hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-accent-500/10 dark:hover:text-accent-500"
              >
                {city}
              </button>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        onClick={handleDontKnow}
        className="text-xs text-amber-700 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 underline-offset-2 hover:underline"
      >
        не знаю — Москва (по умолчанию)
      </button>
    </div>
  );
}
