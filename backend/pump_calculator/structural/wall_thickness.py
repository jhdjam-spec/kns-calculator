"""Расчёт минимальной толщины стенки полимерного корпуса.

ISO 9969 — классификация по жёсткости SN:
- SN2:  ≥ 2 кН/м²    — лёгкие условия (мелкое заложение, песок)
- SN4:  ≥ 4 кН/м²    — стандартные ливнёвки
- SN8:  ≥ 8 кН/м²    — типовая канализация под дорогой
- SN16: ≥16 кН/м²    — глубокое заложение, тяжёлые условия
- SN32: ≥32 кН/м²    — экстремальные (промышленные глубокие котлованы)

Минимальная толщина для типовых диаметров (примерные значения для HDPE/FRP):
"""
from __future__ import annotations

from .models import StructuralScenarioInput, WallThicknessResult

# Минимальная толщина стенки HDPE/PE-100 в зависимости от диаметра и SN.
# Источник: ISO 9969 + ГОСТ 32415-2013 + каталоги BloPlast/Plastek/Rainpark.
# Ключ: (D_mm_max, SN_class) → толщина_min_mm
HDPE_MIN_THICKNESS_MM: dict[str, dict[int, float]] = {
    # SN8 — стандарт для канализации
    "SN4": {500: 6, 800: 8, 1200: 12, 1800: 18, 2500: 25, 3500: 35},
    "SN8": {500: 8, 800: 12, 1200: 18, 1800: 25, 2500: 35, 3500: 45},
    "SN16": {500: 12, 800: 18, 1200: 25, 1800: 35, 2500: 50, 3500: 65},
}


# Стеклопластик (FRP) — гораздо прочнее, толщина меньше
FIBERGLASS_MIN_THICKNESS_MM: dict[str, dict[int, float]] = {
    "SN4": {500: 4, 800: 5, 1200: 7, 1800: 10, 2500: 14, 3500: 20},
    "SN8": {500: 5, 800: 7, 1200: 10, 1800: 14, 2500: 20, 3500: 28},
    "SN16": {500: 7, 800: 10, 1200: 14, 1800: 20, 2500: 28, 3500: 40},
}


def _select_sn_class(burial_depth_m: float, has_groundwater: bool) -> str:
    """Выбор класса SN по глубине заложения."""
    if has_groundwater or burial_depth_m > 4:
        return "SN16"   # тяжёлые условия
    if burial_depth_m > 2:
        return "SN8"
    return "SN4"


def calc_polymer_wall_thickness(inputs: StructuralScenarioInput) -> WallThicknessResult:
    """Расчёт минимальной толщины стенки полимерного корпуса."""
    has_gw = inputs.groundwater_depth_m < inputs.burial_depth_m
    sn_class = _select_sn_class(inputs.burial_depth_m, has_gw)

    if inputs.material in ("fiberglass",):
        table = FIBERGLASS_MIN_THICKNESS_MM
    elif inputs.material in ("hdpe", "polypropylene"):
        table = HDPE_MIN_THICKNESS_MM
    else:
        # Бетон/сталь — отдельный расчёт по СП 14/СП 22, не через эту функцию
        return WallThicknessResult(
            required_thickness_mm=inputs.wall_thickness_mm,
            is_current_sufficient=True,
            sn_class="N/A",
            safety_margin_pct=0,
            notes=[
                f"Материал {inputs.material} — расчёт стенки не по полимерной методике",
                "Для бетона/стали — расчёт по СП 14.13330 / ГОСТ 25192-2012",
            ],
        )

    # Поиск ближайшего большего D_mm в таблице
    D_mm = inputs.diameter_m * 1000
    table_for_sn = table[sn_class]
    required_t = next(
        (t for d, t in sorted(table_for_sn.items()) if d >= D_mm),
        max(table_for_sn.values()),
    )

    is_sufficient = inputs.wall_thickness_mm >= required_t
    margin_pct = (inputs.wall_thickness_mm - required_t) / required_t * 100

    notes = [
        f"Класс SN: {sn_class} (глубина {inputs.burial_depth_m} м, УГВ {has_gw})",
        f"Материал: {inputs.material}",
        f"D = {inputs.diameter_m} м → требуемая толщина {required_t} мм",
        f"Текущая толщина {inputs.wall_thickness_mm} мм → "
        + ("ДОСТАТОЧНО" if is_sufficient else "НЕДОСТАТОЧНО"),
        f"Запас {margin_pct:.1f}%",
    ]

    return WallThicknessResult(
        required_thickness_mm=required_t,
        is_current_sufficient=is_sufficient,
        sn_class=sn_class,
        safety_margin_pct=round(margin_pct, 1),
        notes=notes,
    )
