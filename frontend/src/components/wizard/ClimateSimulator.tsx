"use client";

/**
 * ClimateSimulator — выбор города → climate-карточка + рекомендации.
 *
 * Использует backend endpoints:
 *   GET /climate/cities (76 городов)
 *   GET /climate/{city} (полная карточка + recommendations)
 *
 * Mode-aware: engineer видит технические значения (frost_depth, t_min_5pct),
 * manager — простые подписи + рекомендации текстом.
 *
 * Может вызывать onCityChange(city, altitude_m) для авто-fill L1 в визарде.
 */
import { useEffect, useMemo, useState } from "react";
import { useMode } from "@/components/providers/ModeProvider";
import {
  climateApi,
  type ClimateCardResponse,
  type ClimateCity,
} from "@/lib/api-extended";

export interface ClimateSimulatorProps {
  /** Текущий выбранный город (controlled). */
  value?: string;
  /** Callback при смене города. altitude_m нужен для L1.altitude_m. */
  onChange?: (city: string, altitude_m?: number) => void;
  /** Сколько городов показывать в datalist (по умолчанию все). */
  limit?: number;
}

export function ClimateSimulator({ value, onChange, limit }: ClimateSimulatorProps) {
  const { mode } = useMode();
  const isEngineer = mode === "engineer";

  const [cities, setCities] = useState<ClimateCity[]>([]);
  const [citiesLoading, setCitiesLoading] = useState(true);
  const [citiesError, setCitiesError] = useState<string | null>(null);

  const [input, setInput] = useState<string>(value || "");
  const [card, setCard] = useState<ClimateCardResponse | null>(null);
  const [cardLoading, setCardLoading] = useState(false);
  const [cardError, setCardError] = useState<string | null>(null);

  useEffect(() => {
    if (value !== undefined && value !== input) setInput(value);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useEffect(() => {
    let cancelled = false;
    climateApi
      .cities()
      .then((res) => {
        if (!cancelled) {
          setCities(res.cities);
          setCitiesLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setCitiesError(String(e));
          setCitiesLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Получаем карточку для текущего города (если он есть в БД)
  useEffect(() => {
    if (!input.trim()) {
      setCard(null);
      return;
    }
    // Проверим, есть ли точное (case-insensitive) совпадение в списке
    const match = cities.find(
      (c) => c.city.toLowerCase() === input.trim().toLowerCase(),
    );
    if (!match) {
      setCard(null);
      return;
    }
    let cancelled = false;
    setCardLoading(true);
    setCardError(null);
    climateApi
      .forCity(match.city)
      .then((res) => {
        if (!cancelled) {
          setCard(res);
          setCardLoading(false);
          // Bubble up altitude — для авто-fill L1.altitude_m
          onChange?.(match.city, match.altitude_m);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setCardError(String(e));
          setCardLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, cities]);

  const visibleCities = useMemo(() => {
    if (limit && cities.length > limit) return cities.slice(0, limit);
    return cities;
  }, [cities, limit]);

  return (
    <div data-testid="climate-simulator" className="space-y-3">
      <div>
        <label htmlFor="climate-city-input" className="block text-sm text-ink-300 mb-1.5">
          Город (для climate-рекомендаций)
        </label>
        <input
          id="climate-city-input"
          type="text"
          list="climate-city-list"
          className="form-input w-full"
          autoComplete="off"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            onChange?.(e.target.value);
          }}
          placeholder={citiesLoading ? "Загрузка городов…" : "Начните вводить город…"}
          aria-describedby="climate-city-hint"
        />
        <datalist id="climate-city-list">
          {visibleCities.map((c) => (
            <option key={c.city} value={c.city}>
              {c.region} · {c.climate_zone}
            </option>
          ))}
        </datalist>
        <div id="climate-city-hint" className="text-xs text-ink-500 mt-1">
          Источник: СП 131.13330.2020, {cities.length} городов в БД
        </div>
      </div>

      {citiesError && (
        <div className="text-xs text-red-600">Не удалось загрузить список городов: {citiesError}</div>
      )}

      {cardLoading && (
        <div className="text-sm text-ink-500" data-testid="climate-loading">Загрузка карточки климата…</div>
      )}
      {cardError && (
        <div className="text-xs text-red-600" data-testid="climate-error">
          {cardError}
        </div>
      )}

      {card && !cardLoading && (
        <ClimateCard card={card} isEngineer={isEngineer} />
      )}
    </div>
  );
}

function ClimateCard({ card, isEngineer }: { card: ClimateCardResponse; isEngineer: boolean }) {
  const c = card.climate;
  return (
    <div
      data-testid="climate-card"
      className="rounded-card bg-ink-900 border border-ink-800 p-4 space-y-3"
    >
      <div className="flex items-baseline justify-between">
        <h4 className="font-display font-semibold text-ink-50">{c.city}</h4>
        <span className="text-xs font-mono text-ink-500 uppercase tracking-wider">
          {c.climate_zone}
        </span>
      </div>
      <div className="text-xs text-ink-400">{c.region}</div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        <Datum label="Высота над УМ" value={`${c.altitude_m} м`} engineer={isEngineer} />
        <Datum label="Глубина промерзания" value={`${c.frost_depth_mm} мм`} engineer={isEngineer} />
        <Datum
          label="T_min 5% (СП 131)"
          value={`${c.t_min_5pct_c} °C`}
          engineer={isEngineer}
        />
        {c.lat !== null && c.lat !== undefined && (
          <Datum
            label="Координаты"
            value={`${c.lat?.toFixed(2)}, ${c.lon?.toFixed(2)}`}
            engineer={isEngineer}
          />
        )}
      </dl>

      {card.recommendations.length > 0 && (
        <div data-testid="climate-recommendations">
          <div className="text-xs font-mono uppercase tracking-wider text-ink-500 mb-1.5">
            Рекомендации
          </div>
          <ul className="space-y-1.5">
            {card.recommendations.map((r) => (
              <li
                key={r.code}
                data-severity={r.severity}
                className={
                  r.severity === "critical"
                    ? "text-sm text-red-300 border-l-2 border-red-500 pl-3"
                    : r.severity === "warning"
                    ? "text-sm text-amber-300 border-l-2 border-amber-500 pl-3"
                    : "text-sm text-ink-300 border-l-2 border-ink-700 pl-3"
                }
              >
                <strong>{r.title}</strong>: {r.text}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Datum({
  label,
  value,
  engineer,
}: {
  label: string;
  value: string;
  engineer: boolean;
}) {
  return (
    <>
      <dt className="text-ink-500" title={engineer ? undefined : "Технический параметр"}>
        {label}
      </dt>
      <dd className="text-ink-100 font-mono tabular-nums">{value}</dd>
    </>
  );
}
