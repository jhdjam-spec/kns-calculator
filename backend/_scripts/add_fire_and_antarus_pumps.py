"""Добавляет:
- 10 пожарных многоступенчатых/центробежных насосов (KSB, Wilo, Grundfos, ИЛТ)
- 3 ANTARUS из эталонов Волновахи (MLV32-3, MST65-200) и Бондаревской ВЭС

Цель: закрыть calibration-пробелы Q>100 м³/ч fire_protection.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "02_dataset" / "pumps" / "pumps.json"

NEW_PUMPS = [
    # ──────────────────────────────────────────────────────────────────
    # ANTARUS MLV/MST из эталона Волноваха (СКЯ-23/24-НВК)
    # ──────────────────────────────────────────────────────────────────
    {
        "id": "antarus-2mlv32-3-gprs",
        "brand": "Antarus",
        "model": "2 MLV32-3/01/GPRS",
        "type": "booster_station",
        "impeller": "multi-channel",
        "free_passage_mm": 0,
        "envelope": {
            "Q_min_m3h": 10,
            "Q_max_m3h": 60,
            "H_min_m": 30,
            "H_max_m": 60,
            "Q_BEP_m3h": 34.2,
            "H_BEP_m": 45.0,
            "eta_BEP_pct": 65.0,
            "NPSHr_at_BEP_m": 3.5,
        },
        "power": {
            "P_kW": 7.5,
            "voltage_v": 380,
            "phase": 3,
            "ip_rating": "IP55",
        },
        "discharge": {"DN_mm": 100},
        "wastewater_compat": ["clean_water"],
        "price_segment": "mid",
        "available_ru": {"status": "official", "distributor": "Antarus"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "ВНС хозпит 2-насосная (1 раб + 1 рез) с GPRS-диспетчеризацией. "
            "Q=34.2 м³/ч H=45 м P=7.5 кВт. Эталон СКЯ-23/24-НВК (Волноваха спорткомплекс \"Ямал\"). "
            "Корпус подземный стеклопластик Ø3600×2200. Опции: ОПЦ DN100, СПД, обогрев ЭКСП 2."
        ),
        "_source": "СКЯ-23/24-НВК Волноваха ЖСК \"Гор-Строй\" 2026",
        "_added": "2026-05-09",
    },
    {
        "id": "antarus-2mst65-200-15-gprs",
        "brand": "Antarus",
        "model": "2 MST65-200/15/DS1-GPRS",
        "type": "fire_protection",
        "impeller": "channel",
        "envelope": {
            "Q_min_m3h": 30,
            "Q_max_m3h": 100,
            "H_min_m": 30,
            "H_max_m": 65,
            "Q_BEP_m3h": 61.3,
            "H_BEP_m": 45.2,
            "eta_BEP_pct": 70.0,
            "NPSHr_at_BEP_m": 3.8,
        },
        "power": {
            "P_kW": 15.0,
            "voltage_v": 380,
            "phase": 3,
            "ip_rating": "IP55",
        },
        "discharge": {"DN_mm": 65, "PN": 16},
        "wastewater_compat": ["clean_water"],
        "price_segment": "mid",
        "available_ru": {"status": "official", "distributor": "Antarus"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Установка пожаротушения 2-насосная с DS1 (датчик сухого хода) + GPRS. "
            "Q=61.3 м³/ч H=45.2 м P=15 кВт. Эталон СКЯ-23/24-НВК (Волноваха). "
            "Корпус Ø3200×4400 стеклопластик подземный. Опции: ОПЦ СХ12, СПД."
        ),
        "_source": "СКЯ-23/24-НВК Волноваха 2026",
        "_added": "2026-05-09",
    },
    # ──────────────────────────────────────────────────────────────────
    # KSB Multitec — пожарные многоступенчатые (для Q=100-200, H=20-100)
    # ──────────────────────────────────────────────────────────────────
    {
        "id": "ksb-multitec-65-3",
        "brand": "KSB",
        "model": "Multitec A 65/3-7.1",
        "type": "fire_protection",
        "impeller": "radial-multistage",
        "envelope": {
            "Q_min_m3h": 30,
            "Q_max_m3h": 110,
            "H_min_m": 30,
            "H_max_m": 90,
            "Q_BEP_m3h": 80,
            "H_BEP_m": 70,
            "eta_BEP_pct": 73.0,
            "NPSHr_at_BEP_m": 4.0,
        },
        "power": {
            "P_kW": 30,
            "voltage_v": 400,
            "phase": 3,
            "n_rpm": 2900,
            "ip_rating": "IP55",
            "insulation_class": "F",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 65, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Многоступенчатый горизонтальный для пожаротушения и водоснабжения. "
            "3 ступени, корпус EN-GJL-250 серый чугун. Соответствует EN 12845 для спринклерных систем."
        ),
        "_source": "KSB Multitec catalog 2024",
        "_added": "2026-05-09",
    },
    {
        "id": "ksb-multitec-100-4",
        "brand": "KSB",
        "model": "Multitec A 100/4-9",
        "type": "fire_protection",
        "impeller": "radial-multistage",
        "envelope": {
            "Q_min_m3h": 60,
            "Q_max_m3h": 200,
            "H_min_m": 25,
            "H_max_m": 75,
            "Q_BEP_m3h": 130,
            "H_BEP_m": 50,
            "eta_BEP_pct": 75.0,
            "NPSHr_at_BEP_m": 4.5,
        },
        "power": {
            "P_kW": 37,
            "voltage_v": 400,
            "phase": 3,
            "n_rpm": 2950,
            "ip_rating": "IP55",
            "insulation_class": "F",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 100, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "4-ступенчатый, для крупных пожарных насосных Q>100 м³/ч. "
            "Эталон Бондаревская ВЭС Q=133.2 H=30."
        ),
        "_source": "KSB Multitec catalog 2024",
        "_added": "2026-05-09",
    },
    {
        "id": "ksb-multitec-150-3",
        "brand": "KSB",
        "model": "Multitec V 150/3-9.2",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 80,
            "Q_max_m3h": 250,
            "H_min_m": 20,
            "H_max_m": 50,
            "Q_BEP_m3h": 160,
            "H_BEP_m": 35,
            "eta_BEP_pct": 76.0,
            "NPSHr_at_BEP_m": 5.0,
        },
        "power": {
            "P_kW": 22,
            "voltage_v": 400,
            "phase": 3,
            "n_rpm": 2950,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 150, "PN": 16},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": "Вертикальный многоступенчатый для пожарной насосной 1 рабочий + 1 резерв.",
        "_source": "KSB Multitec V catalog 2024",
        "_added": "2026-05-09",
    },
    # ──────────────────────────────────────────────────────────────────
    # Wilo Helix V — вертикальные многоступенчатые
    # ──────────────────────────────────────────────────────────────────
    {
        "id": "wilo-helix-v-1606",
        "brand": "Wilo",
        "model": "Helix V 1606",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 6,
            "Q_max_m3h": 24,
            "H_min_m": 20,
            "H_max_m": 80,
            "Q_BEP_m3h": 16,
            "H_BEP_m": 60,
            "eta_BEP_pct": 70.0,
            "NPSHr_at_BEP_m": 2.5,
        },
        "power": {
            "P_kW": 5.5,
            "voltage_v": 400,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 50, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": "Вертикальный многоступенчатый для повысительных и пожарных систем малых объектов.",
        "_source": "Wilo Helix V catalog 2024",
        "_added": "2026-05-09",
    },
    {
        "id": "wilo-helix-v-3606",
        "brand": "Wilo",
        "model": "Helix V 3606",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 18,
            "Q_max_m3h": 60,
            "H_min_m": 30,
            "H_max_m": 110,
            "Q_BEP_m3h": 36,
            "H_BEP_m": 80,
            "eta_BEP_pct": 73.0,
            "NPSHr_at_BEP_m": 3.0,
        },
        "power": {
            "P_kW": 15,
            "voltage_v": 400,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 65, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": "Вертикальный многоступенчатый, средняя мощность для МКД и общественных зданий.",
        "_source": "Wilo Helix V catalog 2024",
        "_added": "2026-05-09",
    },
    {
        "id": "wilo-helix-v-5208",
        "brand": "Wilo",
        "model": "Helix V 5208",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 25,
            "Q_max_m3h": 80,
            "H_min_m": 40,
            "H_max_m": 130,
            "Q_BEP_m3h": 52,
            "H_BEP_m": 90,
            "eta_BEP_pct": 75.0,
            "NPSHr_at_BEP_m": 3.5,
        },
        "power": {
            "P_kW": 22,
            "voltage_v": 400,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 65, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": "Для зданий повышенной этажности и пожарных насосных с большой высотой подъёма.",
        "_source": "Wilo Helix V catalog 2024",
        "_added": "2026-05-09",
    },
    # ──────────────────────────────────────────────────────────────────
    # Grundfos CR / преемница ИЛТ-VLE
    # ──────────────────────────────────────────────────────────────────
    {
        "id": "grundfos-cr-32-4-2",
        "brand": "Grundfos",
        "model": "CR 32-4-2",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 12,
            "Q_max_m3h": 40,
            "H_min_m": 30,
            "H_max_m": 70,
            "Q_BEP_m3h": 26,
            "H_BEP_m": 50,
            "eta_BEP_pct": 70.0,
            "NPSHr_at_BEP_m": 2.8,
        },
        "power": {
            "P_kW": 7.5,
            "voltage_v": 400,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 50, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import_or_replacement"},
        "_engineer_flag": "ok",
        "_engineer_note": "Российская преемница — ИСТРАТЕХ ИЛТ 32-4. Эталон Сочи Роза Хутор Grundfos SP 95-4.",
        "_source": "Grundfos CR catalog (parallel)",
        "_added": "2026-05-09",
    },
    {
        "id": "grundfos-cr-64-3-2",
        "brand": "Grundfos",
        "model": "CR 64-3-2",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 30,
            "Q_max_m3h": 90,
            "H_min_m": 25,
            "H_max_m": 80,
            "Q_BEP_m3h": 60,
            "H_BEP_m": 55,
            "eta_BEP_pct": 73.0,
            "NPSHr_at_BEP_m": 3.5,
        },
        "power": {
            "P_kW": 18.5,
            "voltage_v": 400,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 80, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import_or_replacement"},
        "_engineer_flag": "ok",
        "_engineer_note": "Преемница ИСТРАТЕХ ИЛТ 64-3. Для пожарных насосных Q>40 H<80.",
        "_source": "Grundfos CR catalog (parallel)",
        "_added": "2026-05-09",
    },
    {
        "id": "grundfos-cr-95-2-2",
        "brand": "Grundfos",
        "model": "CR 95-2-2",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 50,
            "Q_max_m3h": 130,
            "H_min_m": 20,
            "H_max_m": 60,
            "Q_BEP_m3h": 95,
            "H_BEP_m": 40,
            "eta_BEP_pct": 75.0,
            "NPSHr_at_BEP_m": 4.5,
        },
        "power": {
            "P_kW": 22,
            "voltage_v": 400,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 100, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "available_ru": {"status": "parallel_import_or_replacement"},
        "_engineer_flag": "ok",
        "_engineer_note": "Подходит для Бондаревской ВЭС Q=133 H=30 (диктующий пожарный расход 31 л/с).",
        "_source": "Grundfos CR catalog (parallel)",
        "_added": "2026-05-09",
    },
    # ──────────────────────────────────────────────────────────────────
    # ИСТРАТЕХ ИЛТ — российские преемники Grundfos CR
    # ──────────────────────────────────────────────────────────────────
    {
        "id": "istratech-ilt-95-2",
        "brand": "ИСТРАТЕХ",
        "model": "ИЛТ 95-2",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 50,
            "Q_max_m3h": 140,
            "H_min_m": 20,
            "H_max_m": 60,
            "Q_BEP_m3h": 100,
            "H_BEP_m": 40,
            "eta_BEP_pct": 73.0,
            "NPSHr_at_BEP_m": 4.5,
        },
        "power": {
            "P_kW": 22,
            "voltage_v": 380,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 100, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "mid",
        "available_ru": {"status": "official", "distributor": "ИСТРАТЕХ Групп"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Российская преемница Grundfos CR 95-2-2 (после ухода Grundfos из РФ). "
            "Подходит для пожарных насосных Q≈130-140 м³/ч H≈30-40 м. "
            "Эталон Бондаревской ВЭС Q=133 H=30."
        ),
        "_source": "ИСТРАТЕХ Групп каталог 2026 (research 2026-05-08)",
        "_added": "2026-05-09",
    },
    {
        "id": "istratech-ilt-64-3",
        "brand": "ИСТРАТЕХ",
        "model": "ИЛТ 64-3",
        "type": "fire_protection",
        "impeller": "radial-multistage-vertical",
        "envelope": {
            "Q_min_m3h": 30,
            "Q_max_m3h": 90,
            "H_min_m": 30,
            "H_max_m": 80,
            "Q_BEP_m3h": 60,
            "H_BEP_m": 55,
            "eta_BEP_pct": 71.0,
            "NPSHr_at_BEP_m": 3.5,
        },
        "power": {
            "P_kW": 18.5,
            "voltage_v": 380,
            "phase": 3,
            "ip_rating": "IP55",
            "motor_efficiency_class": "IE3",
        },
        "discharge": {"DN_mm": 80, "PN": 25},
        "wastewater_compat": ["clean_water"],
        "price_segment": "mid",
        "available_ru": {"status": "official", "distributor": "ИСТРАТЕХ Групп"},
        "_engineer_flag": "ok",
        "_engineer_note": "Преемница Grundfos CR 64-3. Для МКД и зданий повышенной этажности.",
        "_source": "ИСТРАТЕХ Групп каталог 2026",
        "_added": "2026-05-09",
    },
]


def main():
    if not DB.exists():
        print(f"[!] Не найден {DB}")
        return 1
    data = json.loads(DB.read_text(encoding="utf-8"))
    existing_ids = {p["id"] for p in data["pumps"]}
    added = 0
    skipped = 0
    for new_pump in NEW_PUMPS:
        if new_pump["id"] in existing_ids:
            print(f"[-] Пропуск (уже есть): {new_pump['id']}")
            skipped += 1
            continue
        data["pumps"].append(new_pump)
        added += 1
        print(f"[+] {new_pump['id']:40} ({new_pump['brand']} {new_pump['model']})")
    data["_updated"] = "2026-05-09"
    DB.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[+] Добавлено: {added}, пропущено: {skipped}")
    print(f"[+] Всего насосов в БД: {len(data['pumps'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
