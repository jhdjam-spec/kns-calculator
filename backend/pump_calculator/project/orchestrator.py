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
        "gazprom": "Газпром / нефтегаз СТО",
        "agricultural": "Сельхоз / коровник",
        "school": "Школа / детсад",
        "hospital": "Больница / клиника",
        "custom": "Произвольный",
    }
    descriptions = {
        "ihs": "4-5 жителей, септик ЛОС, без пожарки",
        "kotedj_settlement": "Магистральная КНС + ЛОС + ливнёвка",
        "apartment_complex": "Бытовая КНС + наружная пожарка + ВПВ",
        "hotel": "Полный комплект ВНС + пожарка + ЛОС",
        "trc": "Дренажные парковки + спринклеры + большая пожарка",
        "azs": "ЛОС с нефтеуловителем + ливневая КНС",
        "industrial": "Промстоки + ППД + промливнёвка",
        "warehouse": "Холодный склад: пожарка + ливнёвка",
        "gazprom": "СТО: ABB AC500, HART, -47°C, ATEX",
        "agricultural": "Полив + дренаж + бытовая КНС",
        "school": "Хозпит. + пожарка по СП 10",
        "hospital": "I категория надёжности, повышенные требования",
        "custom": "Настройка вручную",
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


def _calc_kns_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема КНС — вызывает основной /select."""
    from pump_calculator.matching import select_pumps as run_selection
    from pump_calculator.schemas import L0Input, SelectionRequest

    # Оценка Q по населению (норма 200 л/чел·сут × коэф_часовой)
    q_avg_m3day = inputs.population * 0.25
    q_max_m3h = q_avg_m3day / 24 * 2.5  # K_час_max ≈ 2.5

    try:
        request = SelectionRequest(L0=L0Input(
            Q_m3h=max(q_max_m3h, 1.0),
            dH_m=5,
            L_m=50,
            wastewater_type="domestic",
        ))
        result = run_selection(request)
        return SubsystemResult(
            name="КНС хозбытовая",
            status="ok",
            summary=f"Q={q_max_m3h:.1f} м³/ч, подобрано {len(result.results)} вариантов",
            data={"Q_m3h": q_max_m3h, "selection": result.model_dump()},
            references=[
                {"regulation_code": "СП 32.13330.2018", "section": "§6", "purpose": "Канализация наружная"},
            ],
        )
    except Exception as e:
        return SubsystemResult(
            name="КНС хозбытовая",
            status="error",
            summary=f"Ошибка расчёта: {e}",
            data={},
        )


def _calc_water_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема ВНС хозпитьевая (Phase 23)."""
    from pump_calculator.water_supply import (
        WaterScenarioInput,
        calc_water_demand,
        sizing_water_station,
    )
    try:
        # Маппинг preset → building_type
        bt_map = {
            "ihs": "residential_with_baths",
            "apartment_complex": "residential_with_baths",
            "hotel": "hotel_standard",
            "trc": "trc",
            "school": "school",
            "hospital": "hospital",
            "industrial": "industrial_generic",
        }
        bt = bt_map.get(inputs.preset, "residential_with_baths")
        water_input = WaterScenarioInput(
            building_type=bt,
            population=max(inputs.population, 1),
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


def _calc_los_subsystem(inputs: ProjectInput) -> SubsystemResult:
    """Подсистема ЛОС (Phase 27)."""
    from pump_calculator.los import LOSScenarioInput, select_los_block

    try:
        flow_m3day = inputs.population * 0.20    # хозбытовая норма
        los_input = LOSScenarioInput(
            source_type="domestic",
            flow_m3_per_day=max(flow_m3day, 1.0),
            discharge_category="irrigation",
            population_equivalent=inputs.population,
        )
        result = select_los_block(los_input)
        block = result.selected_block
        if block:
            summary = f"{block.manufacturer} {block.model}, {block.capacity_m3_per_day} м³/сут"
        else:
            summary = f"Q={flow_m3day:.1f} м³/сут — индивидуальный проект"
        return SubsystemResult(
            name="ЛОС биологическая",
            status="ok" if block else "warning",
            summary=summary,
            data=result.model_dump(),
            references=result.references,
            warnings=result.warnings,
        )
    except Exception as e:
        return SubsystemResult(
            name="ЛОС биологическая",
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
    if inputs.subsystems.los:
        result.los = _calc_los_subsystem(inputs)
    if inputs.subsystems.climate:
        result.climate = _calc_climate_subsystem(inputs)
    if inputs.subsystems.structural:
        result.structural = _calc_structural_subsystem(inputs)
    # storm — пока пропускаем (требует много полей по поверхностям)

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
