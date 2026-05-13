"""7-шаговый алгоритм первичного подбора насоса.

Соответствует ALGORITHM_SPEC.md §2 и 01_spec/matching.md.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
from pump_calculator.cavitation import (
    CavitationResult,
    analyze_cavitation,
    explain_cavitation_engineer,
    explain_cavitation_manager,
)
from pump_calculator.hydraulics import aor_zone, compute_hydraulics
from pump_calculator.pricing import (
    estimate_fire_kit_price,
    estimate_kns_kit_price,
    estimate_spd_kit_price,
)
from pump_calculator.pump_station_geometry import (
    calc_specific_speed_ns,
    score_ns_compatibility,
)
from pump_calculator.result_enrichment import (
    build_summary_text,
    calculate_completeness_pct,
    fill_price_ranges,
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


# ----------------------- «Why this pump?» explainer -----------------------

# Цитаты СП/HI — кликабельные ссылки рендерит фронтенд. URL — на encyclopedia
# страницы или официальные ГОСТ/СП.
_CITATIONS_BEP = {
    "text": "СП 32.13330 §6.5 — допустимое отклонение рабочей точки от BEP ±20%",
    "url": "/teach/bep",
}
_CITATIONS_AOR = {
    "text": "ANSI/HI 9.6.3 — POR (0.7…1.2)·Q_BEP, AOR (0.4…1.5)·Q_BEP",
    "url": "/teach/aor-por",
}
_CITATIONS_NPSH = {
    "text": "СП 32.13330 §6.4 — расчёт NPSH и кавитации",
    "url": "/teach/npsh",
}
_CITATIONS_FREE_PASSAGE = {
    "text": "СП 32.13330 п.6.2 — свободный проход насоса для бытовых стоков ≥40 мм",
    "url": "/teach/free-passage",
}


def build_score_explanation(
    pump: dict[str, Any],
    breakdown: dict,
    zone: str | None,
    Q_m3h: float,
    H_full_m: float,
    wastewater_type: str = "domestic",
) -> dict:
    """Структурированное «Why this pump?» — для UI explainer panel.

    Поля step_5_segment и rank проставляются позже в pick_top_per_segment(),
    когда известна позиция в сегменте.

    Возвращает dict с шагами 1-4 + citations. Используется в make_pump_result.
    Не меняет core-логику matching — только обогащает PumpResult.
    """
    e = pump["envelope"]
    Q_min, Q_max = e["Q_min_m3h"], e["Q_max_m3h"]
    H_min, H_max = e["H_min_m"], e["H_max_m"]
    Q_BEP = e.get("Q_BEP_m3h") or (Q_min + Q_max) / 2

    # Шаг 1: фильтр по типу стоков + free_passage
    fp = pump.get("free_passage_mm") or 0
    fp_min, _ = catalog.get_free_passage_required_mm(wastewater_type)
    step_1 = (
        f"Прошёл фильтр: wastewater_type={wastewater_type}, "
        f"free_passage={fp:g} мм ≥ {fp_min:g} мм требуемых"
    )

    # Шаг 2: Q-H envelope
    step_2 = (
        f"Q={Q_m3h:g} м³/ч в диапазоне [{Q_min:g}, {Q_max:g}]; "
        f"H_full={H_full_m:g} м ≤ H_max={H_max:g} м "
        f"(допуск +5%); H_min насоса {H_min:g} м"
    )

    # Шаг 3: AOR/POR
    if pump.get("type") == "submersible_sewage":
        step_3 = (
            f"Работа в pulsed-режиме (циклы вкл/выкл по поплавкам) — "
            f"формальная AOR-проверка не применяется. Q/Q_BEP = "
            f"{(Q_m3h / Q_BEP * 100) if Q_BEP else 0:.0f}%."
        )
    else:
        zone_label = {
            "POR": "POR (Preferred Operating Region, 0.7…1.2 Q_BEP) — оптимум",
            "AOR": "AOR (Allowable Operating Region, 0.4…1.5 Q_BEP) — допустимо",
            "outside": "outside AOR — повышенный износ",
        }.get(zone or "", "неизвестно")
        step_3 = (
            f"Точка работы: Q/Q_BEP = {(Q_m3h / Q_BEP * 100) if Q_BEP else 0:.0f}% "
            f"→ {zone_label}"
        )

    # Шаг 4: композит-скор — value × weight = contribution
    bep_v = breakdown.get("bep_proximity", 0.0)
    eta_v = breakdown.get("eta", 0.0)
    h_v = breakdown.get("h_margin_quality", 0.0)
    avail_v = breakdown.get("ru_availability", 0.0)
    warr_v = breakdown.get("warranty", 0.0)
    step_4 = {
        "bep_proximity": {
            "value": bep_v,
            "weight": 0.40,
            "contribution": round(bep_v * 0.40, 4),
            "label": "Близость к BEP",
            "hint_engineer": (
                f"bep_prox = max(0, 1 - |Q - Q_BEP|/Q_BEP) = "
                f"max(0, 1 - |{Q_m3h:g} - {Q_BEP:g}|/{Q_BEP:g}) = {bep_v:.3f}"
            ),
            "hint_manager": (
                f"Насколько близко рабочая точка к идеалу: {bep_v * 100:.0f}% — "
                f"чем выше, тем меньше износ и расход энергии."
            ),
        },
        "eta": {
            "value": eta_v,
            "weight": 0.25,
            "contribution": round(eta_v * 0.25, 4),
            "label": "КПД в BEP",
            "hint_engineer": (
                f"η_BEP = {eta_v * 100:.0f}%"
                + ("" if e.get("eta_BEP_pct") else " (fallback 30% — нет в БД)")
            ),
            "hint_manager": (
                f"Эффективность насоса {eta_v * 100:.0f}% — "
                f"влияет на счёт за электричество."
            ),
        },
        "h_margin": {
            "value": h_v,
            "weight": 0.20,
            "contribution": round(h_v * 0.20, 4),
            "label": "Запас по напору",
            "hint_engineer": (
                f"H_max/H_full = {e['H_max_m']:g}/{H_full_m:g} = "
                f"{(e['H_max_m'] / H_full_m if H_full_m else 0):.2f}; "
                f"идеал в [1.05, 1.15] → h_q={h_v:.2f}"
            ),
            "hint_manager": (
                f"Запас напора подобран на {h_v * 100:.0f}% от идеала — "
                f"насос не «впритык» и не сильно избыточен."
            ),
        },
        "availability": {
            "value": avail_v,
            "weight": 0.10,
            "contribution": round(avail_v * 0.10, 4),
            "label": "Доступность в РФ",
            "hint_engineer": (
                f"available_ru.status = "
                f"{pump.get('available_ru', {}).get('status', 'unknown')} "
                f"→ avail={avail_v:.2f}"
            ),
            "hint_manager": (
                f"Поставка в РФ оценена в {avail_v * 100:.0f}% "
                f"(официальный канал=100%, параллельный=60%, под заказ=40%)."
            ),
        },
        "warranty": {
            "value": warr_v,
            "weight": 0.05,
            "contribution": round(warr_v * 0.05, 4),
            "label": "Гарантия",
            "hint_engineer": (
                f"warranty = min({pump.get('warranty_months', 12)}/24, 1.0) "
                f"= {warr_v:.2f}"
            ),
            "hint_manager": (
                f"Заводская гарантия {pump.get('warranty_months', 12)} мес "
                f"— нормирована к 24 мес (=100%)."
            ),
        },
    }

    # Композит base_score = сумма contribution × ns_factor × penalties
    composite_sum = round(
        bep_v * 0.40 + eta_v * 0.25 + h_v * 0.20 + avail_v * 0.10 + warr_v * 0.05,
        4,
    )

    citations = []
    citations.append(_CITATIONS_BEP)
    if pump.get("type") != "submersible_sewage":
        citations.append(_CITATIONS_AOR)
    if wastewater_type in ("domestic", "drainage", "industrial"):
        citations.append(_CITATIONS_FREE_PASSAGE)
    if e.get("NPSHr_at_BEP_m"):
        citations.append(_CITATIONS_NPSH)

    return {
        "step_1_filter": step_1,
        "step_2_envelope": step_2,
        "step_3_aor": step_3,
        "step_4_composite": step_4,
        "step_4_composite_sum": composite_sum,
        "step_4_final_score": breakdown.get("final_score", 0.0),
        # step_5_segment + rank проставляются в pick_top_per_segment.
        "step_5_segment": "",
        "rank_in_segment": None,
        "candidates_in_segment": None,
        "citations": citations,
    }


# Иерархия защиты IP — ключ для сравнения "не ниже". Используется в filter_by_ip_motor.
_IP_RANK: dict[str, int] = {"IP54": 1, "IP55": 2, "IP58": 3, "IP68": 4}


def filter_by_ip_motor(
    pumps: list[dict[str, Any]], required_ip: str | None
) -> list[dict[str, Any]]:
    """Фильтр по IP-рейтингу двигателя (L1.ip_motor).

    Если required_ip=None — фильтр не применяется (backward compat).
    Иначе оставляем только насосы с pump.power.ip_rating >= required_ip.

    NB: Если у насоса ip_rating не задан — пропускаем (НЕ отсекаем),
    чтобы не «обрубать» БД с неполной паспортизацией. Это
    консервативное поведение для текущего состояния каталога (~70% насосов
    без IP-поля), но в будущем может стать строгим (deprecation warning
    в notes).
    """
    if not required_ip or required_ip not in _IP_RANK:
        return pumps
    threshold = _IP_RANK[required_ip]
    out = []
    for p in pumps:
        pump_ip = (p.get("power") or {}).get("ip_rating")
        if not pump_ip:
            # Поле не задано — оставляем (консервативно, чтобы не вырезать пол-БД).
            out.append(p)
            continue
        if pump_ip not in _IP_RANK:
            # Странный формат IP — оставляем
            out.append(p)
            continue
        if _IP_RANK[pump_ip] >= threshold:
            out.append(p)
    return out


def filter_by_ex(
    pumps: list[dict[str, Any]],
    ex_required: bool,
    ex_zone: str | None = None,
) -> list[dict[str, Any]]:
    """Шаг 5б: фильтр по ATEX-маркировке для взрывоопасных зон.

    v0.3 (2026-05-13) — добавлено по PhD-Electrical audit P0-1
    + Sc.D. cross-domain (filter_by_ex отсутствовал, что = риск ст. 217.2 УК РФ).

    Источник: IEC 60079-0:2017 «Электроустановки во взрывоопасных зонах».
    ТР ТС 012/2011 «О безопасности оборудования для работы во взрывоопасных средах».

    Логика:
      - Если ex_required=False и ex_zone in (None, "none") — фильтр не применяется
        (выдаём все насосы, включая неEx — это обычные объекты).
      - Если ex_required=True ИЛИ ex_zone in {Zone_0, Zone_1, Zone_2, Zone_20/21/22}:
        оставляем только насосы с power.ex_rating НЕ null И НЕ "none",
        ИЛИ с явным is_ex=True, ИЛИ с "Ex"/"ATEX" в model/id (паттерн ETL).

    NB: При недостатке Ex-моделей в каталоге (≤80% БД без ex_rating) функция
    может вернуть пустой список — в pipeline это даёт пустой выход + триггер
    auto_no_match → handoff инженеру (это safe behavior, ст.217.2 УК РФ
    лучше handoff, чем wrong спецификация).
    """
    if not ex_required and (not ex_zone or ex_zone == "none"):
        return pumps
    out = []
    for p in pumps:
        power = p.get("power") or {}
        ex_rating = power.get("ex_rating")
        is_ex_flag = power.get("is_ex") or p.get("is_ex")
        model_str = str(p.get("model", "")).lower()
        id_str = str(p.get("id", "")).lower()
        # 1) Прямой флаг is_ex=True
        if is_ex_flag is True:
            out.append(p)
            continue
        # 2) ex_rating задан и не пустой
        if ex_rating and str(ex_rating).lower() not in ("none", "null", ""):
            out.append(p)
            continue
        # 3) Паттерн "Ex" в id/model (например kaiquan-50wqe-15-15-ex)
        # NB: проверяем границы слова, чтобы не путать "exempt"/"extra"
        import re
        if re.search(r"(?:^|[-_\s/])ex(?:$|[-_\s/0-9])", id_str) or \
           re.search(r"(?:^|[-_\s/])ex(?:$|[-_\s/0-9])", model_str):
            out.append(p)
            continue
        if "atex" in id_str or "atex" in model_str:
            out.append(p)
            continue
    return out


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
    L1: L1Input | None = None,
    H_full_m: float = 0.0,
) -> PumpResult:
    """Конвертация из raw JSON в типизированный PumpResult с оценкой цены комплекта.

    L1 пробрасывается опционально для применения uplift'ов:
    level_sensor_type, modbus_rtu_required, above_ground_pavilion.
    """
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
        # 2026-05-10: anti-buoyancy uplift из L1.groundwater_level_m (СП 32 §6.3).
        gw_level = L1.groundwater_level_m if L1 is not None else None
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
            groundwater_level_m=gw_level,
        )

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: uplift'ы по L1-полям (level_sensor / modbus / pavilion).
    # Применяем к цене ПОСЛЕ расчёта основного BOM, чтобы держать
    # estimate_*_kit_price чистыми (без знания о new L1 fields).
    # ──────────────────────────────────────────────────────────────────
    pump_notes: list[str] = []
    if L1 is not None:
        # n_pumps для расчёта поплавков/датчиков уровня
        n_actual = max(2, n_pumps_override) if n_pumps_override else 2

        # 1. level_sensor_type — заменяем floats на выбранный тип уровня.
        #    Цены за насос: floats=5k, ultrasonic=15k, capacitive=10k, pneumatic=8k.
        #    floats — стандартный default, поэтому только не-floats добавляют дельту.
        if L1.level_sensor_type and L1.level_sensor_type != "floats":
            sensor_prices = {"ultrasonic": 15_000, "capacitive": 10_000, "pneumatic": 8_000}
            new_sensor = sensor_prices[L1.level_sensor_type] * n_actual
            old_floats = price_breakdown.floats_rub
            delta = new_sensor - old_floats
            price_breakdown.floats_rub = new_sensor
            price_breakdown.total_rub += delta
            price_breakdown.total_dealer_rub = int(round(price_breakdown.total_rub * 0.75))
            pump_notes.append(
                f"💡 Датчик уровня: {L1.level_sensor_type} "
                f"({new_sensor:,} ₽ за {n_actual} шт)".replace(",", " ")
            )
        elif L1.level_sensor_type == "floats":
            # Явно поплавки — ничего не меняем (default), но фиксируем в notes.
            pump_notes.append("💡 Датчик уровня: поплавки (default, 5 000 ₽ × 4 шт)")

        # 2. modbus_rtu_required — uplift на шкаф +50k за модуль связи.
        if L1.modbus_rtu_required:
            uplift = 50_000
            price_breakdown.cabinet_rub += uplift
            price_breakdown.total_rub += uplift
            price_breakdown.total_dealer_rub = int(round(price_breakdown.total_rub * 0.75))
            pump_notes.append(f"📡 Modbus RTU модуль для SCADA: +{uplift:,} ₽".replace(",", " "))

        # 3a. groundwater_level_m — anti-buoyancy uplift уже учтён в corpus_rub
        # внутри estimate_kns_kit_price; здесь добавляем инженерный note для UX.
        if L1.groundwater_level_m is not None and L1.groundwater_level_m > -2.0:
            from pump_calculator.pricing import (
                _estimate_corpus_volume_m3,
                estimate_anti_buoyancy_uplift_rub,
            )
            v_m3 = _estimate_corpus_volume_m3(Q_m3h)
            uplift = estimate_anti_buoyancy_uplift_rub(
                L1.groundwater_level_m, v_m3, segment,
            )
            if uplift > 0:
                pump_notes.append(
                    f"⚓ Anti-buoyancy ж/б пригруз (СП 32 §6.3, УГВ "
                    f"{L1.groundwater_level_m:+.1f} м): +{uplift:,} ₽".replace(",", " ")
                )

        # 3. above_ground_pavilion — добавить павильон 200-500k в зависимости от Q.
        if L1.above_ground_pavilion:
            # Ориентир: малая КНС (Q≤30) → ~200k, средняя (Q≤100) → ~350k, крупная → ~500k.
            if Q_m3h <= 30:
                pavilion = 200_000
            elif Q_m3h <= 100:
                pavilion = 350_000
            else:
                pavilion = 500_000
            # Кладём в corpus_rub (павильон как часть строительной части).
            price_breakdown.corpus_rub += pavilion
            price_breakdown.total_rub += pavilion
            price_breakdown.total_dealer_rub = int(round(price_breakdown.total_rub * 0.75))
            pump_notes.append(
                f"🏠 Наземный павильон над КНС: +{pavilion:,} ₽".replace(",", " ")
            )

    # Сборка notes из _engineer_note + флаг-предупреждения для пользователя
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

    # 4. dry_run_protection=False — note о риске (warning формируется в select_pumps).
    if L1 is not None and L1.dry_run_protection is False:
        pump_notes.insert(0, (
            "⚠ Защита от сухого хода ОТКЛЮЧЕНА. Насос может перегреться и сгореть "
            "при пустой камере. По СП 32 §6.2 защита от сухого хода обязательна."
        ))

    # 5. inlet_pipe_diam_mm — фиксируем выбранный диаметр подвода в notes.
    if L1 is not None and L1.inlet_pipe_diam_mm:
        pump_notes.append(
            f"🔧 Диаметр подвода (input): DN{int(L1.inlet_pipe_diam_mm)} "
            f"мм — учтён в выборе DN корпуса."
        )

    # 2026-05-11: «Why this pump?» — структурированное объяснение для UI.
    # Шаги 1-4 + цитаты. step_5_segment / rank проставляются в pick_top_per_segment
    # (там известно положение в сегменте).
    H_full_for_explainer = H_full_m if H_full_m else (
        e["H_max_m"] / 1.10 if e.get("H_max_m") else 1.0
    )
    score_explanation = build_score_explanation(
        pump=pump,
        breakdown=breakdown,
        zone=zone,
        Q_m3h=Q_m3h,
        H_full_m=H_full_for_explainer,
        wastewater_type=wastewater_type,
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
        score_explanation=score_explanation,
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
    L1: L1Input | None = None,
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
            L1=L1,
            H_full_m=H_full_m,
        )
        # Duty point — точка работы
        pr.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        # Sync price_estimate_rub после возможных uplift'ов в make_pump_result.
        pr.price_estimate_rub = pr.price_breakdown.total_rub
        # 2026-05-11: проставляем step_5_segment / rank в explainer
        # (известно только тут — позиция в сегменте + всего кандидатов).
        if pr.score_explanation:
            pr.score_explanation["step_5_segment"] = (
                f"Лучший в сегменте «{segment}»: рейтинг 1 из {len(seg_candidates)} "
                f"кандидатов (score={best[1]:.3f})"
            )
            pr.score_explanation["rank_in_segment"] = 1
            pr.score_explanation["candidates_in_segment"] = len(seg_candidates)
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
            L1=L1,
            H_full_m=H_full_m,
        )
        alt.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        alt.price_estimate_rub = alt.price_breakdown.total_rub
        # Alternatives — отметим что это «лучший в бренде» вне топ-сегмента.
        if alt.score_explanation:
            alt.score_explanation["step_5_segment"] = (
                f"Альтернатива из сегмента «{p.get('price_segment')}» "
                f"(другой бренд, score={score:.3f})"
            )
        alternatives.append(alt)

    return results, len(scored), warnings, alternatives


# ----------------------- Шаг 7: триггеры hand-off -----------------------

def build_suggestions(
    L0: L0Input, L1: L1Input | None, computed: ComputedHydraulics, triggers: list[str]
) -> list:
    """«Возможно вы имели в виду...» — мягкие предложения исправить вход.

    Каждое предложение включает физическое/гидравлическое/математическое
    обоснование (формула + следствие). Frontend рендерит модалку «Применить?».
    Никогда не модифицирует L0/L1 — только предлагает.
    """
    from pump_calculator.schemas import InputSuggestion
    suggestions = []

    # 1. Q < 0.1 м³/ч — частая опечатка единиц измерения
    # Физика: типичный человек потребляет ~0.2 м³/сут = 0.0083 м³/ч.
    # КНС на 1 человека — 0.5+ м³/ч (с пиковыми коэф. К_сут × К_час).
    if L0.Q_m3h < 0.1:
        Q_lpm = L0.Q_m3h * 60   # из л/мин → м³/ч если перепутали
        Q_lps = L0.Q_m3h * 3.6  # из л/с → м³/ч если перепутали
        eng_text = (
            f"📏 Единица: Q={L0.Q_m3h} м³/ч = {L0.Q_m3h * 1000:.1f} л/час "
            f"= {L0.Q_m3h * 1000 / 60:.2f} л/мин — это меньше расхода обычного крана.\n"
            f"💡 Если в опросном листе указано {L0.Q_m3h} л/мин, "
            f"в м³/ч это будет {Q_lpm:.1f} (×60).\n"
            f"💡 Если {L0.Q_m3h} л/с — то {Q_lps:.1f} м³/ч (×3.6).\n"
            f"📐 Норма СНиП 2.04.01-85 для бытовой канализации: "
            f"≥ 0.5 м³/ч на 1 человека (с учётом К_неравн = 2.5)."
        )
        mgr_text = (
            f"⚠️ Q={L0.Q_m3h} м³/ч — это меньше расхода одного кухонного крана.\n"
            f"💧 Если клиент дал расход в л/мин — то в правильных единицах "
            f"это {Q_lpm:.1f} м³/ч.\n"
            f"💧 Если в л/с — то {Q_lps:.1f} м³/ч.\n"
            f"📞 Уточните у клиента в каких единицах присылал данные. "
            f"Иначе подберём огромный насос на 5+ кВт за 200+ тыс ₽ — "
            f"для микро-расхода это переплата ×20 и быстрая поломка из-за "
            f"коротких циклов вкл/выкл (защита двигателя ≤6 циклов/час)."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{Q_lpm:.1f}",
            reason=eng_text,
            reason_engineer=eng_text,
            reason_manager=mgr_text,
            severity="critical",
        ))

    # 2. dH отрицательный — нарушение определения «насос как генератор давления»
    # Физика: уравнение Бернулли P₁/(ρg) + z₁ + v²/(2g) = P₂/(ρg) + z₂ + v²/(2g) + h_тр
    # При z₂ < z₁ (отрицательный геометрический напор) насос НЕ нужен —
    # жидкость сама течёт под действием силы тяжести (gh).
    if L0.dH_m is not None and L0.dH_m < 0:
        eng_dh = (
            f"⚖️ Физика: dH = z₂ - z₁ = разность отметок (точка сброса минус "
            f"точка забора). dH={L0.dH_m} м означает что приёмник на |{L0.dH_m}| м "
            f"НИЖЕ источника.\n"
            f"🔬 По уравнению Бернулли P₁/(ρg) + z₁ = P₂/(ρg) + z₂ + h_тр: "
            f"при z₂ < z₁ жидкость течёт самотёком, насос не нужен.\n"
            f"💡 Если приёмник ВЫШЕ источника на {abs(L0.dH_m)} м — "
            f"уберите минус и поставьте {abs(L0.dH_m)}.\n"
            f"📐 По СП 32 §6.4 насос требуется только при положительном "
            f"геометрическом напоре + потерях на трение."
        )
        mgr_dh = (
            f"🌊 dH={L0.dH_m} м — точка сброса НИЖЕ точки забора. "
            f"Вода и так потечёт сама собой, насос не нужен.\n"
            f"💰 Решение: уточните у клиента схему — где источник, где приёмник?\n"
            f"  • Если перепутали знак — поставьте +{abs(L0.dH_m)} м, "
            f"тогда подберём насос (стандартная КНС 200-1500 тыс ₽).\n"
            f"  • Если действительно самотёк — нужен только самотёчный "
            f"коллектор и колодец (60-200 тыс ₽, без насоса вообще).\n"
            f"⏱ Без уточнения тратить время на подбор насоса бессмысленно — "
            f"клиент откажется когда увидит чек."
        )
        suggestions.append(InputSuggestion(
            field="dH_m",
            current_value=f"{L0.dH_m}",
            suggested_value=f"{abs(L0.dH_m)}",
            reason=eng_dh,
            reason_engineer=eng_dh,
            reason_manager=mgr_dh,
            severity="critical",
        ))

    # 3. L < 5 м для Q > 50 м³/ч — несоразмерно
    # Гидравлика: для серьёзных расходов внутриплощадочная трасса обычно
    # 30-100+ м (оборудование разнесено). L < 5 м физически возможен только
    # для микро-объектов (квартира).
    if L0.L_m is not None and L0.L_m < 5 and L0.Q_m3h > 50:
        eng_l = (
            f"📏 L={L0.L_m} м для Q={L0.Q_m3h} м³/ч — несоразмерно.\n"
            f"🔬 Гидравлика: для Q={L0.Q_m3h} м³/ч типовая трасса "
            f"30-100+ м (соединение между КНС, ОС, выпуском). "
            f"L<5 м означает почти отсутствие трубы.\n"
            f"💡 Возможно вы имели в виду {L0.L_m * 10} м (опечатка ×10)?\n"
            f"📐 Для Q≥50 м³/ч обычная норма: L_внутри = 50-200 м, "
            f"L_вне = 200-2000 м (СП 32 §6.5)."
        )
        mgr_l = (
            f"📏 Трасса {L0.L_m} м при расходе {L0.Q_m3h} м³/ч — "
            f"подозрительно мало. Так бывает только если КНС стоит "
            f"прямо у точки сброса (внутри здания).\n"
            f"💰 Если на самом деле трасса {L0.L_m * 10} м (типичная опечатка) — "
            f"подбор изменится: понадобится более мощный насос (+10-30% к цене) "
            f"и больший диаметр трубы.\n"
            f"📞 Уточните у клиента: какое реальное расстояние между КНС "
            f"и точкой сброса/ОС? Если ошибиться — насос не вытянет напор "
            f"и стоки пойдут наружу через 1-2 месяца эксплуатации."
        )
        suggestions.append(InputSuggestion(
            field="L_m",
            current_value=f"{L0.L_m}",
            suggested_value=f"{L0.L_m * 10}",
            reason=eng_l,
            reason_engineer=eng_l,
            reason_manager=mgr_l,
            severity="warning",
        ))

    # 4. v < 0.5 м/с (заиливание) — pipe_D_mm слишком велик
    # СП 32 §5.4: минимальная скорость самоочищения для канализационных
    # стоков v_min = 0.7 м/с (бытовые), 1.0 м/с (производственные).
    # При v < v_min осадок не уносится потоком, происходит заиливание.
    # Формула: D = sqrt(4Q/(πv)), для v=1.2 м/с (оптимум по СП 32).
    if L1 and L1.pipe_D_mm and computed.v_ms < 0.5:
        import math
        Q_m3s = L0.Q_m3h / 3600
        D_optimal = math.sqrt(4 * Q_m3s / (math.pi * 1.2)) * 1000
        for std in [50, 65, 80, 100, 125, 150, 200, 250, 300]:
            if std >= D_optimal:
                D_optimal = std
                break
        eng_vlow = (
            f"🔬 Гидравлика: при D={L1.pipe_D_mm} мм скорость "
            f"v=Q/A=Q/(πD²/4)={computed.v_ms:.3f} м/с.\n"
            f"⚠ По СП 32 §5.4 для бытовой канализации v_min=0.7 м/с — "
            f"при меньших скоростях осадок (взвешенные вещества) не "
            f"уносится, происходит ЗАИЛИВАНИЕ за месяцы.\n"
            f"📐 Расчёт оптимального D: D = √(4Q/(πv)), для v=1.2 м/с "
            f"(середина допустимого диапазона 0.7-2.5 м/с) → "
            f"D = √(4·{Q_m3s:.4f}/(π·1.2))·1000 = {D_optimal} мм (стандартный DN).\n"
            f"💡 Замените pipe_D_mm на {D_optimal}."
        )
        mgr_vlow = (
            f"🌊 Труба DN{int(L1.pipe_D_mm)} слишком широкая для расхода "
            f"{L0.Q_m3h} м³/ч — вода течёт медленно ({computed.v_ms:.2f} м/с), "
            f"осадок (песок, тряпки) оседает прямо в трубе.\n"
            f"💰 Через 3-6 мес труба зарастёт изнутри, насос будет давить "
            f"в забитую трубу — поломка двигателя 80-200 тыс ₽.\n"
            f"💡 Решение: труба DN{int(D_optimal)} вместо DN{int(L1.pipe_D_mm)} — "
            f"экономия на трубе ~30-50% + насос проработает 10 лет вместо 2.\n"
            f"📞 Если клиент настаивает на DN{int(L1.pipe_D_mm)} — "
            f"закладывайте промывку трассы 2 раза в год (40-80 тыс ₽/год OPEX)."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=eng_vlow,
            reason_engineer=eng_vlow,
            reason_manager=mgr_vlow,
            severity="warning",
        ))

    # 5. v > 3 м/с (эрозия) — pipe_D_mm слишком мал
    # СП 32 §5.4: v_max=2.5 м/с (бытовые), 3.0 м/с (производственные).
    # При v > v_max начинается абразивный износ труб (особенно ПЭ),
    # повышается риск гидроудара (Δp_гидроудар ~ ρ·a·Δv по Жуковскому).
    if L1 and L1.pipe_D_mm and computed.v_ms > 3.0:
        import math
        Q_m3s = L0.Q_m3h / 3600
        D_optimal = math.sqrt(4 * Q_m3s / (math.pi * 1.2)) * 1000
        for std in [50, 65, 80, 100, 125, 150, 200, 250, 300]:
            if std >= D_optimal:
                D_optimal = std
                break
        # Расчёт давления гидроудара по Жуковскому
        a_pe100 = 320  # скорость волны в PE100 (м/с)
        delta_p_bar = 1000 * a_pe100 * computed.v_ms / 1e5
        eng_vhigh = (
            f"🔬 Гидравлика: при D={L1.pipe_D_mm} мм скорость "
            f"v={computed.v_ms:.2f} м/с.\n"
            f"⚠ СП 32 §5.4: v_max=2.5 м/с — иначе абразивный износ "
            f"трубы (срок службы падает в 2-3 раза) и эрозия фасонок.\n"
            f"💥 Жуковский: при резком закрытии клапана Δp = ρ·a·Δv = "
            f"1000·320·{computed.v_ms:.2f} ≈ {delta_p_bar:.1f} бар "
            f"(только для PE100, для стали ×3). Может разорвать трубу.\n"
            f"📐 Оптимум: D = √(4Q/(πv)) для v=1.2 м/с → {D_optimal} мм.\n"
            f"💡 Замените pipe_D_mm на {D_optimal}."
        )
        mgr_vhigh = (
            f"🌊 Труба DN{int(L1.pipe_D_mm)} слишком узкая для расхода "
            f"{L0.Q_m3h} м³/ч — вода летит со скоростью {computed.v_ms:.1f} м/с, "
            f"стенки трубы стирает песок и взвесь как наждачкой.\n"
            f"💰 Последствия:\n"
            f"  • Срок службы ПЭ-трубы падает с 50 лет до 15-20 лет.\n"
            f"  • При закрытии клапана возможен гидроудар ~{delta_p_bar:.0f} бар — "
            f"риск разрыва трубы (замена трассы 500-2000 тыс ₽).\n"
            f"💡 Решение: труба DN{int(D_optimal)} вместо DN{int(L1.pipe_D_mm)} — "
            f"увеличение цены трубы ~25-40%, но окупится в первые 5 лет.\n"
            f"⏱ Срок поставки больших диаметров +1-2 недели."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=eng_vhigh,
            reason_engineer=eng_vhigh,
            reason_manager=mgr_vhigh,
            severity="warning",
        ))

    # 6. PE100/PP/PVC + горячая жидкость → деградация полимера
    # Материаловедение: ПЭ100 имеет температуру длительной эксплуатации до 60°C
    # (паспорт ISO 4427). При T > 60°C ускоряется ползучесть, падает долговечность
    # с 50 лет (норма) до 5-10 лет. Сталь — до 200°C при PN16.
    pipe_mat = L1.pipe_material if L1 else None
    temp_c = L1.liquid_temp_c if L1 else None
    if pipe_mat in ("pe100_sdr17", "pp", "pvc") and temp_c is not None and temp_c > 60:
        # Для PP допустимо до 70°C, но запас ниже
        eng_pipe = (
            f"🧪 Материаловедение: {pipe_mat} имеет T_max = 60°C "
            f"для длительной эксплуатации (ISO 4427 для ПЭ100).\n"
            f"📉 При T={temp_c}°C ползучесть ускоряется по закону "
            f"Аррениуса (k = A·exp(-E_a/RT)): срок службы падает "
            f"с 50 лет до 5-10 лет. Возможно разрушение трубы за месяцы.\n"
            f"💡 Замените на steel_seamless_new — до 200°C при PN ≤ 16 бар, "
            f"либо cast_iron_new — до 150°C, дешевле стали."
        )
        mgr_pipe = (
            f"🔥 Полимерная труба ({pipe_mat}) не выдержит стоки T={temp_c}°C — "
            f"размягчится и потечёт через 6-12 мес. Производитель не покрывает "
            f"гарантией работу >60°C.\n"
            f"💰 Замена трубы по материалам:\n"
            f"  • Сталь бесшовная (до 200°C) — +80-150% к цене ПЭ.\n"
            f"  • Чугун ВЧШГ (до 150°C) — +50-100% к цене ПЭ, дешевле стали.\n"
            f"⏱ Срок поставки стали/чугуна 2-4 недели против 1-2 для ПЭ.\n"
            f"📞 Если оставить ПЭ — клиент через год придёт менять всю трассу "
            f"за свой счёт (500-1500 тыс ₽) и будет ругать нас за плохой подбор."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_material",
            current_value=f"{pipe_mat}",
            suggested_value="steel_seamless_new",
            reason=eng_pipe,
            reason_engineer=eng_pipe,
            reason_manager=mgr_pipe,
            severity="critical",
        ))

    # 7. inflow > Q насоса × 1.5 — баланс масс не выполняется
    # Закон сохранения массы: dV/dt = Q_in - Q_out. Если Q_in > Q_out,
    # уровень в приёмной камере растёт линейно: ΔV = (Q_in - Q_out)·t.
    # При V_камеры=10 м³ и Δ=80 м³/ч переполнение через t = 10/80*60 = 7.5 мин.
    if L1 and L1.inflow_per_hour_m3 and L1.inflow_per_hour_m3 > L0.Q_m3h * 1.5:
        suggested_Q = round(L1.inflow_per_hour_m3 * 1.2, 1)
        delta = L1.inflow_per_hour_m3 - L0.Q_m3h
        # Время переполнения камеры 5м³ при текущем балансе
        t_overflow_min = 5.0 / delta * 60 if delta > 0 else float("inf")
        eng_inflow = (
            f"⚖️ Баланс масс (закон сохранения): dV/dt = Q_in - Q_out.\n"
            f"При Q_in={L1.inflow_per_hour_m3} > Q_out={L0.Q_m3h} м³/ч "
            f"уровень растёт со скоростью {delta:.1f} м³/ч.\n"
            f"⏱ Камера 5 м³ переполнится за {t_overflow_min:.1f} мин — "
            f"стоки пойдут на улицу.\n"
            f"💡 Решение 1: Q_насоса = Q_in × 1.2 = {suggested_Q} м³/ч "
            f"(+20% запас по СП 32 §6.5).\n"
            f"💡 Решение 2: 2-3 насоса параллельно (1+1 рабочий+резерв).\n"
            f"💡 Решение 3: увеличить V_камеры (буфер) — но это OPEX, не CAPEX."
        )
        mgr_inflow = (
            f"⚖️ Приток в КНС ({L1.inflow_per_hour_m3} м³/ч) больше, чем "
            f"вытаскивает насос ({L0.Q_m3h} м³/ч). Камера переполнится "
            f"за {t_overflow_min:.0f} минут, стоки польются на улицу.\n"
            f"💰 Решения:\n"
            f"  • Поставить насос побольше Q={suggested_Q} м³/ч — "
            f"+20-40% к цене насоса.\n"
            f"  • Поставить 2 насоса в параллель (раб+рез по СП 32) — "
            f"+60-100% к цене (2× оборудования).\n"
            f"⏱ Без увеличения мощности — первый ливень = аварийный звонок "
            f"клиента + штраф Росприроднадзора 100-500 тыс ₽ "
            f"за загрязнение земли (КоАП ст.8.6).\n"
            f"📞 Срочно уточните реальный приток у клиента (паспорт объекта)."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{suggested_Q}",
            reason=eng_inflow,
            reason_engineer=eng_inflow,
            reason_manager=mgr_inflow,
            severity="critical",
        ))

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: 10 научных расширений — suggestions с 2-level reasons
    # ──────────────────────────────────────────────────────────────────

    # EXT-1: боковое давление грунта (СП 22.13330.2016 §5.6.5)
    # v0.3 (2026-05-13): теперь учитывает L1.soil_type (PhD-Mechanics audit
    # P1-4) и σ_водн = γ_w·z_w при УГВ выше дна (P0-3, реальный кейс
    # эталона Евпатория). Если soil_type не задан — fallback на default
    # sand_medium (старое поведение, K_a=0.33).
    if "auto_lateral_earth_pressure" in triggers and L1 and L1.install_depth_inlet_mm:
        # v0.4 (2026-05-13): рефакторинг под единый GroundContext
        # (Sc.D. cross-domain P0 «N×M связность soil/gwl/T»). γ/φ/K_a/K_p
        # читаются из coefficients.json soil_parameters_sp22.
        from pump_calculator.structural import (
            GroundContext,
            check_corpus_strength,
        )
        ctx = GroundContext.from_l1(L1)
        z_m = ctx.install_depth_m
        result = check_corpus_strength(ctx, z_max_m=z_m)
        gamma = ctx.gamma_kN_m3
        phi = ctx.phi_deg
        K_a = ctx.K_a
        K_p = ctx.K_p
        sigma_x_grunt_kpa = result["pressure_breakdown"]["soil_active_kPa"]
        sigma_x_water_kpa = result["pressure_breakdown"]["water_kPa"]
        sigma_x_kpa = result["sigma_total_kPa"]
        sigma_p_kpa = result["pressure_breakdown"]["passive_resistance_kPa"]
        gwl_note = ""
        if sigma_x_water_kpa > 0:
            z_w = ctx.gwl_above_bottom_m
            gwl_note = (
                f"\n💧 УГВ ({ctx.groundwater_level_m:.1f} м от земли) выше дна "
                f"корпуса на {z_w:.1f} м. СП 22 §5.6.5: добавляется "
                f"σ_водн = γ_w·z_w = 9.81·{z_w:.1f} ≈ {sigma_x_water_kpa:.1f} кПа."
            )
        sigma_PE_kpa = result["sigma_allowable_kPa"]
        overstress_note = ""
        if sigma_x_kpa > sigma_PE_kpa:
            overstress_note = (
                f"\n🚨 σ_x={sigma_x_kpa:.0f} кПа > σ_доп ПЭ100 SDR17 (50 кПа). "
                f"Рекомендация: {result['recommendation']}."
            )
        # K_p — пассивный отпор грунта для глубоких котлованов ≥5 м
        # (откол грунта при открытой траншее, СП 22 §5.6.2).
        kp_note = ""
        if z_m >= 5.0:
            kp_note = (
                f"\n🪨 K_p={K_p:.2f} (пассивный отпор грунта) — при открытом "
                f"котловане σ_p = γ·z·K_p ≈ {sigma_p_kpa:.0f} кПа удерживает "
                f"стенку. Контролировать откол при глубине ≥5 м."
            )
        eng = (
            f"🪨 СП 22.13330.2016 «Основания зданий и сооружений», §5.6.5 — "
            f"расчёт горизонтального давления грунта по теории Кулона.\n"
            f"📐 Формула: σ_x = γ·z·K_a + γ_w·z_w (при УГВ выше дна), "
            f"K_a = tan²(45°-φ/2).\n"
            f"Грунт: {ctx.label} (γ={gamma} кН/м³, φ={phi}°, K_a={K_a:.2f}).\n"
            f"При z={z_m:.1f} м: σ_грунт = {gamma}·{z_m:.1f}·{K_a:.2f} ≈ "
            f"{sigma_x_grunt_kpa:.1f} кПа.{gwl_note}\n"
            f"Σ σ_x ≈ {sigma_x_kpa:.1f} кПа на стенку корпуса.{overstress_note}{kp_note}\n"
            f"⚠ Для ПЭ-корпуса σ_доп=50 кПа (SDR17) / 80 кПа (SDR11) по ISO 9080. "
            f"При превышении — рёбра жёсткости и/или ж/б обойма."
        )
        mgr = (
            f"🏗 Глубина {z_m:.1f} м, грунт: {ctx.label}.\n"
            f"💰 Давление грунта {sigma_x_kpa:.0f} кПа на корпус.\n"
            f"  • Если σ_x ≤ 50 кПа — стандартный ПЭ100 SDR17 OK.\n"
            f"  • Если 50-80 кПа — нужен SDR11 (+15-25% цены корпуса).\n"
            f"  • Если >80 кПа — рёбра жёсткости (+150-300 тыс ₽) "
            f"или ж/б обойма (+800 тыс — 1.5 млн ₽).\n"
            f"⏱ Срок изготовления усиленного корпуса +3-5 недель.\n"
            f"📞 Передайте инженеру для расчёта по СП 22.13330."
        )
        suggestions.append(InputSuggestion(
            field="L1.install_depth_inlet_mm",
            current_value=f"{L1.install_depth_inlet_mm}",
            suggested_value=f"{L1.install_depth_inlet_mm}",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-2: класс нагрузки крышки (СП 35.13330)
    if "auto_traffic_load_class" in triggers and L1:
        eng = (
            f"🚛 СП 35.13330 «Мосты и трубы», табл.6.4 — классы нагрузки крышек "
            f"по EN 124:\n"
            f"  • A15 (15 кН) — пешеходные зоны\n"
            f"  • B125 (125 кН) — паркинги легковых\n"
            f"  • C250 (250 кН) — заездные карманы\n"
            f"  • D400 (400 кН) — проезжие части дорог\n"
            f"📐 При install_depth={L1.install_depth_inlet_mm} мм без павильона "
            f"крышка находится на уровне земли — высокий риск наезда транспорта.\n"
            f"⚠ Чугунная D400 обязательна если возможен заезд авто."
        )
        mgr = (
            "🚧 Корпус КНС без павильона на малой глубине — крышка на уровне земли.\n"
            "💰 Стоимость крышки по классам:\n"
            "  • A15 (тротуар) — 8-15 тыс ₽\n"
            "  • B125 (паркинг) — 25-40 тыс ₽\n"
            "  • D400 (дорога) — 60-120 тыс ₽\n"
            "⏱ Уточните у клиента: возможен ли заезд авто над КНС? "
            "Если да — закладывайте D400, иначе риск разрушения за 1 сезон."
        )
        suggestions.append(InputSuggestion(
            field="L1.cover_load_class",
            current_value="не задано",
            suggested_value="D400",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-3: заземление (ПУЭ 1.7)
    if "auto_grounding_required" in triggers and L1:
        why = "взрывозащита" if L1.Ex_required else "I категория надёжности"
        eng = (
            f"⚡ ПУЭ 1.7 «Заземление и защитные меры», п.1.7.103 — "
            f"требование к заземляющему устройству для {why}.\n"
            f"📐 R_зазем ≤ 4 Ом для системы TN-S; ≤ 10 Ом для повторного "
            f"заземления (ПУЭ 1.7.62).\n"
            f"🔬 Расчёт по СО 153-34.21.122: R = ρ_грунта/(2π·L)·ln(2L/d), "
            f"где ρ — удельное сопротивление грунта (Ом·м), L — длина "
            f"электрода, d — диаметр.\n"
            f"⚠ Для Ex-зон обязательно: уравнивание потенциалов всех "
            f"металлических корпусов + контур ≤ 4 Ом."
        )
        mgr = (
            f"⚡ Для объекта с {why} требуется отдельный контур заземления.\n"
            f"💰 Стоимость:\n"
            f"  • Базовый контур (3-5 электродов) — 35-60 тыс ₽\n"
            f"  • Молниеотвод + уравнивание — 80-150 тыс ₽\n"
            f"  • Замер сопротивления + протокол — 12-18 тыс ₽\n"
            f"⏱ Монтаж 2-4 дня. Без протокола замера ввод в эксплуатацию "
            f"запрещён (Ростехнадзор)."
        )
        suggestions.append(InputSuggestion(
            field="L1.grounding_required",
            current_value="не учтено",
            suggested_value="контур ≤ 4 Ом",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-4: молниезащита (СО 153-34.21.122)
    if "auto_lightning_protection_required" in triggers:
        eng = (
            "🌩 СО 153-34.21.122-2003 «Молниезащита зданий и сооружений», "
            "п.2.2 — наземное здание подлежит классификации по уровню защиты:\n"
            "  • I уровень — взрывоопасные зоны (Ex)\n"
            "  • II уровень — пожароопасные / I категория надёжности\n"
            "  • III-IV уровень — обычные здания\n"
            "📐 Зона защиты молниеотвода (одиночный стержень): "
            "R_зоны = 1.5·h_стержня (тип А).\n"
            "⚠ Для электрооборудования внутри павильона — обязательны УЗИП "
            "класса I (ГОСТ Р 51992-2011), I_имп ≥ 25 кА."
        )
        mgr = (
            "🌩 Наземный павильон требует молниезащиты (СО 153-34.21.122).\n"
            "💰 Комплект:\n"
            "  • Молниеотвод-стержень с креплением — 25-45 тыс ₽\n"
            "  • УЗИП класса I в ШУ — 18-30 тыс ₽\n"
            "  • Контур + спуск + протокол — 60-90 тыс ₽\n"
            "📞 Один удар молнии без защиты убивает ШУ + ЧРП "
            "(~400 тыс ₽ замены) и приводит к пожару павильона."
        )
        suggestions.append(InputSuggestion(
            field="L1.lightning_protection",
            current_value="не учтено",
            suggested_value="молниеотвод + УЗИП",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # EXT-5: утепление труб (СП 41-103)
    if "auto_pipe_insulation_required" in triggers and L1:
        reason_short = (
            "горячая жидкость (>40°C)"
            if (L1.liquid_temp_c and L1.liquid_temp_c > 40)
            else "холодный регион (горы)"
        )
        eng = (
            f"🧊 СП 41-103-2000 «Тепловая изоляция оборудования и "
            f"трубопроводов», табл.7.1 — требования к толщине изоляции.\n"
            f"📐 Тепловой поток через стенку: q = 2πλΔT/ln(D₂/D₁) Вт/м, "
            f"где λ — коэф. теплопроводности изоляции (Вт/м·К).\n"
            f"Для пеноПЭ λ=0.04, при ΔT=50°C, D₁=110, D₂=160 мм: "
            f"q ≈ 33 Вт/м.\n"
            f"Причина: {reason_short}.\n"
            f"⚠ Без изоляции в холодных регионах — замерзание за 4-8 ч "
            f"простоя; для горячих стоков — потери температуры > 5°C/100 м."
        )
        mgr = (
            f"🧊 Требуется утепление напорной трассы ({reason_short}).\n"
            f"💰 Стоимость:\n"
            f"  • Трубчатая ПЭ-изоляция (Energoflex) — 250-450 ₽/п.м\n"
            f"  • Минвата с фольгой (для горячих) — 500-800 ₽/п.м\n"
            f"  • Кожух из оцинковки — +600-900 ₽/п.м\n"
            f"  • Монтаж — 200-300 ₽/п.м\n"
            f"⏱ Для трассы 100 м: ориентир 130-200 тыс ₽ под ключ."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_insulation",
            current_value="не учтено",
            suggested_value="требуется изоляция",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-6: греющий кабель
    if "auto_heating_cable_required" in triggers and L1 and L1.altitude_m is not None:
        # Бытовая мощность саморегулирующегося кабеля ~30 Вт/м
        eng = (
            f"🔥 Греющий кабель для напорной трассы — высота "
            f"{L1.altitude_m:.0f} м (горный регион, минимальная T_зимы < -25°C).\n"
            f"📐 Расчёт мощности: P = K·π·D·(T_внутр - T_окр)/R_изол, "
            f"где K — коэф. теплопередачи (Вт/м²·К).\n"
            f"Для DN50-150 без изоляции: P ≈ 30 Вт/м (саморегулирующийся "
            f"кабель типа FROSTOP-Black, Raychem или Lavita).\n"
            f"⚠ Запитка через УЗО 30 мА (ПУЭ 7.1.79). При длине трассы L "
            f"общая мощность P_total = 30·L Вт."
        )
        mgr = (
            f"🔥 Объект на высоте {L1.altitude_m:.0f} м (горы) — "
            f"в зимние морозы трубы замёрзнут за часы простоя.\n"
            f"💰 Греющий кабель саморегулирующийся 30 Вт/м:\n"
            f"  • Кабель — 850-1200 ₽/п.м\n"
            f"  • Терморегулятор + датчик — 8-15 тыс ₽\n"
            f"  • УЗО 30 мА + автомат — 4-7 тыс ₽\n"
            f"  • Монтаж + запенивание — 400-600 ₽/п.м\n"
            f"⏱ Для трассы 100 м: 150-200 тыс ₽ комплект + монтаж."
        )
        suggestions.append(InputSuggestion(
            field="L1.heating_cable",
            current_value="не учтено",
            suggested_value="30 Вт/м саморегулирующийся",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-7: седиментация Stokes
    if "auto_sedimentation_check" in triggers:
        # v_осаж по Стоксу для песчинки 0.5 мм, ρ=2650 кг/м³
        rho_p = 2650
        rho_w = 1000
        g = 9.81
        d_m = 0.5e-3
        mu = 1e-3
        v_sed = (rho_p - rho_w) * g * d_m**2 / (18 * mu)  # м/с
        eng = (
            f"⚗ Закон Стокса для седиментации частиц в промстоках:\n"
            f"📐 v_осаж = (ρ_частицы - ρ_воды)·g·d²/(18·μ)\n"
            f"Для песчинки d=0.5 мм, ρ_p=2650 кг/м³, μ=1e-3 Па·с:\n"
            f"v_осаж = (2650-1000)·9.81·(5e-4)²/(18·1e-3) ≈ {v_sed*1000:.1f} мм/с "
            f"= {v_sed*60*100:.1f} см/мин.\n"
            f"⚠ При Q={L0.Q_m3h} м³/ч (industrial) поток в DN150 v≈{L0.Q_m3h*4/3600/3.14/0.15**2:.2f} м/с — "
            f"крупные частицы (>0.5 мм) оседают в трубе и приёмной камере.\n"
            f"💡 Решение: песколовка / гидроциклон до КНС "
            f"(СП 32 §7.4 — обязательна для содержания песка >100 мг/л)."
        )
        mgr = (
            f"⚗ Промстоки с малым расходом Q={L0.Q_m3h} м³/ч — поток "
            f"медленный, песок оседает в трубах и насосе.\n"
            f"💰 Песколовка тангенциальная DN300:\n"
            f"  • Корпус ПЭ — 85-140 тыс ₽\n"
            f"  • Гидроциклон чугунный — 180-320 тыс ₽\n"
            f"  • Монтаж + обвязка — 40-70 тыс ₽\n"
            f"⏱ Без песколовки замена рабочего колеса насоса каждые "
            f"6-12 мес (1 колесо = 80-200 тыс ₽)."
        )
        suggestions.append(InputSuggestion(
            field="L1.sand_separator",
            current_value="не учтено",
            suggested_value="песколовка/гидроциклон",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-8: УФ/озон обеззараживание (v0.4: dose дифференцирована по target_discharge)
    if "auto_disinfection_required" in triggers:
        uv_dose, target = _ext_8_uv_dose_required(L1)
        eng = (
            f"🦠 СанПиН 2.1.5.980-00 «Гигиенические требования к охране "
            f"поверхностных вод», п.4.1.5 — обеззараживание стоков "
            f"перед сбросом в водоём (хоз-бытовые Q={L0.Q_m3h} > 100 м³/ч).\n"
            f"📐 УФ-доза по МУК 4.3.2030-05: D = I·t ≥ {uv_dose} мДж/см² "
            f"для целевого сброса '{target}' (E.coli 3 lg, колифаги 2 lg).\n"
            f"📐 NB для непрозрачных стоков (turbidity > 30 NTU) — озон "
            f"вместо УФ: C·t ≥ 5 мг·мин/л.\n"
            f"⚠ Хлорирование запрещено для сброса в рыбохозяйственные "
            f"водоёмы (Приказ Росрыболовства №20).\n"
            f"💡 30 мДж/см² — стандарт general_use; для fishery_water "
            f"требуется 80-120 мДж/см² с предобработкой."
        )
        mgr = (
            f"🦠 Q={L0.Q_m3h} м³/ч хоз-бытовых, сброс в '{target}' — "
            f"по СанПиН требуется УФ-доза {uv_dose} мДж/см².\n"
            f"💰 Варианты:\n"
            f"  • УФ-стерилизатор Sita / Wedeco на Q=100-200 — 380-650 тыс ₽\n"
            f"  • Озонатор 50-100 г/ч — 850 тыс — 1.5 млн ₽\n"
            f"  • Контактная камера + смеситель — 120-220 тыс ₽\n"
            f"  • Лампы УФ замена раз в год — 35-60 тыс ₽/год OPEX\n"
            f"⏱ Без обеззараживания штраф Росприроднадзора 250-500 тыс ₽ "
            f"(ст.8.13 КоАП) + остановка сброса."
        )
        suggestions.append(InputSuggestion(
            field="L1.disinfection",
            current_value="не учтено",
            suggested_value="УФ или озон",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-9: нитри/денитрификация (v0.4: точный расчёт по NH4 / C:N / target)
    if "auto_nitrification_check" in triggers:
        # Перевычисляем dict-параметры (single source of truth — _check_ext_9_nitrification)
        ext9 = _check_ext_9_nitrification(L0, L1, computed)
        if ext9 is None:
            # Safety: триггер прошёл, но детали не совпали (T/UI desync).
            # Используем generic-фолбэк без чисел.
            ext9 = {
                "nh4": 25.0, "bod5": 250.0, "c_to_n": 10.0,
                "T": 20.0, "nh4_limit": 2.0, "target": "municipal_sewage",
                "srt_min_d": 15.0,
            }
        eng = (
            f"🧪 Нитри/денитрификация в ЛОС (СП 32.13330 §9.2.5 + Henze IWA "
            f"2008 §3.4).\n"
            f"📐 Параметры стоков: NH4_in={ext9['nh4']:.0f} мг/л > "
            f"ПДК={ext9['nh4_limit']} мг/л для '{ext9['target']}', "
            f"C:N=БПК5/N={ext9['c_to_n']:.1f}, T={ext9['T']:.0f}°C.\n"
            f"📐 Кинетика по Monod: μ = μ_max·S/(K_s+S), где для "
            f"Nitrosomonas μ_max=0.8 сут⁻¹, K_s≈1 мг/л NH4-N (Henze IWA "
            f"§3.4, Arrhenius θ=1.103).\n"
            f"📐 SRT_min = 15·1.103^(15−T) = {ext9['srt_min_d']:.1f} сут.\n"
            f"⚠ Условия для биоты (нитрификаторы Nitrosomonas+Nitrobacter):\n"
            f"  • Возраст ила θ_c ≥ {ext9['srt_min_d']:.0f} сут\n"
            f"  • Аэрация DO ≥ 2 мг/л в зоне нитрификации\n"
            f"  • MLSS 3-5 г/л (активный ил), пенный индекс <150 мл/г\n"
            f"  • T 12-35°C (вне диапазона нитрификаторы гибнут)\n"
            f"  • pH 7.5-8.5 (оптимум для аммоний-окисляющих)\n"
            f"  • Рециркуляция нитратов 200-400% для денитрификации.\n"
            f"📐 Объём аэротенка: V = Q·SRT_min/MLSS·(1+R_recycle)."
        )
        mgr = (
            f"🧪 Аммоний NH4={ext9['nh4']:.0f} мг/л превышает норматив "
            f"({ext9['nh4_limit']} мг/л для '{ext9['target']}') — нужна "
            f"биологическая очистка (аэротенк с активным илом).\n"
            f"💰 ЛОС на Q={L0.Q_m3h} м³/ч с нитри/денитри:\n"
            f"  • Аэротенк ж/б 50-150 м³ — 1.5-3.5 млн ₽\n"
            f"  • Воздуходувка + аэраторы — 450-850 тыс ₽\n"
            f"  • Вторичный отстойник — 380-720 тыс ₽\n"
            f"  • Автоматика DO/pH/NH4 — 280-450 тыс ₽\n"
            f"⏱ Срок: 4-6 нед проектирование+поставка, ~600-1200 тыс ₽ "
            f"к стоимости ЛОС. Запуск биоценоза 4-8 недель.\n"
            f"📞 Передайте инженеру-технологу для расчёта по реальным "
            f"показателям сточных вод (БПК, ХПК, NH4, P)."
        )
        suggestions.append(InputSuggestion(
            field="L1.nitrification_required",
            current_value="не учтено",
            suggested_value="аэротенк θ_c≥10 сут",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-12 (v0.3 2026-05-13): термический derating двигателя (IEC 60034-1 §8.10)
    if "auto_motor_thermal_derate" in triggers and L1 and L1.liquid_temp_c is not None:
        T = L1.liquid_temp_c
        # K_derate из coefficients.json motor_thermal_derating_iec60034
        _K_DERATE_TABLE = [
            (40, 1.00), (50, 0.90), (60, 0.80), (65, 0.70), (70, 0.60),
        ]
        K = 1.0
        for T_max, k_val in _K_DERATE_TABLE:
            if T <= T_max:
                K = k_val
                break
        else:
            K = 0.60
        derate_pct = int((1.0 - K) * 100)
        eng = (
            f"🔥 IEC 60034-1:2017 §8.10.2 «Temperature derating» — "
            f"снижение допустимой мощности двигателя при повышенной "
            f"температуре жидкости.\n"
            f"📐 Поправка K_derate = {K:.2f} ({derate_pct}% derating) при "
            f"T_жидк = {T:.0f}°C.\n"
            f"  • T ≤40°C: K=1.00 (номинал, класс изоляции F)\n"
            f"  • T 41-50°C: K=0.90 (граница F)\n"
            f"  • T 51-60°C: K=0.80 + обязателен класс H (180°C)\n"
            f"  • T 61-65°C: K=0.70 + PTC-термистор обмотки\n"
            f"  • T >65°C: K=0.60 + jacket cooling или поверхностный насос\n"
            f"⚠ Без derate двигатель сгорает за 1-3 месяца. ГОСТ Р 52776."
        )
        mgr = (
            f"🌡 Температура стоков {T:.0f}°C — выше нормы для стандартного "
            f"двигателя.\n"
            f"💰 Нужны:\n"
            f"  • Двигатель класса H (изоляция 180°C) — +25-40% к цене насоса\n"
            f"  • PTC-термистор обмотки + защита класса 10A в ШУ — +15-30 тыс ₽\n"
            f"  • Запас мощности {derate_pct}% — берите следующий типоразмер\n"
            f"⏱ Срок изготовления Ex-H исполнения +6-10 недель.\n"
            f"📞 Передайте инженеру для подбора Wilo Rexa SUPRA-class или "
            f"KSB Amarex KRT с water-jacket cooling."
        )
        suggestions.append(InputSuggestion(
            field="L1.liquid_temp_c",
            current_value=f"{T:.0f}°C",
            suggested_value=f"K_derate={K:.2f}, изоляция H",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical" if T > 60 else "warning",
        ))

    # EXT-13 (v0.3 2026-05-13): анаэробная биокоррозия бетона при простоях
    if "auto_anaerobic_corrosion_risk" in triggers:
        cycles = (computed.cycles_per_hour_estimate
                  if computed and computed.cycles_per_hour_estimate is not None
                  else 0.0)
        eng = (
            "🦠 Metcalf & Eddy «Wastewater Engineering» 5th ed. (2014) §5-4 — "
            "анаэробная биокоррозия бетона КНС.\n"
            "📐 Механизм:\n"
            "  • При простое >12ч сульфаты SO4²⁻ восстанавливаются "
            "бактериями Desulfovibrio до H2S (анаэробно).\n"
            "  • H2S мигрирует в крышку, где влажная плёнка + Thiobacillus → "
            "H2SO4 (pH 1-2).\n"
            "  • Скорость разрушения бетона: 5-15 мм/год по своду крышки.\n"
            f"⚠ Расчётные циклы вкл/выкл: {cycles:.2f}/ч — слишком "
            f"редкие пуски (норма 2-15/ч).\n"
            "📋 Меры:\n"
            "  • Защитное покрытие бетона эпоксидом (Sika, MasterSeal) — "
            "20 лет ресурса\n"
            "  • Вентиляция приёмной камеры 8-12 крат/ч (СП 60.13330 §7.5)\n"
            "  • Nitrate-shock dosing (NaNO3, 50-100 мг/л при простоях)\n"
            "  • Или замена на ПЭ/стеклопластик корпус (нет H2S коррозии)."
        )
        mgr = (
            "🦠 Большие интервалы между запусками → биокоррозия бетона.\n"
            "💰 Защита:\n"
            "  • Эпоксидное покрытие бетонной крышки — 80-150 тыс ₽\n"
            "  • Вентилятор + воздуховоды — 45-90 тыс ₽\n"
            "  • Дозатор нитратов NaNO3 (опционально) — 35-60 тыс ₽\n"
            "  • Или сразу ПЭ-корпус (Серво-Юг default) — без коррозии\n"
            "⏱ Без защиты бетонный корпус разрушится за 5-10 лет вместо 50.\n"
            "📞 Передайте инженеру для решения о материале корпуса."
        )
        suggestions.append(InputSuggestion(
            field="L1.corpus_material",
            current_value="bетон (предполагается)",
            suggested_value="pe (ПЭ) или защитное покрытие бетона",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-10: гидробак ВНС (СП 30.13330)
    if "auto_hydrobak_required" in triggers:
        # V_бака = (Q_max - Q_min)·t_цикл/4, типовое t_цикл=6 мин (10 пусков/час)
        Q_min = L0.Q_m3h * 0.2  # типовое 20% от номинала
        Q_max = L0.Q_m3h
        t_cycle_min = 6.0
        V_bak_l = (Q_max - Q_min) * 1000 * (t_cycle_min / 60) / 4
        eng = (
            f"💧 СП 30.13330.2020 «Внутренний водопровод», п.11.7 — "
            f"гидроаккумулятор для повысительной насосной с переменным расходом.\n"
            f"📐 Расчёт ёмкости: V_бака = (Q_max - Q_min)·t_цикл / 4·a, "
            f"где a — число включений/час (обычно ≤ 10), t_цикл — "
            f"длительность одного цикла.\n"
            f"Для Q_max={Q_max:.1f}, Q_min={Q_min:.1f} м³/ч, t=6 мин:\n"
            f"V = ({Q_max:.1f} - {Q_min:.1f}) · 1000 · (6/60) / 4 ≈ "
            f"{V_bak_l:.0f} литров.\n"
            f"⚠ Без гидробака ЧРП работает в режиме «дёрганья» — "
            f"частые пуски, гидроудары, износ обратного клапана."
        )
        mgr = (
            f"💧 Q={L0.Q_m3h} м³/ч ВНС чистой воды — нужен гидроаккумулятор "
            f"для сглаживания пиков (СП 30.13330).\n"
            f"💰 Мембранный гидробак ~{V_bak_l:.0f} л:\n"
            f"  • Reflex / Wester / Джилекс 500-1000 л — 45-95 тыс ₽\n"
            f"  • Большой 2000-5000 л — 180-380 тыс ₽\n"
            f"  • Манометр + предохранительный клапан — 8-15 тыс ₽\n"
            f"  • Подключение + мембраны замена раз в 5 лет — 12-25 тыс ₽\n"
            f"⏱ Без гидробака — частые пуски ЧРП (ресурс ЧРП -50%, "
            f"замена 280-450 тыс ₽ через 2-3 года вместо 6-8)."
        )
        suggestions.append(InputSuggestion(
            field="L1.hydrobak_volume_l",
            current_value="не учтено",
            suggested_value=f"{V_bak_l:.0f} л",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # EXT-11: anti-buoyancy при УГВ > 0 (СП 32 §6.3 + Архимед).
    # Если УГВ выше отметки земли, площадка затоплена — корпус КНС всплывёт
    # без бетонного пригруза. Critical, suggestion с ценой пригруза.
    if (
        "auto_groundwater_above_surface" in triggers
        and L1
        and L1.groundwater_level_m is not None
    ):
        gw = L1.groundwater_level_m
        # Грубая оценка V_корпуса по Q (см. _estimate_corpus_volume_m3).
        if L0.Q_m3h <= 30:
            V_corpus = 5.7
        elif L0.Q_m3h <= 60:
            V_corpus = 6.8
        elif L0.Q_m3h <= 130:
            V_corpus = 12.6
        elif L0.Q_m3h <= 252:
            V_corpus = 28.3
        else:
            V_corpus = 55.4
        # F_Архимеда = ρ·g·V (ρ=1000, g=9.81)
        F_arch_kn = 1000 * 9.81 * V_corpus / 1000.0  # кН
        F_arch_t = F_arch_kn / 9.81  # тонн (масса эквивалента)
        # V_бетона ≥ F / (ρ_бет_эфф · g), ρ_эфф_подвода = 1400
        V_concrete_m3 = F_arch_kn * 1000.0 / (1400.0 * 9.81)
        eng = (
            f"⚓ Закон Архимеда + СП 32.13330.2018 §6.3 — расчёт пригруза.\n"
            f"📐 Подъёмная сила: F = ρ_воды · g · V_корпуса = "
            f"1000 · 9.81 · {V_corpus:.1f} = {F_arch_kn:.0f} кН ({F_arch_t:.1f} тонн).\n"
            f"📐 Удержание ж/б пригрузом: V_бетон ≥ F / (ρ_бет_эфф · g), "
            f"где ρ_бет_эфф = ρ_бет − ρ_воды = 2400 − 1000 = 1400 кг/м³ "
            f"(бетон сам в воде).\n"
            f"V_бетон = {F_arch_kn:.0f} · 1000 / (1400 · 9.81) ≈ "
            f"{V_concrete_m3:.1f} м³ ж/б класса B20-B25.\n"
            f"При УГВ = {gw:+.1f} м (выше уровня земли) площадка постоянно "
            f"затоплена — без пригруза корпус всплывёт за 1-3 года при паводке.\n"
            f"⚠ K_запаса = 1.1 (СП 32 §6.3); для Ex-зон и I категории — 1.5."
        )
        mgr = (
            f"⚓ УГВ выше земли на {gw:+.1f} м — площадка затоплена. "
            f"Без бетонного пригруза корпус КНС всплывёт через 2-3 года "
            f"при первом паводке.\n"
            f"💰 Стоимость:\n"
            f"  • Ж/б пригруз ({V_concrete_m3:.1f} м³ ≈ {F_arch_t:.0f} тонн) — "
            f"200-500 тыс ₽ сразу (бетон + арматура + опалубка).\n"
            f"  • Усиление обоймы корпуса по СП 22 §5.4 — +50-150 тыс ₽.\n"
            f"⚠ Если не учесть: аварийный ремонт (откопка + монтаж пригруза + "
            f"замена корпуса) — 500-1500 тыс ₽ + остановка КНС на 2 недели.\n"
            f"📞 Передайте инженеру для детального расчёта по СП 32 §6.3 "
            f"(structural/ballast.py)."
        )
        suggestions.append(InputSuggestion(
            field="L1.groundwater_level_m",
            current_value=f"{gw:+.1f}",
            suggested_value=f"ж/б пригруз {V_concrete_m3:.1f} м³",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-11: 11 legacy triggers без отдельной InputSuggestion —
    # дополняем 2-level пояснения для UI «возможно вы имели в виду».
    # Frontend рендерит таб «Инженер»/«Менеджер» по reason_engineer/_manager.
    # ──────────────────────────────────────────────────────────────────

    # LEG-1: auto_q_high — Q > 500 м³/ч
    if "auto_q_high" in triggers:
        eng = (
            f"📈 Q={L0.Q_m3h} м³/ч > 500 — выход за диапазон бюджетных серий "
            f"(ANTARUS / Pedrollo / CNP заканчиваются на ~400-500 м³/ч).\n"
            f"🔬 Для такого расхода применяются промышленные классы: "
            f"  • Центробежные одноступенчатые (KSB Sewabloc, Wilo EMU FA) "
            f"до 1500 м³/ч.\n"
            f"  • Многоступенчатые ЦНС (ЦНС-300, ЦНС-500) для напоров > 50 м.\n"
            f"📐 NPSHr таких насосов 5-8 м — требуется проверка кавитации.\n"
            f"⚠ AOR-зона уже на 70-115% BEP; работа вне AOR резко снижает "
            f"ресурс рабочего колеса (СП 32 §6.5)."
        )
        mgr = (
            f"🏭 Расход {L0.Q_m3h} м³/ч — это уже промышленный масштаб "
            f"(район/посёлок/завод).\n"
            f"💰 Цена:\n"
            f"  • Насос промышленный — 500 тыс — 2.5 млн ₽ за единицу.\n"
            f"  • КНС-комплект 2+1 — 3-8 млн ₽ под ключ.\n"
            f"⏱ Срок поставки нестандартного заказа — 4-8 недель "
            f"(склада нет, делают под проект).\n"
            f"📞 Обязательно передайте инженеру — нужен индивидуальный "
            f"расчёт магистральной КНС, бюджетные серии не подойдут."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value="промышленная КНС, инженерный подбор",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-2: auto_h_high — H_full > 80 м
    if "auto_h_high" in triggers:
        eng = (
            f"📈 H_full={computed.H_full_m:.1f} м > 80 — за пределами "
            f"одноступенчатых центробежных канализационных насосов.\n"
            f"🔬 Для H>80 нужны:\n"
            f"  • Многоступенчатые насосы CR/MFL/ЦНС (вертикальные in-line).\n"
            f"  • Либо бустер-станция: 2 КНС последовательно с промежуточным "
            f"резервуаром (СП 32 §6.5).\n"
            f"📐 NPSH_required растёт с числом ступеней (NPSHr ~ k·√i) — "
            f"риск кавитации при низком подпоре."
        )
        mgr = (
            f"⛰ Напор {computed.H_full_m:.0f} м — это подъём на 20+ этажей. "
            f"Обычные канализационные насосы такое не вытягивают.\n"
            f"💰 Цена:\n"
            f"  • Многоступенчатый насос CR/MFL — 600 тыс — 1.2 млн ₽.\n"
            f"  • Бустер-станция (2 КНС) — 1.5-3 млн ₽.\n"
            f"⏱ Спецзаказ под проект, срок 4-6 недель.\n"
            f"📞 Передайте инженеру — нужен расчёт по двум вариантам "
            f"(одна высоконапорная vs две последовательные)."
        )
        suggestions.append(InputSuggestion(
            field="H_full_m",
            current_value=f"{computed.H_full_m:.1f}",
            suggested_value="multi-stage или бустер",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-3: auto_industrial — wastewater_type=industrial
    if "auto_industrial" in triggers:
        eng = (
            "🏭 Промстоки требуют индустриального класса оборудования:\n"
            "📐 free_passage насоса ≥ 35-50 мм (вместо 10-20 для бытовых).\n"
            "📐 Материалы: чугун ВЧШГ / нерж 316L (против абразива и "
            "коррозии); сталь для t > 60°C.\n"
            "⚡ Электрика по зонам ATEX (если есть органика/растворители): "
            "II 2G Ex db IIB T4 — насос+ЩУ+датчики уровня.\n"
            "🧪 Возможна необходимость песколовки/гидроциклона перед КНС "
            "(СП 32 §7.4) и аэротенка для биологии (СП 32 §9)."
        )
        mgr = (
            f"🏭 Промстоки ({L0.Q_m3h} м³/ч) — это совсем другой класс "
            f"оборудования, не бытовой.\n"
            f"💰 Наценка к бытовому варианту:\n"
            f"  • Чугунный/нержавеющий насос — +50-100% к цене.\n"
            f"  • ATEX-исполнение (если требуется) — ещё +30-50%.\n"
            f"  • Песколовка/гидроциклон — +200-500 тыс ₽.\n"
            f"⏱ Срок поставки 6-10 недель (производство под заказ).\n"
            f"📞 Уточните у клиента: состав стоков (pH, T, абразив, "
            f"взрывоопасность), это влияет на цену в 2-3 раза."
        )
        suggestions.append(InputSuggestion(
            field="wastewater_type",
            current_value="industrial",
            suggested_value="индустриальный класс, требуется анализ стоков",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-4: auto_fire_protection
    if "auto_fire_protection" in triggers:
        eng = (
            "🔥 Пожарная насосная установка (ПНУ) — отдельный класс по СП "
            "8.13130.2020 «Источники наружного противопожарного водоснабжения» "
            "и СП 10.13130.2020 «Внутренний противопожарный водопровод».\n"
            "📐 Обязательный состав:\n"
            "  • Резервуар пожарного запаса (V по СП 8 §6 = 3 ч × Q_расч).\n"
            "  • Насос рабочий + резервный (1+1, СП 10 §6.5).\n"
            "  • Жокей-насос для поддержания давления.\n"
            "  • Автоматика по ГОСТ Р 53325 (датчики давления, ШУ ПНУ).\n"
            "⚠ Расчёт Q_расч и H_расч зависит от категории помещения "
            "(А-Д), типа спринклеров, длины самых удалённых ветвей."
        )
        mgr = (
            "🔥 Пожарная установка — это не наш стандартный профиль. "
            "Требует индивидуального проектирования и сертификации МЧС.\n"
            "💰 Ориентир:\n"
            "  • Насосы + ШУ ПНУ — 400 тыс — 1.5 млн ₽.\n"
            "  • Резервуар 50-200 м³ — 500 тыс — 1.5 млн ₽.\n"
            "  • Проект + согласование с МЧС — 200-500 тыс ₽.\n"
            "⏱ Полный цикл (проект → согласование → монтаж → испытания) — "
            "1-3 месяца.\n"
            "📞 Передайте инженеру и менеджеру по пожарным проектам — "
            "это смежная компетенция, отдельный продукт."
        )
        suggestions.append(InputSuggestion(
            field="wastewater_type",
            current_value="fire_protection",
            suggested_value="пожарная установка, отдельное проектирование",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-5: auto_ex — Ex_required=True
    if "auto_ex" in triggers and L1 and L1.Ex_required:
        eng = (
            "⚠ Взрывозащищённое исполнение по ТР ТС 012/2011 и ГОСТ "
            "IEC 60079-0:\n"
            "📐 Маркировка для КНС: II 2G Ex db IIB T4 Gb или II 3G "
            "Ex eb IIA T3.\n"
            "🔬 Применяется когда в стоках возможны летучие "
            "углеводороды/растворители (АЗС, нефтебазы, СТО, химпром).\n"
            "⚡ Требования:\n"
            "  • NPSHa critical (нельзя допускать кавитацию — искра).\n"
            "  • Корпус двигателя: алюминий/чугун с искробезопасным "
            "монтажом, кабельные вводы Ex e.\n"
            "  • ШУ — в отдельном безопасном помещении или Ex-исполнение.\n"
            "  • Заземление обязательно (ПУЭ 7.3.139) + протокол замера."
        )
        mgr = (
            "⚡ Взрывозащищённый насос — спецзаказ для опасных зон "
            "(АЗС, нефтебаза, химия).\n"
            "💰 Наценка к стандартному исполнению:\n"
            "  • Насос Ex (Grundfos SE/SL, Wilo EMU FA) — +30-50%.\n"
            "  • Ex-кабель + вводы — +50-100 тыс ₽.\n"
            "  • Сертификат Ex-зоны от Ростехнадзора — 80-150 тыс ₽.\n"
            "⏱ Срок поставки 8-12 недель (нет на складе, делают под заказ).\n"
            "📞 Уточните у клиента класс зоны (1/2 = 2G/3G) и группу газов "
            "(IIA/IIB/IIC). Без этого подобрать нельзя."
        )
        suggestions.append(InputSuggestion(
            field="L1.Ex_required",
            current_value="True",
            suggested_value="ATEX II 2G/3G, спецзаказ",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-6: auto_npsha_low — NPSHa < 5 м (горы)
    if "auto_npsha_low" in triggers and L1 and L1.altitude_m and computed.npsha_m is not None:
        eng = (
            f"🌡 NPSHa={computed.npsha_m:.2f} м < 5 м на высоте "
            f"{L1.altitude_m:.0f} м над уровнем моря.\n"
            f"📐 Формула: NPSHa = (P_atm - P_vapor)/(ρ·g) - H_suction - h_тр.\n"
            f"  • P_atm с высотой падает по барометрической формуле "
            f"(P = P₀·exp(-h/8400)); на 2000 м ~80 кПа vs 101 на 0 м.\n"
            f"  • P_vapor растёт с температурой (при T=60°C ≈ 20 кПа).\n"
            f"⚠ NPSHr типичных канализационных насосов 2-4 м. "
            f"NPSHa - NPSHr < 0.5 м = кавитация (шум, эрозия колеса, "
            f"снижение Q-H кривой).\n"
            f"💡 Решение: насос с низким NPSHr (Grundfos SEG Quick-action, "
            f"WILO Drain TS) либо подпор / снижение T."
        )
        mgr = (
            f"⛰ Объект на высоте {L1.altitude_m:.0f} м — воздух разрежен, "
            f"обычные насосы будут кавитировать (шуметь, ломать колесо).\n"
            f"💰 Последствия:\n"
            f"  • Без спецнасоса — рабочее колесо разрушается за 6-12 мес.\n"
            f"  • Аварийный ремонт + замена колеса — 200-500 тыс ₽.\n"
            f"  • Эксплуатация в шуме > 80 дБ — жалобы клиента.\n"
            f"💡 Решение: насос с низким NPSHr (Grundfos SEG, WILO TS) — "
            f"+20-30% к цене стандартного, но окупится за 2 года.\n"
            f"📞 Передайте инженеру для проверки NPSHr-кривой "
            f"конкретной модели по высоте объекта."
        )
        suggestions.append(InputSuggestion(
            field="L1.altitude_m",
            current_value=f"{L1.altitude_m:.0f}",
            suggested_value="насос с низким NPSHr",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-7: auto_l_long_zhukovsky — L > 500 м
    if "auto_l_long_zhukovsky" in triggers:
        # Δp_удар = ρ·a·Δv; для PE100 a=320 м/с, для стали ~1100 м/с
        a_pe = 320
        a_steel = 1100
        v_typ = computed.v_ms if computed.v_ms > 0 else 1.5
        dp_pe_bar = 1000 * a_pe * v_typ / 1e5
        dp_steel_bar = 1000 * a_steel * v_typ / 1e5
        eng = (
            f"💥 Закон Жуковского: Δp_удар = ρ·a·Δv, где a — скорость "
            f"распространения волны (м/с).\n"
            f"📐 Для L={L0.L_m:.0f} м, v={v_typ:.2f} м/с:\n"
            f"  • ПЭ100: a≈320 м/с → Δp = 1000·320·{v_typ:.2f} ≈ {dp_pe_bar:.0f} бар.\n"
            f"  • Сталь: a≈1100 м/с → Δp ≈ {dp_steel_bar:.0f} бар.\n"
            f"⚠ Гидроудар возникает при резком закрытии обратного клапана "
            f"или останове насоса — может разорвать трубу/арматуру.\n"
            f"💡 Решения:\n"
            f"  • Обратный клапан с soft-close (демпфирование) — обязателен.\n"
            f"  • Уравнительная башня / воздушный колпак (для длинных трасс).\n"
            f"  • ЧРП на насосе с плавным остановом (rampdown ≥10 с)."
        )
        mgr = (
            f"💥 Трасса {L0.L_m:.0f} м — длинная, при резком останове насоса "
            f"возникает гидроудар (как удар молотом по трубе).\n"
            f"💰 Без защиты:\n"
            f"  • Обычный обратный клапан треснет за 1-3 удара.\n"
            f"  • Возможен разрыв трубы или арматуры — замена 800 тыс — 2 млн ₽ "
            f"(земляные работы + труба + простой).\n"
            f"💡 Решение: обратный клапан с soft-close (демпфер) — "
            f"+40-80 тыс ₽ к стандартному. Окупается с первой аварией.\n"
            f"⏱ Срок поставки клапана с демпфером — 1-2 недели."
        )
        suggestions.append(InputSuggestion(
            field="L_m",
            current_value=f"{L0.L_m:.0f}",
            suggested_value="soft-close клапан обязателен",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-8: auto_category_I — I категория надёжности
    if "auto_category_I" in triggers:
        eng = (
            "🏛 СП 31.13330.2021 «Водоснабжение. Наружные сети», табл.7.1 — "
            "I категория надёжности (объекты, перерыв в работе которых "
            "недопустим > 10 мин).\n"
            "📐 Требования:\n"
            "  • Резервирование 2+1 минимум (2 рабочих + 1 резерв).\n"
            "  • Два независимых источника электропитания (ПУЭ 1.2.18) "
            "+ АВР на вводе.\n"
            "  • Резервный электроагрегат (ДГУ) или питание от двух подстанций.\n"
            "  • Автоматическое управление, диспетчеризация.\n"
            "⚠ По СП 32 §6.2 для КНС I кат. редундантность пересчитывается:\n"
            "  • Schema 1+1 → 2+1 = 3 насоса.\n"
            "  • Schema 2+1 → 3+1 = 4 насоса."
        )
        mgr = (
            "🏛 I категория надёжности — объект критической важности "
            "(больница, водозабор, металлургия). Простой запрещён > 10 минут.\n"
            "💰 Цена удваивается:\n"
            "  • Насосов 3 вместо 2 (раб+раб+рез) — +50% к насосам.\n"
            "  • Два независимых ввода питания + АВР — 200-500 тыс ₽.\n"
            "  • ДГУ резервный — 600 тыс — 2 млн ₽ (зависит от мощности).\n"
            "  • Автоматика, диспетчеризация — 200-400 тыс ₽.\n"
            "⏱ Срок проектирования и монтажа +4-6 недель.\n"
            "📞 Уточните у клиента: реальная I кат. или просто перестраховка? "
            "Иногда II кат. достаточно (×1.3 вместо ×2)."
        )
        suggestions.append(InputSuggestion(
            field="L1.reliability_category",
            current_value="I",
            suggested_value="2+1 + 2 ввода + ДГУ",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-9: auto_no_match — кандидатов нет
    if "auto_no_match" in triggers:
        eng = (
            f"🔍 Ни один насос из БД не попадает в envelope "
            f"Q={L0.Q_m3h} м³/ч × H={computed.H_full_m:.1f} м.\n"
            f"📐 Возможные причины:\n"
            f"  • Q или H за диапазоном БД (текущая БД 0.5-500 м³/ч, 5-100 м).\n"
            f"  • Жёсткий фильтр L1 (IP_motor, Ex, wastewater_type) "
            f"отсёк всех кандидатов.\n"
            f"  • Комбинация параметров нетипична (например, Q=1 м³/ч H=80 м — "
            f"нужен бытовой дозирующий, не КНС).\n"
            f"💡 Решения:\n"
            f"  • Ослабить L1-фильтры (попробовать без Ex / без точного IP).\n"
            f"  • Проверить единицы Q (л/с vs м³/ч).\n"
            f"  • Передать инженеру для подбора по импортному каталогу."
        )
        mgr = (
            f"🔍 По заданным параметрам Q={L0.Q_m3h}/H={computed.H_full_m:.1f} "
            f"наших стандартных насосов не нашлось.\n"
            f"💰 Что делать:\n"
            f"  • Уточните данные у клиента (возможно ошибка в единицах).\n"
            f"  • Передайте инженеру для индивидуального подбора.\n"
            f"⏱ Ответ инженера обычно за 1-3 рабочих дня. "
            f"Бывает что подходит импортный/нестандартный насос — "
            f"тогда срок поставки до 8-12 недель и цена +50-100% к каталожной."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}/{computed.H_full_m:.1f}",
            suggested_value="инженерный подбор",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    # LEG-10: auto_low_match_count — мало кандидатов (< 2)
    if "auto_low_match_count" in triggers:
        eng = (
            f"⚠ Найден всего 1 насос для Q={L0.Q_m3h}/H={computed.H_full_m:.1f}.\n"
            f"📐 Это значит:\n"
            f"  • Точка работы близка к границе AOR (точка наименьшей энергии).\n"
            f"  • КПД может быть низким (BEP далеко от рабочей точки).\n"
            f"  • Износ ускоренный (работа вне POR/AOR).\n"
            f"⚠ score обычно < 0.4 — насос работать будет, но не оптимально.\n"
            f"💡 Решение: рассмотреть параллельную работу двух меньших "
            f"насосов или сместить точку (другая труба → другой H)."
        )
        mgr = (
            "⚠ По вашим параметрам подходит только 1 насос — он будет "
            "работать, но не в оптимальной точке.\n"
            "💰 Что это значит на практике:\n"
            "  • КПД ниже паспортного на 10-20% → перерасход электричества "
            "30-50% от номинала.\n"
            "  • Для типового насоса 5 кВт это +1500-2500 кВт·ч/год = "
            "+15-30 тыс ₽/год к счёту за свет.\n"
            "  • За 5 лет переплата по OPEX 75-150 тыс ₽.\n"
            "💡 Рекомендуем уточнить параметры с инженером и/или "
            "посмотреть альтернативу (2 меньших насоса в параллель)."
        )
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}/{computed.H_full_m:.1f}",
            suggested_value="проверить альтернативы",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="warning",
        ))

    # LEG-11: auto_pipe_temp_incompatible — уже обработан suggestion #6 (eng_pipe).
    # Этот блок служит fallback для случаев, когда suggestion #6 не сработал
    # (например, нет L1.pipe_material, но trigger пришёл из другой логики).
    if "auto_pipe_temp_incompatible" in triggers and not any(
        s.field == "L1.pipe_material" for s in suggestions
    ):
        pipe_mat = L1.pipe_material if L1 else "неизвестно"
        temp_c = L1.liquid_temp_c if L1 else 0
        eng = (
            f"🧪 {pipe_mat} + T={temp_c}°C — материал не выдержит длительной "
            f"эксплуатации при такой температуре (ISO 4427 для ПЭ100: T_max=60°C).\n"
            f"📐 По Аррениусу срок службы падает в 5-10 раз. См. полную "
            f"справку в suggestion на pipe_material."
        )
        mgr = (
            f"🔥 Полимерная труба и горячие стоки T={temp_c}°C — несовместимы. "
            f"Через 6-12 мес труба потечёт. См. рекомендацию по замене "
            f"материала (сталь/чугун) в основном suggestion."
        )
        suggestions.append(InputSuggestion(
            field="L1.pipe_material",
            current_value=f"{pipe_mat}",
            suggested_value="steel_seamless_new или cast_iron_new",
            reason=eng,
            reason_engineer=eng,
            reason_manager=mgr,
            severity="critical",
        ))

    return suggestions


# ---------------------------------------------------------------------------
# Phase 34+ (2026-05-13): научные helper-функции для EXT-9 / EXT-8.
# Возвращают «срабатывает ли триггер» + структурированные параметры (NH4, C:N,
# SRT, ПДК), которые потом используются в build_suggestions для формирования
# 2-уровневого reason_engineer / reason_manager.
# ---------------------------------------------------------------------------

def _check_ext_9_nitrification(
    L0: L0Input, L1: L1Input | None, computed: ComputedHydraulics | None
) -> dict | None:
    """EXT-9: проверка необходимости нитрификации по Henze IWA 2008 §3.4.

    Возвращает dict с параметрами расчёта (nh4, bod5, T, srt_min, ПДК, target)
    либо None если нитрификация не требуется.

    Условия срабатывания (все AND):
      • NH4+ > 20 мг/л (default бытовые 25, индустр 100)
      • C:N = БПК5/NH4 > 3 (углерод для гетеротрофов нитрификаторов)
      • 12°C ≤ T ≤ 35°C (Nitrosomonas/Nitrobacter — Arrhenius θ=1.103)
      • heavy_metals_present=False (Cr, Cd, Hg, Pb убивают активный ил)
      • Ex_required=False (нефтехимия — отдельная анаэробная фаза)
      • NH4_in > ПДК(target_discharge): рыбхоз 0.4, общ. 2.0, полив 10, муниц. 40
    """
    if L1 and L1.Ex_required:
        return None  # АЗС/нефтехимия — биообработка не работает
    if L0.wastewater_type not in ("industrial", "domestic"):
        return None  # drainage / clean_water / fire — не для биологии
    # Heavy metals → биота отравлена, нужна физ-химия
    if L1 and getattr(L1, "heavy_metals_present", False):
        return None

    # NH4_in: явно задано либо default по типу стоков (TYPICAL_INFLUENT)
    nh4 = (L1.nh4_in_mgL if L1 and L1.nh4_in_mgL is not None else None)
    if nh4 is None:
        _NH4_DEFAULTS = {
            "domestic": 25.0, "industrial": 100.0,
            "drainage": 5.0, "clean_water": 0.5, "fire_protection": 0.0,
        }
        nh4 = _NH4_DEFAULTS.get(L0.wastewater_type or "domestic", 25.0)

    # BOD5_in для C:N
    bod5 = (L1.bod5_in_mgL if L1 and L1.bod5_in_mgL is not None else None)
    if bod5 is None:
        _BOD5_DEFAULTS = {
            "domestic": 250.0, "industrial": 500.0,
            "drainage": 30.0, "clean_water": 2.0, "fire_protection": 0.0,
        }
        bod5 = _BOD5_DEFAULTS.get(L0.wastewater_type or "domestic", 250.0)

    # T-gate (нитрификаторы работают при 12-35°C)
    T = (L1.liquid_temp_c if L1 and L1.liquid_temp_c is not None else 20.0)
    if T < 12.0 or T > 35.0:
        return None

    # NH4-порог Henze: если меньше — нитрификация не нужна
    if nh4 < 20.0:
        return None

    # C:N ratio (нужен углерод для гетеротрофов / денитрификаторов)
    c_to_n = bod5 / nh4 if nh4 > 0 else 0.0
    if c_to_n < 3.0:
        return None

    # ПДК по target_discharge
    target = (L1.target_discharge if L1 and L1.target_discharge else "municipal_sewage")
    _NH4_LIMITS = {
        "fishery_water": 0.4,     # рыбхоз — жёсткая (МУК + Приказ Росрыболовства №20)
        "general_use": 2.0,       # СанПиН 2.1.5.980-00
        "reuse_irrigation": 10.0, # СанПиН СЭ 6.04.001
        "municipal_sewage": 40.0, # городская канализация — мягкая
    }
    nh4_limit = _NH4_LIMITS.get(target, 2.0)
    if nh4 <= nh4_limit:
        return None  # уже в норме

    # SRT correction по T (Arrhenius θ=1.103, Henze IWA §3.4)
    srt_min_d = 15.0 * (1.103 ** (15.0 - T))

    return {
        "nh4": nh4,
        "bod5": bod5,
        "c_to_n": c_to_n,
        "T": T,
        "nh4_limit": nh4_limit,
        "target": target,
        "srt_min_d": srt_min_d,
    }


def _ext_8_uv_dose_required(L1: L1Input | None) -> tuple[int, str]:
    """EXT-8: возвращает (uv_dose мДж/см², target) по L1.target_discharge.

    Доза по МУК 4.3.2030-05 / СанПиН 2.1.5.980-00:
      • municipal_sewage — 25 мДж/см² (E.coli 3 lg)
      • general_use — 30 мДж/см² (водоём культ-быт)
      • reuse_irrigation — 60 мДж/см² (СанПиН СЭ 6.04.001 — на полив)
      • fishery_water — 100 мДж/см² (МУК + Приказ Росрыболовства №20)
    """
    target = (L1.target_discharge if L1 and L1.target_discharge else "municipal_sewage")
    _UV_DOSE = {
        "fishery_water": 100,
        "general_use": 30,
        "reuse_irrigation": 60,
        "municipal_sewage": 25,
    }
    return _UV_DOSE.get(target, 30), target


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

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: триггеры из 8 активированных L1-полей
    # ──────────────────────────────────────────────────────────────────

    # TRIG-DRY-RUN: защита от сухого хода отключена. Может сжечь насос
    # при пустой камере (типичная причина выхода из строя за 1-3 цикла).
    # СП 32 §6.2 — обязательная защита.
    if L1 and L1.dry_run_protection is False:
        triggers.append("auto_no_dry_run_protection")

    # TRIG-NPSHA-LOW: NPSHa < 5 м (горный регион). Если altitude_m задан и
    # рассчитанный NPSHa упал ниже 5 м — большинство насосов с NPSHr ~2-4
    # будут в пограничной зоне. Нужна верификация конкретной NPSHr-кривой.
    if (
        L1 and L1.altitude_m is not None
        and L1.altitude_m > 2000
        and computed.npsha_m is not None
        and computed.npsha_m < 5.0
    ):
        triggers.append("auto_npsha_low")

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: 10 научных расширений (СП/ПУЭ/материаловедение/биология)
    # ──────────────────────────────────────────────────────────────────

    # EXT-1: СП 22.13330.2016 «Основания зданий». Глубокий заглубленный корпус
    # испытывает боковое давление грунта по Кулону: σ_x = γ·z·K_a + γ_w·z_w.
    # v0.3 (2026-05-13): порог теперь зависит от soil_type и УГВ
    # (PhD-Mechanics audit P1-7, P0-3). Для глины K_a=0.5-0.65, порог z>3 м;
    # для УГВ выше дна — z>2.5 м (PhD Sc.D. cross-domain audit).
    if L1 and L1.install_depth_inlet_mm is not None:
        z_m = L1.install_depth_inlet_mm / 1000
        # Порог по типу грунта (СП 22.13330.2016 табл. А.1)
        _SOIL_THRESHOLDS = {
            "sand_dense": 5.5, "sand_medium": 5.0, "sand_loose": 4.0,
            "sand_water_saturated": 3.5, "loam": 4.0,
            "clay_hard": 4.0, "clay_plastic": 3.3, "clay_soft": 3.0,
            "peat": 2.5,  # болото — всегда P0
        }
        soil_threshold = _SOIL_THRESHOLDS.get(L1.soil_type or "sand_medium", 5.0)
        # При УГВ выше дна корпуса — порог снижается до 2.5 м (Sc.D. P0-blocker)
        if L1.groundwater_level_m is not None and (z_m + L1.groundwater_level_m) > 0:
            soil_threshold = min(soil_threshold, 2.5)
        if z_m > soil_threshold:
            triggers.append("auto_lateral_earth_pressure")

    # EXT-2: СП 35.13330 «Мосты и трубы». При подземном корпусе крышка
    # должна выдержать класс нагрузки А15 (тротуары, < 1.5 т), B125 (паркинги,
    # 12.5 т), C250 (зоны заезда, 25 т) или D400 (магистрали, 40 т).
    # Без павильона + малая глубина → высокая вероятность транспорта над крышкой.
    if (
        L1 and L1.above_ground_pavilion is False
        and L1.install_depth_inlet_mm is not None
        and L1.install_depth_inlet_mm < 1000
    ):
        triggers.append("auto_traffic_load_class")

    # EXT-3: ПУЭ 1.7 «Заземление». Для взрывозащиты или I категории надёжности
    # требуется отдельный расчёт заземляющего устройства. R_зазем ≤ 4 Ом
    # для TN-S (ПУЭ 1.7.103), ≤ 10 Ом для повторного заземления.
    if L1 and (L1.Ex_required or L1.reliability_category == "I"):
        triggers.append("auto_grounding_required")

    # EXT-4: СО 153-34.21.122 «Молниезащита». Наземный павильон —
    # отдельное здание выше 10 м или в зоне молниевой активности →
    # молниеотвод обязателен, II категория защиты для электрооборудования.
    if L1 and L1.above_ground_pavilion:
        triggers.append("auto_lightning_protection_required")

    # EXT-5: СП 41-103-2000 «Тепловая изоляция». Горячие стоки (>40°C)
    # ИЛИ горные / холодные регионы (altitude>1500 м — климат суровый):
    # без утепления труба теряет тепло (h_loss = 2πλΔT/ln(D₂/D₁)),
    # риск замерзания / конденсата.
    if L1 and (
        (L1.liquid_temp_c is not None and L1.liquid_temp_c > 40)
        or (L1.altitude_m is not None and L1.altitude_m > 1500)
    ):
        triggers.append("auto_pipe_insulation_required")

    # EXT-6: Греющий кабель для напорной трассы. В горных регионах
    # (altitude>1500 м) минимальная зимняя T часто < -25°C, замерзание
    # за часы простоя. Бытовая мощность кабеля ~30 Вт/м для DN50-150.
    if L1 and L1.altitude_m is not None and L1.altitude_m > 1500:
        triggers.append("auto_heating_cable_required")

    # EXT-7: Седиментация Stokes для промстоков с малым Q (<50 м³/ч):
    # v_осаж = (ρ_частицы - ρ_воды)·g·d²/(18·μ). При Q<50 скорость потока
    # низкая → крупные частицы (>0.5 мм) оседают в трубе или приёмной камере,
    # требуется песколовка / гидроциклон до КНС.
    if L0.wastewater_type == "industrial" and L0.Q_m3h < 50:
        triggers.append("auto_sedimentation_check")

    # EXT-8: УФ/озон обеззараживание (СанПиН 2.1.5.980-00 §4.1.5 + МУК 4.3.2030-05).
    # v0.3 (2026-05-13): УФ-доза дифференцирована по target_discharge
    # (Sc.D. audit). По МУК 4.3.2030-05:
    #   • Сброс в канализацию города — 30 мДж/см² (default для домашних > 100 м³/ч)
    #   • Сброс в водоём культурно-бытового назначения — 60 мДж/см²
    #   • Сброс в рыбохозяйственный водоём — 80-120 мДж/см² (с предобработкой!)
    if L0.wastewater_type == "domestic" and L0.Q_m3h > 100:
        triggers.append("auto_disinfection_required")

    # EXT-12 (новый, v0.3 2026-05-13): термический derating двигателя
    # (PhD-Electrical audit + Sc.D. cross-domain).
    # IEC 60034-1 §8.10.2: при T_жидк >40°C погружной двигатель надо derate.
    # При T>60°C обязателен класс изоляции H + PTC-термистор обмотки.
    if L1 and L1.liquid_temp_c is not None and L1.liquid_temp_c > 40:
        triggers.append("auto_motor_thermal_derate")

    # EXT-13 (новый, v0.3 2026-05-13): анаэробная биокоррозия бетона
    # при длительных простоях КНС (Metcalf & Eddy §5-4 + Sc.D. audit).
    # При cycles_per_hour < 0.5 (длительный простой >2ч) — H2S + Thiobacillus
    # → H2SO4 → разрушение бетона 5-15 мм/год.
    if (
        computed
        and computed.cycles_per_hour_estimate is not None
        and computed.cycles_per_hour_estimate < 0.5
        and computed.cycles_per_hour_estimate > 0  # 0 = continuous, не простой
    ):
        triggers.append("auto_anaerobic_corrosion_risk")

    # EXT-9: Нитри/денитрификация по строгим параметрам Monod / Henze IWA 2008 §3.4
    # v0.4 (Phase 34+, 2026-05-13): полностью переписан после PhD-Biology audit +
    # Sc.D. cross-domain. Решено через _check_ext_9_nitrification, который
    # учитывает NH4_in, BOD5_in, тяжёлые металлы, T-gate, ПДК по target_discharge.
    # Срабатывает когда:
    #   NH4_in > 20 мг/л (Henze IWA 2008 §3.4)
    #   AND C:N = BOD5/NH4 > 3 (нужен углерод для гетеротрофов)
    #   AND 12°C ≤ T ≤ 35°C (Nitrosomonas/Nitrobacter диапазон)
    #   AND нет тяжёлых металлов (Cr, Cd, Pb, Hg отравляют ил)
    #   AND нет Ex_required (нефтехимия не подлежит биообработке)
    #   AND NH4_in > ПДК по target_discharge (рыбхоз 0.4, общ. 2.0, муниц. 40)
    if _check_ext_9_nitrification(L0, L1, computed):
        triggers.append("auto_nitrification_check")

    # EXT-10: Гидробак ВНС (СП 30.13330 §11). Для повысительных насосных
    # станций чистой воды Q>50 м³/ч переменный расход компенсируется
    # гидроаккумулятором: V_бака = (Q_max - Q_min)·t_цикл/4. Без бака —
    # частые пуски ЧРП / гидроудары.
    if L0.wastewater_type == "clean_water" and L0.Q_m3h > 50:
        triggers.append("auto_hydrobak_required")

    return triggers


# ---------------------- Кавитационный анализ ----------------------
# Sc.D. audit 2026-05-13: заменяем примитивный `NPSHa - NPSHr >= 0.5`
# на полный Thoma σ + σ_3% по ISO 9906:2024 (Karassik §22.7).
# См. pump_calculator/cavitation.py.

def _map_pump_type_for_cavitation(
    pump_type_db: str,
) -> str:
    """Маппинг pump.type (БД) → cavitation pump_type.

    Submersible_sewage / drainage_pump → "submersible" (мягкие пороги).
    Multistage / booster_station → "multistage" (строгие пороги Karassik).
    Иначе → "surface" (default консервативный).
    """
    pt = (pump_type_db or "").lower()
    if pt in ("submersible_sewage", "submersible", "drainage_pump", "submersible_drainage"):
        return "submersible"
    if pt in ("multistage", "booster_station", "vertical_multistage"):
        return "multistage"
    return "surface"


def evaluate_cavitation_for_results(
    results: SelectionResultsBySegment,
    computed: ComputedHydraulics,
    L1: L1Input | None,
) -> dict[str, CavitationResult]:
    """Полный кавитационный анализ для каждого подобранного насоса.

    Возвращает {segment: CavitationResult} только для сегментов где есть
    результат + NPSHr_at_BEP_m задан (backward-compat: если NPSHr
    отсутствует — analyze_cavitation вернёт marginal с предупреждением).

    Используется как замена примитивного `NPSHa − NPSHr ≥ 0.5`.
    """
    out: dict[str, CavitationResult] = {}
    if computed.npsha_m is None or computed.H_full_m is None:
        return out
    liquid_temp_c = (L1.liquid_temp_c if L1 and L1.liquid_temp_c is not None else 20.0)

    for segment in ("budget", "mid", "premium"):
        pr = getattr(results, segment, None)
        if pr is None:
            continue
        npshr_m = pr.envelope.NPSHr_at_BEP_m
        if npshr_m is None:
            # Backward-compat: NPSHr нет в паспорте → analyze_cavitation
            # вернёт marginal с recommendations. Не пропускаем сегмент.
            npshr_m = 0.0
        cav_pump_type = _map_pump_type_for_cavitation(pr.type)
        result = analyze_cavitation(
            NPSHa_m=computed.npsha_m,
            NPSHr_3pct_m=npshr_m,
            H_full_m=computed.H_full_m,
            pump_type=cav_pump_type,  # type: ignore[arg-type]
            liquid_temp_c=liquid_temp_c,
        )
        out[segment] = result
    return out


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
        for s in sc_suggestions:
            if not s.reason_engineer:
                s.reason_engineer = s.reason
            if not s.reason_manager:
                s.reason_manager = s.reason
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

    # Шаг 5б: ATEX-фильтр (v0.3 — добавлено 2026-05-13 по PhD-Electrical
    # audit P0-1: для Ex-зон обычные насосы исключаются (ст. 217.2 УК РФ).
    ex_required_flag = bool(L1 and L1.Ex_required)
    ex_zone_val = (L1.ex_zone_class if L1 else None)
    f3 = filter_by_ex(f3, ex_required_flag, ex_zone_val)

    # Шаг 5в: IP-фильтр двигателя (если L1.ip_motor задан).
    f3 = filter_by_ip_motor(f3, L1.ip_motor if L1 else None)

    # Шаг 6
    corpus_material = (L1.corpus_material if L1 and L1.corpus_material else "pe")
    ex_required = bool(L1 and L1.Ex_required)
    # n_pumps: единый резолвер (override > redundancy > 2).
    # Передаём в pricing именно эффективное число — чтобы redundancy="2+1" (=3)
    # и pumps_total_override=3 давали одинаковый BOM.
    if L1 is not None and (L1.pumps_total_override or L1.redundancy):
        from pump_calculator.hydraulics import _resolve_n_pumps  # избежать цикла на верхнем уровне
        n_pumps_override = _resolve_n_pumps(L1)
    else:
        n_pumps_override = None
    results, candidates_total, warnings, alternatives = pick_top_per_segment(
        f3, L0_filled.Q_m3h, computed.H_full_m, corpus_material=corpus_material,
        wastewater_type=L0_filled.wastewater_type,
        ex_required=ex_required,
        n_pumps_override=n_pumps_override,
        L1=L1,
    )

    # Шаг 7
    triggers = evaluate_handoff_triggers(L0_filled, L1, computed, candidates_total)

    # Шаг 7b: кавитационный анализ по ISO 9906:2024 (Sc.D. 2026-05-13).
    # Заменяет примитивный `NPSHa - NPSHr >= 0.5`. Анализ выполняется
    # для **каждого** подобранного насоса (budget/mid/premium) — важно
    # для многоступенчатых, где простая разница даёт ложно-зелёный сигнал.
    cavitation_per_segment = evaluate_cavitation_for_results(results, computed, L1)
    # Берём worst-case (если хоть один сегмент warning/critical — добавляем trigger).
    cav_risks = [r.risk for r in cavitation_per_segment.values()]
    if "critical" in cav_risks or "warning" in cav_risks:
        if "auto_cavitation_warning" not in triggers:
            triggers.append("auto_cavitation_warning")

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
    if "auto_no_dry_run_protection" in triggers:
        warnings.insert(0, (
            "⚠ Защита от сухого хода отключена (dry_run_protection=False). "
            "По СП 32 §6.2 защита обязательна — без неё насос может перегореть "
            "при опорожнении приёмной камеры (один цикл = выход из строя)."
        ))
    if "auto_npsha_low" in triggers and L1 and L1.altitude_m and computed.npsha_m is not None:
        warnings.insert(0, (
            f"⚠ NPSHa = {computed.npsha_m:.2f} м (на высоте {L1.altitude_m:.0f} м "
            f"над уровнем моря) < 5 м. Большинство насосов имеют NPSHr 2-4 м — "
            f"риск кавитации. Проверьте NPSHr-кривую конкретной модели и "
            f"рассмотрите снижение T или подпора."
        ))

    # Sc.D. audit 2026-05-13: полный кавитационный анализ ISO 9906:2024.
    # Заменяет старую проверку `NPSHa - NPSHr >= 0.5` (которая на много-
    # ступенчатых даёт ложно-зелёный сигнал).
    if "auto_cavitation_warning" in triggers and cavitation_per_segment:
        worst_segment, worst_result = None, None
        for seg, cav in cavitation_per_segment.items():
            if cav.risk in ("critical", "warning"):
                if worst_result is None or cav.margin < worst_result.margin:
                    worst_segment, worst_result = seg, cav
        if worst_result is not None:
            warnings.insert(0, (
                f"⚠ Кавитация (ISO 9906:2024, сегмент «{worst_segment}»): "
                f"margin σ_avail/σ_req = {worst_result.margin:.2f}, "
                f"risk={worst_result.risk}. {worst_result.risk_reason} "
                f"Рекомендации: {'; '.join(worst_result.recommendations[:2])}"
            ))

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: warnings для 10 научных расширений
    # ──────────────────────────────────────────────────────────────────
    if "auto_lateral_earth_pressure" in triggers and L1 and L1.install_depth_inlet_mm:
        z = L1.install_depth_inlet_mm / 1000
        warnings.insert(0, (
            f"⚠ Глубина монтажа {z:.1f} м > 5 м — боковое давление грунта "
            f"по СП 22.13330 (Кулон) ≈ {18*z*0.33:.0f} кПа. Стандартный ПЭ-корпус "
            f"может деформироваться. Требуются рёбра жёсткости / ж/б обойма + "
            f"расчёт инженером-конструктором."
        ))
    if "auto_traffic_load_class" in triggers:
        warnings.insert(0, (
            "⚠ Подземный корпус без павильона на малой глубине — крышка "
            "находится на уровне земли. По СП 35.13330 при возможном заезде "
            "транспорта требуется чугунная крышка класса D400 (40 т)."
        ))
    if "auto_grounding_required" in triggers:
        why = "Ex-зона" if (L1 and L1.Ex_required) else "I категория надёжности"
        warnings.insert(0, (
            f"⚠ Для {why} обязателен расчёт заземляющего устройства "
            f"по ПУЭ 1.7.103: R_зазем ≤ 4 Ом (TN-S). Требуется протокол замера "
            f"перед вводом в эксплуатацию (Ростехнадзор)."
        ))
    if "auto_lightning_protection_required" in triggers:
        warnings.insert(0, (
            "⚠ Наземный павильон — обязательна молниезащита по СО 153-34.21.122 "
            "(II категория для электрооборудования) + УЗИП класса I на вводе ШУ."
        ))
    if "auto_pipe_insulation_required" in triggers:
        warnings.insert(0, (
            "⚠ Требуется тепловая изоляция напорной трассы по СП 41-103 "
            "(горячая жидкость > 40°C либо холодный регион). Без изоляции — "
            "замерзание/конденсат и потери тепла."
        ))
    if "auto_heating_cable_required" in triggers and L1 and L1.altitude_m:
        warnings.insert(0, (
            f"⚠ Высота {L1.altitude_m:.0f} м (горный регион) — рекомендован "
            f"греющий саморегулирующийся кабель ~30 Вт/м на напорную трассу "
            f"для предотвращения замерзания зимой."
        ))
    if "auto_sedimentation_check" in triggers:
        warnings.insert(0, (
            f"⚠ Промстоки с малым Q={L0.Q_m3h} м³/ч — низкая скорость "
            f"потока, крупные частицы оседают (закон Стокса). "
            f"Рекомендуется песколовка/гидроциклон до КНС (СП 32 §7.4)."
        ))
    if "auto_disinfection_required" in triggers:
        _uv_dose, _target = _ext_8_uv_dose_required(L1)
        warnings.insert(0, (
            f"⚠ Q={L0.Q_m3h} м³/ч хоз-бытовых, сброс в '{_target}' — "
            f"по СанПиН 2.1.5.980-00 обязательно обеззараживание "
            f"(УФ ≥{_uv_dose} мДж/см² или озон ≥5 мг/л) "
            f"перед сбросом в водоём. Иначе штраф 250-500 тыс ₽ (КоАП 8.13)."
        ))
    if "auto_nitrification_check" in triggers:
        warnings.insert(0, (
            "⚠ Промстоки — требуется проверка необходимости нитри/денитрификации "
            "(СП 32 §9). Возраст ила ≥10 сут, аэрация ≥6 ч, T ≥12°C. "
            "Передайте инженеру-технологу."
        ))
    if "auto_hydrobak_required" in triggers:
        V_bak_l = (L0.Q_m3h - L0.Q_m3h * 0.2) * 1000 * 0.1 / 4
        warnings.insert(0, (
            f"⚠ ВНС чистой воды Q={L0.Q_m3h} м³/ч — нужен гидроаккумулятор "
            f"~{V_bak_l:.0f} л (СП 30.13330 §11). Без него ЧРП работает в режиме "
            f"частых пусков, ресурс падает в 2 раза."
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
    # Backward-compat: если reason_engineer/reason_manager пустые → копируем reason.
    # Frontend может рендерить tab "Инженер"/"Менеджер" по этим полям.
    # NB: на 2026-05-10 build_suggestions заполняет только reason. Расширение
    # под двухуровневые тексты для каждого case — отдельный backlog item
    # (часть UX edge cases spec, см. memory reference_kns_ux_edge_cases_2026-05-10).
    for s in suggestions:
        if not s.reason_engineer:
            s.reason_engineer = s.reason
        if not s.reason_manager:
            s.reason_manager = s.reason

    # Sc.D. 2026-05-13: 2-level reason для auto_cavitation_warning.
    # Берём worst case среди сегментов (наименьший margin).
    if "auto_cavitation_warning" in triggers and cavitation_per_segment:
        from pump_calculator.schemas import InputSuggestion
        worst = min(
            cavitation_per_segment.values(),
            key=lambda r: r.margin,
        )
        # Карта pump_type для текста ISO порога
        worst_seg_pump_type = "submersible"
        for seg, cav in cavitation_per_segment.items():
            if cav is worst:
                pr = getattr(results, seg, None)
                if pr is not None:
                    worst_seg_pump_type = _map_pump_type_for_cavitation(pr.type)
                break
        severity = "critical" if worst.risk == "critical" else "warning"
        eng_text = explain_cavitation_engineer(worst, worst_seg_pump_type)  # type: ignore[arg-type]
        mgr_text = explain_cavitation_manager(worst)
        suggestions.append(InputSuggestion(
            field="L1.altitude_m",
            current_value=f"NPSHa={worst.NPSHa_m:.2f} м",
            suggested_value=f"насос с NPSHr_3% < {worst.NPSHa_m * 0.7:.1f} м",
            reason=eng_text,
            reason_engineer=eng_text,
            reason_manager=mgr_text,
            severity=severity,
        ))

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
    import math

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

    # 2026-05-10: используем install_depth_inlet_mm из L1 если задан
    depth_inlet_mm = L1.install_depth_inlet_mm if L1 and L1.install_depth_inlet_mm else None

    cs = _cs(
        Q_m3h=L0_filled.Q_m3h,
        P_kW=sample_pump.P_kW,
        depth_inlet_mm=depth_inlet_mm,
        n_pumps=n_pumps,
        corpus_type=corpus_material,  # type: ignore[arg-type]
    )

    # 2026-05-10: inlet_pipe_diam_mm из L1 переопределяет дефолтный inlet_DN
    # из таблицы (если задан и больше расчётного).
    inlet_dn = cs.inlet_DN_mm
    extra_notes = list(cs.notes)
    if L1 and L1.inlet_pipe_diam_mm:
        if L1.inlet_pipe_diam_mm > cs.inlet_DN_mm:
            inlet_dn = float(L1.inlet_pipe_diam_mm)
            extra_notes.append(
                f"DN подвода увеличен до {int(inlet_dn)} мм по L1.inlet_pipe_diam_mm "
                f"(default по Q был {int(cs.inlet_DN_mm)} мм)."
            )
        else:
            extra_notes.append(
                f"L1.inlet_pipe_diam_mm={int(L1.inlet_pipe_diam_mm)} мм — "
                f"меньше расчётного DN {int(cs.inlet_DN_mm)} мм по Q. Оставлен "
                f"расчётный (большего достаточно для приёма самотёка)."
            )

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: weight_estimate_kg + reinforcement_kg
    # Геометрия стенок: A_walls = π·D·H, A_caps = 2·π·D²/4 (дно+крышка).
    # ПЭ100 SDR17: δ = D/17, ρ = 950 кг/м³ → W_pe = (A_walls·δ + A_caps·δ)·ρ.
    # Стеклопластик (glass): эмпирика 130 кг/м² (см. corpus_sizing.py).
    # Reinforcement по СП 22.13330 (Кулон): σ_x = γ·z·K_a при γ=18 кН/м³,
    # K_a=tan²(45-φ/2)=0.33 для φ=30°. На z=6м → σ_x=35.6 кПа.
    # ПЭ100 SDR17 выдерживает ~50 кН/м² → нужна добавка усиления:
    #   - z=4-5 м: рёбра жёсткости ПЭ (~5% от веса корпуса)
    #   - z=5-7 м: частичная ж/б обойма (площадь стенок · 100 кг/м²)
    #   - z>7 м:  полная ж/б обойма (площадь стенок · 250 кг/м²)
    # ──────────────────────────────────────────────────────────────────
    D_m = cs.diameter_mm / 1000.0
    H_m = cs.height_mm / 1000.0
    A_walls_m2 = math.pi * D_m * H_m
    A_caps_m2 = 2.0 * math.pi * (D_m / 2.0) ** 2
    A_total_m2 = A_walls_m2 + A_caps_m2

    weight_estimate_kg: float | None
    if corpus_material == "pe":
        # SDR17 → толщина стенки δ = D/17 (м)
        wall_thickness_m = D_m / 17.0
        rho_pe100 = 950.0  # кг/м³
        weight_estimate_kg = round(A_total_m2 * wall_thickness_m * rho_pe100, 1)
    else:
        # Стеклопластик: используем эмпирическую оценку (130 кг/м²)
        weight_estimate_kg = float(cs.weight_estimate_kg)

    # Reinforcement только при глубокой установке (depth_inlet > 4000 мм)
    reinforcement_kg: float | None = None
    z_m = (depth_inlet_mm or 0.0) / 1000.0
    if z_m > 4.0 and weight_estimate_kg is not None:
        if z_m <= 5.0:
            # Рёбра жёсткости ПЭ ~5% от веса корпуса
            reinforcement_kg = round(weight_estimate_kg * 0.05, 1)
            extra_notes.append(
                f"Усиление: рёбра жёсткости ПЭ +{reinforcement_kg:.0f} кг "
                f"(z={z_m:.1f} м, σ_x≈{18.0 * z_m * 0.33:.1f} кПа по СП 22.13330)."
            )
        elif z_m <= 7.0:
            # Частичная ж/б обойма (только стенки) — 100 кг/м²
            reinforcement_kg = round(A_walls_m2 * 100.0, 1)
            extra_notes.append(
                f"Усиление: частичная ж/б обойма +{reinforcement_kg:.0f} кг "
                f"(z={z_m:.1f} м, σ_x≈{18.0 * z_m * 0.33:.1f} кПа по СП 22.13330)."
            )
        else:
            # Полная ж/б обойма — 250 кг/м²
            reinforcement_kg = round(A_walls_m2 * 250.0, 1)
            extra_notes.append(
                f"Усиление: полная ж/б обойма +{reinforcement_kg:.0f} кг "
                f"(z={z_m:.1f} м, σ_x≈{18.0 * z_m * 0.33:.1f} кПа по СП 22.13330)."
            )

    return CorpusSize(
        diameter_mm=cs.diameter_mm,
        height_mm=cs.height_mm,
        inlet_DN_mm=inlet_dn,
        outlet_DN_mm=cs.outlet_DN_mm,
        weight_estimate_kg=weight_estimate_kg,
        reinforcement_kg=reinforcement_kg,
        notes=extra_notes,
    )
