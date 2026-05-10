"""7-шаговый алгоритм первичного подбора насоса.

Соответствует ALGORITHM_SPEC.md §2 и 01_spec/matching.md.
"""

from __future__ import annotations

from typing import Any

from pump_calculator import catalog
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
        )
        # Duty point — точка работы
        pr.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        # Sync price_estimate_rub после возможных uplift'ов в make_pump_result.
        pr.price_estimate_rub = pr.price_breakdown.total_rub
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
        )
        alt.duty_point = {"Q_m3h": Q_m3h, "H_m": H_full_m}
        alt.price_estimate_rub = alt.price_breakdown.total_rub
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
        suggestions.append(InputSuggestion(
            field="dH_m",
            current_value=f"{L0.dH_m}",
            suggested_value=f"{abs(L0.dH_m)}",
            reason=(
                f"⚖️ Физика: dH = z₂ - z₁ = разность отметок (точка сброса минус "
                f"точка забора). dH={L0.dH_m} м означает что приёмник на |{L0.dH_m}| м "
                f"НИЖЕ источника.\n"
                f"🔬 По уравнению Бернулли P₁/(ρg) + z₁ = P₂/(ρg) + z₂ + h_тр: "
                f"при z₂ < z₁ жидкость течёт самотёком, насос не нужен.\n"
                f"💡 Если приёмник ВЫШЕ источника на {abs(L0.dH_m)} м — "
                f"уберите минус и поставьте {abs(L0.dH_m)}.\n"
                f"📐 По СП 32 §6.4 насос требуется только при положительном "
                f"геометрическом напоре + потерях на трение."
            ),
            severity="critical",
        ))

    # 3. L < 5 м для Q > 50 м³/ч — несоразмерно
    # Гидравлика: для серьёзных расходов внутриплощадочная трасса обычно
    # 30-100+ м (оборудование разнесено). L < 5 м физически возможен только
    # для микро-объектов (квартира).
    if L0.L_m is not None and L0.L_m < 5 and L0.Q_m3h > 50:
        suggestions.append(InputSuggestion(
            field="L_m",
            current_value=f"{L0.L_m}",
            suggested_value=f"{L0.L_m * 10}",
            reason=(
                f"📏 L={L0.L_m} м для Q={L0.Q_m3h} м³/ч — несоразмерно.\n"
                f"🔬 Гидравлика: для Q={L0.Q_m3h} м³/ч типовая трасса "
                f"30-100+ м (соединение между КНС, ОС, выпуском). "
                f"L<5 м означает почти отсутствие трубы.\n"
                f"💡 Возможно вы имели в виду {L0.L_m * 10} м (опечатка ×10)?\n"
                f"📐 Для Q≥50 м³/ч обычная норма: L_внутри = 50-200 м, "
                f"L_вне = 200-2000 м (СП 32 §6.5)."
            ),
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
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=(
                f"🔬 Гидравлика: при D={L1.pipe_D_mm} мм скорость "
                f"v=Q/A=Q/(πD²/4)={computed.v_ms:.3f} м/с.\n"
                f"⚠ По СП 32 §5.4 для бытовой канализации v_min=0.7 м/с — "
                f"при меньших скоростях осадок (взвешенные вещества) не "
                f"уносится, происходит ЗАИЛИВАНИЕ за месяцы.\n"
                f"📐 Расчёт оптимального D: D = √(4Q/(πv)), для v=1.2 м/с "
                f"(середина допустимого диапазона 0.7-2.5 м/с) → "
                f"D = √(4·{Q_m3s:.4f}/(π·1.2))·1000 = {D_optimal} мм (стандартный DN).\n"
                f"💡 Замените pipe_D_mm на {D_optimal}."
            ),
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
        suggestions.append(InputSuggestion(
            field="L1.pipe_D_mm",
            current_value=f"{L1.pipe_D_mm}",
            suggested_value=f"{D_optimal}",
            reason=(
                f"🔬 Гидравлика: при D={L1.pipe_D_mm} мм скорость "
                f"v={computed.v_ms:.2f} м/с.\n"
                f"⚠ СП 32 §5.4: v_max=2.5 м/с — иначе абразивный износ "
                f"трубы (срок службы падает в 2-3 раза) и эрозия фасонок.\n"
                f"💥 Жуковский: при резком закрытии клапана Δp = ρ·a·Δv = "
                f"1000·320·{computed.v_ms:.2f} ≈ {delta_p_bar:.1f} бар "
                f"(только для PE100, для стали ×3). Может разорвать трубу.\n"
                f"📐 Оптимум: D = √(4Q/(πv)) для v=1.2 м/с → {D_optimal} мм.\n"
                f"💡 Замените pipe_D_mm на {D_optimal}."
            ),
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
        suggestions.append(InputSuggestion(
            field="L1.pipe_material",
            current_value=f"{pipe_mat}",
            suggested_value="steel_seamless_new",
            reason=(
                f"🧪 Материаловедение: {pipe_mat} имеет T_max = 60°C "
                f"для длительной эксплуатации (ISO 4427 для ПЭ100).\n"
                f"📉 При T={temp_c}°C ползучесть ускоряется по закону "
                f"Аррениуса (k = A·exp(-E_a/RT)): срок службы падает "
                f"с 50 лет до 5-10 лет. Возможно разрушение трубы за месяцы.\n"
                f"💡 Замените на steel_seamless_new — до 200°C при PN ≤ 16 бар, "
                f"либо cast_iron_new — до 150°C, дешевле стали."
            ),
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
        suggestions.append(InputSuggestion(
            field="Q_m3h",
            current_value=f"{L0.Q_m3h}",
            suggested_value=f"{suggested_Q}",
            reason=(
                f"⚖️ Баланс масс (закон сохранения): dV/dt = Q_in - Q_out.\n"
                f"При Q_in={L1.inflow_per_hour_m3} > Q_out={L0.Q_m3h} м³/ч "
                f"уровень растёт со скоростью {delta:.1f} м³/ч.\n"
                f"⏱ Камера 5 м³ переполнится за {t_overflow_min:.1f} мин — "
                f"стоки пойдут на улицу.\n"
                f"💡 Решение 1: Q_насоса = Q_in × 1.2 = {suggested_Q} м³/ч "
                f"(+20% запас по СП 32 §6.5).\n"
                f"💡 Решение 2: 2-3 насоса параллельно (1+1 рабочий+резерв).\n"
                f"💡 Решение 3: увеличить V_камеры (буфер) — но это OPEX, не CAPEX."
            ),
            severity="critical",
        ))

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-10: 10 научных расширений — suggestions с 2-level reasons
    # ──────────────────────────────────────────────────────────────────

    # EXT-1: боковое давление грунта (СП 22.13330)
    if "auto_lateral_earth_pressure" in triggers and L1 and L1.install_depth_inlet_mm:
        z_m = L1.install_depth_inlet_mm / 1000
        gamma = 18.0  # кН/м³, объёмный вес грунта
        K_a = 0.33    # активное давление при φ=30°
        sigma_x_kpa = gamma * z_m * K_a
        eng = (
            f"🪨 СП 22.13330 «Основания зданий и сооружений», п.5.4 — "
            f"расчёт горизонтального давления грунта по теории Кулона.\n"
            f"📐 Формула: σ_x = γ·z·K_a, где K_a = tan²(45°-φ/2) — коэф. "
            f"активного давления.\n"
            f"При z={z_m:.1f} м, γ=18 кН/м³, φ=30° → K_a=0.33:\n"
            f"σ_x = 18·{z_m:.1f}·0.33 ≈ {sigma_x_kpa:.1f} кПа на стенку корпуса.\n"
            f"⚠ При z>5 м стандартный гладкий ПЭ-корпус деформируется — "
            f"требуются продольные рёбра жёсткости и/или ж/б обойма."
        )
        mgr = (
            f"🏗 Глубина монтажа {z_m:.1f} м — это глубокий заглубленный корпус.\n"
            f"💰 Стандартный ПЭ-корпус не справится с давлением грунта "
            f"({sigma_x_kpa:.0f} кПа) — нужны рёбра жёсткости (+150-300 тыс ₽) "
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

    # EXT-8: УФ/озон обеззараживание
    if "auto_disinfection_required" in triggers:
        eng = (
            f"🦠 СанПиН 2.1.5.980-00 «Гигиенические требования к охране "
            f"поверхностных вод», п.4.1.5 — обеззараживание стоков "
            f"перед сбросом в водоём (хоз-бытовые Q={L0.Q_m3h} > 100 м³/ч).\n"
            f"📐 УФ-доза по МУК 4.3.2030-05: D = I·t ≥ 30 мДж/см² "
            f"для инактивации E.coli (3 lg) и колифагов (2 lg).\n"
            f"📐 Озон по СанПиН: C·t ≥ 5 мг·мин/л (5 мг/л при t=1 мин).\n"
            f"⚠ Хлорирование запрещено для сброса в рыбохозяйственные "
            f"водоёмы (Приказ Росрыболовства №20)."
        )
        mgr = (
            f"🦠 Q={L0.Q_m3h} м³/ч хоз-бытовых — по СанПиН обязательно "
            f"обеззараживание перед сбросом.\n"
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

    # EXT-9: нитри/денитрификация
    if "auto_nitrification_check" in triggers:
        eng = (
            "🧪 Нитри/денитрификация в ЛОС промстоков (СП 32.13330 §9.2.5).\n"
            "📐 Кинетика по Monod: μ = μ_max·S/(K_s+S), где для "
            "Nitrosomonas μ_max=0.8 сут⁻¹, K_s≈1 мг/л NH4-N.\n"
            "⚠ Условия:\n"
            "  • Возраст ила θ_c ≥ 10 сут (бактерии медленно растут)\n"
            "  • Аэрация ≥ 6 ч (DO ≥ 2 мг/л в зоне нитрификации)\n"
            "  • T ≥ 12°C (при <10°C нитрификация останавливается)\n"
            "  • pH 7.5-8.5 (оптимум для аммоний-окисляющих)\n"
            "  • Рециркуляция нитратов 200-400% для денитри (аноксидная зона).\n"
            "📐 Объём аэротенка: V = Q·θ_аэр + Q·θ_денитр."
        )
        mgr = (
            f"🧪 Промстоки с азотом — нужна полноценная биологическая "
            f"очистка (нитри + денитрификация).\n"
            f"💰 ЛОС на Q={L0.Q_m3h} м³/ч с нитри/денитри:\n"
            f"  • Аэротенк ж/б 50-150 м³ — 1.5-3.5 млн ₽\n"
            f"  • Воздуходувка + аэраторы — 450-850 тыс ₽\n"
            f"  • Вторичный отстойник — 380-720 тыс ₽\n"
            f"  • Автоматика DO/pH/NH4 — 280-450 тыс ₽\n"
            f"⏱ Запуск ила (наработка биоценоза) — 4-8 недель.\n"
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

    # EXT-1: СП 22.13330 «Основания зданий». Глубокий заглубленный корпус
    # испытывает боковое давление грунта по Кулону: σ_x = γ·z·K_a, где
    # γ=18 кН/м³ (типовой грунт), K_a = tan²(45°-φ/2) = 0.33 при φ=30°.
    # При z=5+ м σ_x достигает 30 кПа — нужны рёбра жёсткости / спец-расчёт.
    if L1 and L1.install_depth_inlet_mm is not None and L1.install_depth_inlet_mm > 5000:
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

    # EXT-8: УФ/озон обеззараживание (СанПиН 2.1.5.980-00 §4.1.5).
    # При Q>100 м³/ч хоз-бытовых стоков обязателен сброс через ЛОС с
    # обеззараживанием перед выпуском в водоём. УФ-доза ≥30 мДж/см² или
    # озон 5 мг/л.
    if L0.wastewater_type == "domestic" and L0.Q_m3h > 100:
        triggers.append("auto_disinfection_required")

    # EXT-9: Нитри/денитрификация для промстоков (СП 32 §9). При наличии
    # азота аммонийного (NH4+ > 20 мг/л) необходим аэротенк с возрастом ила
    # ≥10 суток, аэрация ≥6 ч, рециркуляция нитратов 200-400%.
    if L0.wastewater_type == "industrial":
        triggers.append("auto_nitrification_check")

    # EXT-10: Гидробак ВНС (СП 30.13330 §11). Для повысительных насосных
    # станций чистой воды Q>50 м³/ч переменный расход компенсируется
    # гидроаккумулятором: V_бака = (Q_max - Q_min)·t_цикл/4. Без бака —
    # частые пуски ЧРП / гидроудары.
    if L0.wastewater_type == "clean_water" and L0.Q_m3h > 50:
        triggers.append("auto_hydrobak_required")

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

    # Шаг 5b: IP-фильтр двигателя (если L1.ip_motor задан).
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
        warnings.insert(0, (
            f"⚠ Q={L0.Q_m3h} м³/ч хоз-бытовых — по СанПиН 2.1.5.980-00 "
            f"обязательно обеззараживание (УФ ≥30 мДж/см² или озон ≥5 мг/л) "
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

    return CorpusSize(
        diameter_mm=cs.diameter_mm,
        height_mm=cs.height_mm,
        inlet_DN_mm=inlet_dn,
        outlet_DN_mm=cs.outlet_DN_mm,
        weight_estimate_kg=cs.weight_estimate_kg,
        notes=extra_notes,
    )
