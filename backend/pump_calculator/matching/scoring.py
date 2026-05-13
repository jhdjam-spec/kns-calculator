"""Composite score (Шаг 5) + «Why this pump?» explainer + selection per segment.

Соответствует matching.md §5-6. Содержит:
- composite_score()           — 0.40·BEP + 0.25·η + 0.20·H_margin + 0.10·avail + 0.05·warranty
- build_score_explanation()   — структурированное объяснение для UI explainer
- make_pump_result()          — конвертация raw dict → PumpResult с ценой комплекта
- pick_top_per_segment()      — топ-1 в каждом из {budget, mid, premium} + alternatives
- _CITATIONS_* константы

NB: модуль НЕ применяет фильтры — это делает matching.filtering. Здесь только
скоринг уже отфильтрованного списка.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
from pump_calculator.hydraulics import aor_zone
from pump_calculator.pricing import (
    estimate_fire_kit_price,
    estimate_kns_kit_price,
    estimate_spd_kit_price,
)
from pump_calculator.pump_station_geometry import (
    calc_specific_speed_ns,
    score_ns_compatibility,
)
from pump_calculator.schemas import (
    L1Input,
    PumpEnvelope,
    PumpResult,
    SelectionResultsBySegment,
)


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
