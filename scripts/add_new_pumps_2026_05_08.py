"""Добавить 11 новых моделей насосов в pumps.json после массового аудита 2026-05-08.

Источник данных: memory/reference_kns_zip_2026-05-08_audit.md
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "02_dataset" / "pumps" / "pumps.json"


def main() -> int:
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    existing_ids = {p["id"] for p in db["pumps"]}

    new_pumps: list[dict] = []

    # 1. Vandjord SG.50.75.2.5.0D — cutter, gap-filler для Q=5-28 H=20-48
    new_pumps.append({
        "id": "vandjord-sg-50-75-25-0d",
        "brand": "Vandjord",
        "model": "SG.50.75.2.5.0D",
        "type": "submersible_sewage",
        "impeller": "cutter",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 0.5,
            "Q_max_m3h": 28,
            "H_min_m": 30,
            "H_max_m": 48,
            "Q_BEP_m3h": 15,
            "H_BEP_m": 44,
            "eta_BEP_pct": 30,
            "NPSHr_at_BEP_m": None,
        },
        "power": {
            "P_kW": 7.5,
            "P_input_P1_kW": 9.4,
            "voltage_v": 380,
            "phase": 3,
            "current_A": 15.7,
            "n_rpm": 2850,
            "ip_rating": "IP68",
            "insulation_class": "F",
            "motor_protection": "PTC_built_in",
        },
        "discharge": {"DN_mm": 50, "PN": 10},
        "weight_kg": 94,
        "max_starts_per_hour": 20,
        "max_submersion_m": 10,
        "wastewater_compat": ["domestic", "drainage", "industrial"],
        "price_segment": "mid",
        "price_rub_2026": None,
        "available_ru": {"status": "official", "distributor": "Vandjord Group Moscow"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Cutter с режущим колесом из высокохромистого сплава, "
            "двойное торцевое уплотнение SiC/SiC. Закрывает gap БД "
            "для Q=5-28 / H=30-48. VJ Select подбор."
        ),
        "_source": "Vandjord ТКП 20260216 (Q=9 H=45)",
        "_added": "2026-05-08",
    })

    # 2. KAIQUAN 50WQS202-3 — Мысхако МФИ
    new_pumps.append({
        "id": "kaiquan-50wqs202-3",
        "brand": "KAIQUAN",
        "model": "50WQS202-3",
        "type": "submersible_sewage",
        "impeller": "single-channel",
        "free_passage_mm": 50,
        "envelope": {
            "Q_min_m3h": 5,
            "Q_max_m3h": 30,
            "H_min_m": 6,
            "H_max_m": 22,
            "Q_BEP_m3h": 21.2,
            "H_BEP_m": 15,
            "eta_BEP_pct": 46.4,
            "NPSHr_at_BEP_m": None,
        },
        "power": {
            "P_kW": 3.0,
            "P_input_kW": 2.34,
            "voltage_v": 380,
            "phase": 3,
            "current_A": 6.2,
            "ip_rating": "IP68",
        },
        "discharge": {"DN_mm": 50},
        "wastewater_compat": ["domestic", "drainage"],
        "price_segment": "budget",
        "price_rub_2026": None,
        "available_ru": {"status": "official"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Эталон ARTWIND РД АВ.1382 Мысхако/Новороссийск — "
            "установлен в готовой КНС BloPlast PV-1590/3400 (Блорэй). "
            "Калибровочный кейс Q=21,2 H=15 для бытовой Q≈40 м³/сут."
        ),
        "_source": "ARTWIND РД АВ.1382.08.23-М-НК",
        "_added": "2026-05-08",
    })

    # 3. ANTARUS 2-150-30-150-22-TB
    new_pumps.append({
        "id": "antarus-2-150-30-150-22-tb",
        "brand": "Antarus",
        "model": "2-150-30-150-22-TB-10M",
        "type": "submersible_sewage",
        "impeller": "vortex",
        "free_passage_mm": 80,
        "envelope": {
            "Q_min_m3h": 100,
            "Q_max_m3h": 500,
            "H_min_m": 5,
            "H_max_m": 30,
            "Q_BEP_m3h": 352,
            "H_BEP_m": 22,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {
            "P_kW": 22,
            "voltage_v": 380,
            "phase": 3,
            "n_rpm": 1450,
            "cos_phi": 0.78,
            "ip_rating": "IP68",
        },
        "discharge": {"DN_mm": 150},
        "wastewater_compat": ["drainage", "industrial"],
        "price_segment": "mid",
        "price_rub_2026": None,
        "available_ru": {"status": "official_RU"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "TB-исполнение (увеличенный проход), 10M кабель. "
            "Эталон Стандартпарк/Элита Краснодар (КП №39053 27.09.2024) — "
            "ливневая КНС Q=352 H=22 в Ø3200×4800 ст.AISI304+полимер, 2+1 рез. "
            "Расценка комплекта 10 192 942 ₽."
        ),
        "_source": "КП №39053 27.09.2024, Краснодар ул.2-я Линия",
        "_added": "2026-05-08",
    })

    # 4. KAIQUAN 100WQ60-9-3-EC — ЛОС Свирь-15
    new_pumps.append({
        "id": "kaiquan-100wq60-9-3-ec",
        "brand": "KAIQUAN",
        "model": "100WQ60-9-3-EC",
        "type": "submersible_sewage",
        "impeller": "vortex",
        "free_passage_mm": 100,
        "envelope": {
            "Q_min_m3h": 20,
            "Q_max_m3h": 90,
            "H_min_m": 4,
            "H_max_m": 12,
            "Q_BEP_m3h": 60,
            "H_BEP_m": 9,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 3.0, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 100},
        "wastewater_compat": ["drainage", "domestic"],
        "price_segment": "budget",
        "price_rub_2026": None,
        "available_ru": {"status": "official"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Эталон ЛОС Свирь-15 (СЗ-РФ): 4 насоса в ливневой КНС Ø2300×2000 "
            "для Q=15 л/с (54 м³/ч). Малый ливневый. EC = epoxy coated."
        ),
        "_source": "Проект ЛОС Свирь-15 263-НВК",
        "_added": "2026-05-08",
    })

    # 5. CNP 50WQ12-10-0.75 — китайский ультрабюджет
    new_pumps.append({
        "id": "cnp-50wq12-10-075",
        "brand": "CNP",
        "model": "50WQ12-10-0.75",
        "type": "submersible_sewage",
        "impeller": "vortex",
        "free_passage_mm": 50,
        "envelope": {
            "Q_min_m3h": 3,
            "Q_max_m3h": 20,
            "H_min_m": 5,
            "H_max_m": 14,
            "Q_BEP_m3h": 12,
            "H_BEP_m": 10,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 0.75, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 50},
        "wastewater_compat": ["domestic", "drainage"],
        "price_segment": "budget",
        "price_rub_2026": None,
        "available_ru": {"status": "official", "distributor": "CNP / Nanfang Pump Industry"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Эталон ПВТ Краснодар КНС-1: малая бытовая Q≤12 H=10. "
            "CNP = Nanfang Pump Industry."
        ),
        "_source": "ТКП ПВТ 822005890-ОК-НВК-6.4",
        "_added": "2026-05-08",
    })

    # 6. CNP 250WQ600-10-22 — крупный ливневый
    new_pumps.append({
        "id": "cnp-250wq600-10-22",
        "brand": "CNP",
        "model": "250WQ600-10-22",
        "type": "submersible_sewage",
        "impeller": "vortex",
        "free_passage_mm": 250,
        "envelope": {
            "Q_min_m3h": 200,
            "Q_max_m3h": 800,
            "H_min_m": 4,
            "H_max_m": 14,
            "Q_BEP_m3h": 600,
            "H_BEP_m": 10,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 22, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 250},
        "wastewater_compat": ["drainage", "industrial"],
        "price_segment": "mid",
        "price_rub_2026": None,
        "available_ru": {"status": "official"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Эталон ПВТ Краснодар КНС-2: Q=600 м³/ч (255 л/с) H=10. "
            "Установлено в Ø4000×6540 ПВТ-корпусе. Крупный ливневый."
        ),
        "_source": "ТКП ПВТ 822005890-ОК-НВК-6.4",
        "_added": "2026-05-08",
    })

    # 7. CNP CHL 8-50 — vertical multistage booster (редкий класс Q=7 H=40)
    new_pumps.append({
        "id": "cnp-chl-8-50",
        "brand": "CNP",
        "model": "CHL 8-50",
        "type": "booster_station",
        "impeller": "multi-stage",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 2,
            "Q_max_m3h": 12,
            "H_min_m": 25,
            "H_max_m": 55,
            "Q_BEP_m3h": 7.16,
            "H_BEP_m": 40,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {
            "P_kW": 2.2,
            "voltage_v": 380,
            "phase": 3,
            "n_rpm": 2900,
            "ip_rating": "IP55",
        },
        "discharge": {"DN_mm": 32, "PN": 16},
        "wastewater_compat": ["clean_water"],
        "price_segment": "mid",
        "price_rub_2026": None,
        "available_ru": {"status": "official"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Вертикальный многоступенчатый — редкий класс для пром. ливневой/"
            "хвостовой подачи Q=7 H=40. Эталон РД №12-НВК (2 насоса 1+1 + резервуар V=20 м³)."
        ),
        "_source": "РД №12-НВК",
        "_added": "2026-05-08",
    })

    # 8. Pedrollo F 65/200AR — крупный консольный для I-кат жилья
    new_pumps.append({
        "id": "pedrollo-f-65-200ar",
        "brand": "Pedrollo",
        "model": "F 65/200AR",
        "type": "booster_station",
        "impeller": "single_stage_centrifugal",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 50,
            "Q_max_m3h": 250,
            "H_min_m": 30,
            "H_max_m": 70,
            "Q_BEP_m3h": 156,
            "H_BEP_m": 57,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": None, "voltage_v": 380, "phase": 3, "ip_rating": "IP55"},
        "discharge": {"DN_mm": 65, "PN": 16},
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "price_rub_2026": None,
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "calibration_pending",
        "_engineer_note": (
            "Крупный консольный одноступенчатый для повысительных I-категории "
            "(22-этажный жилой Краснодар). Q=156 H=57. Закрывает gap премиум booster."
        ),
        "_source": "Паспорт ПВТ Краснодар (16-20-НВК) + 22-эт.",
        "_added": "2026-05-08",
    })

    # 9. Wilo BL 80/200-30/2 — пожарный с сухим ротором
    new_pumps.append({
        "id": "wilo-bl-80-200-30-2",
        "brand": "Wilo",
        "model": "BL 80/200-30/2",
        "type": "fire_protection",
        "impeller": "channel",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 50,
            "Q_max_m3h": 200,
            "H_min_m": 30,
            "H_max_m": 56,
            "Q_BEP_m3h": 133.8,
            "H_BEP_m": 48.07,
            "eta_BEP_pct": 73.89,
            "NPSHr_at_BEP_m": 3.49,
        },
        "power": {
            "P_kW": 30,
            "P_shaft_kW": 23.76,
            "voltage_v": 400,
            "phase": 3,
            "current_A": 52,
            "n_rpm": 2955,
            "n_pole": 2,
            "cos_phi": 0.9,
            "ip_rating": "IP55",
            "insulation_class": "F",
            "motor_efficiency_class": "IE2",
            "motor_protection": "PTC_integrated",
        },
        "discharge": {"DN_mm": 80, "PN": 16},
        "weight_kg": 268,
        "wastewater_compat": ["clean_water"],
        "price_segment": "premium",
        "price_rub_2026": None,
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Насос с сухим ротором блочный, 2-полюсный. Корпус EN-GJL-250 + катафорез, "
            "колесо EN-GJL-200, уплотнение AQ1EGG (SiC/SiC). "
            "Эталон BloPlast SPT-2900/5700 (Блорэй), 1+1 для Q=174 H=43."
        ),
        "_source": "Wilo Spaix datasheet 2022.09.21 + BloPlast SPT-2900/5700",
        "_added": "2026-05-08",
    })

    # 10. WILO Rexa PRO C08DA-415 — бытовая Q=10 H=15
    new_pumps.append({
        "id": "wilo-rexa-pro-c08da-415",
        "brand": "Wilo",
        "model": "Rexa PRO C08DA-415/EAD1X2-T0025",
        "type": "submersible_sewage",
        "impeller": "channel",
        "free_passage_mm": 80,
        "envelope": {
            "Q_min_m3h": 5,
            "Q_max_m3h": 30,
            "H_min_m": 8,
            "H_max_m": 22,
            "Q_BEP_m3h": 10,
            "H_BEP_m": 15,
            "eta_BEP_pct": None,
            "NPSHr_at_BEP_m": None,
        },
        "power": {"P_kW": 3.2, "voltage_v": 380, "phase": 3, "ip_rating": "IP68"},
        "discharge": {"DN_mm": 80},
        "wastewater_compat": ["domestic", "drainage"],
        "price_segment": "premium",
        "price_rub_2026": None,
        "available_ru": {"status": "parallel_import"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "Бытовая мини-КНС, эталон 18-007-ТХ Крым (КОС хоз-быт) — 1+1 рез. "
            "Q=10 H=15 в КНС-3 Ø2200."
        ),
        "_source": "18-007-ТХ Крым (экспертиза 9102031438)",
        "_added": "2026-05-08",
    })

    # 11. Grundfos SEG.40.09.2.50B — полный паспорт
    new_pumps.append({
        "id": "grundfos-seg-40-09-2-50b",
        "brand": "Grundfos",
        "model": "SEG.40.09.2.50B",
        "type": "submersible_sewage",
        "impeller": "cutter",
        "free_passage_mm": None,
        "envelope": {
            "Q_min_m3h": 1,
            "Q_max_m3h": 16,
            "H_min_m": 3,
            "H_max_m": 12,
            "Q_BEP_m3h": 7.85,
            "H_BEP_m": 8.7,
            "eta_BEP_pct": 71,
            "NPSHr_at_BEP_m": None,
        },
        "power": {
            "P_kW": 0.9,
            "P_input_P1_kW": 1.3,
            "voltage_v": 400,
            "phase": 3,
            "current_A": 3.0,
            "current_start_A": 21,
            "n_rpm": 2860,
            "cos_phi": 0.72,
            "ip_rating": "IP68",
            "insulation_class": "F",
            "frequency_hz": 50,
        },
        "discharge": {"DN_mm": 40, "PN": 10},
        "weight_kg": None,
        "wastewater_compat": ["domestic", "drainage"],
        "price_segment": "premium",
        "price_rub_2026": None,
        "available_ru": {"status": "parallel_import", "distributor": "via Турция/Казахстан"},
        "_engineer_flag": "ok",
        "_engineer_note": (
            "AUTOADAPT — самонастраивающаяся характеристика. SmartTrim. "
            "Уплотнение SiC/SiC + LIPSEAL. Корпус EN-GJL-200, импеллер PA-I. "
            "ISO9906:2012 grade 3B2. Артикул 96075897. Габариты 374×118×216×546 мм."
        ),
        "_source": "Grundfos SEG4009250B полный паспорт (артикул 96075897)",
        "_added": "2026-05-08",
    })

    # Add only those NOT already in DB
    added = 0
    skipped = 0
    for p in new_pumps:
        if p["id"] in existing_ids:
            print(f"SKIP (exists): {p['id']}")
            skipped += 1
            continue
        db["pumps"].append(p)
        existing_ids.add(p["id"])
        added += 1
        print(f"ADD: {p['id']} -- {p['brand']} {p['model']}")

    # Update version metadata
    db["_updated"] = "2026-05-08"
    db["_version"] = "0.2"
    notes = db.get("_engineer_note", "")
    suffix = (
        "\n[2026-05-08] +11 new models from kns.zip mass audit: "
        "Vandjord SG cutter (Q=15 H=44), KAIQUAN 50WQS202-3 (Мысхако), "
        "ANTARUS 2-150-30-150-22-TB (Q=352 H=22), KAIQUAN 100WQ60-9-3, "
        "CNP 50WQ12 + 250WQ600 + CHL 8-50, Pedrollo F 65/200AR, "
        "Wilo BL 80/200-30 + Rexa PRO C08DA, Grundfos SEG.40.09 (full datasheet)."
    )
    db["_engineer_note"] = (notes + suffix).strip()

    # Write back
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("---")
    print(f"Added: {added} | Skipped: {skipped}")
    print(f"Total in DB now: {len(db['pumps'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
