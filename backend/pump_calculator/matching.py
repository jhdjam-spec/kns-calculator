"""7-шаговый алгоритм первичного подбора насоса.

Соответствует ALGORITHM_SPEC.md §2 и 01_spec/matching.md.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
from pump_calculator.hydraulics import aor_zone, compute_hydraulics
from pump_calculator.pricing import estimate_kns_kit_price
from pump_calculator.schemas import (
    ComputedHydraulics,
    L0Input,
    L1Input,
    PumpEnvelope,
    PumpResult,
    SelectionRequest,
    SelectionResult,
    SelectionResultsBySegment,
)


# ----------------------- Дефолты для неполного L0 -----------------------

L0_DEFAULT_DH_M = 5.0
L0_DEFAULT_L_M = 50.0
L0_DEFAULT_WW_TYPE = "domestic"


def apply_l0_defaults(L0: L0Input) -> tuple[L0Input, list[str]]:
    """Подставляем безопасные дефолты для пропущенных полей L0.

    Возвращает (новый L0 с заполненными полями, список assumptions для UX).
    """
    assumptions: list[str] = []
    dH = L0.dH_m
    L_m = L0.L_m
    ww = L0.wastewater_type

    if dH is None:
        dH = L0_DEFAULT_DH_M
        assumptions.append(
            f"dH не указан — использован {L0_DEFAULT_DH_M:g} м (типичный перепад внутри площадки)"
        )
    if L_m is None:
        L_m = L0_DEFAULT_L_M
        assumptions.append(
            f"L не указана — использовано {L0_DEFAULT_L_M:g} м (типовая внутриплощадочная трасса)"
        )
    if ww is None:
        ww = L0_DEFAULT_WW_TYPE
        assumptions.append(
            f"Тип стоков не указан — использован 'domestic' (хоз-бытовые, наиболее частый сценарий)"
        )

    # Если dH=0 и L=0 — сценарий «насос на месте» нереалистичен для подбора:
    # подставим минимальный H_full=2 м путём задания dH=2
    if dH == 0 and L_m == 0:
        dH = 2.0
        assumptions.append(
            "dH и L оба 0 — установлен dH=2 м (минимум для подбора насоса)"
        )

    return (
        L0Input(Q_m3h=L0.Q_m3h, dH_m=dH, L_m=L_m, wastewater_type=ww),
        assumptions,
    )

# ----------------------- Шаг 3: жёсткий фильтр -----------------------

def filter_by_wastewater_type(
    pumps: list[dict[str, Any]], wastewater_type: str
) -> list[dict[str, Any]]:
    """Шаг 3: фильтр по свободному проходу и совместимости с типом стоков."""
    free_passage_min, allowed_impellers = catalog.get_free_passage_required_mm(wastewater_type)
    out = []
    for p in pumps:
        if p.get("_engineer_flag") == "not_recommended":
            continue
        if wastewater_type not in p.get("wastewater_compat", []):
            continue
        if p.get("free_passage_mm", 0) < free_passage_min:
            continue
        if p.get("impeller") and p["impeller"] not in allowed_impellers:
            continue
        out.append(p)
    return out


# ----------------------- Шаг 4: Q-H envelope -----------------------

def filter_by_envelope(
    pumps: list[dict[str, Any]], Q_m3h: float, H_full_m: float
) -> list[dict[str, Any]]:
    """Шаг 4: Q ∈ [Q_min·0.85, Q_max·1.15], H_full ∈ [H_min, H_max·1.05]."""
    out = []
    for p in pumps:
        e = p["envelope"]
        if not (e["Q_min_m3h"] * 0.85 <= Q_m3h <= e["Q_max_m3h"] * 1.15):
            continue
        if not (e["H_min_m"] <= H_full_m <= e["H_max_m"] * 1.05):
            continue
        out.append(p)
    return out


# ----------------------- Шаг 5: AOR/POR + composite score -----------------------

def composite_score(pump: dict[str, Any], Q_m3h: float, H_full_m: float) -> tuple[float, dict, str | None]:
    """Composite score = 0.40·BEP + 0.25·η + 0.20·H_margin + 0.10·avail + 0.05·warranty.

    Возвращает (score, breakdown, aor_zone_label).
    """
    e = pump["envelope"]

    # BEP proximity (40%)
    Q_BEP = e.get("Q_BEP_m3h") or (e["Q_min_m3h"] + e["Q_max_m3h"]) / 2
    bep_prox = max(0.0, 1.0 - abs(Q_m3h - Q_BEP) / Q_BEP)

    # КПД в BEP (25%) — fallback 0.30 (а не 0.50, чтобы стимулировать заполнение БД)
    eta_pct = e.get("eta_BEP_pct")
    eta = (eta_pct / 100.0) if eta_pct else 0.30

    # H margin quality (20%) — идеал H_max/H_full в [1.05, 1.15]
    ratio = e["H_max_m"] / H_full_m if H_full_m > 0 else 0
    if 1.05 <= ratio <= 1.15:
        h_q = 1.0
    elif 1.0 <= ratio < 1.05 or 1.15 < ratio <= 1.30:
        h_q = 0.7
    elif 1.30 < ratio <= 1.60:
        h_q = 0.5
    elif ratio < 1.0:
        h_q = 0.0
    else:
        h_q = 0.3  # сильно избыточный запас

    # Доступность РФ (10%)
    avail_map = {"official": 1.0, "parallel_import": 0.6, "stock_only": 0.4, "discontinued": 0.0}
    avail = avail_map.get(pump.get("available_ru", {}).get("status", ""), 0.5)

    # Гарантия (5%)
    warranty_months = pump.get("warranty_months", 12)
    warranty = min(warranty_months / 24.0, 1.0)

    base_score = 0.40 * bep_prox + 0.25 * eta + 0.20 * h_q + 0.10 * avail + 0.05 * warranty

    # AOR/POR penalty
    zone = aor_zone(Q_m3h, e.get("Q_BEP_m3h"))
    if zone == "outside":
        # Вне AOR — кандидат уже должен быть отсечён, но если попал — штраф
        score = base_score * 0.3
    elif zone == "AOR":
        # В AOR но вне POR — penalty
        score = base_score * 0.7
    else:
        # POR или нет данных Q_BEP — без штрафа
        score = base_score

    breakdown = {
        "bep_proximity": round(bep_prox, 3),
        "eta": round(eta, 3),
        "h_margin_quality": round(h_q, 3),
        "ru_availability": round(avail, 3),
        "warranty": round(warranty, 3),
        "base_score": round(base_score, 4),
        "final_score": round(score, 4),
    }
    return score, breakdown, zone


def filter_by_aor(pumps: list[dict[str, Any]], Q_m3h: float) -> list[dict[str, Any]]:
    """Шаг 5а (новое в v0.2): отсечь кандидатов вне AOR (40-150% Q_BEP)."""
    out = []
    for p in pumps:
        Q_BEP = p["envelope"].get("Q_BEP_m3h")
        if not Q_BEP:
            # Нет данных Q_BEP — пропускаем без AOR-фильтра, но с пометкой
            out.append(p)
            continue
        zone = aor_zone(Q_m3h, Q_BEP)
        if zone == "outside":
            continue
        out.append(p)
    return out


# ----------------------- Шаг 6: топ-1 в каждом сегменте -----------------------

def make_pump_result(
    pump: dict[str, Any],
    score: float,
    breakdown: dict,
    zone: str | None,
    Q_m3h: float = 0.0,
    corpus_material: str = "pe",
) -> PumpResult:
    """Конвертация из raw JSON в типизированный PumpResult с оценкой цены комплекта."""
    e = pump["envelope"]
    P_kW = (pump.get("power") or {}).get("P_kW", 0)
    DN_mm = (pump.get("discharge") or {}).get("DN_mm")
    segment = pump["price_segment"]

    # Первичная оценка цены КНС-комплекта (1 раб + 1 рез по умолчанию)
    price_breakdown, confidence = estimate_kns_kit_price(
        P_kW=P_kW,
        Q_m3h=Q_m3h,
        discharge_DN_mm=DN_mm,
        segment=segment,
        n_pumps=2,
        corpus_material=corpus_material,  # type: ignore[arg-type]
    )

    return PumpResult(
        id=pump["id"],
        brand=pump["brand"],
        model=pump["model"],
        type=pump["type"],
        impeller=pump.get("impeller"),
        free_passage_mm=pump.get("free_passage_mm", 0),
        envelope=PumpEnvelope(**{k: v for k, v in e.items() if k in PumpEnvelope.model_fields}),
        P_kW=P_kW,
        discharge_DN_mm=DN_mm,
        price_segment=segment,
        available_ru_status=(pump.get("available_ru") or {}).get("status", "unknown"),
        score=round(score, 4),
        score_breakdown=breakdown,
        aor_zone=zone,
        notes=([pump["_engineer_note"]] if pump.get("_engineer_note") else []),
        price_estimate_rub=price_breakdown.total_rub,
        price_breakdown=price_breakdown,
        price_confidence=confidence,
    )


def pick_top_per_segment(
    pumps: list[dict[str, Any]],
    Q_m3h: float,
    H_full_m: float,
    corpus_material: str = "pe",
) -> tuple[SelectionResultsBySegment, int, list[str]]:
    """Шаг 6: топ-1 в каждом из {budget, mid, premium}."""
    scored = []
    for p in pumps:
        score, breakdown, zone = composite_score(p, Q_m3h, H_full_m)
        scored.append((p, score, breakdown, zone))

    results = SelectionResultsBySegment()
    warnings = []
    for segment in ("budget", "mid", "premium"):
        seg_candidates = [s for s in scored if s[0]["price_segment"] == segment]
        if not seg_candidates:
            warnings.append(f"{segment}: нет кандидатов в этом ценовом сегменте")
            continue
        best = max(seg_candidates, key=lambda x: x[1])
        pr = make_pump_result(
            best[0], best[1], best[2], best[3],
            Q_m3h=Q_m3h, corpus_material=corpus_material,
        )
        # Duty point — точка работы
        pr.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        setattr(results, segment, pr)

    return results, len(scored), warnings


# ----------------------- Шаг 7: триггеры hand-off -----------------------

def evaluate_handoff_triggers(
    L0: L0Input, L1: L1Input | None, computed: ComputedHydraulics, candidates_count: int
) -> list[str]:
    """Возвращает список trigger_reasons (TRIG-1..10 + новые)."""
    triggers = []

    # TRIG-1: Q или H высокие (выход за бюджетные серии)
    if L0.Q_m3h > 500:
        triggers.append("auto_q_high")
    if computed.H_full_m > 80:
        triggers.append("auto_h_high")

    # TRIG-2: промстоки
    if L0.wastewater_type == "industrial":
        triggers.append("auto_industrial")

    # TRIG-3: длинная трасса — гидроудар
    if L0.L_m > 500:
        triggers.append("auto_l_long_zhukovsky")

    # TRIG-4: горячая жидкость — NPSH
    if L1 and L1.liquid_temp_c and L1.liquid_temp_c > 40:
        triggers.append("auto_npsh_hot")

    # TRIG-5: I категория надёжности
    if L1 and L1.reliability_category == "I":
        triggers.append("auto_category_I")

    # TRIG-6: мало кандидатов
    if candidates_count < 1:
        triggers.append("auto_no_match")
    elif candidates_count < 2:
        triggers.append("auto_low_match_count")

    # TRIG-9: Ex
    if L1 and L1.Ex_required:
        triggers.append("auto_ex")

    return triggers


# ----------------------- Главная функция -----------------------

def select_pumps(L0: L0Input, L1: L1Input | None = None) -> SelectionResult:
    """Полный пайплайн: 7 шагов алгоритма + первичная оценка цены.

    Возвращает SelectionResult с топ-1 в каждом ценовом сегменте +
    флаги hand-off + полная гидравлика + price_estimate_rub в каждом PumpResult +
    assumptions со списком подставленных дефолтов.

    Терпим к неполному L0: если dH/L/wastewater_type=None → подставляются дефолты.
    """
    # Шаг 0: подставляем дефолты для пропущенных полей L0
    L0_filled, assumptions = apply_l0_defaults(L0)

    # Шаги 1-2
    computed = compute_hydraulics(L0_filled, L1)

    # Шаг 3
    pumps_all = catalog.load_pumps()
    f1 = filter_by_wastewater_type(pumps_all, L0_filled.wastewater_type)

    # Шаг 4
    f2 = filter_by_envelope(f1, L0_filled.Q_m3h, computed.H_full_m)

    # Шаг 5а: AOR
    f3 = filter_by_aor(f2, L0_filled.Q_m3h)

    # Шаг 6
    corpus_material = (L1.corpus_material if L1 and L1.corpus_material else "pe")
    results, candidates_total, warnings = pick_top_per_segment(
        f3, L0_filled.Q_m3h, computed.H_full_m, corpus_material=corpus_material,
    )

    # Шаг 7
    triggers = evaluate_handoff_triggers(L0_filled, L1, computed, candidates_total)

    # Жёсткий триггер: если ни один сегмент не заполнен — handoff обязателен
    if results.budget is None and results.mid is None and results.premium is None:
        if "auto_no_match" not in triggers:
            triggers.append("auto_no_match")

    return SelectionResult(
        input=SelectionRequest(L0=L0_filled, L1=L1),
        computed=computed,
        results=results,
        candidates_total=candidates_total,
        warnings=warnings,
        engineer_handoff_required=bool(triggers),
        trigger_reasons=triggers,
        assumptions=assumptions,
    )
