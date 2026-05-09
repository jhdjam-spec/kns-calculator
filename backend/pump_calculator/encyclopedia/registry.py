"""Реестр энциклопедических тем + загрузка markdown-файлов.

Связывает топики с файлами и описывает интерактивные примеры
из эталонных проектов.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _resolve_encyclopedia_dir() -> Path:
    """Найти каталог md-файлов энциклопедии.

    Структура отличается локально (`backend/pump_calculator/...`) и в YC
    Function deploy package (`pump_calculator/...` без `backend/`). Ищем
    `02_dataset/_analysis/encyclopedia` в нескольких кандидатах.
    """
    # 1) env override (deploy задаёт KNS_DATASET_ROOT=./02_dataset)
    env_root = os.environ.get("KNS_DATASET_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        target = candidate / "_analysis" / "encyclopedia"
        if target.is_dir():
            return target
    # 2) walk up from this file looking for 02_dataset
    here = Path(__file__).resolve()
    for parent in here.parents:
        target = parent / "02_dataset" / "_analysis" / "encyclopedia"
        if target.is_dir():
            return target
    # 3) cwd fallback (last resort)
    return Path.cwd() / "02_dataset" / "_analysis" / "encyclopedia"


ENCYCLOPEDIA_DIR = _resolve_encyclopedia_dir()
PROJECT_ROOT = ENCYCLOPEDIA_DIR.parent.parent.parent  # backwards-compat для других модулей


@dataclass(frozen=True)
class RegulationFull:
    """Полное название норматива для отображения в UI энциклопедии."""

    code: str    # "СП 8.13130.2020"
    name: str    # "Источники наружного противопожарного водоснабжения"


@dataclass(frozen=True)
class EncyclopediaTopic:
    """Описание одной темы энциклопедии."""

    key: str                # "fire" | "water" | "electrical" | ...
    title: str              # "Пожарное водоснабжение"
    short_description: str  # Для карточки в /teach
    file: str               # Имя markdown-файла
    api_module: str         # Связанный backend-модуль (для кросс-ссылок)
    sections_count: int     # Сколько разделов внутри (для UI)
    regulations_full: tuple[RegulationFull, ...] = ()  # Полные названия норм


ENCYCLOPEDIA_TOPICS: dict[str, EncyclopediaTopic] = {
    "fire": EncyclopediaTopic(
        key="fire",
        title="Пожарное водоснабжение",
        short_description=(
            "Расчёт расхода и резервуаров пожаротушения. "
            "Категории зданий, степени огнестойкости, насосные станции."
        ),
        file="fire_water_encyclopedia.md",
        api_module="fire_water",
        sections_count=14,
        regulations_full=(
            RegulationFull("СП 8.13130.2020",
                "Системы противопожарной защиты. Источники наружного противопожарного водоснабжения"),
            RegulationFull("СП 10.13130.2020",
                "Системы противопожарной защиты. Внутренний противопожарный водопровод"),
            RegulationFull("СП 485.1311500.2020",
                "Установки пожаротушения автоматические. Нормы и правила проектирования"),
            RegulationFull("123-ФЗ от 22.07.2008",
                "Технический регламент о требованиях пожарной безопасности"),
        ),
    ),
    "water": EncyclopediaTopic(
        key="water",
        title="Хозяйственно-питьевое водоснабжение",
        short_description=(
            "Нормы потребления, расчёт ВНС, скважинных водозаборов, "
            "горячей воды, повысительных станций. 21 тип объекта."
        ),
        file="water_supply_encyclopedia.md",
        api_module="water_supply",
        sections_count=15,
        regulations_full=(
            RegulationFull("СП 30.13330.2020", "Внутренний водопровод и канализация зданий"),
            RegulationFull("СП 31.13330.2021", "Водоснабжение. Наружные сети и сооружения"),
            RegulationFull("СП 399.1325800.2018",
                "Здания и сооружения. Правила проектирования сетей водоснабжения и водоотведения"),
            RegulationFull("СанПиН 2.1.3684-21",
                "Санитарно-эпидемиологические требования к содержанию территорий, водоснабжению"),
        ),
    ),
    "electrical": EncyclopediaTopic(
        key="electrical",
        title="Электрика и автоматика",
        short_description=(
            "Подбор двигателя, кабеля, автомата, шкафов МИНИ/ОПТИ/МАКС/ATEX. "
            "Категории надёжности I/II/III."
        ),
        file="electrical_automation_encyclopedia.md",
        api_module="electrical",
        sections_count=16,
        regulations_full=(
            RegulationFull("ПУЭ 7-е изд.", "Правила устройства электроустановок"),
            RegulationFull("ТР ТС 004/2011", "О безопасности низковольтного оборудования"),
            RegulationFull("ТР ТС 020/2011", "Электромагнитная совместимость технических средств"),
            RegulationFull("ТР ТС 012/2011",
                "О безопасности оборудования для работы во взрывоопасных средах (ATEX)"),
            RegulationFull("ГОСТ Р 50571 (серия)", "Электроустановки низковольтные"),
            RegulationFull("ГОСТ IEC 60034-1-2014",
                "Машины электрические вращающиеся. Номинальные данные и характеристики"),
            RegulationFull("СП 6.13130.2020",
                "Системы противопожарной защиты. Электрооборудование"),
        ),
    ),
    "hydraulics": EncyclopediaTopic(
        key="hydraulics",
        title="Гидравлика и физика",
        short_description=(
            "Бернулли, Идельчик, Дарси-Вейсбах, NPSH, гидроудар Жуковского, "
            "параллельная работа насосов. Полная теория с выводами."
        ),
        file="hydraulics_physics_encyclopedia.md",
        api_module="physics_advanced",
        sections_count=17,
        regulations_full=(
            RegulationFull("СП 32.13330.2018", "Канализация. Наружные сети и сооружения"),
            RegulationFull("СП 31.13330.2021",
                "Водоснабжение. Наружные сети (§11 — гидравлический расчёт)"),
            RegulationFull("ГОСТ 6134-2007 (ISO 9906:2012 IDT)",
                "Насосы динамические. Методы испытаний"),
            RegulationFull("ISO 9906:2012",
                "Rotodynamic pumps — Hydraulic performance acceptance tests"),
            RegulationFull("ГОСТ Р 56541-2015",
                "Гидравлические расчёты систем водоснабжения и водоотведения"),
        ),
    ),
    "structural": EncyclopediaTopic(
        key="structural",
        title="Корпус, прочность, климат",
        short_description=(
            "Материалы корпусов, нагрузки, сейсмика, мерзлота, "
            "пригруз бетоном при УГВ. 11 производителей корпусов."
        ),
        file="corpus_structural_climate_encyclopedia.md",
        api_module="structural",
        sections_count=18,
        regulations_full=(
            RegulationFull("СП 20.13330.2016", "Нагрузки и воздействия (снег, ветер, грунт)"),
            RegulationFull("СП 14.13330.2018",
                "Строительство в сейсмических районах + ОСР-2015 (карты сейсморайонирования)"),
            RegulationFull("СП 25.13330.2020",
                "Основания и фундаменты на вечномёрзлых грунтах"),
            RegulationFull("СП 131.13330.2020", "Строительная климатология"),
            RegulationFull("СП 12-104-2002",
                "Безопасность труда в строительстве. Лестницы, площадки"),
            RegulationFull("СП 22.13330.2016", "Основания зданий и сооружений"),
            RegulationFull("ISO 9969", "Классификация полимерных труб по жёсткости (SN)"),
        ),
    ),
    "los": EncyclopediaTopic(
        key="los",
        title="ЛОС, биология, экология",
        short_description=(
            "Состав стоков, ПДК для 6 категорий сброса, биологическая очистка, "
            "выбор ЛОС-блока (PEGAS, ТОПАС, БиоПроект). Штрафы за превышение."
        ),
        file="los_biology_ecology_encyclopedia.md",
        api_module="los",
        sections_count=21,
        regulations_full=(
            RegulationFull("СП 32.13330.2018 §7",
                "Канализация. Очистные сооружения"),
            RegulationFull("ПП РФ № 728 от 13.07.2013",
                "Об утверждении Правил холодного водоснабжения и водоотведения"),
            RegulationFull("ПП РФ № 644 от 29.07.2013",
                "Правила холодного водоснабжения и водоотведения"),
            RegulationFull("Приказ Минсельхоза РФ № 552 от 13.12.2016",
                "Нормативы качества воды водных объектов рыбохозяйственного значения"),
            RegulationFull("СанПиН 2.1.5.980-00",
                "Гигиенические требования к охране поверхностных вод"),
            RegulationFull("ИТС 10-2015",
                "Очистка сточных вод с использованием централизованных систем (НДТ)"),
        ),
    ),
    "documentation": EncyclopediaTopic(
        key="documentation",
        title="Рабочая документация и сметы",
        short_description=(
            "Состав ПД и РД, разделы ИОС, расчётно-пояснительная записка (РПЗ), "
            "сметы (ССР/ОС/ЛСР), согласования и экспертиза. "
            "Глоссарий 150 терминов проектировщика и сметчика."
        ),
        file="project_documentation_encyclopedia.md",
        api_module="reports",
        sections_count=14,
        regulations_full=(
            RegulationFull("ПП РФ № 87 от 16.02.2008",
                "Состав разделов проектной документации (12 разделов + ИОС1-7)"),
            RegulationFull("ГОСТ Р 21.101-2020",
                "Система проектной документации для строительства (СПДС). Основные требования к рабочей документации"),
            RegulationFull("ГОСТ 21.110-2013",
                "СПДС. Спецификация оборудования, изделий и материалов (форма 7)"),
            RegulationFull("ГОСТ 21.601-2011",
                "СПДС. Внутренние системы водопровода и канализации"),
            RegulationFull("ГОСТ 21.704-2011",
                "СПДС. Наружные сети водопровода и канализации"),
            RegulationFull("ГОСТ 21.205-2016",
                "СПДС. Условные графические обозначения санитарно-технических систем"),
            RegulationFull("МДС 81-35.2004",
                "Методика определения стоимости строительной продукции (расчёт смет, ЛСР)"),
            RegulationFull("ст. 49 ГрК РФ",
                "Государственная и негосударственная экспертиза проектной документации"),
        ),
    ),
}


# Интерактивные примеры из эталонных проектов.
# Каждый пример — pre-filled запрос на одно из API.
# Используется в /teach: переход на калькулятор с заполненными полями.
@dataclass(frozen=True)
class EncyclopediaExample:
    """Эталонный пример для запуска из энциклопедии."""

    id: str
    title: str
    topic: str          # Связанная тема
    description: str    # Что показывает
    api_endpoint: str   # На какое API отправлять
    payload: dict       # Pre-filled данные
    expected_outcome: str  # Что должен увидеть пользователь


EXAMPLES_REGISTRY: list[EncyclopediaExample] = [
    EncyclopediaExample(
        id="vbd_ekb_storm",
        title="Ливневая КНС — F=7.7 га, северный регион",
        topic="hydraulics",
        description="Расчёт пикового расхода ливневых стоков по СП 32 для F=7.7 га, северный регион",
        api_endpoint="/storm/calc",
        payload={
            "sp_revision": "SP_32_2018",
            "region_city": "Екатеринбург",
            "surfaces": {"asphalt_ha": 6.5, "lawn_ha": 1.2},
            "period_P_year": 1,
        },
        expected_outcome="Q_r ≈ 540 л/с",
    ),
    EncyclopediaExample(
        id="ppd_omon_fire",
        title="Пожарное водоснабжение — общественное здание 202 чел",
        topic="fire",
        description="ВНС-2 пожарная для общественного здания на 202 чел + спорткомплекс",
        api_endpoint="/fire-water/calc",
        payload={
            "occupancy": "public",
            "building_class": "I",
            "volume_m3": 30000,
            "floors": 3,
            "population": 202,
            "water_source": "reservoir",
            "fire_duration_h": 3.0,
        },
        expected_outcome="Q_наруж=15-20 л/с, V_резервуара ≈ 200 м³ (4×50 м³)",
    ),
    EncyclopediaExample(
        id="rvb_kuban_kns9",
        title="Хозбытовая КНС — подбор электрики, Q=86 м³/ч",
        topic="electrical",
        description="Хозбытовая КНС Q=86 м³/ч H=7 м, 2 рабочих + 1 резерв",
        api_endpoint="/select",
        payload={
            "L0": {"Q_m3h": 86.22, "dH_m": 7, "L_m": 50, "wastewater_type": "domestic"},
        },
        expected_outcome="2 насоса по 43 м³/ч, P≈2.2 кВт каждый, ШУ с АВР (категория I)",
    ),
    EncyclopediaExample(
        id="promlivnevka_atex",
        title="Промливневая КНС Q=132 — взрывозащищённое исполнение",
        topic="electrical",
        description="ATEX зона B-1а / IIB-T3, 2×Q_66 параллельно × H=35",
        api_endpoint="/select",
        payload={
            "L0": {"Q_m3h": 132, "dH_m": 35, "L_m": 100, "wastewater_type": "industrial"},
        },
        expected_outcome="Шкаф ATEX, IP66, газоанализатор, цена 500тыс-2.5млн ₽",
    ),
    EncyclopediaExample(
        id="pedrollo_household",
        title="Бытовая КНС в сборе — частный дом 4-5 чел",
        topic="hydraulics",
        description="Готовая КНС в сборе SAR550 + VXm 15/50, типовое решение для 4-5 чел",
        api_endpoint="/select",
        payload={
            "L0": {"Q_m3h": 15, "dH_m": 10, "L_m": 30, "wastewater_type": "domestic"},
        },
        expected_outcome="Pedrollo VXm 15/50-N, P=1.1 кВт, шкаф МИНИ, 70-110 тыс ₽",
    ),
    EncyclopediaExample(
        id="jk_50_apartments",
        title="МКД 12 этажей, 150 жителей — пожарка + хозпит.",
        topic="fire",
        description="Жилой 12 этажей, V=15000 м³, 150 жителей",
        api_endpoint="/fire-water/calc",
        payload={
            "occupancy": "residential",
            "floors": 12,
            "volume_m3": 15000,
            "population": 150,
            "water_source": "reservoir",
        },
        expected_outcome="Q_наруж=15 л/с, Q_внутр=2.6 л/с (1 струя), V_рез ≈200 м³",
    ),
    EncyclopediaExample(
        id="kotedge_los_5_persons",
        title="Частный дом 5 чел — ЛОС бытовая",
        topic="los",
        description="ИЖС-семья, сброс на полив, типовое решение",
        api_endpoint="/los/select",
        payload={
            "source_type": "domestic",
            "flow_m3_per_day": 1.0,
            "discharge_category": "irrigation",
            "population_equivalent": 5,
        },
        expected_outcome="Бюджетный класс 67-95 тыс ₽ или премиум 95-130 тыс ₽",
    ),
    EncyclopediaExample(
        id="krasnodar_burial",
        title="Глубина заложения трубы — южный регион",
        topic="structural",
        description="Хозбытовая канализация DN200, суглинок, без УГВ",
        api_endpoint="/climate/burial-depth",
        payload={
            "region_city": "Краснодар",
            "soil_type": "clay_loam",
            "pipe_dn_mm": 200,
            "has_groundwater": False,
        },
        expected_outcome="d_заложения ≈ 1.1 м (d_fn=0.8 + 0.3 запас по СП 32 §6.5)",
    ),
]


def list_topics() -> list[dict]:
    """Список всех тем для главной /teach страницы."""
    return [
        {
            "key": t.key,
            "title": t.title,
            "short_description": t.short_description,
            "api_module": t.api_module,
            "sections_count": t.sections_count,
            "regulations_full": [
                {"code": r.code, "name": r.name} for r in t.regulations_full
            ],
        }
        for t in ENCYCLOPEDIA_TOPICS.values()
    ]


def get_topic_full(topic_key: str) -> dict | None:
    """Полное содержимое статьи по топику.

    Returns:
        {key, title, content_markdown, examples} либо None.
    """
    if topic_key not in ENCYCLOPEDIA_TOPICS:
        return None
    topic = ENCYCLOPEDIA_TOPICS[topic_key]
    file_path = ENCYCLOPEDIA_DIR / topic.file
    if not file_path.exists():
        return {
            "key": topic.key,
            "title": topic.title,
            "content_markdown": f"# {topic.title}\n\n*Файл {topic.file} не найден.*",
            "examples": [],
        }

    content = file_path.read_text(encoding="utf-8")
    examples = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "api_endpoint": e.api_endpoint,
            "payload": e.payload,
            "expected_outcome": e.expected_outcome,
        }
        for e in EXAMPLES_REGISTRY
        if e.topic == topic_key
    ]
    return {
        "key": topic.key,
        "title": topic.title,
        "short_description": topic.short_description,
        "api_module": topic.api_module,
        "content_markdown": content,
        "examples": examples,
        "regulations_full": [
            {"code": r.code, "name": r.name} for r in topic.regulations_full
        ],
    }


def get_topic_section(topic_key: str, section_anchor: str) -> dict | None:
    """Фрагмент статьи по якорю заголовка.

    Используется для drawer drill-down: при клике на «Q_r формула 8 СП 32 §6.2.4»
    → возвращаем секцию из hydraulics-encyclopedia с этим заголовком.

    Args:
        topic_key: топик ("hydraulics", "fire" и т.д.)
        section_anchor: строка для поиска в заголовке (case-insensitive)
    """
    full = get_topic_full(topic_key)
    if full is None:
        return None

    content = full["content_markdown"]
    lines = content.split("\n")

    # Поиск раздела по подстроке в заголовке (## или ###)
    found_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("##") and section_anchor.lower() in line.lower():
            found_idx = i
            break

    if found_idx < 0:
        return None

    # Извлекаем секцию до следующего того же или большего уровня заголовка
    section_lines = [lines[found_idx]]
    header_level = lines[found_idx].count("#", 0, 6)

    for line in lines[found_idx + 1 :]:
        if line.startswith("#"):
            this_level = line.count("#", 0, 6)
            if this_level <= header_level:
                break
        section_lines.append(line)
        # Ограничение — не более 200 строк
        if len(section_lines) >= 200:
            break

    return {
        "topic": topic_key,
        "section_anchor": section_anchor,
        "section_title": lines[found_idx].lstrip("#").strip(),
        "content_markdown": "\n".join(section_lines),
    }
