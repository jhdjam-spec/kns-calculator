"""Расчёт лестницы и площадок внутри корпуса по СП 12-104-2002.

Главные требования:
- Угол наклона ≤ 60° (стационарная)
- Высота между площадками ≤ 3.0 м (после 6 м обязательна площадка)
- Ширина ступени ≥ 0.6 м
- Высота поручня ≥ 1.1 м
- Материал для канализации: AISI 304 или горячецинк сталь
"""
from __future__ import annotations

from .models import LadderResult


def calc_ladder_geometry(
    height_m: float,
    pit_diameter_m: float,
    is_corrosive_environment: bool = True,
) -> LadderResult:
    """Расчёт геометрии лестницы для КНС/НС/ЛОС.

    Args:
        height_m: глубина приямка (от верха до дна), м
        pit_diameter_m: диаметр приямка, м
        is_corrosive_environment: канализация/химия → AISI 304/316
    """
    notes = []

    # Промежуточные площадки каждые 3.0 м (СП 12-104 §3.6)
    if height_m <= 3.0:
        n_landings = 0
        landing_heights = []
        notes.append("H≤3 м → площадки не требуются")
    elif height_m <= 6.0:
        n_landings = 1
        landing_heights = [height_m / 2]
        notes.append(f"H={height_m} м → 1 промежуточная площадка на {height_m/2:.1f} м")
    else:
        # На каждые 3 м — площадка
        n_landings = int((height_m - 0.001) / 3.0)
        landing_heights = [3.0 * (i + 1) for i in range(n_landings)]
        notes.append(f"H={height_m} м → {n_landings} площадок (через 3 м)")

    # Угол лестницы (стандарт 60° для стационарной)
    ladder_angle = 60.0
    # Длина одной маршевой части
    march_length = height_m / 0.866  # cos(30°) = 0.866 для угла 60° от вертикали

    # Поручень (СП 12-104 §3.5)
    handrail_h = 1.1
    notes.append(f"Поручень высотой {handrail_h} м (СП 12-104 §3.5)")

    # Материал
    if is_corrosive_environment:
        material = "AISI 304 (или AISI 316 для агрессивных стоков)"
        notes.append("Канализация → AISI 304/316 (СП 28.13330)")
    else:
        material = "Сталь Ст3 + горячее цинкование 80 мкм"
        notes.append("Чистые среды → горячецинк сталь")

    # Если приямок узкий (D < 1.5 м) — стационарная маршевая может не вписаться
    if pit_diameter_m < 1.5 and height_m > 3:
        notes.append(
            f"⚠ Узкий приямок D={pit_diameter_m} м: "
            "стандартная маршевая лестница не вписывается, "
            "рекомендуется вертикальная стремянка с площадками + страховочная система"
        )

    references = [
        {
            "regulation_code": "СП 12-104-2002",
            "section": "§3",
            "purpose": "Требования к стационарным лестницам и площадкам",
            "url": "https://docs.cntd.ru/document/901833065",
        },
        {
            "regulation_code": "СП 28.13330.2017",
            "section": "табл. Х.5",
            "purpose": "Антикоррозионная защита нержавейки в канализационных средах",
            "url": "https://docs.cntd.ru/document/456083243",
        },
    ]

    return LadderResult(
        n_landings=n_landings,
        landing_heights_m=landing_heights,
        ladder_angle_deg=ladder_angle,
        ladder_total_length_m=round(march_length, 2),
        handrail_height_m=handrail_h,
        material=material,
        notes=notes,
        references=references,
    )
