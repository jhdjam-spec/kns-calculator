"""Конвертация RawPumpRecord → формат pumps.json.

Формат на выходе соответствует 02_dataset/pumps/schema.json.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from pump_calculator.etl.curve_fitter import fit_qh_curve
from pump_calculator.etl.schemas import RawPumpRecord


def _make_pump_id(brand: str, model: str) -> str:
    """Сгенерировать стабильный id из brand+model.

    Примеры:
        ("KAIQUAN", "50WQ/S 20-22-3") → "kaiquan-50wqs-20-22-3"
        ("Wilo", "Wilo-Rexa PRO V05") → "wilo-rexa-pro-v05"
    """
    raw = f"{brand}-{model}".lower()
    # Оставляем только буквы/цифры/дефис, всё остальное → дефис
    raw = re.sub(r"[^\w\-]+", "-", raw)
    raw = re.sub(r"-+", "-", raw)
    return raw.strip("-")


def import_raw_pump(raw: RawPumpRecord) -> dict[str, Any]:
    """Сконвертировать RawPumpRecord в запись формата pumps.json.

    Шаги:
        1. Аппроксимация Q-H/η кривой → envelope (Q_min/max, H_min/max, BEP)
        2. Сборка структуры строго по 02_dataset/pumps/schema.json
        3. Валидация (jsonschema здесь не подключаем, но соблюдаем поля)
    """
    curve = fit_qh_curve(raw.qh_curve)

    today = date.today().isoformat()
    pump_id = _make_pump_id(raw.brand, raw.model)

    return {
        "id": pump_id,
        "brand": raw.brand,
        "model": raw.model,
        "type": raw.type,
        "impeller": raw.impeller,
        "free_passage_mm": raw.free_passage_mm,

        "envelope": {
            "Q_min_m3h": round(curve.Q_min_m3h, 2),
            "Q_max_m3h": round(curve.Q_max_m3h, 2),
            "H_min_m": round(curve.H_min_m, 2),
            "H_max_m": round(curve.H_max_m, 2),
            "Q_BEP_m3h": round(curve.Q_BEP_m3h, 2) if curve.Q_BEP_m3h is not None else None,
            "H_BEP_m": round(curve.H_BEP_m, 2) if curve.H_BEP_m is not None else None,
            "eta_BEP_pct": round(curve.eta_BEP_pct, 1) if curve.eta_BEP_pct is not None else None,
            "NPSHr_at_BEP_m": round(curve.NPSHr_at_BEP_m, 2) if curve.NPSHr_at_BEP_m is not None else None,
        },

        "qh_curve": [
            {
                "Q_m3h": p.Q_m3h,
                "H_m": p.H_m,
                **({"eta_pct": p.eta_pct} if p.eta_pct is not None else {}),
                **({"P_kW": p.P_kW} if p.P_kW is not None else {}),
                **({"NPSHr_m": p.NPSHr_m} if p.NPSHr_m is not None else {}),
            }
            for p in raw.qh_curve
        ],

        "power": {
            "P_kW": raw.P_kW,
            "voltage_v": raw.voltage_v,
            "phase": raw.phase,
            "ip_rating": raw.ip_rating,
            "ex_rating": raw.ex_rating,
        },

        "discharge": {"DN_mm": raw.discharge_DN_mm} if raw.discharge_DN_mm else None,

        "wastewater_compat": raw.wastewater_compat,
        "price_segment": raw.price_segment,

        "available_ru": {
            "status": raw.available_ru_status,
            "distributor": raw.distributor,
            "lead_time": raw.lead_time_ru,
        },

        "warranty_months": raw.warranty_months,
        "datasheet_url": raw.datasheet_url,
        "image_url": raw.image_url,
        "notes": raw.notes,

        "_engineer_flag": "needs_review",  # Все импортированные → по умолчанию на ревью
        "_engineer_note": "Импортирован через ETL — проверить корректность аппроксимации Q-H и КПД до production-использования.",
        "_source": raw.source,
        "_added": today,
        "_updated": today,
    }


def import_raw_pumps_from_json(input_path: Path | str) -> list[dict[str, Any]]:
    """Прочитать список raw-записей из JSON, импортировать всё.

    Файл-входу — список объектов формата RawPumpRecord.
    """
    path = Path(input_path)
    with open(path, encoding="utf-8") as f:
        raw_list = json.load(f)

    if not isinstance(raw_list, list):
        raise ValueError(f"Expected JSON array, got {type(raw_list).__name__}")

    results = []
    for i, raw_dict in enumerate(raw_list):
        try:
            raw = RawPumpRecord.model_validate(raw_dict)
            results.append(import_raw_pump(raw))
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Record #{i}: {e}") from e
    return results


def merge_into_pumps_json(
    new_pumps: list[dict[str, Any]],
    pumps_json_path: Path | str,
    *,
    overwrite: bool = False,
) -> tuple[int, int]:
    """Слить новые записи в существующий pumps.json.

    Args:
        new_pumps: результат import_raw_pumps_from_json
        pumps_json_path: путь к 02_dataset/pumps/pumps.json
        overwrite: если True — перезаписывать существующие id; иначе — пропускать

    Returns:
        (added, skipped) — сколько добавлено и сколько пропущено как дубли
    """
    path = Path(pumps_json_path)
    with open(path, encoding="utf-8") as f:
        existing = json.load(f)

    existing_pumps = existing.get("pumps", [])
    existing_ids = {p["id"]: i for i, p in enumerate(existing_pumps)}

    added = 0
    skipped = 0
    for new_p in new_pumps:
        new_id = new_p["id"]
        if new_id in existing_ids:
            if overwrite:
                existing_pumps[existing_ids[new_id]] = new_p
                added += 1
            else:
                skipped += 1
        else:
            existing_pumps.append(new_p)
            added += 1

    existing["pumps"] = existing_pumps
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return added, skipped
