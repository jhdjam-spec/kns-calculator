"""Построить агрегированную pricing-tier таблицу из pegas_engineering.json.

PEGAS — крупнейший российский конкурент Серво-Юг по бытовым ЛОС/КНС/танкам.
174 модели в 12 линейках, цены 2023 г. (нужно индексировать к 2026 ×1.20).

Цель: дать калькулятору **референсный коридор цен** для price_segment
("budget" / "standard" / "premium") по типу объекта (КНС / ЛОС / резервуар / и т.д.).

Выход: 02_dataset/pricing/pegas_tier.json — quantile_25/median/quantile_75
по линейкам и категориям, с инфляционной поправкой к 2026.

Использование:
  python backend/_scripts/build_pegas_pricing_tier.py
  python backend/_scripts/build_pegas_pricing_tier.py --inflation 1.20
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DS = ROOT / "02_dataset"

# Включаем ТОЛЬКО pegas_kns — корпуса КНС.
# По требованию пользователя: септики (lite/ekonom/base/premium/s_65),
# станции биологической очистки (pegas_pro), накопительные ёмкости и
# всё прочее (жироуловители/кессоны/погреба/бассейны) НЕ нужны в калькуляторе.
LINE_TO_SEGMENT: dict[str, str] = {
    "pegas_kns": "standard",  # КНС стеклопластиковые корпуса (Ø1000-1900мм, H3-4м)
}

LINE_TO_CATEGORY: dict[str, str] = {
    "pegas_kns": "kns_corpus",
}

# Линейки, ИСКЛЮЧЁННЫЕ из расчёта (не относятся к КНС):
# pegas_lite, pegas_ekonom, pegas_base — септики
# pegas_premium, pegas_s_65 — септики с принудительной аэрацией
# pegas_pro — промышленные ЛОС / станции биологической очистки
# pegas_grease_traps — жироуловители
# pegas_tanks_accumulator — накопительные ёмкости
# pegas_caissons, pegas_pogreba, pegas_pools — кессоны/погреба/бассейны


def percentile(sorted_values: list[float], pct: float) -> float:
    """Линейная интерполяция перцентиля по отсортированному списку."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def build_tier(inflation: float = 1.20) -> dict:
    """Собрать pricing-tier из PEGAS данных. inflation = коэф к 2023 ценам."""
    src = DS / "corpora" / "pegas_engineering.json"
    with open(src, encoding="utf-8") as f:
        pegas = json.load(f)

    tiers = {}
    by_segment: dict[str, list[float]] = {"budget": [], "standard": [], "premium": []}

    for line_name, line in pegas.get("lines", {}).items():
        # Пропускаем линейки, не относящиеся к КНС/насосам
        if line_name not in LINE_TO_SEGMENT:
            continue

        models = line.get("models", [])
        # PEGAS использует разные поля цены: price_rub_2023 (для большинства)
        # и price_rub_2023_corpus_only (для pegas_kns — только корпус, без насосов).
        prices_2023 = []
        for m in models:
            p = (
                m.get("price_rub_2023")
                or m.get("price_rub_2023_corpus_only")
            )
            if p and p > 0:
                prices_2023.append(p)
        if not prices_2023:
            continue

        prices_2026 = [round(p * inflation) for p in prices_2023]
        prices_sorted = sorted(prices_2026)

        segment = LINE_TO_SEGMENT[line_name]
        category = LINE_TO_CATEGORY[line_name]

        tiers[line_name] = {
            "category": category,
            "segment": segment,
            "models_count": len(models),
            "priced_count": len(prices_2023),
            "min_rub_2026": prices_sorted[0],
            "q25_rub_2026": round(percentile(prices_sorted, 0.25)),
            "median_rub_2026": round(percentile(prices_sorted, 0.50)),
            "q75_rub_2026": round(percentile(prices_sorted, 0.75)),
            "max_rub_2026": prices_sorted[-1],
            "mean_rub_2026": round(statistics.mean(prices_2026)),
            "stdev_rub_2026": (
                round(statistics.stdev(prices_2026)) if len(prices_2026) > 1 else 0
            ),
        }
        by_segment[segment].extend(prices_2026)

    # Агрегация по сегменту
    segment_summary = {}
    for seg, prices in by_segment.items():
        if not prices:
            continue
        prices_sorted = sorted(prices)
        segment_summary[seg] = {
            "samples_count": len(prices),
            "min_rub_2026": prices_sorted[0],
            "q25_rub_2026": round(percentile(prices_sorted, 0.25)),
            "median_rub_2026": round(percentile(prices_sorted, 0.50)),
            "q75_rub_2026": round(percentile(prices_sorted, 0.75)),
            "max_rub_2026": prices_sorted[-1],
            "mean_rub_2026": round(statistics.mean(prices)),
        }

    return {
        "_version": "0.1",
        "_updated": "2026-05-08",
        "_source": "02_dataset/corpora/pegas_engineering.json (174 модели PEGAS Engineering)",
        "_inflation_2023_to_2026": inflation,
        "_description": (
            "Референсные ценовые коридоры от крупного российского "
            "конкурента (PEGAS Engineering, 12 линеек, 2023 prices × inflation). "
            "Используется для калибровки price_segment в калькуляторе."
        ),
        "_engineer_note": (
            "ВАЖНО: PEGAS — конкурент, наши цены могут быть на 5-15% выше "
            "(брендовая премия Серво-Юг как инжиниринг + фирменное обслуживание). "
            "Используйте median+15% как ориентир для standard, q75+10% для premium."
        ),
        "tiers_by_line": tiers,
        "tiers_by_segment": segment_summary,
        "categories_used": sorted(set(LINE_TO_CATEGORY.values())),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--inflation", type=float, default=1.20,
                        help="Поправка цен 2023 to 2026 (default 1.20)")
    args = parser.parse_args()

    tier_data = build_tier(inflation=args.inflation)

    out = DS / "pricing" / "pegas_tier.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(tier_data, f, ensure_ascii=False, indent=2)

    print(f"Saved: {out}")
    print(f"Lines processed: {len(tier_data['tiers_by_line'])}")
    print()
    print("=== By segment (2026 prices, RUB) ===")
    for seg, d in tier_data["tiers_by_segment"].items():
        print(
            f"  {seg:9s}: median={d['median_rub_2026']:>10,}  "
            f"q25={d['q25_rub_2026']:>10,}  q75={d['q75_rub_2026']:>10,}  "
            f"({d['samples_count']} samples)"
        )
    print()
    print("=== By line (2026 prices, median) ===")
    for line, d in tier_data["tiers_by_line"].items():
        print(
            f"  {line:30s} [{d['segment']:8s}/{d['category']:20s}]"
            f"  median={d['median_rub_2026']:>10,}"
            f"  ({d['priced_count']}/{d['models_count']})"
        )


if __name__ == "__main__":
    main()
