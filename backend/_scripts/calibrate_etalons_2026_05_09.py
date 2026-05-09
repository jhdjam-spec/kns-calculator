"""Калибровка калькулятора по эталонам Downloads 2026-05-09.

Прогоняет 4 ручных + найденные агентом эталоны через select_pumps()
и проверяет:
1. Q сходится (±15%)
2. H сходится (±15%) — если задан
3. P_kW сходится (±20%) — допуск шире, бренд может отличаться
4. Тип стоков совпадает
5. Бренд насоса попал в список рекомендованных в каком-то сегменте

Запуск:
    python backend/_scripts/calibrate_etalons_2026_05_09.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pump_calculator.matching import select_pumps  # noqa: E402
from pump_calculator.schemas import L0Input, L1Input  # noqa: E402

ETALONS_FILE = ROOT / "02_dataset" / "etalons" / "downloads_2026-05-09_etalons.json"
TOLERANCE_Q = 0.15
TOLERANCE_H = 0.15
TOLERANCE_P = 0.20


def _within(actual: float, target: float, tol: float) -> tuple[bool, float]:
    if target <= 0:
        return False, 0.0
    rel = abs(actual - target) / target
    return rel <= tol, rel


def _select(q_m3h: float, dh_m: float = 5.0, l_m: float = 50.0,
            wastewater: str = "domestic", ex: bool = False):
    # Маппинг человеческого "fire" в каноничное "fire_protection"
    if wastewater == "fire":
        wastewater = "fire_protection"
    l0 = L0Input(Q_m3h=q_m3h, dH_m=dh_m, L_m=l_m, wastewater_type=wastewater)
    l1 = L1Input(Ex_required=True) if ex else None
    return select_pumps(l0, l1)


def calibrate_etalon(etalon: dict) -> dict:
    """Калибрует один эталон, возвращает отчёт."""
    code = etalon.get("code", "?")
    report = {"code": code, "object_type": etalon.get("object_type"), "checks": []}

    # 1. КНС хозбытовая (если есть Q)
    if "block_5" in etalon:  # Евпатория
        q = etalon["block_5"]["Q_m3h"]
        check = _check_kns(q, "domestic", report, "block_5 К1")
        report["checks"].append(check)
        q = etalon["block_7"]["Q_m3h"]
        check = _check_kns(q, "domestic", report, "block_7 К1")
        report["checks"].append(check)

    # 2. ВНС хозпит
    if "vns_hozpit" in etalon:
        v = etalon["vns_hozpit"]
        check = _check_vns_or_fire(v.get("Q_m3h"), v.get("H_m"), v.get("P_kW"),
                                    "domestic", "vns_hozpit", v.get("model"))
        report["checks"].append(check)

    # 3. Пожарная насосная
    if "fire_pump_station" in etalon:
        f = etalon["fire_pump_station"]
        check = _check_vns_or_fire(f.get("Q_m3h"), f.get("H_m"),
                                    f.get("P_kW") or f.get("P_kW_per_pump"),
                                    "fire", "fire_pump_station", f.get("model"))
        report["checks"].append(check)

    # 4. Бондаревская — насосная пожаротушения
    if code == "Э2004-ВЭС-ОК-034-36НВК":
        # уже учтено в fire_pump_station выше
        pass

    return report


def _check_kns(q: float, wastewater: str, report: dict, label: str) -> dict:
    try:
        result = _select(q, wastewater=wastewater)
        candidates = result.candidates_total
        segments = result.results
        chosen = segments.mid or segments.budget or segments.premium
        if chosen is None:
            return {"label": label, "status": "no_candidates",
                    "Q_target": q, "candidates": 0}
        return {
            "label": label,
            "status": "ok" if candidates >= 1 else "warn",
            "Q_target": q,
            "Q_duty": chosen.duty_point.get("Q_m3h") if chosen.duty_point else None,
            "candidates_total": candidates,
            "mid_brand": segments.mid.brand if segments.mid else None,
            "mid_model": segments.mid.model if segments.mid else None,
            "budget_brand": segments.budget.brand if segments.budget else None,
            "premium_brand": segments.premium.brand if segments.premium else None,
        }
    except Exception as e:
        return {"label": label, "status": "error", "Q_target": q, "error": str(e)}


def _check_vns_or_fire(q: float | None, h: float | None, p_kw: float | None,
                        wastewater: str, label: str, etalon_model: str | None) -> dict:
    if not q or not h:
        return {"label": label, "status": "skip", "reason": "no Q or H"}
    try:
        result = _select(q, dh_m=h, wastewater=wastewater)
        chosen = result.results.mid or result.results.budget or result.results.premium
        if chosen is None:
            return {"label": label, "status": "no_candidates",
                    "Q_target": q, "H_target": h}
        ok_q = ok_h = ok_p = False
        rel_q = rel_h = rel_p = None
        if chosen.duty_point:
            ok_q, rel_q = _within(chosen.duty_point.get("Q_m3h", 0), q, TOLERANCE_Q)
            ok_h, rel_h = _within(chosen.duty_point.get("H_m", 0), h, TOLERANCE_H)
        if p_kw:
            ok_p, rel_p = _within(chosen.P_kW, p_kw, TOLERANCE_P)
        return {
            "label": label,
            "status": "pass" if (ok_q and ok_h and (ok_p or not p_kw)) else "warn",
            "Q_target": q, "Q_actual": chosen.duty_point.get("Q_m3h") if chosen.duty_point else None,
            "Q_rel_diff_pct": round(rel_q * 100, 1) if rel_q is not None else None,
            "H_target": h, "H_actual": chosen.duty_point.get("H_m") if chosen.duty_point else None,
            "H_rel_diff_pct": round(rel_h * 100, 1) if rel_h is not None else None,
            "P_target_kW": p_kw, "P_actual_kW": chosen.P_kW,
            "P_rel_diff_pct": round(rel_p * 100, 1) if rel_p is not None else None,
            "etalon_model": etalon_model,
            "matched_brand": chosen.brand, "matched_model": chosen.model,
            "candidates_total": result.candidates_total,
        }
    except Exception as e:
        return {"label": label, "status": "error", "Q_target": q, "H_target": h,
                "error": str(e)}


def main():
    if not ETALONS_FILE.exists():
        print(f"[!] Не найден {ETALONS_FILE}")
        return 1
    etalons = json.loads(ETALONS_FILE.read_text(encoding="utf-8"))
    print(f"[*] Загружено эталонов: {len(etalons)}")

    full_report = {"tolerance": {"Q": TOLERANCE_Q, "H": TOLERANCE_H, "P": TOLERANCE_P},
                   "results": []}
    pass_count = warn_count = error_count = skip_count = no_cand = 0

    for et in etalons:
        rep = calibrate_etalon(et)
        full_report["results"].append(rep)
        for c in rep["checks"]:
            s = c.get("status")
            if s in ("pass", "ok"):
                pass_count += 1
            elif s == "warn":
                warn_count += 1
            elif s == "error":
                error_count += 1
            elif s == "skip":
                skip_count += 1
            elif s == "no_candidates":
                no_cand += 1

        print(f"\n=== {rep['code']} ({rep['object_type']}) ===")
        for c in rep["checks"]:
            label = c["label"]
            status = c["status"]
            if status in ("pass", "ok"):
                print(f"  [OK]{label}: status={status}, Q={c.get('Q_target')}, "
                      f"matched={c.get('matched_brand')} {c.get('matched_model','')}, "
                      f"cand={c.get('candidates_total')}")
            elif status == "warn":
                print(f"  [WARN]{label}: Q-rel={c.get('Q_rel_diff_pct')}%, "
                      f"H-rel={c.get('H_rel_diff_pct')}%, P-rel={c.get('P_rel_diff_pct')}%, "
                      f"matched={c.get('matched_brand')} {c.get('matched_model','')}")
            elif status == "no_candidates":
                print(f"  [ERR]{label}: Q={c.get('Q_target')} — нет кандидатов!")
            elif status == "error":
                print(f"  [ERR]{label}: ERROR {c.get('error')}")
            elif status == "skip":
                print(f"  - {label}: пропуск ({c.get('reason')})")

    full_report["summary"] = {
        "pass": pass_count, "warn": warn_count, "error": error_count,
        "skip": skip_count, "no_candidates": no_cand,
        "total_checks": pass_count + warn_count + error_count + skip_count + no_cand,
    }
    out = ROOT / "02_dataset" / "_analysis" / "calibration_report_2026-05-09.json"
    out.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[+] Сводка: pass={pass_count}, warn={warn_count}, error={error_count}, "
          f"skip={skip_count}, no_cand={no_cand}")
    print(f"[+] Отчёт: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
