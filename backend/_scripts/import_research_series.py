"""Импорт серий насосов из multi-agent research в pumps.json (envelope-only).

Источник: 02_dataset/_analysis/manufacturers_full_list.json (research-агент 2026-05-08).

Стратегия — НЕ копируем 150+ моделей сразу, а добавляем по 1 ENVELOPE-записи
на серию (с Q_min/Q_max/H_min/H_max). Это закрывает 80% случаев подбора и
быстро заполняет дыры в Q-H матрице. Конкретные модели добавляются по мере
поступления реальных сделок (с реальными Q_BEP, NPSHr, ценой).

ПРИОРИТЕТЫ (топ-15):
1. ИСТРАТЕХ (преемник Grundfos Истра) — 6 серий, гос-тендеры
2. ЦНС (HMS Ливгидромаш + 9 заводов СНГ) — закрывает H=150-600м (главная дыра)
3. CNP — 12 серий с 6 открытыми ценами 2026
4. Ясногорский ЗМР — H до 300м, реестр Минпромторг
5. Sulzer ABS — для Q≥1500 (дыра 1)
6. Кронштадт — российский премиум
7. ОНИКС-СПДТ — пожарные многоступенчатые
8. Wilo MVI/Helix — H=150 (дыра 3)
9. Tsurumi — японские для дренажа
10. Caprari Defender — итальянские premium

Все добавленные с _engineer_flag=needs_review_research,
_source=research_2026-05-08, без точных BEP.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DS = ROOT / "02_dataset"
RESEARCH_JSON = DS / "_analysis" / "manufacturers_full_list.json"
PUMPS_JSON = DS / "pumps" / "pumps.json"

# Маппинг типов из research → нашей схемы
TYPE_MAP = {
    "submersible_sewage": "submersible_sewage",
    "submersible_sewage_premium": "submersible_sewage",
    "submersible_sewage_with_capture": "submersible_sewage",
    "drainage_dirty": "submersible_sewage",
    "horizontal_sewage": "vertical_dry_well",
    "multistage_vertical": "booster_station",
    "single_stage_inline": "booster_station",
    "console_monoblock": "booster_station",
    "fire_protection_high_head": "booster_station",
    "deep_well": "booster_station",
    "centrifugal_horizontal": "booster_station",
    "submersible_clean_water": "booster_station",
    "multistage_csm": "booster_station",
    "multistage_pi": "booster_station",
    "high_pressure_multistage": "booster_station",
    "fire_pump": "booster_station",
}

# Импеллер по типу серии (грубо)
IMPELLER_MAP = {
    "submersible_sewage": "channel",
    "submersible_sewage_premium": "channel",
    "submersible_sewage_with_capture": "cutter",
    "drainage_dirty": "vortex",
    "horizontal_sewage": "channel",
    "multistage_vertical": "centrifugal_closed",
    "single_stage_inline": "centrifugal_closed",
    "console_monoblock": "centrifugal_closed",
    "fire_protection_high_head": "centrifugal_closed",
    "deep_well": "centrifugal_closed",
    "centrifugal_horizontal": "centrifugal_closed",
    "submersible_clean_water": "centrifugal_closed",
    "multistage_csm": "centrifugal_closed",
    "multistage_pi": "centrifugal_closed",
    "high_pressure_multistage": "centrifugal_closed",
    "fire_pump": "centrifugal_closed",
}

# Wastewater compat по типу
WASTEWATER_MAP = {
    "submersible_sewage": ["domestic", "drainage", "industrial"],
    "submersible_sewage_premium": ["domestic", "drainage", "industrial"],
    "submersible_sewage_with_capture": ["domestic", "industrial"],
    "drainage_dirty": ["drainage", "industrial"],
    "horizontal_sewage": ["domestic", "drainage", "industrial"],
    "multistage_vertical": ["clean_water", "fire_protection"],
    "single_stage_inline": ["clean_water"],
    "console_monoblock": ["clean_water"],
    "fire_protection_high_head": ["fire_protection", "clean_water"],
    "deep_well": ["clean_water"],
    "centrifugal_horizontal": ["clean_water"],
    "submersible_clean_water": ["clean_water"],
    "multistage_csm": ["clean_water", "fire_protection"],
    "multistage_pi": ["clean_water", "fire_protection"],
    "high_pressure_multistage": ["clean_water", "fire_protection"],
    "fire_pump": ["fire_protection"],
}

# Сегмент по производителю
SEGMENT_MAP = {
    "istratech": "premium",
    "livgidromash": "standard",
    "yasnogorsk": "standard",
    "antey_kazprom": "standard",
    "kron": "premium",
    "onis": "standard",
    "cnp": "budget",
    "aikon": "budget",
    "leo": "budget",
    "shimge": "budget",
    "fancy": "budget",
    "sulzer_abs": "premium",
    "andritz": "premium",
    "tsurumi": "standard",
    "ebara": "standard",
    "homa": "premium",
    "caprari": "premium",
    "dab": "standard",
    "lowara": "standard",
    "calpeda": "standard",
    "wilo_mvi": "premium",
    "wilo_helix": "premium",
}

# Origin status по производителю
ORIGIN_MAP = {
    "istratech": ("domestic_manufacturer", "ИСТРАТЕХ Групп (преемник Grundfos Истра)"),
    "livgidromash": ("domestic_manufacturer", "АО \"ЛИВГИДРОМАШ\" / HMS"),
    "yasnogorsk": ("domestic_manufacturer", "Ясногорский завод машиностроения"),
    "antey_kazprom": ("domestic_manufacturer", "Antey/Казпром (ЦНС)"),
    "kron": ("domestic_manufacturer", "Кронштадт"),
    "onis": ("domestic_manufacturer", "ОНИКС-СПДТ"),
    "cnp": ("imported_china", "CNP через AC Russia / Аркада"),
    "aikon": ("imported_china", "AIKON (CNP суббренд)"),
    "sulzer_abs": ("parallel_import", "Sulzer ABS через Hycom/Кронштадт"),
    "andritz": ("parallel_import", "ANDRITZ через Sevit/BaumGroup"),
    "tsurumi": ("parallel_import", "Tsurumi через Хайтек"),
    "ebara": ("parallel_import", "Ebara через дилеров"),
    "homa": ("parallel_import", "HOMA через дилеров EU"),
    "caprari": ("parallel_import", "Caprari Italy"),
    "dab": ("parallel_import", "DAB Italy"),
    "lowara": ("parallel_import", "Lowara/Xylem"),
    "calpeda": ("parallel_import", "Calpeda Italy"),
}


def slugify(s: str) -> str:
    """RU/EN → ASCII slug для id."""
    s = s.lower().strip()
    # Транслит ключевых букв
    tr = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        " ": "-", "/": "-", "_": "-", "(": "", ")": "", ",": "", ".": "",
    })
    s = s.translate(tr)
    return re.sub(r"[^a-z0-9-]+", "-", s).strip("-")


def make_pump_record(mfg: dict, series: dict) -> dict | None:
    mfg_id = mfg["id"]
    series_code = series.get("code", "")
    series_type = series.get("type", "submersible_sewage")
    pump_type = TYPE_MAP.get(series_type, "submersible_sewage")
    impeller = IMPELLER_MAP.get(series_type, "channel")
    wastewater = WASTEWATER_MAP.get(series_type, ["domestic"])

    Q_min = series.get("Q_min")
    Q_max = series.get("Q_max")
    H_min = series.get("H_min")
    H_max = series.get("H_max")
    P_max = series.get("P_max")

    if any(v is None for v in [Q_min, Q_max, H_min, H_max]):
        return None

    pump_id = slugify(f"{mfg_id} {series_code} series")
    if not pump_id or len(pump_id) < 5:
        return None

    Q_BEP = (Q_min + Q_max) / 2
    H_BEP = (H_min + H_max) / 2

    segment = SEGMENT_MAP.get(mfg_id, "standard")
    origin_status, distributor = ORIGIN_MAP.get(
        mfg_id, ("parallel_import", "уточнить дилера")
    )

    free_pass = None
    if pump_type == "submersible_sewage":
        # Грубая оценка по particles_mm или 80 по умолчанию
        free_pass = series.get("particles_mm") or 80
    elif pump_type == "vertical_dry_well":
        free_pass = 80

    note_parts = [
        f"СЕРИЯ {series_code} (envelope-only, не одна модель)",
        f"Аналог: {series.get('analog_of', 'нет')}" if series.get("analog_of") else "",
        f"_note: {series.get('_note', '')}" if series.get("_note") else "",
        "Точные BEP/NPSHr/цена требуют верификации по конкретной модели серии.",
    ]
    note = "; ".join(p for p in note_parts if p)

    return {
        "id": pump_id,
        "brand": mfg.get("name", mfg_id),
        "model": f"{series_code} series (envelope)",
        "type": pump_type,
        "impeller": impeller,
        "free_passage_mm": free_pass,
        "envelope": {
            "Q_min_m3h": Q_min,
            "Q_max_m3h": Q_max,
            "H_min_m": H_min,
            "H_max_m": H_max,
            "Q_BEP_m3h": round(Q_BEP, 1),
            "H_BEP_m": round(H_BEP, 1),
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {
            "P_kW": P_max,
            "voltage_v": 380,
            "phase": 3,
            "ip_rating": "IP68" if pump_type == "submersible_sewage" else "IP55",
        },
        "discharge": {"DN_mm": None},
        "wastewater_compat": wastewater,
        "price_segment": segment,
        "available_ru": {
            "status": origin_status,
            "distributor": distributor,
        },
        "_engineer_flag": "needs_review_research",
        "_engineer_note": note,
        "_source": "manufacturers_full_list.json (research 2026-05-08)",
        "_added": "2026-05-08",
        "_is_envelope": True,
        "_minpromtorg_eligible": bool(mfg.get("minpromtorg_register")),
    }


def main(dry_run: bool = False):
    with open(RESEARCH_JSON, encoding="utf-8") as f:
        research = json.load(f)
    with open(PUMPS_JSON, encoding="utf-8") as f:
        pumps_data = json.load(f)

    existing_ids = {p["id"] for p in pumps_data["pumps"]}

    # Приоритетные производители
    priority = {
        "istratech", "livgidromash", "yasnogorsk", "antey_kazprom",
        "kron", "onis", "cnp", "aikon", "sulzer_abs", "tsurumi",
        "caprari", "dab",
    }

    new_pumps = []
    skipped = 0
    for mfg in research.get("manufacturers", []):
        if mfg.get("already_in_db", False):
            continue
        if mfg["id"] not in priority:
            continue
        for series in mfg.get("model_series_full", []):
            rec = make_pump_record(mfg, series)
            if rec is None:
                skipped += 1
                continue
            if rec["id"] in existing_ids:
                continue
            new_pumps.append(rec)
            existing_ids.add(rec["id"])

    print(f"Total new envelope records: {len(new_pumps)}")
    print(f"Skipped (no Q-H or duplicate): {skipped}")
    print()

    by_brand = {}
    for p in new_pumps:
        by_brand.setdefault(p["brand"], 0)
        by_brand[p["brand"]] += 1
    print("By brand:")
    for b, n in sorted(by_brand.items(), key=lambda x: -x[1]):
        print(f"  {b:30s} +{n}")

    if not dry_run:
        pumps_data["pumps"].extend(new_pumps)
        pumps_data["_updated"] = "2026-05-08"
        pumps_data["_engineer_note"] = (
            f"+{len(new_pumps)} envelope-серий из research 2026-05-08. "
            f"Всё помечено _engineer_flag=needs_review_research."
        )
        with open(PUMPS_JSON, "w", encoding="utf-8") as f:
            json.dump(pumps_data, f, ensure_ascii=False, indent=2)
        print()
        print(f"WROTE: {PUMPS_JSON}")
        print(f"Total pumps now: {len(pumps_data['pumps'])}")
    else:
        print()
        print("DRY RUN - no changes")


if __name__ == "__main__":
    import sys
    main(dry_run="--dry-run" in sys.argv)
