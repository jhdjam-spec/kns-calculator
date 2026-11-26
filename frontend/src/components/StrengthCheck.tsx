"use client";

import { useState } from "react";
import clsx from "clsx";
import { ShieldCheck, AlertTriangle, ChevronDown } from "lucide-react";
import {
  structuralApi,
  type BallastResult,
  type WallThicknessResult,
} from "@/lib/api-extended";

/** Материалы корпуса, поддерживаемые backend /structural/* эндпоинтами. */
export type CorpusMaterial =
  | "polypropylene"
  | "hdpe"
  | "fiberglass"
  | "concrete"
  | "concrete_monolith"
  | "steel"
  | "stainless";

interface StrengthCheckProps {
  /** Диаметр корпуса, мм (из формы /tanks/) */
  diameter_mm: number;
  /** Высота корпуса, мм */
  height_mm: number;
  /** Толщина стенки, мм (текущая выбранная) */
  wall_thickness_mm: number;
  /** Материал. Дефолт — polypropylene для КНС-форм /tanks/. */
  material?: CorpusMaterial;
}

/**
 * Прочностной чек корпуса КНС/ёмкости. Подключается к backend:
 *  - POST /structural/ballast — нужен ли пригруз, объём бетона
 *  - POST /structural/wall-thickness — толщина по ISO 9969 SN
 *
 * Применяется на /tanks/ как раскрывающаяся секция «Проверить прочность».
 * Доп. поля: глубина заложения, УГВ, тип грунта.
 */
const SOIL_TYPES = [
  { id: "sand", label: "Песок", density: 1700, phi: 32 },
  { id: "sandy_loam", label: "Супесь", density: 1700, phi: 28 },
  { id: "loam", label: "Суглинок", density: 1750, phi: 22 },
  { id: "clay", label: "Глина", density: 1800, phi: 18 },
  { id: "gravel", label: "Гравий", density: 1900, phi: 38 },
] as const;

export function StrengthCheck({
  diameter_mm,
  height_mm,
  wall_thickness_mm,
  material = "polypropylene",
}: StrengthCheckProps) {
  const [open, setOpen] = useState(false);
  const [burialDepth, setBurialDepth] = useState((height_mm / 1000).toFixed(1));
  const [groundwaterDepth, setGroundwaterDepth] = useState("0.5");
  const [soilId, setSoilId] = useState<(typeof SOIL_TYPES)[number]["id"]>("sandy_loam");
  const [fillPct, setFillPct] = useState("20");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ballast, setBallast] = useState<BallastResult | null>(null);
  const [wall, setWall] = useState<WallThicknessResult | null>(null);

  const soil = SOIL_TYPES.find((s) => s.id === soilId) ?? SOIL_TYPES[0];

  const handleCheck = async () => {
    setError(null);
    setLoading(true);
    setBallast(null);
    setWall(null);
    try {
      const burial_depth_m = parseFloat(burialDepth);
      const groundwater_depth_m = parseFloat(groundwaterDepth);
      const fill_level_pct = parseFloat(fillPct);
      if (
        !Number.isFinite(burial_depth_m) || burial_depth_m < 0.5 ||
        !Number.isFinite(groundwater_depth_m) || groundwater_depth_m < 0 ||
        !Number.isFinite(fill_level_pct) || fill_level_pct < 0 || fill_level_pct > 100
      ) {
        setError("Проверьте введённые значения: глубина ≥ 0.5 м, УГВ ≥ 0 м, заполнение 0–100%.");
        return;
      }
      const input = {
        diameter_m: diameter_mm / 1000,
        height_m: height_mm / 1000,
        material,
        wall_thickness_mm,
        groundwater_depth_m,
        burial_depth_m,
        soil_density_kg_m3: soil.density,
        soil_friction_angle_deg: soil.phi,
        contents_density_kg_m3: 1000,
        fill_level_pct,
      };
      const [b, w] = await Promise.all([
        structuralApi.ballast(input),
        structuralApi.wallThickness(input),
      ]);
      setBallast(b);
      setWall(w);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="mt-6 rounded-lg border border-clover-200 dark:border-clover-700/40 bg-clover-50/50 dark:bg-clover-900/20">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="strength-panel"
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} strokeWidth={1.75} className="text-clover-600 dark:text-clover-300 shrink-0" />
          <div>
            <div className="font-medium text-foreground dark:text-ink-100">
              Проверить прочность корпуса
            </div>
            <div className="text-xs text-muted dark:text-ink-400">
              Пригруз против всплытия + толщина стенки по ISO 9969 (СП 22 / СП 32)
            </div>
          </div>
        </div>
        <ChevronDown
          size={18}
          className={clsx(
            "shrink-0 text-muted transition-transform duration-base",
            open ? "rotate-180" : "rotate-0",
          )}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div id="strength-panel" className="border-t border-clover-200 dark:border-clover-700/40 p-4 space-y-4">
          {/* Inputs */}
          <div className="grid sm:grid-cols-2 gap-3">
            <label className="flex flex-col text-sm">
              <span className="text-ink-700 dark:text-ink-300 mb-1">
                Глубина заложения, м
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="0.1"
                min="0.5"
                max="10"
                value={burialDepth}
                onChange={(e) => setBurialDepth(e.target.value)}
                className="rounded-md border border-ink-300 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 text-foreground dark:text-ink-100 focus:border-clover-500 outline-none"
              />
            </label>

            <label className="flex flex-col text-sm">
              <span className="text-ink-700 dark:text-ink-300 mb-1">
                УГВ от поверхности, м
                <span className="text-muted text-xs ml-1">(0 = на уровне)</span>
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="0.1"
                min="0"
                max="10"
                value={groundwaterDepth}
                onChange={(e) => setGroundwaterDepth(e.target.value)}
                className="rounded-md border border-ink-300 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 text-foreground dark:text-ink-100 focus:border-clover-500 outline-none"
              />
            </label>

            <label className="flex flex-col text-sm">
              <span className="text-ink-700 dark:text-ink-300 mb-1">Тип грунта</span>
              <select
                value={soilId}
                onChange={(e) => setSoilId(e.target.value as typeof soilId)}
                className="rounded-md border border-ink-300 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 text-foreground dark:text-ink-100 focus:border-clover-500 outline-none"
              >
                {SOIL_TYPES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label} (γ={s.density} кг/м³, φ={s.phi}°)
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col text-sm">
              <span className="text-ink-700 dark:text-ink-300 mb-1">
                Заполнение при поверке, %
                <span className="text-muted text-xs ml-1">(20% = худший случай)</span>
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="5"
                min="0"
                max="100"
                value={fillPct}
                onChange={(e) => setFillPct(e.target.value)}
                className="rounded-md border border-ink-300 dark:border-ink-700 bg-white dark:bg-ink-900 px-3 py-2 text-foreground dark:text-ink-100 focus:border-clover-500 outline-none"
              />
            </label>
          </div>

          <button
            type="button"
            onClick={handleCheck}
            disabled={loading}
            className="w-full sm:w-auto inline-flex items-center justify-center min-h-11 px-5 rounded-md bg-clover-500 hover:bg-clover-600 disabled:bg-ink-300 dark:disabled:bg-ink-700 text-white font-medium transition-colors"
          >
            {loading ? "Считаем…" : "Запустить проверку"}
          </button>

          {error && (
            <div role="alert" className="rounded-md border border-red-400/40 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-700 dark:text-red-300">
              Ошибка: {error}
            </div>
          )}

          {/* Результаты */}
          {(ballast || wall) && (
            <div className="grid md:grid-cols-2 gap-3 pt-2">
              {wall && <WallThicknessCard result={wall} current={wall_thickness_mm} />}
              {ballast && <BallastCard result={ballast} />}
            </div>
          )}

          <p className="text-xs text-muted dark:text-ink-500 leading-relaxed pt-2">
            Расчёт по СП 22.13330 (грунты, активное давление) + СП 32.13330 §6.3
            (всплытие при УГВ) + ISO 9969 (SN-классы для полимерных корпусов).
            Это инженерный ориентир — финальное проектное решение принимает инженер ПТО
            с учётом конкретной геологии участка.
          </p>
        </div>
      )}
    </section>
  );
}

function WallThicknessCard({
  result,
  current,
}: {
  result: WallThicknessResult;
  current: number;
}) {
  const ok = result.is_current_sufficient;
  return (
    <div
      className={clsx(
        "rounded-md border p-4 space-y-2",
        ok
          ? "border-green-300 dark:border-green-700/50 bg-green-50/50 dark:bg-green-900/20"
          : "border-amber-300 dark:border-amber-700/50 bg-amber-50/50 dark:bg-amber-900/20",
      )}
    >
      <div className="flex items-center gap-2">
        {ok ? (
          <ShieldCheck size={16} className="text-green-700 dark:text-green-300" />
        ) : (
          <AlertTriangle size={16} className="text-amber-700 dark:text-amber-300" />
        )}
        <span className="font-medium text-foreground dark:text-ink-100">
          Толщина стенки {ok ? "достаточна" : "требует усиления"}
        </span>
      </div>
      <dl className="text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-muted dark:text-ink-400">Текущая</dt>
        <dd className="font-mono tabular-nums">{current} мм</dd>
        <dt className="text-muted dark:text-ink-400">Требуется</dt>
        <dd className="font-mono tabular-nums">
          {result.required_thickness_mm.toFixed(1)} мм ({result.sn_class})
        </dd>
        <dt className="text-muted dark:text-ink-400">Запас</dt>
        <dd className="font-mono tabular-nums">
          {result.safety_margin_pct >= 0 ? "+" : ""}
          {result.safety_margin_pct.toFixed(1)}%
        </dd>
      </dl>
      {result.notes?.length > 0 && (
        <ul className="text-xs text-muted dark:text-ink-400 mt-2 space-y-0.5 list-disc list-inside">
          {result.notes.slice(0, 3).map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function BallastCard({ result }: { result: BallastResult }) {
  const required = result.is_required;
  return (
    <div
      className={clsx(
        "rounded-md border p-4 space-y-2",
        required
          ? "border-amber-300 dark:border-amber-700/50 bg-amber-50/50 dark:bg-amber-900/20"
          : "border-green-300 dark:border-green-700/50 bg-green-50/50 dark:bg-green-900/20",
      )}
    >
      <div className="flex items-center gap-2">
        {required ? (
          <AlertTriangle size={16} className="text-amber-700 dark:text-amber-300" />
        ) : (
          <ShieldCheck size={16} className="text-green-700 dark:text-green-300" />
        )}
        <span className="font-medium text-foreground dark:text-ink-100">
          {required ? "Нужен пригруз" : "Пригруз не требуется"}
        </span>
      </div>
      <dl className="text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-muted dark:text-ink-400">Архимед</dt>
        <dd className="font-mono tabular-nums">
          {result.archimedes_force_kn.toFixed(1)} кН
        </dd>
        <dt className="text-muted dark:text-ink-400">Удерж. вес</dt>
        <dd className="font-mono tabular-nums">
          {(result.self_weight_kn + result.contents_weight_kn).toFixed(1)} кН
        </dd>
        <dt className="text-muted dark:text-ink-400">Коэф. запаса</dt>
        <dd
          className={clsx(
            "font-mono tabular-nums",
            result.safety_factor < 1.1 && "text-amber-700 dark:text-amber-300 font-semibold",
          )}
        >
          {result.safety_factor.toFixed(2)} {result.safety_factor < 1.1 && "⚠"}
        </dd>
        {required && result.ballast_concrete_volume_m3 > 0 && (
          <>
            <dt className="text-muted dark:text-ink-400">Объём бетона</dt>
            <dd className="font-mono tabular-nums">
              {result.ballast_concrete_volume_m3.toFixed(2)} м³ (
              {result.ballast_concrete_thickness_m.toFixed(2)} м толщ.)
            </dd>
          </>
        )}
      </dl>
      {result.notes?.length > 0 && (
        <ul className="text-xs text-muted dark:text-ink-400 mt-2 space-y-0.5 list-disc list-inside">
          {result.notes.slice(0, 3).map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
