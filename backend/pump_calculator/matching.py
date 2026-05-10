"""7-шаговый алгоритм первичного подбора насоса.

Соответствует ALGORITHM_SPEC.md §2 и 01_spec/matching.md.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
from pump_calculator.result_enrichment import (
    build_summary_text,
    calculate_completeness_pct,
    fill_price_ranges,
)
from pump_calculator.hydraulics import aor_zone, compute_hydraulics
from pump_calculator.pump_station_geometry import (
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
    # На 2026-05-10 ВСЯ БД (471 насос) имеет rpm=0 (не парсится из PDF
    # паспортов), поэтому ns_factor=1.0 для всех. Ветка оживёт когда ETL
    # обогатит rpm. НЕ удаляем — Ns_value и ns_factor попадают в breakdown.
    rpm = (pump.get("power") or {}).get("rpm", 0)
    H_BEP = e.get("H_BEP_m") or H_full_m
    Ns_value = calc_specific_speed_ns(rpm, Q_m3h, H_BEP)
    ns_factor = score_ns_compatibility(Ns_value)
    base_score *= ns_factor

    # Штраф для некалиброванных ETL-импортов: ~13% БД имеют
    # _engineer_flag="needs_review" — pdfplumber-парсинг с непроверенными
    # данными, но цена есть. Снижаем score ×0.7.
    # Штраф ×0.5 для request_quote (~32% БД — Antarus+KSB B2B-only / exit РФ):
    # цена недоступна публично, нужно ручное обращение к дилеру.
    flag = pump.get("_engineer_flag")
    if flag == "needs_review":
        base_score *= 0.7
    elif flag == "request_quote":
        base_score *= 0.5

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

    # Сборка notes из _engineer_note + флаг-предупреждения для пользователя
    pump_notes: list[str] = []
    if pump.get("_engineer_note"):
        pump_notes.append(pump["_engineer_note"])
    flag = pump.get("_engineer_flag")
    if flag == "request_quote":
        pump_notes.insert(0, (
            "⚠ Цена по запросу. Этот насос распространяется только через B2B-канал "
            "или официальных дилеров. Цена и наличие подтверждаются звонком."
        ))
    elif flag == "needs_review":
        pump_notes.insert(0, (
            "⚠ Данные импортированы автоматически (pdfplumber) и не сверены инженером. "
            "Перед заказом — верифицировать паспорт и цену у поставщика."
        ))

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
        notes=pump_notes,
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

def build_suggestions(
    L0: L0Input, L1: L1Input | None, computed: ComputedHydraulics, triggers: list[str]
) -> list:
    """«Возможно вы имели в виду...» — мягкие предложения исправить вход.

    Анализирует подозрительные значения и предлагает конкретные правки.
    Frontend может рендерить модалку "Применить?" с этими предложениями.

    Возвращает list[InputSuggestion]. Никогда не модифицирует L0/L1 — только
    предлагает.
    """
    from pump_calculator.schemas import InputSuggestion
    suggestions = []

    # 1. Q < 0.1 м³/ч — возможно опечатка. Часто 0.05 → 5 (л/мин→м³/ч?)
    if L0.Q_m3h < 0.1:
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{L0.Q_m3h * 60:.1f}",  # л/мин → м³/ч если перепутали
            reason=(
                f"Q={L0.Q_m3h} м³/ч ≈ {L0.Q_m3h * 1000:.0f} л/час — это очень мало. "
                f"Если вы имели в виду л/мин, то в м³/ч это {L0.Q_m3h * 60:.1f}. "
                f"Если л/с — то {L0.Q_m3h * 3.6:.1f}."
            ),
            severity="critical",
        ))

    # 2. dH отрицательный — возможно знак неверный
    if L0.dH_m is not None and L0.dH_m < 0:
        suggestions.append(InputSuggestion(
            field="dH_m",
            current_value=f"{L0.dH_m}",
            suggested_value=f"{abs(L0.dH_m)}",
            reason=(
                f"dH={L0.dH_m} м (отрицательный) — точка сброса ниже точки забора. "
                f"Возможно, вы имели в виду {abs(L0.dH_m)} м (положительный подъём)? "
                f"Отрицательный dH = самотёк, насос обычно не нужен."
            ),
            severity="critical",
        ))

    # 3. L < 5 м для серьёзного Q — может быть опечатка (10 вместо 100, и т.д.)
    if L0.L_m is not None and L0.L_m < 5 and L0.Q_m3h > 50:
        suggestions.append(InputSuggestion(
            field="L_m",
            current_value=f"{L0.L_m}",
            suggested_value=f"{L0.L_m * 10}",
            reason=(
                f"L={L0.L_m} м для Q={L0.Q_m3h} м³/ч — почти отсутствие трассы. "
                f"Возможно вы имели в виду {L0.L_m * 10} м? "
                f"При Q ≥ 50 м³/ч обычно нужна напорная трасса от 50 м."
            ),
            severity="warning",
        ))

    # 4. Скорость v < 0.5 м/с (намного ниже минимума) — pipe_D_mm слишком велик
    if L1 and L1.pipe_D_mm and computed.v_ms < 0.5:
        # Подберём D для v=1.2
        import math
        Q_m3s = L0.Q_m3h / 3600
        # v = Q / (π D² / 4) → D = sqrt(4 Q / (π v))
        D_optimal = math.sqrt(4 * Q_m3s / (math.pi * 1.2)) * 1000
        # Округлим до стандартного DN
        for std in [50, 65, 80, 100, 125, 150, 200, 250, 300]:
            if std >= D_optimal:
                D_optimal = std
                break
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=(
                f"При D={L1.pipe_D_mm} мм скорость v={computed.v_ms:.2f} м/с (заиливание). "
                f"Для Q={L0.Q_m3h} м³/ч оптимальный D ≈ {D_optimal} мм (v ~1.2 м/с)."
            ),
            severity="warning",
        ))

    # 5. Скорость v > 3 м/с — pipe_D_mm слишком мал
    if L1 and L1.pipe_D_mm and computed.v_ms > 3.0:
        import math
        Q_m3s = L0.Q_m3h / 3600
        D_optimal = math.sqrt(4 * Q_m3s / (math.pi * 1.2)) * 1000
        for std in [50, 65, 80, 100, 125, 150, 200, 250, 300]:
            if std >= D_optimal:
                D_optimal = std
                break
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=(
                f"При D={L1.pipe_D_mm} мм скорость v={computed.v_ms:.2f} м/с (эрозия). "
                f"Для Q={L0.Q_m3h} м³/ч оптимальный D ≈ {D_optimal} мм (v ~1.2 м/с)."
            ),
            severity="warning",
        ))

    # 6. PE100 + горячая жидкость → предложить сталь
    pipe_mat = L1.pipe_material if L1 else None
    temp_c = L1.liquid_temp_c if L1 else None
    if pipe_mat in ("pe100_sdr17", "pp", "pvc") and temp_c is not None and temp_c > 60:
        suggestions.append(InputSuggestion(
            field="L1.pipe_material",
            current_value=f"{pipe_mat}",
            suggested_value="steel_seamless_new",
            reason=(
                f"{pipe_mat} не рассчитан на T={temp_c}°C (max 60°C). "
                f"Сталь бесшовная допускает до 200°C при PN ≤ 16 бар."
            ),
            severity="critical",
        ))

    # 7. inflow > Q насоса в 1.5+ раза — предложить увеличить Q или насосы
    if L1 and L1.inflow_per_hour_m3 and L1.inflow_per_hour_m3 > L0.Q_m3h * 1.5:
        # Предлагаем Q = inflow * 1.2 (с запасом)
        suggested_Q = round(L1.inflow_per_hour_m3 * 1.2, 1)
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{suggested_Q}",
            reason=(
                f"Приток {L1.inflow_per_hour_m3} м³/ч превышает Q насоса "
                f"({L0.Q_m3h} м³/ч). Чтобы система справилась, "
                f"увеличьте Q до {suggested_Q} м³/ч (+20% запас)."
            ),
            severity="critical",
        ))

    return suggestions


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

    # TRIG-1b: Q микро (< 0.1 м³/ч = ~1.6 л/мин) — нереалистично малая нагрузка
    # для КНС. Скорее всего опечатка ввода или неподходящий объект (нужен
    # бытовой грязевой насос, не КНС). Подбор может вернуть "слишком большой"
    # насос, который будет работать в pulsed-mode с потерей ресурса.
    if L0.Q_m3h < 0.1:
        triggers.append("auto_q_micro")

    # TRIG-1c: dH < 0 — отрицательный геометрический перепад (точка сброса
    # ниже точки забора). Физически возможен (напорный сбор с уровня моря
    # на дно), но крайне необычен для КНС. Требует ручной верификации.
    if L0.dH_m is not None and L0.dH_m < 0:
        triggers.append("auto_dh_negative")

    # TRIG-1d: скорость в трубе вне допустимого диапазона СП 32 §5.4
    # (v_min=0.7 м/с — заиливание; v_max=2.5 м/с — эрозия).
    # Срабатывает когда pipe_D_mm задан вручную и не попадает в диапазон.
    if L1 and L1.pipe_D_mm and computed.v_ms < 0.7:
        triggers.append("auto_velocity_low")
    if L1 and L1.pipe_D_mm and computed.v_ms > 2.5:
        triggers.append("auto_velocity_high")

    # TRIG-1e: высота над уровнем моря > 1500 м или < -200 м
    # P_atm падает с высотой (Эльбрус 4500м → 57 кПа vs 101.3 кПа на уровне моря) —
    # NPSHa резко падает, может потребоваться насос с низким NPSHr.
    if L1 and L1.altitude_m is not None and (L1.altitude_m > 1500 or L1.altitude_m < -200):
        triggers.append("auto_altitude_extreme")

    # TRIG-1f: УГВ выше поверхности — насосная будет работать в затопленной
    # площадке, нужна особая защита (IP68, anti-buoyancy расчёт корпуса).
    if L1 and L1.groundwater_level_m is not None and L1.groundwater_level_m > 0:
        triggers.append("auto_groundwater_above_surface")

    # TRIG-1g: приток > Q насоса в 1.5 раза — система не справится,
    # нужно либо увеличить Q, либо несколько насосов в параллель.
    if L1 and L1.inflow_per_hour_m3 and L1.inflow_per_hour_m3 > L0.Q_m3h * 1.5:
        triggers.append("auto_inflow_exceeds_pump")

    # TRIG-1h: PE100/PP/PVC + горячая жидкость > 60°C — деградация трубы.
    # Паспорт ПЭ100: max T = 60°C для длительной эксплуатации (PE100 RC до 80°C
    # при пониженном давлении). Для горячих стоков нужна сталь / ВЧШГ.
    pipe_mat = L1.pipe_material if L1 else None
    temp_c = L1.liquid_temp_c if L1 else None
    if pipe_mat in ("pe100_sdr17", "pp", "pvc") and temp_c is not None and temp_c > 60:
        triggers.append("auto_pipe_temp_incompatible")

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

    # Short-circuit: H_full_m <= 0 — насос физически не нужен (самотёк).
    # Без этой проверки фильтр envelope пропускает все насосы (H_max > 0
    # всегда удовлетворяет H_full_m <= H_max * 1.05), и calculator
    # «успешно» подбирает Fancy/CNP для отрицательного напора. См. PRR
    # subagent edge-experiments 2026-05-10 (negative-dH issue).
    if computed.H_full_m <= 0:
        sc_triggers = ["auto_no_head_required"]
        if L0.dH_m is not None and L0.dH_m < 0:
            sc_triggers.append("auto_dh_negative")
        sc_suggestions = build_suggestions(L0, L1, computed, sc_triggers)
        return SelectionResult(
            input=SelectionRequest(L0=L0_filled, L1=L1),
            computed=computed,
            results=SelectionResultsBySegment(),
            candidates_total=0,
            warnings=[
                f"⚠ Итоговый напор H_full={computed.H_full_m:.2f} м ≤ 0 — "
                f"насос физически не нужен, возможен самотёк. Перепроверьте "
                f"знак dH (сейчас {L0.dH_m if L0.dH_m is not None else 'default'}) "
                f"и схему трассы.",
            ],
            engineer_handoff_required=True,
            trigger_reasons=sc_triggers,
            suggestions=sc_suggestions,
            assumptions=assumptions,
            completeness_pct=calculate_completeness_pct(L0, L1),
            summary_text="Расчёт остановлен: при текущих параметрах насос не требуется.",
        )

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

    # Edge-case warnings: дополняем warnings человекочитаемыми пояснениями
    # для критичных triggers (микро-Q, отриц-dH, аномально большой Q).
    if "auto_q_micro" in triggers:
        warnings.insert(0, (
            f"⚠ Q={L0.Q_m3h} м³/ч — нереалистично малый расход для КНС "
            f"(норма от 0.5 м³/ч). Возможна опечатка ввода. Подбор может "
            f"вернуть переразмеренный насос — обязательна верификация инженером."
        ))
    if "auto_dh_negative" in triggers:
        warnings.insert(0, (
            f"⚠ dH={L0.dH_m} м (отрицательный геометрический перепад). "
            f"Точка сброса ниже точки забора — необычная конфигурация. "
            f"Перепроверьте знак и схему трассы."
        ))
    if "auto_q_high" in triggers:
        warnings.insert(0, (
            f"⚠ Q={L0.Q_m3h} м³/ч превышает 500 м³/ч — рекомендуется "
            f"индивидуальное проектирование магистральной КНС инженером."
        ))
    if "auto_velocity_low" in triggers:
        warnings.insert(0, (
            f"⚠ Скорость в трубе v={computed.v_ms:.2f} м/с < 0.7 м/с (СП 32 §5.4). "
            f"Риск заиливания осадком. Рассмотрите меньший pipe_D_mm "
            f"(сейчас {L1.pipe_D_mm} мм) или увеличьте Q."
        ))
    if "auto_velocity_high" in triggers:
        warnings.insert(0, (
            f"⚠ Скорость в трубе v={computed.v_ms:.2f} м/с > 2.5 м/с (СП 32 §5.4). "
            f"Эрозия трубы и арматуры. Увеличьте pipe_D_mm "
            f"(сейчас {L1.pipe_D_mm} мм) или уменьшите Q."
        ))
    if "auto_altitude_extreme" in triggers:
        alt = L1.altitude_m if L1 else None
        warnings.insert(0, (
            f"⚠ Высота над уровнем моря {alt} м — атмосферное давление "
            f"существенно отличается от стандартного. NPSHa может оказаться "
            f"ниже NPSHr выбранного насоса. Требуется проверка кавитации."
        ))
    if "auto_groundwater_above_surface" in triggers:
        gw = L1.groundwater_level_m if L1 else None
        warnings.insert(0, (
            f"⚠ УГВ {gw} м (выше поверхности земли) — площадка затоплена. "
            f"Требуется: IP68 для всего электрооборудования, расчёт "
            f"anti-buoyancy для корпуса КНС."
        ))
    if "auto_inflow_exceeds_pump" in triggers:
        inflow = L1.inflow_per_hour_m3 if L1 else None
        warnings.insert(0, (
            f"⚠ Приток {inflow} м³/ч превышает производительность насоса "
            f"({L0.Q_m3h} м³/ч) в 1.5+ раза. Система не успеет откачать — "
            f"уровень в приёмной камере будет расти. Увеличьте Q или "
            f"количество насосов в параллель."
        ))
    if "auto_pipe_temp_incompatible" in triggers:
        pipe_mat = L1.pipe_material if L1 else None
        temp_c = L1.liquid_temp_c if L1 else None
        warnings.insert(0, (
            f"⚠ Материал трубы {pipe_mat} не допустим при температуре жидкости "
            f"{temp_c}°C (max 60°C). Грозит деградацией трубы за месяцы. "
            f"Замените pipe_material на 'steel_seamless_new' или 'cast_iron_new'."
        ))
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

    # Phase «Did you mean»: мягкие предложения исправить странные значения
    suggestions = build_suggestions(L0, L1, computed, triggers)

    return SelectionResult(
        input=SelectionRequest(L0=L0_filled, L1=L1),
        computed=computed,
        results=results,
        candidates_total=candidates_total,
        warnings=warnings,
        engineer_handoff_required=handoff_required,
        trigger_reasons=triggers,
        suggestions=suggestions,
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
