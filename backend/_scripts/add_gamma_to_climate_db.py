"""Phase 18.2: добавить поле gamma (показатель степени СП 32 §6.2.4) в climate БД.

Маппинг по табл. Б.4 СП 32:
- γ=1.82 — Юг ЕТР, Кавказ, Крым, Дальний Восток (приморский климат)
- γ=1.54 — Центр ЕТР, Поволжье, Урал, Сибирь, Северо-Запад

Запускать один раз: python backend/_scripts/add_gamma_to_climate_db.py
"""
from __future__ import annotations

import json
from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "02_dataset"
    / "storm_research_raw"
    / "02_climate_db_36_cities.json"
)

# Города с γ=1.82 (южные/приморские зоны по СП 32 табл. Б.4)
GAMMA_182_CITIES = {
    "Краснодар",
    "Сочи",
    "Анапа",
    "Геленджик",
    "Новороссийск",
    "Махачкала",
    "Ставрополь",
    "Ростов-на-Дону",
    "Симферополь",
    "Ялта",
    "Севастополь",
    "Керчь",
    "Евпатория",
    "Грозный",
    "Хабаровск",
    "Владивосток",
}

GAMMA_DEFAULT = 1.54


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        return 1

    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    updated = 0
    skipped = 0

    for city in db["cities"]:
        name = city["name"]
        if "gamma" in city:
            skipped += 1
            continue
        gamma = 1.82 if name in GAMMA_182_CITIES else GAMMA_DEFAULT
        city["gamma"] = gamma
        city["gamma_source"] = "SP_32_table_B4"
        updated += 1

    # Обновим schema_version и notes
    db["schema_version"] = "1.1"
    db["notes"] = (
        db.get("notes", "")
        + " Phase 18.2: добавлено поле gamma (СП 32 §6.2.4 табл. Б.4): "
        "1.82 для юга/Дальнего Востока, 1.54 для центра/Сибири/севера."
    )

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"Updated: {updated} cities, skipped (already had gamma): {skipped}")
    print(f"Cities with gamma=1.82: {sorted(GAMMA_182_CITIES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
