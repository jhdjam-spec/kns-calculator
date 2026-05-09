"""7-шаговый алгоритм первичного подбора насоса.

Соответствует ALGORITHM_SPEC.md §2 и 01_spec/matching.md.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
from pump_calculator.forecast import (
    build_summary_text,
    calculate_completeness_pct,
    fill_price_ranges,
)
from pump_calculator.hydraulics import aor_zone, compute_hydraulics
from pump_calculator.phase15 import (
    calc_specific_speed_ns,
    score_ns_compatibility,
)
from pump_calculator.pricing import (
    estimate_fire_kit_price,
    estimate_kns_kit_price,
    estimate_spd_kit_price,
)
from pump_calculator.schemas import (
    ComputedHydraulics,
    CorpusSize,
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
            "Тип стоков не указан — использован 'domestic' (хоз-бытовые, наиболее частый сценарий)"
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
        # NB: free_passage_mm может быть null у насосов чистой воды (booster_station,
        # CWP, жокей-насосы) — там свободный проход неприменим. Трактуем null как 0
        # (для wastewater_compat=[clean_water]/fire_protection это не блокирует, т.к.
        # для них free_passage_required=0).
        fp = p.get("free_passage_mm") or 0
        if fp < free_passage_min:
            continue
        if p.get("impeller") and p["impeller"] not in allowed_impellers:
            continue
        out.append(p)
    return out


# ----------------------- Шаг 4: Q-H envelope -----------------------

def filter_by_envelope(
    pumps: list[dict[str, Any]], Q_m3h: float, H_full_m: float
) -> list[dict[str, Any]]:
    """Шаг 4: Q ∈ [Q_min·0.85, Q_max·1.15], H_full ∈ [H_min, H_max·1.05].

    Reality: для бытовой канализации Q_клиент часто **меньше** минимума насосной
    серии (нет канализационных <5 м³/ч). Инженер ставит ближайший доступный
    канализационный с большим запасом по Q — это нормально, важнее DN ≥65 и
    free_passage. Поэтому **нижняя граница Q ослаблена до 0.05·Q_min**: насос
    «больше нужного» допускается, выше — отсекаем (overflow точно).
    """
    out = []
    for p in pumps:
        e = p["envelope"]
        # Q: насос может быть до 20× больше нужного по Q (Q_клиент ≥ 5% Q_min).
        # Это инженерная практика для бытовой канализации.
        if Q_m3h > e["Q_max_m3h"] * 1.15:
            continue
        if Q_m3h < e["Q_min_m3h"] * 0.05:
            continue
        # H: верхняя граница строгая (H_full > H_max → не дотянет).
        # Нижняя граница ослаблена для канализационных (см. КП Серво-Юг 2026:
        # H_full=1.92м, ставят KAIQUAN с H_min=6м — насос «слишком сильный»
        # допустим, только КПД ниже).
        if H_full_m > e["H_max_m"] * 1.05:
            continue
        # NB: ceiling H_max не вводим — КП Серво-Юг 2026 показывает что для
        # Q=0.5 H_full=4 ставят KAIQUAN с H_max=25 (6× запас). Защита от
        # экстремальных ЦНС (H до 1422 м) для бытовых запросов работает
        # через filter_by_wastewater_type — ЦНС имеют compat=[clean_water],
        # для domestic/drainage они уже отсеяны.
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

    # §15.6 — Specific Speed Ns multiplier.
    # Если у насоса есть rpm + Q_BEP + H_BEP → считаем Ns и применяем
    # множитель: 1.0 в рабочем диапазоне 15-80, 0.7 на границе, 0.4 за.
    # Если данных нет (rpm=0) — множитель 1.0, не штрафуем.
    rpm = (pump.get("power") or {}).get("rpm", 0)
    H_BEP = e.get("H_BEP_m") or H_full_m
    Ns_value = calc_specific_speed_ns(rpm, Q_m3h, H_BEP)
    ns_factor = score_ns_compatibility(Ns_value)
    base_score *= ns_factor

    # Штраф для некалиброванных ETL-импортов: 49% БД (231 насос) имеют
    # _engineer_flag="needs_review" — преимущественно pdfplumber-парсинг KSB
    # и Antarus, паспортные данные не сверены инженером. Снижаем score ×0.7,
    # чтобы калиброванные модели побеждали при равенстве BEP/η.
    if pump.get("_engineer_flag") == "needs_review":
        base_score *= 0.7

    # Pulsed-mode bonus: для малых Q бытовой канализации (< 5 м³/ч)
    # инженеры предпочитают **минимальный достаточный** насос — меньше Q_BEP,
    # ниже цена, реалистичнее циклы. Если Q_клиент < 5 м³/ч и это
    # submersible_sewage — добавляем бонус за **низкую мощность** и
    # минимальный достаточный DN (65 мм для бытовой канализации).
    if pump.get("type") == "submersible_sewage" and Q_m3h < 5.0:
        P_kW = (pump.get("power") or {}).get("P_kW", 100)
        DN_mm = (pump.get("discharge") or {}).get("DN_mm", 200)
        # Меньше кВт → выше бонус (инвертированная нормировка)
        small_pump_bonus = max(0.0, 1.0 - P_kW / 20.0)  # 0 для 20+ кВт, 1 для 0 кВт
        # DN65–80 — оптимум для бытовой; больше или меньше — penalty
        dn_optimal = 1.0 if 65 <= DN_mm <= 80 else 0.5
        base_score += 0.30 * small_pump_bonus * dn_optimal

    # AOR/POR penalty — только для continuous duty (СПД, чистая вода).
    # Submersible sewage работает в pulsed mode, формальный AOR не применим.
    zone = aor_zone(Q_m3h, e.get("Q_BEP_m3h"))
    if pump.get("type") == "submersible_sewage":
        # Не штрафуем — насос пускается на короткие циклы
        score = base_score
    elif zone == "outside":
        score = base_score * 0.3
    elif zone == "AOR":
        score = base_score * 0.7
    else:
        score = base_score

    breakdown = {
        "bep_proximity": round(bep_prox, 3),
        "eta": round(eta, 3),
        "h_margin_quality": round(h_q, 3),
        "ru_availability": round(avail, 3),
        "warranty": round(warranty, 3),
        "ns_value": Ns_value,
        "ns_factor": round(ns_factor, 3),
        "base_score": round(base_score, 4),
        "final_score": round(score, 4),
    }
    return score, breakdown, zone


def filter_by_aor(pumps: list[dict[str, Any]], Q_m3h: float) -> list[dict[str, Any]]:
    """Шаг 5а: отсечь кандидатов вне AOR (40-150% Q_BEP).

    **Important:** AOR (ANSI/HI 9.6.3) применим к **continuous duty** —
    непрерывной работе. Канализационные погружные (submersible_sewage)
    работают в **on/off cycling** режиме (поплавковое управление, циклы
    1-5 минут), и формально могут быть «outside AOR» по моментальной точке,
    но это нормальная практика для бытовой канализации с малым притоком.

    Реальный кейс: КП Серво-Юг 2026 для Q=0.5 м³/ч ставит KAIQUAN с Q_BEP=18 —
    Q/Q_BEP = 2.8% (outside по HI), но насос пускается раз в 30 минут и
    работает в свою BEP-точку короткое время.

    Для booster_station (СПД) AOR-фильтр сохраняем — там continuous duty.
    """
    out = []
    for p in pumps:
        Q_BEP = p["envelope"].get("Q_BEP_m3h")
        if not Q_BEP:
            out.append(p)
            continue
        # Submersible sewage с pulsed duty — AOR не применяем
        if p.get("type") == "submersible_sewage":
            out.append(p)
            continue
        # Booster / clean water — continuous duty, AOR обязателен
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
    wastewater_type: str = "domestic",
    ex_required: bool = False,
    n_pumps_override: int | None = None,
) -> PumpResult:
    """Конвертация из raw JSON в типизированный PumpResult с оценкой цены комплекта."""
    e = pump["envelope"]
    P_kW = (pump.get("power") or {}).get("P_kW", 0)
    DN_mm = (pump.get("discharge") or {}).get("DN_mm")
    segment = pump["price_segment"]
    explicit_pump_price = pump.get("price_rub_2026")
    pump_type = pump.get("type", "submersible_sewage")

    # Phase 11: пожарная установка — отдельный BOM-шаблон (СП 10.13130).
    # Всегда 1 раб + 1 рез + жокей-насос + пожарный ШУ Sf + PN16 арматура.
    # confidence ВСЕГДА low — индивидуальная калибровка под объект.
    if wastewater_type == "fire_protection":
        # Пожарная: минимум 1 раб + 1 рез по СП 10.13130 п.6.2; override опц.
        n_fire = max(2, n_pumps_override) if n_pumps_override else 2
        price_breakdown, confidence = estimate_fire_kit_price(
            P_kW=P_kW,
            Q_m3h=Q_m3h,
            discharge_DN_mm=DN_mm,
            segment=segment,
            n_pumps=n_fire,
            explicit_pump_price_rub=explicit_pump_price,
            ex_required=ex_required,
        )
    # Phase 8: для booster_station (СПД) — отдельный BOM-шаблон
    # (без АТМ, без корпуса/направляющих, с гидроаккумулятором и ЧРП-шкафом).
    # СПД-блок поставляется как **готовый комплект** — цена насоса в БД обычно
    # включает все насосы блока (например, ANTARUS 3 MLV20-5 = 3.5M за всю
    # станцию из 3 насосов). Поэтому n_pumps=1 (множитель уже учтён в цене).
    elif pump_type == "booster_station":
        # Booster — обычно блок целиком, n_pumps=1; override игнорируем
        # (множитель сделан в цене блока), кроме случаев нескольких блоков подряд.
        n_spd = n_pumps_override if n_pumps_override else 1
        price_breakdown, confidence = estimate_spd_kit_price(
            P_kW=P_kW,
            Q_m3h=Q_m3h,
            discharge_DN_mm=DN_mm,
            segment=segment,
            n_pumps=n_spd,
            explicit_pump_price_rub=explicit_pump_price,
        )
    else:
        # Очень малые бытовые насосы (Q < 5 м³/ч, DN ≤65) обычно ставят в
        # готовый приямок без полноценного ПЭ-корпуса КНС — как в реальном
        # КП Серво-Юг для KAIQUAN 65WQ/S223-2.2 (Q=0.5 м³/ч, частный коттедж).
        # Для Q ≥ 5 (типовая КНС многоквартирной/гостиничной) корпус нужен.
        is_small_kit = Q_m3h < 5.0 and (DN_mm or 0) <= 65

        # КНС бытовая/дренаж/индустрия: дефолт 1+1=2; клиент может задать override.
        n_kns = max(2, n_pumps_override) if n_pumps_override else 2
        price_breakdown, confidence = estimate_kns_kit_price(
            P_kW=P_kW,
            Q_m3h=Q_m3h,
            discharge_DN_mm=DN_mm,
            segment=segment,
            n_pumps=n_kns,
            corpus_material=corpus_material,  # type: ignore[arg-type]
            explicit_pump_price_rub=explicit_pump_price,
            include_corpus=not is_small_kit,
            include_rails=not is_small_kit,
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
    wastewater_type: str = "domestic",
    ex_required: bool = False,
    n_pumps_override: int | None = None,
) -> tuple[SelectionResultsBySegment, int, list[str], list[Any]]:
    """Шаг 6: топ-1 в каждом из {budget, mid, premium} + alternatives с другими брендами.

    Возвращает (results, total_candidates, warnings, alternatives).
    `alternatives` — до 6 кандидатов с уникальными брендами, не попавшими в top-1
    каждого сегмента. Отсортированы по убыванию score.
    """
    scored = []
    for p in pumps:
        score, breakdown, zone = composite_score(p, Q_m3h, H_full_m)
        scored.append((p, score, breakdown, zone))

    results = SelectionResultsBySegment()
    warnings = []
    selected_brands: set[str] = set()  # бренды которые уже в top-1
    selected_ids: set[str] = set()
    for segment in ("budget", "mid", "premium"):
        seg_candidates = [s for s in scored if s[0]["price_segment"] == segment]
        if not seg_candidates:
            warnings.append(f"{segment}: нет кандидатов в этом ценовом сегменте")
            continue
        best = max(seg_candidates, key=lambda x: x[1])
        pr = make_pump_result(
            best[0], best[1], best[2], best[3],
            Q_m3h=Q_m3h, corpus_material=corpus_material,
            wastewater_type=wastewater_type, ex_required=ex_required,
            n_pumps_override=n_pumps_override,
        )
        # Duty point — точка работы
        pr.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        setattr(results, segment, pr)
        selected_brands.add(best[0].get("brand", ""))
        selected_ids.add(best[0].get("id", ""))

    # Альтернативы — топ-1 в каждом ещё не показанном бренде, score сортировка убывания
    # Только из 3 поддерживаемых сегментов (budget/mid/premium); standard и пр. — пропускаем
    SUPPORTED_SEGMENTS = {"budget", "mid", "premium"}
    scored_sorted = sorted(scored, key=lambda x: -x[1])
    alternatives: list[Any] = []
    seen_alt_brands: set[str] = set()
    for p, score, breakdown, zone in scored_sorted:
        if len(alternatives) >= 6:
            break
        if p.get("price_segment") not in SUPPORTED_SEGMENTS:
            continue
        brand = p.get("brand", "")
        if not brand:
            continue
        if p.get("id") in selected_ids:
            continue
        if brand in selected_brands or brand in seen_alt_brands:
            continue
        # Пропустим _NOT_RECOMMENDED маркеры
        if p.get("_engineer_flag") == "not_recommended":
            continue
        seen_alt_brands.add(brand)
        alt = make_pump_result(
            p, score, breakdown, zone,
            Q_m3h=Q_m3h, corpus_material=corpus_material,
            wastewater_type=wastewater_type, ex_required=ex_required,
            n_pumps_override=n_pumps_override,
        )
        alt.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        alternatives.append(alt)

    return results, len(scored), warnings, alternatives


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

    # TRIG-2b (Phase 11): пожарная установка — handoff обязателен.
    # Параметры пожарной СПД зависят от категории помещения, типа спринклеров,
    # нормативного Q пожара (СП 10.13130) — нельзя обобщать одну сделку,
    # требуется индивидуальное проектирование инженером.
    if L0.wastewater_type == "fire_protection":
        triggers.append("auto_fire_protection")

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
    ex_required = bool(L1 and L1.Ex_required)
    n_pumps_override = L1.pumps_total_override if L1 and L1.pumps_total_override else None
    results, candidates_total, warnings, alternatives = pick_top_per_segment(
        f3, L0_filled.Q_m3h, computed.H_full_m, corpus_material=corpus_material,
        wastewater_type=L0_filled.wastewater_type,
        ex_required=ex_required,
        n_pumps_override=n_pumps_override,
    )

    # Шаг 7
    triggers = evaluate_handoff_triggers(L0_filled, L1, computed, candidates_total)

    # Жёсткий триггер: если ни один сегмент не заполнен — handoff обязателен
    if results.budget is None and results.mid is None and results.premium is None:
        if "auto_no_match" not in triggers:
            triggers.append("auto_no_match")

    # Phase 9: полнота входа + диапазон цен + человекочитаемая сводка
    # NB: считаем по **исходному** L0 (без apply_l0_defaults), чтобы дефолты
    # не учитывались как «заданные данные».
    completeness_pct = calculate_completeness_pct(L0, L1)
    fill_price_ranges(results, completeness_pct)
    handoff_required = bool(triggers)
    summary_text = build_summary_text(
        L0=L0_filled,
        L1=L1,
        results=results,
        completeness_pct=completeness_pct,
        candidates_total=candidates_total,
        handoff_required=handoff_required,
    )

    # Phase 13: размеры корпуса КНС (если нужны — для всех КНС бытовых, дренаж,
    # индустриальных, кроме малых Q<5 + DN<=65 в готовом приямке).
    corpus_size = _compute_corpus_size(L0_filled, L1, results, computed)

    return SelectionResult(
        input=SelectionRequest(L0=L0_filled, L1=L1),
        computed=computed,
        results=results,
        candidates_total=candidates_total,
        warnings=warnings,
        engineer_handoff_required=handoff_required,
        trigger_reasons=triggers,
        assumptions=assumptions,
        completeness_pct=completeness_pct,
        summary_text=summary_text,
        corpus_size=corpus_size,
        alternatives=alternatives,
    )


def _compute_corpus_size(
    L0_filled: L0Input,
    L1: L1Input | None,
    results: SelectionResultsBySegment,
    computed: ComputedHydraulics,
) -> CorpusSize | None:
    """Рассчитать размеры корпуса КНС если он нужен.

    Корпус не нужен:
    - clean_water (booster_station — приходит как готовый блок)
    - fire_protection (отдельная ёмкость пожарного запаса)
    - очень малые Q<5 + DN<=65 (готовый приямок)
    """
    from pump_calculator.corpus_sizing import compute_corpus_size as _cs

    wt = L0_filled.wastewater_type
    if wt in ("clean_water", "fire_protection"):
        return None

    # P_kW для footprint берём из mid-сегмента (если есть), иначе budget/premium
    sample_pump = results.mid or results.budget or results.premium
    if sample_pump is None:
        return None

    # Малая бытовая в готовом приямке — корпус не нужен
    DN = sample_pump.discharge_DN_mm or 65.0
    if L0_filled.Q_m3h < 5.0 and DN <= 65:
        return None

    n_pumps = computed.n_pumps_total
    corpus_material = (L1.corpus_material if L1 and L1.corpus_material else "pe")

    cs = _cs(
        Q_m3h=L0_filled.Q_m3h,
        P_kW=sample_pump.P_kW,
        depth_inlet_mm=None,  # default 2000 мм; в будущем можно из L1
        n_pumps=n_pumps,
        corpus_type=corpus_material,  # type: ignore[arg-type]
    )

    return CorpusSize(
        diameter_mm=cs.diameter_mm,
        height_mm=cs.height_mm,
        inlet_DN_mm=cs.inlet_DN_mm,
        outlet_DN_mm=cs.outlet_DN_mm,
        weight_estimate_kg=cs.weight_estimate_kg,
        notes=cs.notes,
    )
