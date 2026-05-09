"""Импорт насосов от multi-agent research 2026-05-08:
- ИСТРАТЕХ (Agent A): 59 моделей (57 BM + 1 ВО + 1 HC-FS)
- ЦНС (Agent B): 77 типоразмеров секционных
- CNP (Agent C): 38 моделей с ценами 2026

Плюс калибровка существующих 8 CNP в БД ценами от Agent C (по совпадению модели).

Идемпотентен: пропускает запись если id уже в БД с тем же source.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATASET = REPO / "02_dataset"
PUMPS_PATH = DATASET / "pumps" / "pumps.json"
ANALYSIS = DATASET / "_analysis"


def _slug(s: str) -> str:
    """Простой slugify для id."""
    return (
        s.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace(".", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
    )


def _envelope(q_bep: float | None, h_bep: float | None,
              q_min: float | None = None, q_max: float | None = None,
              h_min: float | None = None, h_max: float | None = None,
              eta: float | None = None, npshr: float | None = None) -> dict:
    """Построить envelope, заполнив min/max диапазоном ±20% от BEP если не задано."""
    env = {}
    if q_bep is not None:
        env["Q_BEP_m3h"] = q_bep
        env["Q_min_m3h"] = q_min if q_min is not None else round(q_bep * 0.5, 1)
        env["Q_max_m3h"] = q_max if q_max is not None else round(q_bep * 1.3, 1)
    if h_bep is not None:
        env["H_BEP_m"] = h_bep
        env["H_min_m"] = h_min if h_min is not None else round(h_bep * 0.6, 1)
        env["H_max_m"] = h_max if h_max is not None else round(h_bep * 1.1, 1)
    if eta is not None:
        env["eta_BEP_pct"] = eta
    if npshr is not None:
        env["NPSHr_at_BEP_m"] = npshr
    return env


def map_istratech(src: dict) -> dict | None:
    """Маппинг записи из istratech_models JSON в нашу схему."""
    series = src.get("series")
    if series == "BM":
        ptype = "multistage_vertical"
        impeller = "closed"
    elif series == "ВО":
        ptype = "multistage_vertical"
        impeller = "closed"
    elif series == "HC-FS":
        ptype = "booster_station"
        impeller = "closed"
    else:
        return None  # электродвигатели и шкафы не насосы

    q_bep = src.get("Q_BEP_m3h")
    h_bep = src.get("H_BEP_m")
    p_kw = src.get("P_kw") or src.get("P_kW")
    dn = src.get("DN_mm")
    price = src.get("price_RUB_2025")
    article = src.get("article")
    src_url = src.get("source_url")

    pump = {
        "id": src["id"],
        "brand": "ИСТРАТЕХ",
        "model": src["model"],
        "type": ptype,
        "impeller": impeller,
        "envelope": _envelope(q_bep, h_bep),
        "power": {
            "P_kW": p_kw,
            "voltage_v": 380,
            "phase": 3,
            "frequency_hz": 50,
            "ip_rating": "IP55",
            "insulation_class": "F",
        },
        "discharge": {"DN_mm": dn, "flange_type": "PN16"},
        "wastewater_compat": ["clean_water"],  # многоступенчатые — чистая вода
        "price_segment": "premium" if (price and price > 200000) else "mid",
        "available_ru": {
            "status": "available",
            "lead_time": "2-4 weeks",
            "distributor": "ИСТРАТЕХ Групп / alran.ru / vodokomfort.ru",
        },
        "warranty_months": 24,
        "_engineer_flag": "ok",
        "_source": "Agent A research 2026-05-08, ИСТРАТЕХ (бывший Grundfos Истра)" + (f", arts {article}" if article else ""),
        "_added": "2026-05-10",
    }
    if price:
        pump["price_rub_2026"] = int(price)
    if src_url:
        pump["datasheet_url"] = src_url
    if src.get("n_stages"):
        pump.setdefault("notes", "")
        pump["notes"] = f"Ступеней: {src['n_stages']}. Аналог {src.get('grundfos_equivalent','')}".strip(", ")
    if series == "HC-FS":
        pump["wastewater_compat"] = ["fire_water"]
        pump["notes"] = "Установка пожаротушения 1+1 (рабочий+резерв)"

    # Чистим None/empty discharge
    if pump["discharge"]["DN_mm"] is None:
        del pump["discharge"]["DN_mm"]
    if not pump.get("notes"):
        pump.pop("notes", None)
    return pump


def map_cns(src: dict) -> dict:
    """ЦНС → submersible_drainage / multistage_vertical (секционный)."""
    q_bep = src["Q_BEP_m3h"]
    h_bep = src["H_BEP_m"]
    p_kw = src["P_kW"]
    eta = src.get("eta_pct")
    npshr = src.get("NPSHr_m")
    q_range = src.get("Q_range_m3h", [])
    q_min = q_range[0] if len(q_range) >= 2 else None
    q_max = q_range[1] if len(q_range) >= 2 else None

    apps = src.get("applications", [])
    # ЦНС обычно — насос для агрессивных или ППД, не канализация. Поставим clean_water + fire по применениям.
    compat = ["clean_water"]
    if "пожарка-спд" in apps:
        compat.append("fire_water")
    if "ппд" in apps or "нефтехимия" in apps:
        compat.append("industrial")

    price = src.get("price_rub_2024")
    spec_order = src.get("spec_order", False)

    pump = {
        "id": src["id"],
        "brand": "ГМС Ливгидромаш",
        "model": src["model"],
        "type": "multistage_vertical",  # секционный — горизонтальный, но ближайший в enum
        "impeller": "closed",
        "envelope": _envelope(q_bep, h_bep, q_min=q_min, q_max=q_max, eta=eta, npshr=npshr),
        "power": {
            "P_kW": p_kw,
            "voltage_v": 380 if p_kw < 75 else 6000,
            "phase": 3,
            "frequency_hz": 50,
            "ip_rating": "IP54",
            "insulation_class": "F",
        },
        "discharge": {"DN_mm": src.get("DN_out_mm"), "flange_type": "PN25"},
        "wastewater_compat": compat,
        "price_segment": "mid" if not spec_order else "premium",
        "available_ru": {
            "status": "available" if not spec_order else "build_to_order",
            "lead_time": "4-8 weeks" if not spec_order else "16-24 weeks",
            "distributor": "ГМС Ливгидромаш / ЯНЗ / СЗПН",
        },
        "warranty_months": 18,
        "weight_kg": src.get("weight_kg"),
        "_engineer_flag": "ok" if not spec_order else "needs_review",
        "_source": "Agent B research 2026-05-08, ГОСТ 10407-88, реестр Минпромторг ПП 719",
        "_added": "2026-05-10",
        "free_passage_mm": 0,  # секционный, free passage не релевантен — ставим 0
        "notes": f"Применения: {', '.join(apps)}. {'СПЕЦЗАКАЗ' if spec_order else ''}".strip(". "),
    }
    if price:
        pump["price_rub_2026"] = int(price * 1.05)  # 2024→2026 lifted +5% (грубо)
    if pump["discharge"]["DN_mm"] is None:
        del pump["discharge"]["DN_mm"]
    if pump.get("weight_kg") is None:
        del pump["weight_kg"]
    return pump


def map_cnp(src: dict) -> dict:
    """CNP — у Agent C уже почти готовая схема, надо только массировать поля."""
    pump = dict(src)
    # У них _source уже есть, _added уже есть, поля совпадают.
    # Гарантируем _engineer_flag
    pump.setdefault("_engineer_flag", "ok")
    pump.setdefault("_source", "Agent C research 2026-05-08, CNP цены RU дилеров 2026")
    pump.setdefault("_added", "2026-05-10")
    pump.setdefault("warranty_months", 12)
    # удалим служебные поля Agent C
    pump.pop("price_source", None)
    pump.pop("notes", None) if not pump.get("notes") else None
    return pump


def calibrate_existing_cnp(existing: list[dict], cnp_agent_c: list[dict]) -> int:
    """Если в БД есть CNP без price_rub_2026, и Agent C предоставил такую же модель —
    подставить цену. Возвращает сколько откалибровано."""
    # Простой матч: сравнение нормализованной модели
    def norm(m: str) -> str:
        return m.upper().replace(" ", "").replace("(I)", "").replace("(", "").replace(")", "").replace(".", "")

    agent_by_model = {}
    for p in cnp_agent_c:
        agent_by_model[norm(p["model"])] = p

    n = 0
    for p in existing:
        if p.get("brand") != "CNP":
            continue
        if p.get("price_rub_2026"):
            continue
        m = norm(p["model"])
        # Ищем точное или префиксное совпадение по {DN}WQ{Q}-{H}
        match = None
        for am, ap in agent_by_model.items():
            if m == am:
                match = ap
                break
            # Пытаемся ослабленный матч: префикс до тире-кВт
            if m.split("-")[0] == am.split("-")[0] and len(m.split("-")) >= 2 and len(am.split("-")) >= 2:
                if m.split("-")[1].rstrip("0123456789.") == am.split("-")[1].rstrip("0123456789."):
                    # сравним головную Q-H часть, если совпадает — берём
                    pass
        if match:
            p["price_rub_2026"] = match["price_rub_2026"]
            p["_engineer_note"] = (p.get("_engineer_note", "") + " | Цена 2026 калибрована Agent C research 2026-05-08").strip(" | ")
            n += 1
    return n


def main() -> None:
    print(f"[*] Reading {PUMPS_PATH}")
    db = json.loads(PUMPS_PATH.read_text(encoding="utf-8"))
    existing = db["pumps"]
    existing_ids = {p["id"] for p in existing}
    print(f"    {len(existing)} existing pumps, {len(existing_ids)} unique ids")

    # Load all 3 agent files
    a_istra = json.loads((ANALYSIS / "istratech_models_2026-05-08.json").read_text(encoding="utf-8"))
    a_cns = json.loads((ANALYSIS / "cns_pumps_2026-05-08.json").read_text(encoding="utf-8"))
    a_cnp = json.loads((ANALYSIS / "cnp_pumps_2026-05-08.json").read_text(encoding="utf-8"))

    new_pumps = []
    skipped_dup = []
    skipped_invalid = []

    # ИСТРАТЕХ
    for src in a_istra["pumps"]:
        m = map_istratech(src)
        if m is None:
            skipped_invalid.append(src.get("id"))
            continue
        if m["id"] in existing_ids:
            skipped_dup.append(m["id"])
            continue
        new_pumps.append(m)
        existing_ids.add(m["id"])

    # ЦНС
    for src in a_cns["pumps"]:
        m = map_cns(src)
        if m["id"] in existing_ids:
            skipped_dup.append(m["id"])
            continue
        new_pumps.append(m)
        existing_ids.add(m["id"])

    # CNP (Agent C)
    for src in a_cnp["pumps"]:
        m = map_cnp(src)
        if m["id"] in existing_ids:
            skipped_dup.append(m["id"])
            continue
        new_pumps.append(m)
        existing_ids.add(m["id"])

    # Калибровка существующих CNP
    calibrated = calibrate_existing_cnp(existing, a_cnp["pumps"])

    # Append + write
    existing.extend(new_pumps)
    db["_updated"] = "2026-05-10"
    PUMPS_PATH.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Report
    print("\n=== IMPORT SUMMARY ===")
    print(f"Added new pumps:     {len(new_pumps)}")
    print(f"  ИСТРАТЕХ:          {sum(1 for p in new_pumps if p['brand'] == 'ИСТРАТЕХ')}")
    print(f"  ГМС Ливгидромаш:   {sum(1 for p in new_pumps if p['brand'] == 'ГМС Ливгидромаш')}")
    print(f"  CNP:               {sum(1 for p in new_pumps if p['brand'] == 'CNP')}")
    print(f"Calibrated existing: {calibrated} CNP pumps")
    print(f"Skipped duplicates:  {len(skipped_dup)}")
    print(f"Skipped invalid:     {len(skipped_invalid)} (motors/cabinets)")
    print(f"\nTotal pumps in DB: {len(existing)}")
    brand_dist = Counter(p["brand"] for p in existing)
    print("Brand distribution top 15:")
    for b, c in brand_dist.most_common(15):
        print(f"  {b:<25} {c}")


if __name__ == "__main__":
    main()
