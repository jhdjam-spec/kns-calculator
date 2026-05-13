"""Главный orchestrator подбора насоса — `select_pumps()`.

Тонкая обёртка которая склеивает 7 шагов алгоритма:
  0. apply_l0_defaults                              — этот файл
  1-2. compute_hydraulics                           — hydraulics.py
  3. filter_by_wastewater_type                      — matching.filtering
  4. filter_by_envelope                             — matching.filtering
  5а. filter_by_aor                                 — matching.filtering
  5б. filter_by_ex                                  — matching.filtering
  5в. filter_by_ip_motor                            — matching.filtering
  6. pick_top_per_segment (composite_score)         — matching.scoring
  7. evaluate_handoff_triggers                      — matching.triggers
  7b. evaluate_cavitation_for_results               — этот файл (ISO 9906:2024)
  Final. build_suggestions + warnings + corpus_size — matching.suggestions + этот файл
"""

from __future__ import annotations

import math

from pump_calculator import catalog
from pump_calculator.ab_testing import THOMA_CAVITATION, is_flag_on
from pump_calculator.cavitation import (
    CavitationResult,
    analyze_cavitation,
    explain_cavitation_engineer,
    explain_cavitation_manager,
)
from pump_calculator.hydraulics import compute_hydraulics
from pump_calculator.matching.filtering import (
    filter_by_aor,
    filter_by_envelope,
    filter_by_ex,
    filter_by_ip_motor,
    filter_by_wastewater_type,
)
from pump_calculator.matching.scoring import pick_top_per_segment
from pump_calculator.matching.suggestions import build_suggestions
from pump_calculator.matching.triggers import (
    _ext_8_uv_dose_required,
    evaluate_handoff_triggers,
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
    # A/B gate: ISO 9906:2024 Thoma-кавитационный анализ vs legacy NPSHa-check.
    # Sc.D. Cross-Domain 2026-05-13: bucketing по hash(Q,H,L1) — repeat-stable
    # для одного и того же запроса; default_pct=1.0 (полный rollout).
    _cav_bucket_key = f"Q={L0_filled.Q_m3h};H={computed.H_full_m:.2f}"
    if is_flag_on(THOMA_CAVITATION, request_id=_cav_bucket_key):
        cavitation_per_segment = evaluate_cavitation_for_results(results, computed, L1)
        cav_risks = [r.risk for r in cavitation_per_segment.values()]
        if "critical" in cav_risks or "warning" in cav_risks:
            if "auto_cavitation_warning" not in triggers:
                triggers.append("auto_cavitation_warning")
    else:
        # Legacy fallback (до Sc.D. 2026-05-13): простой `NPSHa - NPSHr ≥ 0.5`.
        # Сохраняется только для backward-compat / canary-rollback.
        cavitation_per_segment = {}
        if computed.npsha_m is not None and computed.npsha_m < 5.0:
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
