"""Подбор ЛОС-блока по производительности и требуемой степени очистки.

Каталог производителей в РФ (на основе Agent K research + reference из памяти):
- PEGAS Engineering (Краснодар) — главный конкурент Серво-Юг, 67-1875 тыс ₽
- ТОПАС, Юбас, БиоДека — массовые бытовые
- БиоПроект, КИТ, ГЕОН, ГИС-ЭКОВЭЛЛ, АЛИВА — магистральные
"""
from __future__ import annotations

from .models import (
    DischargeCategory,
    LOSBlock,
    LOSResult,
    LOSScenarioInput,
    LOSTreatmentLevel,
    PollutantConcentration,
)

# Каталог ЛОС-блоков (упрощённый, на базе исследования Agent K и reference)
LOS_CATALOG: list[LOSBlock] = [
    # PEGAS Engineering (Краснодар)
    LOSBlock(
        manufacturer="PEGAS",
        model="ПЕГАС-Б 5",
        capacity_m3_per_day=1.0,
        capacity_population_equivalent=5,
        technology="biological",
        estimated_price_rub_2026=(67_000, 95_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 96, "nh4_n": 80},
        notes=["Бытовая малая, 5 чел", "Аэротенк + вторичный отстойник"],
    ),
    LOSBlock(
        manufacturer="PEGAS",
        model="ПЕГАС-Б 10",
        capacity_m3_per_day=2.0,
        capacity_population_equivalent=10,
        technology="biological",
        estimated_price_rub_2026=(110_000, 145_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 96, "nh4_n": 80},
        notes=["Бытовая семейная, 10 чел"],
    ),
    LOSBlock(
        manufacturer="PEGAS",
        model="ПЕГАС-Б 50",
        capacity_m3_per_day=10.0,
        capacity_population_equivalent=50,
        technology="biological",
        estimated_price_rub_2026=(450_000, 620_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 96, "nh4_n": 85},
        notes=["Коттеджный посёлок 50 чел"],
    ),
    LOSBlock(
        manufacturer="PEGAS",
        model="ПЕГАС-Б 200",
        capacity_m3_per_day=40.0,
        capacity_population_equivalent=200,
        technology="biological",
        estimated_price_rub_2026=(1_400_000, 1_875_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 96, "nh4_n": 85},
        notes=["Магистральная для гостиницы/малого посёлка"],
    ),
    # ТОПАС / БиоДека (массовые)
    LOSBlock(
        manufacturer="ТОПАС",
        model="Топас 5",
        capacity_m3_per_day=1.0,
        capacity_population_equivalent=5,
        technology="biological",
        estimated_price_rub_2026=(95_000, 130_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 95, "nh4_n": 80},
        notes=["Самый популярный для ИЖС, SBR-технология"],
    ),
    LOSBlock(
        manufacturer="БиоДека",
        model="БиоДека-10",
        capacity_m3_per_day=2.0,
        capacity_population_equivalent=10,
        technology="biological",
        estimated_price_rub_2026=(120_000, 160_000),
        typical_purification_pct={"bod5": 96, "suspended_solids": 96, "nh4_n": 82},
        notes=["Альтернатива Топас, схожая технология"],
    ),
    # Магистральные
    LOSBlock(
        manufacturer="БиоПроект",
        model="БиоПроект-200",
        capacity_m3_per_day=200.0,
        capacity_population_equivalent=1000,
        technology="biological",
        estimated_price_rub_2026=(8_500_000, 12_000_000),
        typical_purification_pct={"bod5": 96, "suspended_solids": 97, "nh4_n": 90},
        notes=["Магистральная блочно-модульная"],
    ),
    LOSBlock(
        manufacturer="КИТ",
        model="КИТ ОС-100",
        capacity_m3_per_day=100.0,
        capacity_population_equivalent=500,
        technology="biological",
        estimated_price_rub_2026=(4_500_000, 6_500_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 95, "nh4_n": 85},
        notes=["Универсальная средняя"],
    ),
    LOSBlock(
        manufacturer="ГЕОН",
        model="ГЕОН ЛОС-50",
        capacity_m3_per_day=50.0,
        capacity_population_equivalent=250,
        technology="biological",
        estimated_price_rub_2026=(2_300_000, 3_200_000),
        typical_purification_pct={"bod5": 95, "suspended_solids": 95, "nh4_n": 80},
        notes=["Стеклопластиковый корпус"],
    ),
    # Доочистка для рыбохоз. сброса
    LOSBlock(
        manufacturer="БиоПроект",
        model="БиоПроект-200 + УФ + нано",
        capacity_m3_per_day=200.0,
        capacity_population_equivalent=1000,
        technology="deep_treatment",
        estimated_price_rub_2026=(13_000_000, 18_000_000),
        typical_purification_pct={"bod5": 99, "suspended_solids": 99, "nh4_n": 96, "po4_p": 90},
        notes=["Для рыбохозяйственного сброса (Приказ МСХ-552)"],
    ),
    # Спецтехнологии для leachate
    LOSBlock(
        manufacturer="custom",
        model="Фильтрат ТКО (коагуляция + 2-ст. био + RO)",
        capacity_m3_per_day=100.0,
        capacity_population_equivalent=0,
        technology="advanced",
        estimated_price_rub_2026=(35_000_000, 75_000_000),
        typical_purification_pct={"bod5": 99.5, "cod": 98, "nh4_n": 99, "suspended_solids": 99},
        notes=[
            "Только для фильтрата свалок ТКО",
            "Предобработка коагуляцией FeCl3 → анаэробный реактор UASB",
            "→ аэротенк с нитри/денитрификацией → ультрафильтр → RO",
            "Стоимость на порядки выше типовой ЛОС",
        ],
    ),
]


def _required_treatment_level(discharge: DischargeCategory, source: str) -> LOSTreatmentLevel:
    """Минимально необходимый уровень очистки по точке сброса."""
    if source == "leachate_landfill":
        return "advanced"
    if discharge in ("fishery_water", "drinking_source"):
        return "deep_treatment"
    if discharge == "central_sewerage":
        return "mechanical"  # обычно достаточно ЖГ-уловителя для бытовых
    return "biological"


def select_los_block(
    inputs: LOSScenarioInput,
) -> LOSResult:
    """Подбирает ЛОС-блок по входу и сбросу."""
    from .composition import calc_purification_efficiency, typical_influent_for_object

    influent = inputs.custom_influent or typical_influent_for_object(inputs.source_type)
    notes: list[str] = []
    warnings: list[str] = []

    # 1. Требуемая степень очистки
    purification_required = calc_purification_efficiency(influent, inputs.discharge_category)
    notes.append(f"Тип стоков: {inputs.source_type}, расход {inputs.flow_m3_per_day} м³/сут")
    notes.append(
        f"Сброс в: {inputs.discharge_category} → требуемая очистка по БПК "
        f"{purification_required.get('bod5', 0):.0f}%"
    )

    # 2. Минимальный уровень технологии
    treatment_level = _required_treatment_level(inputs.discharge_category, inputs.source_type)
    notes.append(f"Минимальный уровень технологии: {treatment_level}")

    # 3. Целевой эффлюент (по самой строгой норме)
    from .composition import POLLUTANT_LIMITS_BY_DISCHARGE
    limits = POLLUTANT_LIMITS_BY_DISCHARGE[inputs.discharge_category]
    effluent_target = PollutantConcentration(
        bod5=limits.get("bod5", 0),
        cod=limits.get("cod", 0),
        suspended_solids=limits.get("suspended_solids", 0),
        nh4_n=limits.get("nh4_n", 0),
        po4_p=limits.get("po4_p", 0),
        oil_products=limits.get("oil_products", 0),
        surfactants=limits.get("surfactants", 0),
    )

    # 4. Поиск кандидатов в каталоге
    candidates: list[LOSBlock] = []
    for block in LOS_CATALOG:
        # Производительность подходит (с запасом 20%)
        if block.capacity_m3_per_day < inputs.flow_m3_per_day * 0.8:
            continue
        if block.capacity_m3_per_day > inputs.flow_m3_per_day * 5:
            continue   # сильно избыточный

        # Уровень технологии достаточен
        levels_order = ["mechanical", "biological", "deep_treatment", "advanced"]
        if levels_order.index(block.technology) < levels_order.index(treatment_level):
            continue

        # Степень очистки по БПК достаточна
        if "bod5" in purification_required and purification_required["bod5"] > 0:
            block_eta = block.typical_purification_pct.get("bod5", 0)
            if block_eta < purification_required["bod5"]:
                continue

        candidates.append(block)

    # 5. Сортировка по цене (лучший = с минимальной нижней границей цены, но с покрытием)
    candidates.sort(key=lambda b: b.estimated_price_rub_2026[0])
    selected = candidates[0] if candidates else None

    if selected:
        notes.append(
            f"Выбран: {selected.manufacturer} {selected.model} "
            f"({selected.capacity_m3_per_day} м³/сут, "
            f"{selected.estimated_price_rub_2026[0]/1000:.0f}-{selected.estimated_price_rub_2026[1]/1000:.0f} тыс ₽)"
        )
    else:
        warnings.append(
            f"Не найдено ЛОС в каталоге для Q={inputs.flow_m3_per_day} м³/сут, "
            f"технология {treatment_level}. Возможно нужен индивидуальный проект."
        )

    references = [
        {
            "regulation_code": "СП 32.13330.2018",
            "section": "§7",
            "purpose": "Очистные сооружения канализации",
            "url": "https://docs.cntd.ru/document/554820821",
        },
        {
            "regulation_code": "ПП РФ № 728",
            "section": "прил. 5",
            "purpose": "ПДК для сброса в централизованную канализацию",
            "url": "https://docs.cntd.ru/document/499038947",
        },
        {
            "regulation_code": "Приказ МСХ-552",
            "section": "табл. 1",
            "purpose": "ПДК для рыбохозяйственных водоёмов",
            "url": "https://docs.cntd.ru/document/420389120",
        },
    ]

    return LOSResult(
        influent=influent,
        effluent_target=effluent_target,
        purification_required_pct=purification_required,
        treatment_level=treatment_level,
        selected_block=selected,
        candidate_blocks=candidates[:5],
        notes=notes,
        warnings=warnings,
        references=references,
    )
