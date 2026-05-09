"""Расчёт автоматических спринклерных установок по СП 485.1311500.2020.

СП 485 (заменил СП 5.13130.2009) делит помещения на 7 групп по пожарной нагрузке:

- Группа 1: помещения с мин. пожарной нагрузкой
  (детсады, школы, офисы, библиотеки, музеи)
- Группа 2: помещения средней пожарной нагрузки
  (жилые здания выше 30 м, магазины, гостиницы)
- Группа 3: помещения с повышенной нагрузкой
  (рестораны, аэропорты, ТРЦ открытой планировки)
- Группа 4.1, 4.2: производственные помещения категорий В1-В3
  с разными уровнями пожарной нагрузки
- Группа 5, 6, 7: склады с высотным хранением
  (5 — высота до 4 м, 6 — до 10 м, 7 — выше)

Параметры (табл. 5.1, 5.2, 6.3 СП 485):
- Удельный расход воды q_уд, л/с/м² (от 0.08 до 0.40)
- Расчётная площадь A_расч, м² (от 60 до 360 м² — площадь
  одновременного действия)
- Время работы установки T, мин (60 для большинства, 90 для складов)
- Минимальное число одновременно работающих оросителей
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Группы помещений по СП 485.1311500.2020
SprinklerGroup = Literal["1", "2", "3", "4.1", "4.2", "5", "6", "7"]


@dataclass(frozen=True)
class SprinklerGroupSpec:
    """Параметры спринклерной установки для группы помещений (СП 485 табл. 5.1)."""

    group: SprinklerGroup
    title: str
    examples: str                 # типичные помещения
    q_uds_lps_m2: float           # удельный расход, л/с·м²
    area_m2: float                # расчётная площадь, м²
    duration_min: int             # время работы, мин
    min_pressure_m: float         # минимальное давление у оросителя, м.вод.ст


# Сводка по группам — упрощённая (полная таблица в СП 485 §5).
SPRINKLER_GROUPS: dict[SprinklerGroup, SprinklerGroupSpec] = {
    "1": SprinklerGroupSpec(
        group="1",
        title="Минимальная пожарная нагрузка",
        examples="Детсады, школы, офисы, библиотеки, музеи, стадионы",
        q_uds_lps_m2=0.08,
        area_m2=60.0,
        duration_min=30,
        min_pressure_m=5.0,
    ),
    "2": SprinklerGroupSpec(
        group="2",
        title="Средняя пожарная нагрузка",
        examples="Жилые здания >30 м, магазины, гостиницы, ЛПУ, банки",
        q_uds_lps_m2=0.12,
        area_m2=120.0,
        duration_min=60,
        min_pressure_m=10.0,
    ),
    "3": SprinklerGroupSpec(
        group="3",
        title="Повышенная пожарная нагрузка",
        examples="Рестораны, кафе, аэропорты, ТРЦ открытой планировки",
        q_uds_lps_m2=0.24,
        area_m2=180.0,
        duration_min=60,
        min_pressure_m=10.0,
    ),
    "4.1": SprinklerGroupSpec(
        group="4.1",
        title="Производственные В1-В3 (умеренная нагрузка)",
        examples="Деревообработка, типографии, текстильные цеха",
        q_uds_lps_m2=0.30,
        area_m2=240.0,
        duration_min=60,
        min_pressure_m=15.0,
    ),
    "4.2": SprinklerGroupSpec(
        group="4.2",
        title="Производственные В1-В3 (высокая нагрузка)",
        examples="Резинотехнические, мебельные, бумажная промышленность",
        q_uds_lps_m2=0.40,
        area_m2=240.0,
        duration_min=90,
        min_pressure_m=15.0,
    ),
    "5": SprinklerGroupSpec(
        group="5",
        title="Склады, высота хранения до 4 м",
        examples="Универсальные склады, продуктовые, лёгкая промышленность",
        q_uds_lps_m2=0.20,
        area_m2=180.0,
        duration_min=60,
        min_pressure_m=15.0,
    ),
    "6": SprinklerGroupSpec(
        group="6",
        title="Склады, высота хранения 4-10 м",
        examples="Высотные склады с горючими товарами",
        q_uds_lps_m2=0.30,
        area_m2=240.0,
        duration_min=90,
        min_pressure_m=20.0,
    ),
    "7": SprinklerGroupSpec(
        group="7",
        title="Склады, высота хранения свыше 10 м",
        examples="Автоматизированные склады, паллетные стеллажи",
        q_uds_lps_m2=0.40,
        area_m2=360.0,
        duration_min=90,
        min_pressure_m=25.0,
    ),
}


@dataclass
class SprinklerCalcResult:
    """Результат расчёта спринклерной установки."""

    group: SprinklerGroup
    group_title: str
    q_total_lps: float          # суммарный расход, л/с
    q_total_m3h: float          # то же в м³/ч
    area_m2: float              # расчётная площадь
    duration_min: int           # время работы
    n_sprinklers_min: int       # минимальное число одновременно работающих
    min_pressure_m: float       # минимальное давление у самого удалённого
    water_volume_m3: float      # запас воды для установки
    notes: list[str]
    references: list[dict]


def calc_sprinkler_demand(
    group: SprinklerGroup,
    coverage_area_m2: float | None = None,
) -> SprinklerCalcResult:
    """Расчёт спринклерной установки по СП 485.1311500.2020.

    Args:
        group: группа помещений по табл. 5.1 СП 485
        coverage_area_m2: реальная площадь защищаемого помещения, м²
                          (если меньше расчётной — берём фактическую,
                           но не меньше 60 м² минимум)

    Returns:
        SprinklerCalcResult с полным расчётом расхода, давления, объёма воды.
    """
    if group not in SPRINKLER_GROUPS:
        raise ValueError(f"Unknown sprinkler group: {group}. Valid: {list(SPRINKLER_GROUPS)}")

    spec = SPRINKLER_GROUPS[group]
    notes: list[str] = []

    # Расчётная площадь — как правило берём из таблицы, но если реальная
    # меньше — используем её (не меньше 60 м² по СП 485 §5.7).
    if coverage_area_m2 is not None and coverage_area_m2 < spec.area_m2:
        area = max(coverage_area_m2, 60.0)
        notes.append(
            f"Реальная площадь {coverage_area_m2:.0f} м² меньше расчётной {spec.area_m2:.0f} м² "
            f"→ используется фактическая (мин. 60 м² по СП 485 §5.7)"
        )
    else:
        area = spec.area_m2
        notes.append(f"Расчётная площадь по табл. 5.1: {area:.0f} м²")

    # Расход = q_уд × A_расч
    q_total_lps = spec.q_uds_lps_m2 * area
    q_total_m3h = q_total_lps * 3.6
    notes.append(
        f"q_уд × A = {spec.q_uds_lps_m2} × {area:.0f} = {q_total_lps:.1f} л/с "
        f"({q_total_m3h:.1f} м³/ч)"
    )

    # Минимальное число оросителей: 1 ороситель на 9-12 м² типично
    # СП 485 §6.4: для гр. 1-2 интервал 4 м, для 3-4 — 3 м, для 5-7 — 3 м
    coverage_per_sprinkler = 12.0 if group in ("1", "2") else 9.0
    n_sprinklers_min = max(1, int(area / coverage_per_sprinkler) + 1)
    notes.append(
        f"Число одновременно работающих оросителей ≥ {n_sprinklers_min} "
        f"(шаг {coverage_per_sprinkler}=м²/ороситель)"
    )

    # Запас воды: V = Q × T × 60 / 1000 (л/с × мин × 60 с/мин / 1000 = м³)
    water_volume_m3 = q_total_lps * spec.duration_min * 60 / 1000
    notes.append(
        f"Запас воды: Q × T = {q_total_lps:.1f} × {spec.duration_min}/60·60 "
        f"= {water_volume_m3:.1f} м³"
    )

    references = [
        {
            "regulation_code": "СП 485.1311500.2020",
            "section": "§5 табл. 5.1, 5.2",
            "purpose": "Группы помещений и параметры спринклерных установок",
            "url": "https://docs.cntd.ru/document/566421869",
        },
        {
            "regulation_code": "СП 485.1311500.2020",
            "section": "§6.3-6.4",
            "purpose": "Расчётная площадь и интервал между оросителями",
            "url": "https://docs.cntd.ru/document/566421869",
        },
    ]

    return SprinklerCalcResult(
        group=group,
        group_title=spec.title,
        q_total_lps=round(q_total_lps, 2),
        q_total_m3h=round(q_total_m3h, 2),
        area_m2=area,
        duration_min=spec.duration_min,
        n_sprinklers_min=n_sprinklers_min,
        min_pressure_m=spec.min_pressure_m,
        water_volume_m3=round(water_volume_m3, 2),
        notes=notes,
        references=references,
    )


def list_sprinkler_groups() -> list[dict]:
    """Каталог 8 групп для UI выбора."""
    return [
        {
            "group": s.group,
            "title": s.title,
            "examples": s.examples,
            "q_uds_lps_m2": s.q_uds_lps_m2,
            "area_m2": s.area_m2,
            "duration_min": s.duration_min,
            "min_pressure_m": s.min_pressure_m,
        }
        for s in SPRINKLER_GROUPS.values()
    ]
