"use client";

import { useState } from "react";
import type { ProjectResult, SubsystemResult, BOMItem } from "@/lib/api-extended";
import {
  downloadCalculationPdf,
  downloadBomCsv,
} from "@/lib/api-extended";
import { openEncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
import { SuggestionList } from "@/components/wizard/SuggestionCard";
import type { InputSuggestion } from "@/schemas/result";

/** Маппинг кода норматива → топик энциклопедии для drawer'а. */
const REGULATION_TO_TOPIC: Array<{ pattern: RegExp; topic: string }> = [
  { pattern: /СП 8\.13130|СП 10\.13130|СП 485|123-ФЗ|ФЗ-123/i, topic: "fire" },
  { pattern: /СП 30\.|СП 31\.|СП 399|СанПиН/i, topic: "water" },
  { pattern: /ПУЭ|ТР ТС 004|ТР ТС 020|ТР ТС 012|ГОСТ Р 50571|IEC 60034/i, topic: "electrical" },
  { pattern: /СП 32\.|ГОСТ 6134|ISO 9906/i, topic: "hydraulics" },
  { pattern: /СП 20\.|СП 14\.|СП 25\.|СП 131\.|СП 12-/i, topic: "structural" },
  { pattern: /ПП.*728|ПП.*644|МСХ-552|СанПиН 2\.1\.5|ИТС 10/i, topic: "los" },
];

function topicForRegulation(code: string): string {
  for (const { pattern, topic } of REGULATION_TO_TOPIC) {
    if (pattern.test(code)) return topic;
  }
  return "hydraulics";    // default fallback
}

/** Скачивание blob как файл. */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Извлечение `suggestions[]` из любой подсистемы — backend кладёт их в
 * `subsystem.data.selection.suggestions` (KNS) либо напрямую в
 * `subsystem.data.suggestions` (другие подсистемы). Узкий помощник без
 * жёсткой типизации — schema проверится ниже на runtime.
 */
function extractSuggestions(
  subsystemData: Record<string, unknown> | undefined,
): InputSuggestion[] {
  if (!subsystemData) return [];
  const sel = subsystemData.selection as Record<string, unknown> | undefined;
  const raw =
    (sel?.suggestions as unknown[]) ||
    (subsystemData.suggestions as unknown[]) ||
    [];
  if (!Array.isArray(raw)) return [];
  // Лёгкая sanity-проверка: должен быть объект с field+severity.
  return raw.filter(
    (s): s is InputSuggestion =>
      typeof s === "object" &&
      s !== null &&
      typeof (s as { field?: unknown }).field === "string" &&
      typeof (s as { severity?: unknown }).severity === "string",
  );
}

/** Извлечение price_breakdown подобранного насоса из subsystem.data.selection. */
function extractPumpBreakdown(
  subsystemData: Record<string, unknown> | undefined,
): {
  pump?: Record<string, unknown>;
  breakdown?: Record<string, number>;
} {
  if (!subsystemData) return {};
  const sel = subsystemData.selection as Record<string, unknown> | undefined;
  if (!sel) return {};
  const results = sel.results as
    | { mid?: Record<string, unknown>; budget?: Record<string, unknown>; premium?: Record<string, unknown> }
    | undefined;
  const pump = results?.mid ?? results?.budget ?? results?.premium;
  if (!pump) return {};
  const breakdown = pump.price_breakdown as Record<string, number> | undefined;
  return { pump, breakdown };
}


/** Сборка BOM из ProjectResult — берём реальные цены из price_breakdown. */
function buildBomFromProject(result: ProjectResult): BOMItem[] {
  const items: BOMItem[] = [];

  // ─── КНС: реальный price_breakdown подобранного насоса ──────────────
  if (result.kns?.status === "ok") {
    const { pump, breakdown } = extractPumpBreakdown(result.kns.data);
    const brand = pump ? String(pump.brand ?? "Не выбрано") : "Не выбрано";
    const model = pump ? String(pump.model ?? "") : "";
    const article = pump ? String(pump.id ?? "") : "";
    const Pkw = pump ? Number(pump.P_kW ?? 0) : 0;

    if (breakdown) {
      // Реальные цифры: pump_rub за 2 шт (1 раб + 1 рез)
      if (breakdown.pump_rub > 0) {
        items.push({
          section: "pumps",
          name: `${brand} ${model}`.trim(),
          article,
          manufacturer: brand,
          quantity: 2,
          units: "шт",
          price_rub_2026: breakdown.pump_rub / 2,
          note: `${Pkw} кВт · 1 раб + 1 рез (СП 32 §6.2)`,
        });
      }
      if (breakdown.corpus_rub > 0) {
        items.push({
          section: "corpus",
          name: "Корпус КНС стеклопластик",
          quantity: 1,
          units: "шт",
          price_rub_2026: breakdown.corpus_rub,
        });
      }
      if (breakdown.atm_rub > 0) {
        items.push({
          section: "piping",
          name: "Автомуфта АТМ",
          quantity: 2,
          units: "шт",
          price_rub_2026: breakdown.atm_rub / 2,
        });
      }
      if (breakdown.valve_rub > 0) {
        items.push({
          section: "piping",
          name: "Задвижка",
          quantity: 2,
          units: "шт",
          price_rub_2026: breakdown.valve_rub / 2,
        });
      }
      if (breakdown.check_valve_rub > 0) {
        items.push({
          section: "piping",
          name: "Обратный клапан",
          quantity: 2,
          units: "шт",
          price_rub_2026: breakdown.check_valve_rub / 2,
        });
      }
      if (breakdown.rails_rub > 0) {
        items.push({
          section: "piping",
          name: "Направляющие AISI 304",
          quantity: 1,
          units: "комплект",
          price_rub_2026: breakdown.rails_rub,
        });
      }
      if (breakdown.chain_rub > 0) {
        items.push({
          section: "piping",
          name: "Цепь подъёма",
          quantity: 1,
          units: "комплект",
          price_rub_2026: breakdown.chain_rub,
        });
      }
      if (breakdown.floats_rub > 0) {
        items.push({
          section: "automation",
          name: "Поплавки (датчики уровня)",
          quantity: 4,
          units: "шт",
          price_rub_2026: breakdown.floats_rub / 4,
        });
      }
      if (breakdown.cabinet_rub > 0) {
        items.push({
          section: "control_panel",
          name: "Шкаф управления КНС",
          quantity: 1,
          units: "шт",
          price_rub_2026: breakdown.cabinet_rub,
        });
      }
    } else {
      // Fallback если price_breakdown не пришёл — note об этом
      items.push({
        section: "pumps",
        name: `${brand} ${model}`.trim() || "Насос (не подобран)",
        manufacturer: brand,
        quantity: 2,
        units: "шт",
        price_rub_2026: 0,
        note: "Цены отсутствуют — запросите у инженера Серво-Юг",
      });
    }
  }

  // ─── ВНС хозпит. ─────────────────────────────────────────────────────
  if (result.vns_potable?.status === "ok") {
    const data = result.vns_potable.data as Record<string, unknown>;
    const station = data.station as Record<string, unknown> | undefined;
    const ops = Number(station?.operating_pumps ?? 1);
    const standby = Number(station?.standby_pumps ?? 1);
    items.push({
      section: "pumps",
      name: "Насос повысительный ВНС",
      quantity: ops + standby,
      units: "шт",
      // Эмпирически 75 тыс ₽ за повысительный насос среднего размера —
      // реальный подбор делается позже инженером
      price_rub_2026: 75000,
      note: `${ops} раб + ${standby} рез (СП 31 §6.5). Цена ориентировочная.`,
    });
  }

  // ─── ВНС пожарная ────────────────────────────────────────────────────
  if (result.vns_fire?.status === "ok") {
    const data = result.vns_fire.data as Record<string, unknown>;
    const station = data.pump_station as Record<string, unknown> | undefined;
    const reservoir = data.reservoir as Record<string, unknown> | null;

    const opsFire = Number(station?.operating_pumps ?? 1);
    const stbFire = Number(station?.standby_pumps ?? 1);
    items.push({
      section: "fire_water",
      name: "Насос пожарный",
      quantity: opsFire + stbFire,
      units: "шт",
      price_rub_2026: 120000,
      note: `${opsFire} раб + ${stbFire} рез (СП 10.13130 §6.2). Цена ориентировочная.`,
    });
    if (reservoir) {
      const v_m3 = Number(reservoir.required_volume_m3 ?? 0);
      const n_res = Number(reservoir.n_reservoirs ?? 1);
      // Цена пожарного резервуара ~ 8000₽/м³ для стеклопластика V=50-200 м³
      const v_per = v_m3 / Math.max(n_res, 1);
      items.push({
        section: "fire_water",
        name: `Резервуар пожарный V=${v_per.toFixed(0)} м³`,
        quantity: n_res,
        units: "шт",
        price_rub_2026: Math.round(v_per * 8000),
        note: "Стеклопластиковый, заглубленный (СП 8.13130 §9)",
      });
    }
  }

  // ─── Электрика — реальный шкаф из подсистемы ────────────────────────
  if (result.electrical?.status === "ok") {
    const data = result.electrical.data as Record<string, unknown>;
    const panel = data.panel as Record<string, unknown> | undefined;
    if (panel) {
      const priceTuple = panel.estimated_price_rub_2026 as [number, number] | undefined;
      const avgPanel = priceTuple ? (priceTuple[0] + priceTuple[1]) / 2 : 100000;
      items.push({
        section: "control_panel",
        name: String(panel.name ?? "Шкаф управления"),
        quantity: 1,
        units: "шт",
        price_rub_2026: avgPanel,
        note: `Уровень: ${panel.level} · Категория надёжности по подсистеме`,
      });
    }

    const cable = data.cable as Record<string, unknown> | undefined;
    if (cable) {
      const len = 50;
      const section = Number(cable.section_mm2 ?? 2.5);
      // Цена кабеля примерно 80-200 ₽/м для 2.5-10 мм², растёт с сечением
      const pricePerM = Math.round(50 + section * 18);
      items.push({
        section: "electrical",
        name: `Кабель ${cable.cable_type} ${cable.n_cores}×${section} мм²`,
        quantity: len,
        units: "м",
        price_rub_2026: pricePerM,
        note: "Длина ориентировочная; уточняется по проекту трасс",
      });
    }
  }

  // ─── ЛОС — реальный блок из selected_block ──────────────────────────
  if (result.los?.status === "ok") {
    const data = result.los.data as Record<string, unknown>;
    const block = data.selected_block as Record<string, unknown> | null;
    if (block) {
      const priceTuple = block.estimated_price_rub_2026 as [number, number] | undefined;
      const avg = priceTuple ? (priceTuple[0] + priceTuple[1]) / 2 : 200000;
      items.push({
        section: "los",
        name: `${block.manufacturer} ${block.model}`,
        manufacturer: String(block.manufacturer || ""),
        quantity: 1,
        units: "комплект",
        price_rub_2026: avg,
        note: `Q=${block.capacity_m3_per_day} м³/сут, технология ${block.technology}`,
      });
    }
  }

  // ─── Прочность → пригруз бетоном ────────────────────────────────────
  if (result.structural?.status === "ok") {
    const data = result.structural.data as Record<string, unknown>;
    if (data.is_required) {
      items.push({
        section: "ballast",
        name: "Бетон В20 для пригруза",
        quantity: Number(data.ballast_concrete_volume_m3 ?? 0),
        units: "м³",
        price_rub_2026: 8500,
        note: "Цена бетона В20 в товарной готовности (с доставкой) на 2026",
      });
    }
  }

  // ─── Климат → утепление если требуется ──────────────────────────────
  if (result.climate?.status === "ok") {
    const data = result.climate.data as Record<string, unknown>;
    if (data.insulation_required) {
      const thickness = Number(data.insulation_thickness_mm ?? 50);
      items.push({
        section: "insulation",
        name: `Утепление трубопровода минвата ${thickness} мм`,
        quantity: 50, // длина ориентир.
        units: "м",
        price_rub_2026: 350,
        note: "Длина уточняется по проекту трасс",
      });
    }
  }

  return items;
}

interface Props {
  result: ProjectResult;
  onBack: () => void;
  onRestart: () => void;
}

export function ProjectStepResults({ result, onBack, onRestart }: Props) {
  const [pdfStatus, setPdfStatus] = useState<"idle" | "loading" | "error">("idle");
  const [csvStatus, setCsvStatus] = useState<"idle" | "loading" | "error">("idle");
  const [exportError, setExportError] = useState<string | null>(null);

  const handleDownloadPdf = async () => {
    setPdfStatus("loading");
    setExportError(null);
    try {
      const bomItems = buildBomFromProject(result);
      const blob = await downloadCalculationPdf({
        project_name: result.project_name,
        project_code: result.project_code,
        inputs_summary: {
          "Пресет": result.preset,
          "Подсистем активно": Object.values(result).filter(
            (v) => v && typeof v === "object" && "status" in v,
          ).length,
        },
        hydraulics: result.kns?.data,
        fire_water: result.vns_fire?.data,
        water_supply: result.vns_potable?.data,
        climate: result.climate?.data,
        structural: result.structural?.data,
        los: result.los?.data,
        bom: bomItems.map((it) => ({
          name: it.name,
          article: it.article || "",
          quantity: it.quantity ?? 1,
          price_rub: it.price_rub_2026 ?? 0,
        })),
        references: result.references_consolidated,
      });
      downloadBlob(
        blob,
        `Расчётная_записка_${result.project_code || result.project_name}.pdf`,
      );
      setPdfStatus("idle");
    } catch (e) {
      setPdfStatus("error");
      setExportError(String(e));
    }
  };

  const handleDownloadCsv = async () => {
    setCsvStatus("loading");
    setExportError(null);
    try {
      const items = buildBomFromProject(result);
      const blob = await downloadBomCsv({
        project_code: result.project_code,
        project_name: result.project_name,
        items,
      });
      downloadBlob(blob, `BOM_${result.project_code || result.project_name}.csv`);
      setCsvStatus("idle");
    } catch (e) {
      setCsvStatus("error");
      setExportError(String(e));
    }
  };

  const subsystems: Array<[string, SubsystemResult | null]> = [
    ["КНС хозбытовая", result.kns],
    ["ВНС хозпитьевая", result.vns_potable],
    ["ВНС пожарная", result.vns_fire],
    ["Ливневая канализация", result.storm],
    ["ЛОС биологическая", result.los],
    ["Электрика", result.electrical],
    ["Климат", result.climate],
    ["Прочность", result.structural],
  ];

  const active = subsystems.filter(([, r]) => r !== null);

  // Phase ux-edge-cases — собираем suggestions из всех активных подсистем
  // (в первую очередь — KNS, но другие тоже могут отдавать).
  const allSuggestions: InputSuggestion[] = active.flatMap(([, sub]) =>
    sub ? extractSuggestions(sub.data) : [],
  );

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-display font-semibold text-ink-50 mb-1">
            {result.project_name}
          </h2>
          <p className="text-ink-400 text-sm">
            Пресет: {result.preset} · Подсистем: {active.length}
            {result.total_warnings > 0 && (
              <span className="ml-3 text-yellow-400">
                ⚠ {result.total_warnings} предупреждений
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={onRestart}
          className="text-sm text-ink-400 hover:text-accent-500 transition-colors"
        >
          Новый проект
        </button>
      </div>

      {/* UX edge-cases — backend советует поправить ввод */}
      {allSuggestions.length > 0 && (
        <div className="mb-6">
          <SuggestionList suggestions={allSuggestions} variant="dark" />
        </div>
      )}

      {/* Карточки подсистем */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {active.map(([label, subResult]) => (
          <SubsystemCard key={label} label={label} result={subResult!} />
        ))}
      </div>

      {/* Ссылки на нормативы */}
      {result.references_consolidated.length > 0 && (
        <div className="bg-ink-950 border border-ink-800 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-display font-semibold text-ink-50">
              Нормативная база
            </div>
            <div className="text-xs text-ink-500">Кликните на пункт — откроется справка</div>
          </div>
          <ul className="text-sm text-ink-300 space-y-1.5">
            {result.references_consolidated.map((ref, i) => {
              const topic = topicForRegulation(ref.regulation_code || "");
              const anchor = ref.purpose || ref.section || ref.regulation_code || "";
              return (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() =>
                      openEncyclopediaDrawer({
                        topic,
                        anchor,
                        valueLabel: `${ref.regulation_code} ${ref.section || ""}`.trim(),
                        regulation: ref.regulation_code,
                      })
                    }
                    className="text-left hover:bg-ink-900 rounded px-1.5 py-0.5 -mx-1.5 transition-colors w-full"
                  >
                    <span className="text-accent-500 font-mono">{ref.regulation_code}</span>
                    {ref.section && <span className="text-ink-500"> · {ref.section}</span>}
                    {ref.purpose && <span className="text-ink-400"> — {ref.purpose}</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Действия */}
      <div className="flex flex-col md:flex-row gap-3 mb-2">
        <button
          type="button"
          onClick={handleDownloadPdf}
          disabled={pdfStatus === "loading"}
          className="bg-accent-500 hover:bg-accent-400 disabled:bg-ink-700 disabled:text-ink-500 text-ink-950 px-4 py-2.5 rounded-md font-medium transition-colors"
        >
          {pdfStatus === "loading"
            ? "Генерация PDF…"
            : "📄 Расчётная записка (PDF)"}
        </button>
        <button
          type="button"
          onClick={handleDownloadCsv}
          disabled={csvStatus === "loading"}
          className="bg-ink-100 hover:bg-ink-50 disabled:bg-ink-700 disabled:text-ink-500 text-ink-950 px-4 py-2.5 rounded-md font-medium transition-colors"
        >
          {csvStatus === "loading"
            ? "Сборка CSV…"
            : "📊 BOM — список оборудования / спецификация (CSV / Excel)"}
        </button>
      </div>
      <div className="text-xs text-ink-500 mb-6">
        PDF — пятисекционный отчёт для защиты проекта (ОЛ → методика → результаты →
        BOM → выводы). CSV — список оборудования для импорта в ГРАНД-Смету или Excel.
      </div>

      {exportError && (
        <div className="mb-6 p-3 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-300">
          Ошибка экспорта: {exportError}
        </div>
      )}

      {/* BOM-таблица */}
      <BomTable items={buildBomFromProject(result)} />

      {/* Углублённые расчёты (Phase 21+22 physics_advanced) */}
      <DeepCalculationsLinks />


      {/* Beta предупреждение */}
      <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-md text-sm">
        <span className="text-yellow-400 font-medium">Бета-версия. </span>
        <span className="text-yellow-200">
          Результаты являются информационными. Перед применением в проекте обязательна
          верификация инженером-проектировщиком ВК. Допуск ±15% от реальной документации.
        </span>
      </div>

      <div className="flex justify-between mt-8">
        <button
          type="button"
          onClick={onBack}
          className="text-ink-400 hover:text-ink-200 px-4 py-2 transition-colors"
        >
          ← Изменить параметры
        </button>
      </div>
    </div>
  );
}

/** Блок «Углубиться» — ссылки на разделы энциклопедии гидравлики и физики (Phase 21). */
function DeepCalculationsLinks() {
  const items: Array<{ anchor: string; title: string; description: string }> = [
    {
      anchor: "NPSH",
      title: "NPSH и кавитация",
      description: "Расчёт NPSHa с поправкой на высоту/широту, выбор материалов колеса",
    },
    {
      anchor: "Гидроудар",
      title: "Гидроудар (Жуковский / Михайлов)",
      description: "12 материалов труб, выбор PN-класса, способы защиты",
    },
    {
      anchor: "Дарси",
      title: "Потери Дарси-Вейсбаха",
      description: "λ Swamee-Jain, шероховатость для 13 материалов",
    },
    {
      anchor: "Параллель",
      title: "Параллельная работа насосов",
      description: "Эффективность 60-95%, bear-traps, графика Q-H",
    },
    {
      anchor: "Местные потери",
      title: "Местные потери (Идельчик)",
      description: "200+ ζ-коэффициентов: колена, тройники, задвижки, ОК",
    },
    {
      anchor: "Q-H",
      title: "Q-H характеристика и подобие",
      description: "Аппроксимация, законы подобия, поправка на вязкость",
    },
  ];

  return (
    <div className="bg-ink-950 border border-ink-800 rounded-lg p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-display font-semibold text-ink-50">
            Углубиться в теорию
          </div>
          <div className="text-xs text-ink-500 mt-0.5">
            6 разделов гидравлики и физики (~2300 строк по СП/ГОСТ/Karassik)
          </div>
        </div>
        <a
          href="/teach/hydraulics"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-accent-500 hover:text-accent-400"
        >
          Открыть полную статью →
        </a>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {items.map((it) => (
          <button
            key={it.anchor}
            type="button"
            onClick={() =>
              openEncyclopediaDrawer({
                topic: "hydraulics",
                anchor: it.anchor,
                valueLabel: it.title,
              })
            }
            className="text-left p-3 bg-ink-900 border border-ink-800 rounded-md hover:border-accent-500/50 transition-colors group"
          >
            <div className="text-sm font-display font-medium text-ink-100 group-hover:text-accent-500 transition-colors">
              {it.title}
            </div>
            <div className="text-xs text-ink-400 mt-1">{it.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

/** Таблица BOM (Phase 30) — упрощённая, для отображения в визарде. */
function BomTable({ items }: { items: BOMItem[] }) {
  if (items.length === 0) return null;

  const total = items.reduce(
    (acc, it) => acc + (it.quantity ?? 1) * (it.price_rub_2026 ?? 0),
    0,
  );

  // Группировка по разделам
  const sectionLabels: Record<string, string> = {
    pumps: "Насосы",
    corpus: "Корпус КНС/НС",
    control_panel: "Шкаф управления",
    piping: "Обвязка",
    fire_water: "Пожарка",
    los: "ЛОС",
    ballast: "Пригруз",
    insulation: "Утепление",
    electrical: "Электрика",
  };

  return (
    <div className="bg-ink-950 border border-ink-800 rounded-lg p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-display font-semibold text-ink-50">
            BOM — список оборудования / спецификация
          </div>
          <div className="text-xs text-ink-500 mt-0.5">
            {items.length} позиций · ориентировочные цены 2026
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-ink-500">Итого ориентировочно</div>
          <div className="font-mono text-xl text-accent-500">
            {total.toLocaleString("ru-RU")} ₽
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs font-mono uppercase tracking-wider text-ink-500 border-b border-ink-800">
              <th className="text-left py-2 px-3 w-10">№</th>
              <th className="text-left py-2 px-3">Наименование</th>
              <th className="text-left py-2 px-3 hidden md:table-cell">Раздел</th>
              <th className="text-right py-2 px-3 w-20">Кол-во</th>
              <th className="text-right py-2 px-3 hidden md:table-cell w-28">Цена ₽</th>
              <th className="text-right py-2 px-3 w-28">Сумма ₽</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, i) => {
              const sum = (it.quantity ?? 1) * (it.price_rub_2026 ?? 0);
              return (
                <tr
                  key={i}
                  className="border-b border-ink-900 hover:bg-ink-900/50 transition-colors"
                >
                  <td className="py-2 px-3 text-ink-500 font-mono text-xs">{i + 1}</td>
                  <td className="py-2 px-3">
                    <div className="text-ink-100">{it.name}</div>
                    {it.note && (
                      <div className="text-xs text-ink-500 mt-0.5">{it.note}</div>
                    )}
                  </td>
                  <td className="py-2 px-3 hidden md:table-cell">
                    <span className="text-xs px-1.5 py-0.5 bg-ink-900 text-ink-400 rounded">
                      {sectionLabels[it.section] || it.section}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right text-ink-200 font-mono">
                    {it.quantity ?? 1} {it.units || "шт"}
                  </td>
                  <td className="py-2 px-3 text-right text-ink-300 font-mono hidden md:table-cell">
                    {(it.price_rub_2026 ?? 0).toLocaleString("ru-RU")}
                  </td>
                  <td className="py-2 px-3 text-right text-ink-50 font-mono">
                    {sum.toLocaleString("ru-RU")}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={5} className="py-3 px-3 text-right text-sm text-ink-300 font-medium">
                ИТОГО
              </td>
              <td className="py-3 px-3 text-right font-mono text-lg text-accent-500 font-semibold">
                {total.toLocaleString("ru-RU")} ₽
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="mt-4 text-xs text-ink-500">
        ⚠ Цены ориентировочные на 2026 г. Точные цифры — после запроса дилерам.
        Используйте экспорт CSV для импорта в Excel или ГРАНД-Смету.
      </div>
    </div>
  );
}

/** Маппинг названия подсистемы → топик энциклопедии. */
const SUBSYSTEM_TOPIC: Record<string, string> = {
  "КНС хозбытовая": "hydraulics",
  "ВНС хозпитьевая": "water",
  "ВНС пожарная": "fire",
  "Ливневая канализация": "hydraulics",
  "ЛОС биологическая": "los",
  "Электрика": "electrical",
  "Климат": "structural",
  "Прочность": "structural",
};

function SubsystemCard({ label, result }: { label: string; result: SubsystemResult }) {
  const statusColor: Record<string, string> = {
    ok: "text-green-400 border-green-500/30 bg-green-500/5",
    warning: "text-yellow-400 border-yellow-500/30 bg-yellow-500/5",
    error: "text-red-400 border-red-500/30 bg-red-500/5",
    skipped: "text-ink-500 border-ink-700 bg-ink-900",
  };
  const statusIcon: Record<string, string> = {
    ok: "✓",
    warning: "⚠",
    error: "✕",
    skipped: "—",
  };

  const topic = SUBSYSTEM_TOPIC[label] || "hydraulics";
  // Якорь — берём первое слово подсистемы (КНС/ВНС/Ливневая…) для поиска секции
  const anchor = label.split(" ")[0];

  return (
    <div className={`border rounded-lg p-4 ${statusColor[result.status] || statusColor.skipped}`}>
      <div className="flex items-start justify-between mb-2">
        <button
          type="button"
          onClick={() =>
            openEncyclopediaDrawer({
              topic,
              anchor,
              valueLabel: label,
            })
          }
          className="font-display font-semibold text-ink-50 hover:text-accent-500 transition-colors text-left underline decoration-dotted decoration-accent-500/30 underline-offset-4 hover:decoration-accent-500"
          title="Открыть справку из энциклопедии"
        >
          {label}
        </button>
        <span className="font-mono text-lg">{statusIcon[result.status]}</span>
      </div>
      <div className="text-sm text-ink-300 mb-2">{result.summary}</div>
      {result.warnings && result.warnings.length > 0 && (
        <div className="mt-3 pt-3 border-t border-ink-800/50">
          <div className="text-xs text-yellow-400 font-medium mb-1">Предупреждения:</div>
          <ul className="text-xs text-ink-400 space-y-0.5">
            {result.warnings.map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
