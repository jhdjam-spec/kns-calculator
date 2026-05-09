"""Оркестратор «Проекта»: запускает все нужные расчёты последовательно.

Главная идея: пользователь вводит ОДИН раз базовые параметры
(тип объекта, локация, население, объём) → калькулятор автоматически
вызывает все нужные модули с правильными default-значениями.
"""
from __future__ import annotations

from .models import (
    ProjectInput,
    ProjectPreset,
    ProjectResult,
    ProjectSubsystems,
    SubsystemResult,
)
from pump_calculator.regulations import ref as _reg_ref


def _ref_dict(reg_key: str, section: str, purpose: str, quote: str = "") -> dict:
    """Хелпер: создаёт dict-references из ALL_REGULATIONS через ref().

    Преимущества vs hand-typed dict:
    - regulation_code и url подтянутся автоматически из БД нормативов
    - typo в reg_key выбросит KeyError на инициализации, не silent-bug
    - section/purpose остаются под контролем местного кода

    Использование:
        references=[
            _ref_dict("SP_32", "§6", "Канализация наружная — расчёт КНС"),
            _ref_dict("SP_30", "прил. А.2", "Норма водопотребления"),
        ]
    """
    r = _reg_ref(reg_key, section, purpose, quote)
    return {
        "regulation_code": r.regulation_code,
        "section": r.section,
        "purpose": r.purpose,
        "quote": r.quote,
        "url": r.url,
    }

# Пресеты — какие подсистемы по умолчанию включить для каждого типа объекта.
PRESET_DEFAULT_SUBSYSTEMS: dict[ProjectPreset, ProjectSubsystems] = {
    "ihs": ProjectSubsystems(
        kns=True, los=True, electrical=True, climate=True, structural=True,
        vns_potable=False, vns_fire=False, storm=False, bom_export=True,
    ),
    "kotedj_settlement": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=False, storm=True, los=True,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "apartment_complex": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=True, los=False,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "hotel": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=True, los=False,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "trc": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=True, los=False,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "azs": ProjectSubsystems(
        kns=True, vns_potable=False, vns_fire=False, storm=True, los=True,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "industrial": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=True, los=True,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "warehouse": ProjectSubsystems(
        kns=False, vns_potable=False, vns_fire=True, storm=True, los=False,
        electrical=True, climate=True, structural=False, bom_export=True,
    ),
    "gazprom": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=True, los=True,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "agricultural": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=False, storm=False, los=True,
        electrical=True, climate=True, structural=True, bom_export=True,
    ),
    "school": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=False, los=False,
        electrical=True, climate=True, structural=False, bom_export=True,
    ),
    "hospital": ProjectSubsystems(
        kns=True, vns_potable=True, vns_fire=True, storm=False, los=False,
        electrical=True, climate=True, structural=False, bom_export=True,
    ),
    "custom": ProjectSubsystems(),
}


def list_presets() -> list[dict]:
    """Каталог пресетов для UI выбора типа объекта."""
    titles = {
        "ihs": "ИЖС / частный дом",
        "kotedj_settlement": "Коттеджный посёлок",
        "apartment_complex": "Многоквартирный ЖК",
        "hotel": "Гостиница / отель",
        "trc": "ТРЦ / БЦ",
        "azs": "АЗС / автомойка",
        "industrial": "Промпредприятие",
        "warehouse": "Складской комплекс",
        "gazprom": "Нефтегазовый объект",
        "agricultural": "Сельхоз / коровник",
        "school": "Школа / детсад",
        "hospital": "Больница / клиника",
        "custom": "Произвольный",
    }
    descriptions = {
        "ihs": "Бытовая канализация (КНС) + локальные очистные (ЛОС)",
        "kotedj_settlement": "Магистральная КНС + ЛОС + ливневая канализация",
        "apartment_complex": "Бытовая КНС + наружное и внутреннее пожаротушение (ВПВ)",
        "hotel": "Хозпитьевая ВНС + пожаротушение + ЛОС",
        "trc": "Дренаж парковок + спринклерное пожаротушение",
        "azs": "ЛОС с нефтеуловителем + ливневая КНС",
        "industrial": "Промышленные стоки + ППД (поддержание пластового давления) + ливнёвка",
        "warehouse": "Пожаротушение + ливневая канализация",
        "gazprom": "Корпоративный стандарт нефтегаза: ATEX, HART, исполнение УХЛ1, ABB AC500",
        "agricultural": "Полив + дренаж + бытовая КНС",
        "school": "Хозпитьевое водоснабжение + пожаротушение (СП 10.13130)",
        "hospital": "I категория надёжности по СП 31, повышенные требования",
        "custom": "Настройка подсистем вручную",
    }
    return [
        {
            "key": p,
            "title": titles[p],
            "description": descriptions[p],
            "default_subsystems": PRESET_DEFAULT_SUBSYSTEMS[p].model_dump(),
        }
        for p in PRESET_DEFAULT_SUBSYSTEMS
    ]


# Маппинг preset → тип стоков для КНС
_PRESET_WASTEWATER_TYPE: dict[str, str] = {
    "ihs": "domestic",
    "kotedj_settlement": "domestic",
    "apartment_complex": "domestic",
    "hotel": "domestic",
    "trc": "domestic",
    "azs": "industrial",         # АЗС: нефтесодержащие стоки + ливнёвка через сепаратор
    "industrial": "industrial",
    "warehouse": "drainage",     # склад: преимущественно ливнёвка
    "gazprom": "industrial",
    "agricultural": "drainage",  # сельхоз: дренаж + поилка
    "school": "domestic",
    "hospital": "domestic",
    "custom": "domestic",
}


# Маппинг preset → building_type из water_supply (для нормы потребления)
_PRESET_BUILDING_TYPE: dict[str, str] = {
    "ihs": "residential_with_baths",
    "kotedj_settlement": "residential_with_baths",
    "apartment_complex": "residential_with_baths",
    "hotel": "hotel_standard",
    "trc": "trc",
    "azs": "carwash",       # ближайший аналог в нормах
    "industrial": "industrial_generic",
    "warehouse": "industrial_generic",
    "gazprom": "industrial_generic",
    "agricultural": "agricultural",
    "school": "school",
    "hospital": "hospital",
    "custom": "office",
}


def _resolve_q_for_kns(inputs: ProjectInput) -> tuple[float, str]:
    """Определяет расчётный Q для КНС с учётом типа объекта и числа пользователей.

    Возвращает (Q_max_час_м³/ч, объяснение).
    """
    from pump_calculator.water_supply import NORMS_LITERS_PER_DAY

    bt = _PRESET_BUILDING_TYPE.get(inputs.preset, "office")
    norm = NORMS_LITERS_PER_DAY.get(bt)
    if norm is None:
        return max(inputs.population * 0.25 / 24 * 2.5, 1.0), "fallback 0.25"

    # Определяем число расчётных единиц
    unit = norm["unit"]
    if unit in ("чел", "место", "учащийся", "голова"):
        n_units = inputs.population
    elif unit == "номер":
        n_units = inputs.rooms or max(inputs.population, 1)
    elif unit == "койка":
        n_units = inputs.beds or max(inputs.population, 1)
    elif unit in ("посещение", "посетитель"):
        n_units = inputs.visits_per_day or max(inputs.population, 1)
    elif unit == "100м²":
        n_units = max(int(inputs.area_m2 / 100), 1) if inputs.area_m2 else 1
    elif unit == "авто":
        n_units = inputs.visits_per_day or 50    # default ~50 авто/сут на АЗС
    elif unit == "кг":
        n_units = inputs.visits_per_day or 100
    else:
        n_units = max(inputs.population, 1)

    norm_total = norm["norm_total"]
    K_sut = norm["K_sut_max"]
    K_hour = norm["K_hour_max"]

    # Q_сред (м³/сут) → Q_max_час (м³/ч)
    q_avg = n_units * norm_total / 1000.0      # м³/сут
    q_max_day = q_avg * K_sut
    q_max_hour = q_max_day / 24 * K_hour

    explanation = (
        f"{n_units} {unit} × {norm_total} л/сут × K_сут={K_sut} × K_ч={K_hour}/24 "
        f"= {q_max_hour:.1f} м³/ч"
    )
    return max(q_max_hour, 1.0), explanation


def _calc_kns_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема КНС — вызывает /select с правильным wastewater_type и Q."""
    from pump_calculator.matching import select_pumps as run_selection
    from pump_calculator.schemas import L0Input, L1Input, SelectionRequest

    wastewater = _PRESET_WASTEWATER_TYPE.get(inputs.preset, "domestic")
    q_max_m3h, q_explanation = _resolve_q_for_kns(inputs)

    try:
        l0 = L0Input(
            Q_m3h=q_max_m3h,
            dH_m=5,
            L_m=50,
            wastewater_type=wastewater,
        )
        l1: L1Input | None = None
        if inputs.is_atex_zone:
            l1 = L1Input(Ex_required=True)
        request = SelectionRequest(L0=l0, L1=l1)
        result = run_selection(request)

        atex_note = " (ATEX)" if inputs.is_atex_zone else ""
        return SubsystemResult(
            name=f"КНС {wastewater}{atex_note}",
            status="ok",
            summary=(
                f"Q={q_max_m3h:.1f} м³/ч ({q_explanation}). "
                f"Подобрано {len(result.results.__dict__) if hasattr(result.results, '__dict__') else 3} вариантов."
            ),
            data={
                "Q_m3h": q_max_m3h,
                "wastewater_type": wastewater,
                "atex_required": inputs.is_atex_zone,
                "q_explanation": q_explanation,
                "selection": result.model_dump(),
            },
            references=[
                _ref_dict("SP_32", "§6", "Канализация наружная — расчёт КНС"),
                _ref_dict("SP_30", "прил. А.2", "Норма водопотребления (формула расхода)"),
            ],
        )
    except Exception as e:
        return SubsystemResult(
            name="КНС",
            status="error",
            summary=f"Ошибка расчёта: {e}",
            data={},
        )


def _calc_water_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема ВНС хозпитьевая (Phase 23) с поддержкой rooms/beds."""
    from pump_calculator.water_supply import (
        WaterScenarioInput,
        calc_water_demand,
        sizing_water_station,
    )
    try:
        bt = _PRESET_BUILDING_TYPE.get(inputs.preset, "residential_with_baths")

        # Передаём все возможные единицы — `calc_water_demand` сам выберет
        # подходящее по типу здания.
        water_input = WaterScenarioInput(
            building_type=bt,
            population=max(inputs.population, 1),
            rooms=inputs.rooms,
            beds=inputs.beds,
            visits_per_day=inputs.visits_per_day,
            area_m2=inputs.area_m2,
            floors=inputs.floors,
        )
        demand = calc_water_demand(water_input)
        station = sizing_water_station(water_input, demand)

        return SubsystemResult(
            name="ВНС хозпитьевая",
            status="ok",
            summary=(
                f"Q_сред={demand.total_Q_avg_m3_day:.1f} м³/сут, "
                f"Q_max_сек={demand.total_Q_max_sec_lps:.2f} л/с, "
                f"насосов {station.operating_pumps}+{station.standby_pumps}"
            ),
            data={"demand": demand.model_dump(), "station": station.model_dump()},
            references=demand.references,
        )
    except Exception as e:
        return SubsystemResult(
            name="ВНС хозпитьевая",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


def _calc_fire_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема пожаротушения (Phase 22)."""
    from pump_calculator.fire_water import FireScenarioInput, calculate_fire_scenario

    try:
        occupancy_map = {
            "ihs": "residential",
            "apartment_complex": "residential",
            "kotedj_settlement": "residential",
            "hotel": "public",
            "trc": "public",
            "school": "public",
            "hospital": "public",
            "industrial": "industrial_b",
            "warehouse": "warehouse",
            "azs": "industrial_a",
            "gazprom": "industrial_a",
            "agricultural": "agricultural",
        }
        fire_input = FireScenarioInput(
            occupancy=occupancy_map.get(inputs.preset, "public"),
            building_class="I",
            volume_m3=inputs.volume_m3,
            floors=inputs.floors,
            population=inputs.population,
            water_source="reservoir",
        )
        result = calculate_fire_scenario(fire_input)
        return SubsystemResult(
            name="Пожарное водоснабжение",
            status="ok" if not result.warnings else "warning",
            summary=(
                f"Q_наруж={result.demand.external_lps:.1f} л/с, "
                f"V_резервуара={result.reservoir.required_volume_m3:.0f} м³"
                if result.reservoir
                else f"Q_наруж={result.demand.external_lps:.1f} л/с (городская сеть)"
            ),
            data=result.model_dump(),
            references=[r.model_dump() if hasattr(r, 'model_dump') else r for r in result.references],
            warnings=result.warnings,
        )
    except Exception as e:
        return SubsystemResult(
            name="Пожарное водоснабжение",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


def _calc_climate_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема климата (Phase 25)."""
    from pump_calculator.climate import calc_pipe_burial_depth

    try:
        result = calc_pipe_burial_depth(
            region_city=inputs.region_city,
            soil_type=inputs.soil_type,
            pipe_dn_mm=200,
            has_groundwater=inputs.has_groundwater,
        )
        return SubsystemResult(
            name="Климат и заложение",
            status="ok",
            summary=(
                f"Заложение трубы {result.burial_depth_m:.2f} м "
                f"(d_fn={result.frost_depth_normative_m} м), "
                + ("утепление требуется" if result.insulation_required else "без утепления")
            ),
            data=result.model_dump(),
            references=result.references,
        )
    except Exception as e:
        return SubsystemResult(
            name="Климат и заложение",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


def _calc_structural_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема прочности (Phase 26) — пригруз бетоном."""
    from pump_calculator.structural import StructuralScenarioInput, calc_ballast_concrete

    try:
        # Грубая оценка диаметра/высоты по объёму проекта
        diameter = 1.5 if inputs.volume_m3 < 500 else 2.0 if inputs.volume_m3 < 5000 else 3.0
        height = 2.5
        burial = 2.0
        gw = 0.5 if inputs.has_groundwater else 5.0

        struct_input = StructuralScenarioInput(
            diameter_m=diameter,
            height_m=height,
            material="fiberglass",
            wall_thickness_mm=15,
            groundwater_depth_m=gw,
            burial_depth_m=burial,
            soil_type=inputs.soil_type,
        )
        result = calc_ballast_concrete(struct_input)
        return SubsystemResult(
            name="Прочность корпуса",
            status="ok",
            summary=(
                f"Пригруз {result.ballast_concrete_volume_m3:.1f} м³ бетона"
                if result.is_required
                else "Пригруз не требуется"
            ),
            data=result.model_dump(),
            references=result.references,
        )
    except Exception as e:
        return SubsystemResult(
            name="Прочность корпуса",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


_PRESET_LOS_SOURCE: dict[str, str] = {
    "ihs": "domestic",
    "kotedj_settlement": "domestic",
    "apartment_complex": "domestic",
    "hotel": "domestic",
    "trc": "domestic",
    "azs": "industrial_oily",       # АЗС: нефтесодержащие
    "industrial": "industrial_oily",
    "warehouse": "stormwater",
    "gazprom": "industrial_oily",
    "agricultural": "agricultural",
    "school": "domestic",
    "hospital": "domestic",
    "custom": "domestic",
}


def _calc_los_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема ЛОС (Phase 27) с маппингом preset → source_type."""
    from pump_calculator.los import LOSScenarioInput, select_los_block

    source_type = _PRESET_LOS_SOURCE.get(inputs.preset, "domestic")

    try:
        flow_m3day = inputs.population * 0.20    # хозбытовая норма
        # Для АЗС/промышл. — берём из visits_per_day если задано
        if source_type == "industrial_oily" and inputs.visits_per_day:
            flow_m3day = max(inputs.visits_per_day * 0.25, 1.0)    # ~250 л на авто/посетителя

        los_input = LOSScenarioInput(
            source_type=source_type,
            flow_m3_per_day=max(flow_m3day, 1.0),
            discharge_category="irrigation",
            population_equivalent=inputs.population,
        )
        result = select_los_block(los_input)
        block = result.selected_block
        if block:
            summary = f"{block.manufacturer} {block.model}, {block.capacity_m3_per_day} м³/сут ({source_type})"
        else:
            summary = f"Q={flow_m3day:.1f} м³/сут — индивидуальный проект ({source_type})"
        return SubsystemResult(
            name=f"ЛОС {source_type}",
            status="ok" if block else "warning",
            summary=summary,
            data=result.model_dump(),
            references=result.references,
            warnings=result.warnings,
        )
    except Exception as e:
        return SubsystemResult(
            name="ЛОС",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


# Дефолтные распределения поверхностей по типу объекта (для storm-расчёта)
_PRESET_STORM_SURFACES: dict[str, dict[str, float]] = {
    "ihs":               {"roof": 0.25, "asphalt": 0.20, "lawn": 0.55},
    "kotedj_settlement": {"roof": 0.20, "asphalt": 0.30, "lawn": 0.50},
    "apartment_complex": {"roof": 0.30, "asphalt": 0.50, "lawn": 0.20},
    "hotel":             {"roof": 0.30, "asphalt": 0.40, "lawn": 0.30},
    "trc":               {"roof": 0.40, "asphalt": 0.55, "lawn": 0.05},
    "azs":               {"asphalt": 0.95, "lawn": 0.05},
    "industrial":        {"roof": 0.30, "asphalt": 0.60, "lawn": 0.10},
    "warehouse":         {"roof": 0.50, "asphalt": 0.40, "lawn": 0.10},
    "gazprom":           {"roof": 0.20, "asphalt": 0.70, "lawn": 0.10},
    "agricultural":      {"roof": 0.10, "asphalt": 0.20, "lawn": 0.70},
    "school":            {"roof": 0.30, "asphalt": 0.40, "lawn": 0.30},
    "hospital":          {"roof": 0.30, "asphalt": 0.40, "lawn": 0.30},
    "custom":            {"asphalt": 0.50, "lawn": 0.50},
}


def _calc_storm_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема ливневой канализации (Phase 18) — расчёт пикового Q_r по СП 32 §6.

    Использует площадь территории и дефолтное распределение поверхностей по
    типу объекта.
    """
    from pump_calculator.storm import calculate_full_storm
    from pump_calculator.storm.models import StormInput, SurfaceBreakdown

    if inputs.area_m2 <= 0:
        return SubsystemResult(
            name="Ливневая канализация",
            status="skipped",
            summary="Площадь территории не указана — расчёт ливнёвки невозможен",
            data={},
        )

    try:
        area_ha = inputs.area_m2 / 10000.0
        distribution = _PRESET_STORM_SURFACES.get(inputs.preset, _PRESET_STORM_SURFACES["custom"])

        surfaces = SurfaceBreakdown(
            roof_ha=area_ha * distribution.get("roof", 0),
            asphalt_ha=area_ha * distribution.get("asphalt", 0),
            lawn_ha=area_ha * distribution.get("lawn", 0),
        )

        storm_input = StormInput(
            sp_revision="SP_32_2018",
            region_city=inputs.region_city,
            surfaces=surfaces,
            period_P_year=2 if inputs.preset in ("industrial", "azs", "trc", "gazprom") else 1,
        )
        result = calculate_full_storm(storm_input)

        return SubsystemResult(
            name="Ливневая канализация",
            status="ok",
            summary=(
                f"Q_r = {result.peak_flow.Q_r_l_s:.1f} л/с "
                f"({result.peak_flow.Q_r_m3h:.0f} м³/ч), F={area_ha:.2f} га"
            ),
            data=result.model_dump(),
            references=[
                _ref_dict("SP_32", "§6.2.4", "Метод предельных интенсивностей (ливнёвка)"),
            ],
        )
    except Exception as e:
        return SubsystemResult(
            name="Ливневая канализация",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


def _calc_electrical_subsystem(inputs: ProjectInput, kns_result: SubsystemResult | None) -> SubsystemResult:
    """Подсистема электрики (Phase 24) — мощность двигателя, кабель, шкаф.

    Опирается на результат КНС (мощность подобранного насоса).
    """
    from pump_calculator.electrical import (
        calc_motor_power_required,
        select_cable_section,
        select_circuit_breaker,
        select_control_panel,
    )

    if kns_result is None or kns_result.status != "ok":
        return SubsystemResult(
            name="Электрика",
            status="skipped",
            summary="Электрика рассчитывается на базе КНС — сначала включите КНС",
            data={},
        )

    try:
        # Q и H берём из подобранного насоса (mid-сегмент)
        sel = kns_result.data.get("selection", {})
        results = sel.get("results", {})
        mid = results.get("mid") or results.get("budget") or results.get("premium")
        if not mid:
            return SubsystemResult(
                name="Электрика",
                status="warning",
                summary="Не удалось извлечь параметры подобранного насоса",
                data={},
            )

        Q = mid.get("duty_point", {}).get("Q_m3h", kns_result.data.get("Q_m3h", 10))
        H = mid.get("duty_point", {}).get("H_m", 10)
        P_motor = mid.get("P_kW") or 5.5    # fallback

        motor_calc = calc_motor_power_required(
            Q_m3h=Q, H_m=H,
            pump_efficiency=0.65,
            starting_method="VFD" if inputs.is_atex_zone or P_motor > 30 else "soft_start",
        )
        cable = select_cable_section(
            I_load_a=motor_calc.nominal_current_a,
            L_m=50,
        )
        breaker = select_circuit_breaker(
            I_load_a=motor_calc.nominal_current_a,
            starting_method=motor_calc.starting_method,
        )
        panel = select_control_panel(
            P_motor_kw=motor_calc.P_motor_nominal_kw,
            n_pumps=2,
            reliability_category=1 if inputs.preset == "gazprom" else 2,
            is_atex_zone=inputs.is_atex_zone,
        )

        atex_note = " (ATEX)" if inputs.is_atex_zone else ""
        return SubsystemResult(
            name=f"Электрика и автоматика{atex_note}",
            status="ok",
            summary=(
                f"P_двиг={motor_calc.P_motor_nominal_kw} кВт, "
                f"кабель {cable.cable_type} {cable.n_cores}×{cable.section_mm2} мм², "
                f"автомат {breaker.description}, шкаф {panel.name}"
            ),
            data={
                "motor": motor_calc.__dict__,
                "cable": cable.__dict__,
                "breaker": breaker.__dict__,
                "panel": panel.model_dump(),
            },
            references=[
                _ref_dict("PUE_7", "гл. 1.3, 7.3", "Подбор кабеля и защиты"),
                _ref_dict("IEC_60034", "общ.", "Электрические машины (двигатели насосов)"),
                _ref_dict("TR_TS_004", "общ.", "Безопасность низковольтного оборудования"),
            ],
        )
    except Exception as e:
        return SubsystemResult(
            name="Электрика",
            status="error",
            summary=f"Ошибка: {e}",
            data={},
        )


def calculate_project(inputs: ProjectInput) -> ProjectResult:
    """Главный оркестратор: запускает все нужные подсистемы."""
    notes: list[str] = []

    # Если subsystems = default — берём из preset
    if inputs.preset in PRESET_DEFAULT_SUBSYSTEMS and inputs.subsystems == ProjectSubsystems():
        inputs.subsystems = PRESET_DEFAULT_SUBSYSTEMS[inputs.preset]
        notes.append(f"Подсистемы из пресета '{inputs.preset}'")

    result = ProjectResult(
        project_name=inputs.project_name,
        project_code=inputs.project_code,
        preset=inputs.preset,
        notes=notes,
    )

    # Запускаем каждую подсистему (если включена)
    if inputs.subsystems.kns:
        result.kns = _calc_kns_subsystem(inputs)
    if inputs.subsystems.vns_potable:
        result.vns_potable = _calc_water_subsystem(inputs)
    if inputs.subsystems.vns_fire:
        result.vns_fire = _calc_fire_subsystem(inputs)
    if inputs.subsystems.storm:
        result.storm = _calc_storm_subsystem(inputs)
    if inputs.subsystems.los:
        result.los = _calc_los_subsystem(inputs)
    if inputs.subsystems.climate:
        result.climate = _calc_climate_subsystem(inputs)
    if inputs.subsystems.structural:
        result.structural = _calc_structural_subsystem(inputs)
    # electrical — после KNS, на основе подобранного насоса
    if inputs.subsystems.electrical:
        result.electrical = _calc_electrical_subsystem(inputs, result.kns)

    # Подсчёт сводных метрик
    all_subsystems = [
        result.kns, result.vns_potable, result.vns_fire,
        result.storm, result.los, result.climate, result.structural,
    ]
    active = [s for s in all_subsystems if s is not None]
    result.total_warnings = sum(len(s.warnings) for s in active)

    # Сводка ссылок (без дублей)
    seen_refs: set[tuple] = set()
    for s in active:
        for ref in s.references:
            if isinstance(ref, dict):
                key = (ref.get("regulation_code", ""), ref.get("section", ""))
            else:
                key = (str(ref), "")
            if key not in seen_refs:
                seen_refs.add(key)
                result.references_consolidated.append(
                    ref if isinstance(ref, dict) else {"regulation_code": str(ref), "section": ""}
                )

    notes.append(f"Запущено подсистем: {len(active)}")
    notes.append(f"Предупреждений: {result.total_warnings}")
    return result
