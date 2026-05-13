"""Шаг 7: триггеры hand-off + scientific helpers (EXT-9 / EXT-15 / EXT-16 / EXT-8).

Соответствует matching.md §7. Содержит:
- `evaluate_handoff_triggers()` — главная функция, возвращает list[str] триггеров.
- Helpers `_check_ext_9_nitrification`, `_check_ext_15_phosphorus`,
  `_check_ext_16_denitrification`, `_ext_8_uv_dose_required` — экспортируются
  для прямых вызовов из тестов (test_ext9_nitrification.py).

NB: Никаких InputSuggestion'ов / UX-прозы здесь нет — это matching.suggestions.
Этот модуль возвращает только идентификаторы триггеров (auto_*).
"""

from __future__ import annotations

from pump_calculator.schemas import ComputedHydraulics, L0Input, L1Input

# ---------------------------------------------------------------------------
# Phase 34+ (2026-05-13): научные helper-функции для EXT-9 / EXT-8 / EXT-15 / EXT-16.
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


def _check_ext_15_phosphorus(
    L0: L0Input, L1: L1Input | None
) -> dict | None:
    """EXT-15: проверка необходимости удаления фосфора (Metcalf & Eddy §8-3).

    Возвращает dict с параметрами расчёта (p_in, p_target, dose, method) либо None.

    Условия срабатывания:
      • wastewater_type в (domestic, industrial)
      • Q_m3h ≥ 50 (для малых КНС <50 м³/ч P-removal экономически не оправдан)
      • heavy_metals_present=False (физ-химия требует другого approach)
      • Ex_required=False (нефтехимия)
      • target_discharge в (fishery_water, general_use, reuse_irrigation)
      • P_in > ПДК по target_discharge

    Sc.D. cross-domain: тяжёлые металлы — Cr, Cd, Pb блокируют осаждение FeCl3.
    """
    if L0.wastewater_type not in ("domestic", "industrial"):
        return None
    if L0.Q_m3h < 50:
        return None
    if L1 and L1.Ex_required:
        return None
    if L1 and getattr(L1, "heavy_metals_present", False):
        return None

    target = (L1.target_discharge if L1 and L1.target_discharge else "general_use")
    # Для городской канализации (5 мг/л) — порог высокий, обычно не нужно
    if target == "municipal_sewage":
        return None

    # P_in: явно задано либо default
    p_in = (L1.p_in_mgL if L1 and L1.p_in_mgL is not None else None)
    if p_in is None:
        from pump_calculator.los.phosphorus import get_p_default
        p_in = get_p_default(L0.wastewater_type)

    from pump_calculator.los.phosphorus import calculate_p_removal, get_p_limit
    p_limit = get_p_limit(target)
    if p_in <= p_limit:
        return None

    # Метод: EBPR для бытовых при Q>500, иначе FeCl3 (универсальный)
    if L0.wastewater_type == "domestic" and L0.Q_m3h > 500:
        method = "ebpr"
    else:
        method = "fecl3"

    calc = calculate_p_removal(p_in, p_limit, method=method, Q_m3_h=L0.Q_m3h)
    calc["target"] = target
    return calc


def _check_ext_16_denitrification(
    L0: L0Input, L1: L1Input | None, computed: ComputedHydraulics | None
) -> dict | None:
    """EXT-16: проверка необходимости денитрификации (Henze IWA §3.5).

    Условие: нитрификация уже сработала (EXT-9), т.к. без NH4→NO3 нечего
    денитрифицировать. Затем NO3_in (= NH4_after_nitrification как proxy)
    проверяется против ПДК NO3 по target_discharge.
    """
    ext9 = _check_ext_9_nitrification(L0, L1, computed)
    if ext9 is None:
        return None  # денитрификация без нитрификации не имеет смысла

    # NO3_in после полной нитрификации ≈ NH4_in (1 моль NH4-N → 1 моль NO3-N)
    no3_in = ext9["nh4"]
    bod5 = ext9["bod5"]
    T = ext9["T"]
    target = ext9["target"]

    from pump_calculator.los.denitrification import calculate_denitrification

    # Optional override через L1.no3_target_mgL
    override = L1.no3_target_mgL if L1 and L1.no3_target_mgL is not None else None
    result = calculate_denitrification(
        no3_in_mgL=no3_in,
        target=target,
        bod5_in_mgL=bod5,
        T_c=T,
        no3_target_override=override,
    )
    if not result.get("needed"):
        return None
    return result


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

    # EXT-17 (Sub T cross-domain P2, 2026-05-13): СП 45.13330.2017 §6.1
    # «Земляные сооружения». При глубине котлована > 3 м или УГВ выше дна
    # или слабом грунте (peat / sand_water_saturated / clay_soft) — шпунт
    # рекомендуется/обязателен. PhD-Mechanics backlog: «K_p для траншеи».
    if L1 and L1.install_depth_inlet_mm is not None:
        z_m_trench = L1.install_depth_inlet_mm / 1000
        soil = L1.soil_type or "sand_medium"
        gwl_above_bottom = (
            L1.groundwater_level_m is not None
            and (z_m_trench + L1.groundwater_level_m) > 0
        )
        weak_soil = soil in ("peat", "sand_water_saturated", "clay_soft")
        if (
            z_m_trench > 3.0
            or gwl_above_bottom
            or weak_soil
        ):
            triggers.append("auto_trench_sheet_pile_required")

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

    # EXT-15 (Phase 34+ P2 биология): удаление фосфора (Metcalf & Eddy §8-3).
    # Срабатывает при Q≥50, target ≠ municipal_sewage, P_in > ПДК.
    # Default P_in=8 (бытовые), 20 (индустр); метод FeCl3 для Q<500, EBPR ≥500.
    if _check_ext_15_phosphorus(L0, L1):
        triggers.append("auto_phosphorus_removal")

    # EXT-16 (Phase 34+ P2 биология): денитрификация (Henze IWA §3.5).
    # Срабатывает ТОЛЬКО после EXT-9 (без нитрификации нет нитратов).
    # Проверяет NO3 > ПДК по target_discharge.
    if _check_ext_16_denitrification(L0, L1, computed):
        triggers.append("auto_denitrification_required")

    # EXT-10: Гидробак ВНС (СП 30.13330 §11). Для повысительных насосных
    # станций чистой воды Q>50 м³/ч переменный расход компенсируется
    # гидроаккумулятором: V_бака = (Q_max - Q_min)·t_цикл/4. Без бака —
    # частые пуски ЧРП / гидроудары.
    if L0.wastewater_type == "clean_water" and L0.Q_m3h > 50:
        triggers.append("auto_hydrobak_required")

    return triggers
