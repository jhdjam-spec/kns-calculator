"""Проверка устойчивости откоса траншеи при откопе котлована для КНС.

По СП 45.13330.2017 «Земляные сооружения, основания и фундаменты»
§6.1 «Возведение земляных сооружений»:

  • Угол откоса m=h/l зависит от грунта и глубины (СП 45 табл. 6.1).
  • Для z ≤ 1.5 м: вертикальный откос допустим для большинства грунтов.
  • z > 1.5 м: требуется обоснование (шпунт или откос с m по таблице).
  • z > 5 м или УГВ выше дна / sand_water_saturated / peat / clay_soft —
    шпунтовое ограждение обязательно (СП 45 §6.1.3).

Если откос делается без шпунта — должна выполняться проверка пассивного
давления грунта K_p = tan²(45° + φ/2) (сопротивление выпору соседнего
массива при открытой траншее, СП 22.13330.2016 §5.6.2).

PhD-Mechanics backlog 2026-05-13: «K_p для траншеи (СП 45 §6.1)»
закрывается этим модулем.

Источники:
  • СП 45.13330.2017 §6.1 — cntd.ru/document/456066600
  • СП 22.13330.2016 §5.6.2 — cntd.ru/document/456054206
  • Цытович «Механика грунтов» (1983), §5.4 (K_p теория Кулона)
  • ISO 80000-3 — g = 9.80665 м/с²
"""
from __future__ import annotations

from dataclasses import dataclass

from .ground_context import GroundContext

# СП 45.13330.2017 табл. 6.1 — допустимый угол откоса (m = h_верт : 1 м гориз.)
# для разных грунтов и глубин траншеи. Значения консервативные —
# для проектных оценок до КНС. При z вне диапазона → линейная интерполяция;
# при z >= 5 м шпунт обязателен (§6.1.3).
#
# Формат: {soil_type: {depth_m: slope_ratio_m_per_h}},
# где slope_ratio = горизонтальная составляющая на 1 м вертикальной.
# Чем выше slope_ratio — тем более пологий откос требуется.
SAFE_SLOPE_BY_DEPTH: dict[str, dict[float, float]] = {
    "sand_dense":           {1.5: 0.67, 3.0: 1.00, 5.0: 1.25},  # ≈ 56°
    "sand_medium":          {1.5: 0.50, 3.0: 0.75, 5.0: 1.00},
    "sand_loose":           {1.5: 0.33, 3.0: 0.50, 5.0: 0.67},
    "loam":                 {1.5: 0.67, 3.0: 1.00, 5.0: 1.50},
    "clay_hard":            {1.5: 0.00, 3.0: 0.25, 5.0: 0.50},  # верт. до 1.5 м
    "clay_plastic":         {1.5: 0.25, 3.0: 0.67, 5.0: 1.00},
    "clay_soft":            {1.5: 0.50, 3.0: 0.75, 5.0: 1.25},
    "peat":                 {1.5: 1.00, 3.0: 1.50, 5.0: 2.00},
    "sand_water_saturated": {1.5: 1.00, 3.0: 1.50, 5.0: 2.00},  # шпунт обязат.
}

# Глубина, при которой шпунт обязателен независимо от грунта (СП 45 §6.1.3).
SHEET_PILE_MANDATORY_DEPTH_M: float = 5.0

# Глубина при которой шпунт настоятельно рекомендуется (мягкие грунты ≥3 м).
SHEET_PILE_RECOMMENDED_DEPTH_M: float = 3.0


@dataclass
class TrenchStability:
    """Результат проверки устойчивости откоса траншеи.

    Attributes:
      depth_m: Глубина траншеи от земли, м.
      safe_slope_ratio_m_per_h: Допустимый коэффициент откоса (горизонт.
        составляющая на 1 м вертикальной). 0 = вертикальный.
      horizontal_clearance_m: Минимальная горизонтальная отбивка от низа
        траншеи (для разработки) = depth × slope_ratio.
      sheet_pile_required: True если требуется шпунтовое ограждение.
      sheet_pile_reason: Человеко-читаемая причина (или None).
      passive_resistance_kPa: σ_p = γ·z·K_p, кПа — пассивное сопротивление
        грунта (запас прочности соседнего массива).
    """
    depth_m: float
    safe_slope_ratio_m_per_h: float
    horizontal_clearance_m: float
    sheet_pile_required: bool
    sheet_pile_reason: str | None = None
    passive_resistance_kPa: float = 0.0


def _interp_slope(soil: str, depth_m: float) -> float:
    """Линейная интерполяция допустимого slope по табл. СП 45 6.1."""
    table = SAFE_SLOPE_BY_DEPTH.get(soil, SAFE_SLOPE_BY_DEPTH["sand_medium"])
    depths = sorted(table.keys())
    if depth_m <= depths[0]:
        return table[depths[0]]
    if depth_m >= depths[-1]:
        return table[depths[-1]]
    z_low = max(d for d in depths if d <= depth_m)
    z_high = min(d for d in depths if d >= depth_m)
    slope_low = table[z_low]
    slope_high = table[z_high]
    if z_high == z_low:
        return slope_low
    return slope_low + (slope_high - slope_low) * (depth_m - z_low) / (z_high - z_low)


def check_trench_stability(
    ctx: GroundContext,
    depth_m: float,
    has_sheet_pile: bool = False,
) -> TrenchStability:
    """Проверка устойчивости открытой траншеи под корпус КНС.

    Args:
      ctx: GroundContext (тип грунта + УГВ + установочная глубина).
      depth_m: Глубина проверяемой траншеи от земли, м.
      has_sheet_pile: True если шпунт уже запроектирован. Если False —
        результат укажет, нужен ли он (sheet_pile_required).

    Returns:
      TrenchStability с допустимым углом откоса, σ_p и флагом шпунта.

    СП 45.13330.2017 §6.1.3: при z > 5 м шпунт обязателен независимо
    от грунта. При УГВ выше дна траншеи — шпунт обязателен (вода
    разжижает откос).
    """
    if depth_m < 0:
        depth_m = 0.0

    soil = ctx.soil_type

    # σ_p = γ·z·K_p — пассивное сопротивление грунта на глубине z
    passive_kPa = ctx.gamma_kN_m3 * depth_m * ctx.K_p

    # Случай 1: глубже 5 м — шпунт обязателен (СП 45 §6.1.3)
    if depth_m >= SHEET_PILE_MANDATORY_DEPTH_M:
        return TrenchStability(
            depth_m=depth_m,
            safe_slope_ratio_m_per_h=2.5,
            horizontal_clearance_m=depth_m * 2.5,
            sheet_pile_required=True,
            sheet_pile_reason=(
                f"z={depth_m:.1f} м >= {SHEET_PILE_MANDATORY_DEPTH_M} м — "
                f"шпунтовое ограждение обязательно по СП 45.13330.2017 §6.1.3."
            ),
            passive_resistance_kPa=passive_kPa,
        )

    # Случай 2: УГВ выше дна траншеи — шпунт обязателен
    # (вода + откос → разжижение/обрушение)
    if ctx.is_submerged:
        return TrenchStability(
            depth_m=depth_m,
            safe_slope_ratio_m_per_h=2.0,
            horizontal_clearance_m=depth_m * 2.0,
            sheet_pile_required=True,
            sheet_pile_reason=(
                f"Уровень грунтовых вод на {ctx.gwl_above_bottom_m:.1f} м "
                f"выше дна траншеи — шпунт обязателен (СП 45.13330.2017 "
                f"§6.1.4: разработка ниже УГВ только в шпунте)."
            ),
            passive_resistance_kPa=passive_kPa,
        )

    # Случай 3: слабые грунты — шпунт обязателен
    if soil in ("sand_water_saturated", "peat"):
        return TrenchStability(
            depth_m=depth_m,
            safe_slope_ratio_m_per_h=2.0,
            horizontal_clearance_m=depth_m * 2.0,
            sheet_pile_required=True,
            sheet_pile_reason=(
                f"Грунт «{ctx.label}» — водонасыщенный/слабый. "
                f"СП 45.13330.2017 §6.1.3: шпунт обязателен для таких "
                f"грунтов независимо от глубины."
            ),
            passive_resistance_kPa=passive_kPa,
        )

    # Случай 4: норма — определяем допустимый slope по СП 45 табл. 6.1
    slope = _interp_slope(soil, depth_m)
    horizontal = depth_m * slope

    # Случай 5: clay_soft при z > 3 м — шпунт рекомендуется
    if soil == "clay_soft" and depth_m > SHEET_PILE_RECOMMENDED_DEPTH_M:
        return TrenchStability(
            depth_m=depth_m,
            safe_slope_ratio_m_per_h=slope,
            horizontal_clearance_m=horizontal,
            sheet_pile_required=True,
            sheet_pile_reason=(
                f"z={depth_m:.1f} м > {SHEET_PILE_RECOMMENDED_DEPTH_M} м "
                f"для мягкопластичной глины — шпунт рекомендуется "
                f"СП 45.13330.2017 §6.1.2."
            ),
            passive_resistance_kPa=passive_kPa,
        )

    # Случай 6: открытый откос допустим
    return TrenchStability(
        depth_m=depth_m,
        safe_slope_ratio_m_per_h=slope,
        horizontal_clearance_m=horizontal,
        sheet_pile_required=False,
        sheet_pile_reason=None,
        passive_resistance_kPa=passive_kPa,
    )


__all__ = [
    "SAFE_SLOPE_BY_DEPTH",
    "SHEET_PILE_MANDATORY_DEPTH_M",
    "SHEET_PILE_RECOMMENDED_DEPTH_M",
    "TrenchStability",
    "check_trench_stability",
]
