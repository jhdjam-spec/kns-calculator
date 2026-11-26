"use client";

import { useState, useEffect } from "react";
import clsx from "clsx";
import { Settings2, HelpCircle } from "lucide-react";
import {
  type WastewaterType,
  type QUnit,
  type CorpusMaterial,
} from "@/schemas/input";
import { toM3h } from "@/lib/units";
import type { SelectionResult } from "@/schemas/result";
import { QHelper } from "@/components/QHelper";
import { ResultsCompare } from "./ResultsCompare";
import { useMode } from "@/components/providers/ModeProvider";

interface CalculatorPanelProps {
  onSubmit: (params: {
    Q_m3h: number;
    dH_m?: number;
    L_m?: number;
    pipe_D_mm?: number;
    wastewater_type?: WastewaterType;
    corpus_material?: CorpusMaterial;
  }) => void;
  isPending?: boolean;
  result?: SelectionResult | null;
  resultError?: boolean;
  quickInput?: { flow: number };
}

const wastewaterPills: { id: WastewaterType; label: string; hint: string }[] = [
  { id: "domestic", label: "Бытовая", hint: "Хозбытовые стоки от жилья и офисов" },
  { id: "drainage", label: "Дождевая", hint: "Ливневая канализация с территории" },
  { id: "industrial", label: "Промышленная", hint: "Промстоки с производства" },
  { id: "clean_water", label: "СПД (чистая вода)", hint: "Станция повышения давления — питьевая или техническая вода" },
  { id: "fire_protection", label: "Пожаротушение", hint: "Пожарные насосы по СП 10.13130 (резерв 1+1)" },
];

const corpusPills: { id: CorpusMaterial; label: string }[] = [
  { id: "pe", label: "Полиэтилен" },
  { id: "glass", label: "Стеклопластик" },
];

// Разумные технические границы. Если пользователь ввёл вне — показываем подсказку,
// но не блокируем submit (могут быть редкие промышленные кейсы — пусть бэк ответит).
const Q_M3H_MAX = 10000; // больше — крупная НС, не наш профиль
const DH_M_MAX = 200;    // больше — высотные технологические схемы
const L_M_MAX = 5000;    // больше — магистрали, не наш профиль

export function CalculatorPanel({ onSubmit, isPending, result, resultError, quickInput }: CalculatorPanelProps) {
  const [qValue, setQValue] = useState("21.2");
  const [qUnit, setQUnit] = useState<QUnit>("m3h");
  const [dH, setDH] = useState("8");
  const [L, setL] = useState("120");
  const [pipeD, setPipeD] = useState(""); // Опциональный диаметр напорной трубы, мм
  const [burialDepth, setBurialDepth] = useState(""); // Глубина заложения КНС (низ приёмного колодца)
  const [outletDepth, setOutletDepth] = useState(""); // Глубина точки выхода (врезка в коллектор)
  const [wastewater, setWastewater] = useState<WastewaterType>("domestic");
  const [corpus, setCorpus] = useState<CorpusMaterial>("pe");
  const [advanced, setAdvanced] = useState(false);
  const [helperOpen, setHelperOpen] = useState(false);
  const { mode } = useMode();

  useEffect(() => {
    if (!quickInput) return;
    setQValue(String(quickInput.flow));
    setQUnit("m3h");
    setWastewater("domestic");
    setHelperOpen(false);
  }, [quickInput]);

  // Предзаполнение из URL: ?q=21.2&h=8&pump=<id> — для shareable-ссылок
  // и переходов из Cmd+K палитры (группа «Насосы»). Один раз при mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    const h = params.get("h");
    const pumpId = params.get("pump");
    if (q && Number.isFinite(parseFloat(q))) setQValue(q);
    if (h && Number.isFinite(parseFloat(h))) setDH(h);
    // pump=<id> — пока используем только для якоря/трекинга; в будущем
    // можно дёрнуть /api/pumps/<id> и подставить точные Q_BEP/H_BEP.
    if (pumpId) {
      const stored = sessionStorage.getItem(`pump:${pumpId}`);
      if (stored) {
        try {
          const meta = JSON.parse(stored) as { Q?: number; H?: number };
          if (meta.Q != null) setQValue(String(meta.Q));
          if (meta.H != null) setDH(String(meta.H));
        } catch {
          // ignore corrupted sessionStorage
        }
      }
    }
  }, []);

  // Mode-aware labels: менеджер видит человеческие подписи,
  // инженер — компактные формулы из СП. Единица обновляется вместе с qUnit.
  const qUnitLabel = qUnit === "m3h" ? "м³/ч" : qUnit === "ls" ? "л/с" : "м³/сут";
  const qLabelText =
    mode === "engineer"
      ? `Q, ${qUnitLabel}`
      : `Расход (${qUnitLabel})`;
  const qTooltipText =
    mode === "engineer"
      ? "Расход Q, формула Q = V/t (СП 32.13330 §6.2)"
      : "Сколько воды в час нужно перекачивать";
  const dHLabelText = mode === "engineer" ? "dH, м" : "Перепад высот (м)";
  const lLabelText = mode === "engineer" ? "L, м" : "Длина трубы (м)";

  // Inline-валидация: пустое значение допустимо (поле опциональное), но
  // отрицательное/нечисловое — ошибка. Q обязателен и должен быть >0.
  const Q_num = parseFloat(qValue);
  const Q_m3h_normalized = Number.isFinite(Q_num) ? toM3h(Q_num, qUnit) : NaN;
  const qError =
    qValue.trim() === ""
      ? "Введите расход"
      : !Number.isFinite(Q_num) || Q_num <= 0
        ? "Расход должен быть больше нуля"
        : Q_m3h_normalized > Q_M3H_MAX
          ? "При расходе свыше 10 000 м³/ч обратитесь к инженеру"
          : null;

  const dH_num = parseFloat(dH);
  const dHError =
    dH.trim() === ""
      ? null
      : !Number.isFinite(dH_num)
        ? "Введите число"
        : dH_num < 0
          ? "Перепад высот не может быть отрицательным"
          : dH_num > DH_M_MAX
            ? `Перепад слишком большой (>${DH_M_MAX} м)`
            : null;

  const L_num = parseFloat(L);
  const LError =
    L.trim() === ""
      ? null
      : !Number.isFinite(L_num)
        ? "Введите число"
        : L_num < 0
          ? "Длина не может быть отрицательной"
          : L_num > L_M_MAX
            ? `Длина слишком большая (>${L_M_MAX} м)`
            : null;

  const hasBlockingError = qError !== null;

  // Диаметр напорной трубы — опциональный, в мм. Если задан, backend
  // использует его для расчёта потерь напора (Дарси-Вейсбах) и предупредит
  // о превышении скорости >2.5 м/с (СП 32 §6.5.4) или v<0.7 м/с заиливание.
  const pipeD_num = parseFloat(pipeD);
  const pipeDError =
    pipeD.trim() === ""
      ? null
      : !Number.isFinite(pipeD_num) || pipeD_num <= 0
        ? "Диаметр должен быть >0"
        : pipeD_num > 2000
          ? "Слишком большой диаметр (>2000 мм)"
          : pipeD_num < 25
            ? "Слишком малый диаметр (<25 мм)"
            : null;

  // Расчёт фактической скорости и предупреждение СП 32 (live, без backend)
  const pipeWarning = (() => {
    if (pipeDError || pipeD.trim() === "") return null;
    if (!Number.isFinite(Q_m3h_normalized) || Q_m3h_normalized <= 0) return null;
    const D_m = pipeD_num / 1000;
    const v = (4 * (Q_m3h_normalized / 3600)) / (Math.PI * D_m * D_m);
    if (v > 2.5) return { type: "high" as const, v, hint: `v=${v.toFixed(2)} м/с >2.5 — превышает СП 32 §6.5.4, нужен бо́льший D или насос мощнее` };
    if (v < 0.7) return { type: "low" as const, v, hint: `v=${v.toFixed(2)} м/с <0.7 — риск заиливания (СП 32 §5.4.3), уменьшите D` };
    return { type: "ok" as const, v, hint: `v=${v.toFixed(2)} м/с в норме (0.7-2.5 м/с по СП 32)` };
  })();

  // Глубина заложения КНС и точки выхода. Костя 2026-05-17:
  // «глубина входа в Кнс, соответственно, глубина выхода, потом есть высота подачи»
  // Эти параметры дают авто-расчёт dH (если оба заданы) и проверку реалистичности.
  const burialDepth_num = parseFloat(burialDepth);
  const outletDepth_num = parseFloat(outletDepth);
  const burialError =
    burialDepth.trim() === ""
      ? null
      : !Number.isFinite(burialDepth_num) || burialDepth_num <= 0
        ? "Глубина должна быть > 0"
        : burialDepth_num > 15
          ? "> 15 м — нестандарт, нужен проект ПТО"
          : null;
  const outletError =
    outletDepth.trim() === ""
      ? null
      : !Number.isFinite(outletDepth_num) || outletDepth_num < 0
        ? "Глубина должна быть ≥ 0"
        : outletDepth_num > 15
          ? "> 15 м — нестандарт"
          : null;
  // Если обе глубины заданы — авто-проверка dH-консистентности
  const depthHint = (() => {
    if (burialError || outletError) return null;
    if (burialDepth.trim() === "" || outletDepth.trim() === "") return null;
    // dH ≈ burial_depth - outlet_depth (т.к. выход обычно выше = меньшая глубина)
    // Если outlet выше поверхности земли (отрицательная "глубина") — пишем плюсом
    const computed_dH = burialDepth_num - outletDepth_num;
    if (computed_dH <= 0) {
      return { type: "warn" as const, hint: `Выход глубже приёмного — самотёк (dH=${computed_dH.toFixed(1)}м), насос не нужен` };
    }
    const dH_user = dH_num;
    if (Number.isFinite(dH_user) && Math.abs(computed_dH - dH_user) > 0.5) {
      return { type: "info" as const, hint: `Расчётный геом. перепад: ${computed_dH.toFixed(1)} м (по глубинам). Указанный dH=${dH_user} м` };
    }
    return { type: "ok" as const, hint: `Геом. перепад ${computed_dH.toFixed(1)} м (точка выхода выше дна КНС)` };
  })();

  const handleSubmit = () => {
    if (hasBlockingError) return;
    onSubmit({
      Q_m3h: Q_m3h_normalized,
      dH_m: !dHError && dH.trim() !== "" ? dH_num : undefined,
      L_m: !LError && L.trim() !== "" ? L_num : undefined,
      pipe_D_mm: !pipeDError && pipeD.trim() !== "" ? pipeD_num : undefined,
      wastewater_type: wastewater,
      corpus_material: corpus,
    });
  };

  return (
    <section id="calculator" className="kns-calculator">
      <div className="kns-shell">
        <div className="kns-section-heading">
          <h2>Параметры подбора</h2>
          <p>Укажите тип стоков и расход. Чтобы уточнить расчёт, добавьте параметры напорной линии.</p>
        </div>

        <div className="kns-calculator-card">
          <div className="kns-worksheet-grid">
            {/* Left: form */}
            <div className="kns-worksheet-input min-w-0 space-y-6">
              {/* Тип объекта */}
              <div>
                <div className="kns-field-label mb-3">
                  Тип стоков
                </div>
                <div className="flex flex-wrap gap-2">
                  {wastewaterPills.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      title={p.hint}
                      onClick={() => setWastewater(p.id)}
                      aria-pressed={wastewater === p.id}
                      className={clsx(
                        "px-3 py-2 rounded-md text-sm transition-all duration-base",
                        wastewater === p.id
                          ? "bg-ink-50 text-ink-950 font-medium"
                          : "bg-white/5 text-ink-300 hover:bg-white/10",
                      )}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                {/* Hint выбранного типа стоков */}
                <div className="mt-2 text-xs text-ink-400 leading-snug">
                  {wastewaterPills.find((p) => p.id === wastewater)?.hint}
                </div>
              </div>

              {/* Q + unit */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label
                    htmlFor="calc-q"
                    title={qTooltipText}
                    className="kns-field-label"
                  >
                    {qLabelText}
                  </label>
                  <button
                    type="button"
                    onClick={() => setHelperOpen(!helperOpen)}
                    aria-expanded={helperOpen}
                    className="inline-flex items-center gap-1 text-xs text-accent-500 hover:text-accent-400 transition-colors"
                  >
                    <HelpCircle size={12} strokeWidth={1.75} />
                    Как определить расход
                  </button>
                </div>
                <div className="flex gap-2">
                  <input
                    id="calc-q"
                    type="number"
                    inputMode="decimal"
                    value={qValue}
                    onChange={(e) => setQValue(e.target.value)}
                    step="0.1"
                    min="0"
                    aria-invalid={qError !== null}
                    aria-describedby={qError ? "calc-q-error" : undefined}
                    className={clsx(
                      "min-w-0 flex-1 h-12 px-3 rounded-md bg-white/5 border text-ink-50 font-mono tabular-nums outline-none transition-colors",
                      qError
                        ? "border-red-500/60 focus:border-red-500"
                        : "border-white/10 focus:border-accent-500",
                    )}
                  />
                  <div
                    className="flex bg-white/5 rounded-md p-1 gap-0.5"
                    role="group"
                    aria-label="Единица измерения расхода"
                  >
                    {(["m3h", "ls", "m3sut"] as QUnit[]).map((u) => (
                      <button
                        key={u}
                        type="button"
                        onClick={() => setQUnit(u)}
                        aria-pressed={qUnit === u}
                        className={clsx(
                          "min-h-10 px-2 sm:px-3 text-xs font-mono rounded transition-colors",
                          qUnit === u
                            ? "bg-ink-50 text-ink-950"
                            : "text-ink-400 hover:text-ink-200",
                        )}
                      >
                        {u === "m3h" ? "м³/ч" : u === "ls" ? "л/с" : "м³/сут"}
                      </button>
                    ))}
                  </div>
                </div>
                {qError && (
                  <p id="calc-q-error" role="alert" className="mt-2 text-xs text-red-400">
                    {qError}
                  </p>
                )}
              </div>

              {/* Advanced toggle */}
              <button
                type="button"
                onClick={() => setAdvanced(!advanced)}
                aria-expanded={advanced}
                className="inline-flex items-center gap-2 text-sm text-ink-300 hover:text-accent-500 transition-colors"
              >
                <Settings2 size={14} strokeWidth={1.5} />
                {advanced ? "Скрыть" : "Расширенные параметры"}
              </button>

              {advanced && (
                <div className="space-y-5 pt-2 border-t border-white/[0.06]">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label
                        htmlFor="calc-dh"
                        className="block kns-field-label mb-2"
                      >
                        {dHLabelText}
                      </label>
                      <input
                        id="calc-dh"
                        type="number"
                        inputMode="decimal"
                        value={dH}
                        onChange={(e) => setDH(e.target.value)}
                        step="0.5"
                        min="0"
                        aria-invalid={dHError !== null}
                        aria-describedby={dHError ? "calc-dh-error" : undefined}
                        className={clsx(
                          "w-full h-11 px-3 rounded-md bg-white/5 border text-ink-50 font-mono tabular-nums outline-none transition-colors",
                          dHError
                            ? "border-red-500/60 focus:border-red-500"
                            : "border-white/10 focus:border-accent-500",
                        )}
                      />
                      {dHError && (
                        <p id="calc-dh-error" role="alert" className="mt-1 text-xs text-red-400">
                          {dHError}
                        </p>
                      )}
                    </div>
                    <div>
                      <label
                        htmlFor="calc-l"
                        className="block kns-field-label mb-2"
                      >
                        {lLabelText}
                      </label>
                      <input
                        id="calc-l"
                        type="number"
                        inputMode="decimal"
                        value={L}
                        onChange={(e) => setL(e.target.value)}
                        step="1"
                        min="0"
                        aria-invalid={LError !== null}
                        aria-describedby={LError ? "calc-l-error" : undefined}
                        className={clsx(
                          "w-full h-11 px-3 rounded-md bg-white/5 border text-ink-50 font-mono tabular-nums outline-none transition-colors",
                          LError
                            ? "border-red-500/60 focus:border-red-500"
                            : "border-white/10 focus:border-accent-500",
                        )}
                      />
                      {LError && (
                        <p id="calc-l-error" role="alert" className="mt-1 text-xs text-red-400">
                          {LError}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Диаметр напорного трубопровода — критичен для расчёта потерь
                      по Дарси-Вейсбаху (h ∝ 1/D⁵). СП 32 §6.5.4: v=0.7–2.5 м/с. */}
                  <div>
                    <label
                      htmlFor="calc-d"
                      className="block kns-field-label mb-2"
                    >
                      {mode === "engineer" ? "D, мм (необязательно)" : "Диаметр напорной трубы (мм, опц.)"}
                    </label>
                    <input
                      id="calc-d"
                      type="number"
                      inputMode="decimal"
                      value={pipeD}
                      onChange={(e) => setPipeD(e.target.value)}
                      placeholder="авто по СП 32 (v=1.2 м/с)"
                      step="1"
                      min="0"
                      aria-invalid={pipeDError !== null}
                      aria-describedby={pipeDError ? "calc-d-error" : "calc-d-hint"}
                      className={clsx(
                        "w-full h-11 px-3 rounded-md bg-white/5 border text-ink-50 font-mono tabular-nums outline-none transition-colors",
                        pipeDError
                          ? "border-red-500/60 focus:border-red-500"
                          : "border-white/10 focus:border-accent-500",
                      )}
                    />
                    {pipeDError && (
                      <p id="calc-d-error" role="alert" className="mt-1 text-xs text-red-400">
                        {pipeDError}
                      </p>
                    )}
                    {!pipeDError && pipeWarning && (
                      <p
                        id="calc-d-hint"
                        className={clsx(
                          "mt-1 text-xs",
                          pipeWarning.type === "high" && "text-amber-400",
                          pipeWarning.type === "low" && "text-amber-400",
                          pipeWarning.type === "ok" && "text-clover-400",
                        )}
                      >
                        {pipeWarning.type === "ok" && "✓ "}
                        {pipeWarning.type !== "ok" && "⚠ "}
                        {pipeWarning.hint}
                      </p>
                    )}
                    {!pipeDError && !pipeWarning && (
                      <p id="calc-d-hint-empty" className="mt-1 text-[10px] text-ink-500">
                        Если не указан — программа подберёт по СП 32 §5.4 (v≈1.2 м/с)
                      </p>
                    )}
                  </div>

                  {/* Глубина заложения КНС и точки выхода (запрос Кости 2026-05-17).
                      Информативные, не влияют на подбор насоса напрямую, но
                      дают cross-check с dH и подсказывают высоту корпуса. */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label
                        htmlFor="calc-burial"
                        className="block kns-field-label mb-2"
                      >
                        {mode === "engineer" ? "h_КНС, м" : "Глубина приёмного колодца (м)"}
                      </label>
                      <input
                        id="calc-burial"
                        type="number"
                        inputMode="decimal"
                        value={burialDepth}
                        onChange={(e) => setBurialDepth(e.target.value)}
                        placeholder="напр. 3.5"
                        step="0.1"
                        min="0"
                        max="15"
                        className={clsx(
                          "w-full h-11 px-3 rounded-md bg-white/5 border text-ink-50 font-mono tabular-nums outline-none transition-colors",
                          burialError ? "border-red-500/60 focus:border-red-500" : "border-white/10 focus:border-accent-500",
                        )}
                      />
                      {burialError && (
                        <p className="mt-1 text-xs text-red-400">{burialError}</p>
                      )}
                    </div>
                    <div>
                      <label
                        htmlFor="calc-outlet"
                        className="block kns-field-label mb-2"
                      >
                        {mode === "engineer" ? "h_выход, м" : "Глубина точки выхода (м)"}
                      </label>
                      <input
                        id="calc-outlet"
                        type="number"
                        inputMode="decimal"
                        value={outletDepth}
                        onChange={(e) => setOutletDepth(e.target.value)}
                        placeholder="напр. 1.5"
                        step="0.1"
                        min="0"
                        max="15"
                        className={clsx(
                          "w-full h-11 px-3 rounded-md bg-white/5 border text-ink-50 font-mono tabular-nums outline-none transition-colors",
                          outletError ? "border-red-500/60 focus:border-red-500" : "border-white/10 focus:border-accent-500",
                        )}
                      />
                      {outletError && (
                        <p className="mt-1 text-xs text-red-400">{outletError}</p>
                      )}
                    </div>
                  </div>
                  {depthHint && (
                    <p
                      className={clsx(
                        "text-xs -mt-2",
                        depthHint.type === "warn" && "text-amber-400",
                        depthHint.type === "info" && "text-clover-400",
                        depthHint.type === "ok" && "text-ink-400",
                      )}
                    >
                      {depthHint.type === "warn" ? "⚠ " : depthHint.type === "info" ? "ℹ " : "✓ "}
                      {depthHint.hint}
                    </p>
                  )}

                  <div>
                    <div className="kns-field-label mb-2">
                      Материал корпуса
                    </div>
                    <div className="flex gap-2">
                      {corpusPills.map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => setCorpus(p.id)}
                          className={clsx(
                            "px-3 py-2 rounded-md text-sm transition-all",
                            corpus === p.id
                              ? "bg-ink-50 text-ink-950 font-medium"
                              : "bg-white/5 text-ink-300 hover:bg-white/10",
                          )}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={handleSubmit}
                disabled={isPending || hasBlockingError}
                aria-describedby={hasBlockingError ? "calc-q-error" : undefined}
                className="w-full h-14 rounded-md bg-clover-500 hover:bg-clover-600 disabled:bg-ink-700 disabled:text-ink-500 text-white font-medium transition-colors duration-base"
              >
                {isPending ? "Считаем…" : "Рассчитать по параметрам"}
              </button>
            </div>

            {/* Right: live preview */}
            <div className="kns-worksheet-output min-w-0">
              {resultError && (
                <p role="alert" className="kns-worksheet-error">
                  Не удалось выполнить расчёт. Повторите попытку.
                  {result && " Ниже показан предыдущий расчёт."}
                </p>
              )}
              {helperOpen ? (
                <div className="bg-white rounded-card p-6 max-h-[600px] overflow-y-auto">
                  <QHelper
                    onCalculate={(Q) => {
                      setQValue(Q.toFixed(1));
                      setQUnit("m3h");
                      setHelperOpen(false);
                    }}
                  />
                </div>
              ) : isPending ? (
                <PreviewSkeleton />
              ) : result ? (
                <ResultsCompare result={result} />
              ) : (
                <PreviewEmpty />
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PreviewEmpty() {
  return (
    <div className="h-full min-h-[300px] flex items-center justify-center">
      <div className="text-center max-w-sm">
        <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-2">
          Рекомендованный насос
        </div>
        <p className="text-ink-400 text-sm leading-relaxed">
          Введите расход для подбора моделей. Здесь появятся расчётный напор и стоимость комплекта.
        </p>
      </div>
    </div>
  );
}

function PreviewSkeleton() {
  // Shimmer-skeleton (animate-shimmer из globals.css). Структура повторяет
  // PreviewResult: 2 числа сверху + блок рекомендации + строка-маркер.
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Идёт расчёт подбора">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="h-3 w-20 rounded bg-white/[0.05] animate-shimmer" />
          <div className="h-9 md:h-12 w-24 rounded bg-white/[0.05] animate-shimmer" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-20 rounded bg-white/[0.05] animate-shimmer" />
          <div className="h-9 md:h-12 w-24 rounded bg-white/[0.05] animate-shimmer" />
        </div>
      </div>
      <div className="bg-ink-50/5 dark:bg-white/[0.03] rounded-card p-5 space-y-2 relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-clover-500/40" />
        <div className="h-3 w-32 rounded bg-white/[0.05] animate-shimmer" />
        <div className="h-6 w-44 rounded bg-white/[0.05] animate-shimmer" />
        <div className="h-3 w-56 rounded bg-white/[0.05] animate-shimmer" />
      </div>
      <div className="h-3 w-2/3 rounded bg-white/[0.04] animate-shimmer" />
    </div>
  );
}
