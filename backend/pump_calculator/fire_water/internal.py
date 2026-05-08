"""Расчёт расхода на внутреннее пожаротушение по СП 10.13130.2020.

Главные таблицы:
- Табл. 1: число струй и расход для жилых и общественных зданий (функция этажности
  и объёма).
- Табл. 2: то же для производственных и складских (функция объёма и категории).

Минимальная производительность струи — 2.5-2.6 л/с (диаметр спрыска ≥13 мм
при компактной части струи ≥6 м, СП 10.13130 §4.1).
"""
from __future__ import annotations

from .models import FireScenarioInput, OccupancyType

# СП 10.13130.2020, табл. 1 — внутренний ППВ для жилых/общественных.
# Ключ: (occupancy, etazhi_min, V_max_m3) → (n_струй, расход_струи_лс).
# Этажность ≥ etazhi_min И V ≤ V_max → данные строки.
# Если высота здания <17 м и нет особых требований — внутренний ППВ может не требоваться.
_TABLE_1: list[tuple[OccupancyType, int, int, int, float]] = [
    # (occupancy, floors_min, V_max_m3, n_jets, jet_lps)
    ("residential", 12, 1_000_000, 1, 2.6),       # Жилые 12-16 эт.
    ("residential", 16, 1_000_000, 2, 2.6),       # Жилые 16+ эт.
    ("residential", 25, 1_000_000, 3, 2.6),       # Жилые 25+ эт.
    ("public", 6, 7_500, 1, 2.6),                 # Общ. 6-12 эт., V≤7500
    ("public", 6, 25_000, 2, 2.6),                # Общ. 6-12 эт., V>7500
    ("public", 12, 25_000, 2, 2.6),               # Общ. 12+ эт.
    ("public", 16, 1_000_000, 3, 2.6),            # Общ. 16+ эт.
]

# СП 10.13130.2020, табл. 2 — внутренний ППВ для произв./склад.
_TABLE_2: list[tuple[OccupancyType, int, int, float]] = [
    # (occupancy, V_max_m3, n_jets, jet_lps)
    ("industrial_a", 50_000, 2, 5.0),
    ("industrial_a", 200_000, 4, 5.0),
    ("industrial_a", 1_000_000, 8, 5.0),

    ("industrial_b", 50_000, 2, 2.6),
    ("industrial_b", 200_000, 2, 5.0),
    ("industrial_b", 1_000_000, 4, 5.0),

    ("industrial_d", 200_000, 2, 2.6),
    ("industrial_d", 1_000_000, 2, 2.6),

    ("warehouse", 50_000, 2, 5.0),
    ("warehouse", 200_000, 4, 5.0),

    ("garage", 50_000, 2, 2.6),
    ("garage", 200_000, 2, 5.0),
]


def _is_required(inputs: FireScenarioInput) -> tuple[bool, str]:
    """Решает, требуется ли внутренний ППВ.

    СП 10.13130 §4 (упрощённо):
    - Жилые H ≥ 12 эт. (или ≥28 м) → требуется.
    - Общественные H ≥ 6 эт. → требуется.
    - Производственные/склады кат. А/Б/В при V ≥ 5000 м³ → требуется.
    - Гаражи закрытые ≥2 эт. → требуется.
    """
    if inputs.has_internal_system:
        return True, "Указано пользователем (has_internal_system=True)"

    if inputs.occupancy == "residential" and inputs.floors >= 12:
        return True, "Жилое здание ≥12 этажей (СП 10.13130 §4.1.1)"

    if inputs.occupancy == "public" and inputs.floors >= 6:
        return True, "Общественное здание ≥6 этажей (СП 10.13130 §4.1.2)"

    if inputs.occupancy in ("industrial_a", "industrial_b") and inputs.volume_m3 >= 5000:
        return True, "Произв. кат. А/Б, V≥5000 м³ (СП 10.13130 §4.1.5)"

    if inputs.occupancy == "warehouse" and inputs.volume_m3 >= 5000:
        return True, "Склад V≥5000 м³ (СП 10.13130 §4.1.5)"

    if inputs.occupancy == "garage" and inputs.floors >= 2:
        return True, "Закрытый гараж ≥2 этажей (СП 10.13130 §4.1.6)"

    return False, "По СП 10.13130 — не требуется для этой комбинации"


def calc_internal_demand(inputs: FireScenarioInput) -> tuple[float, list[str]]:
    """Рассчитывает расход внутреннего пожаротушения.

    Returns:
        (расход_лс, замечания) — 0.0 если внутренний ППВ не требуется.
    """
    notes: list[str] = []
    required, reason = _is_required(inputs)

    if not required:
        notes.append(f"Внутренний ППВ не требуется: {reason}")
        return 0.0, notes

    notes.append(f"Внутренний ППВ требуется: {reason}")

    # Если пользователь явно указал параметры струй — берём их (приоритет).
    if inputs.has_internal_system and inputs.n_jets_internal > 0:
        q = inputs.n_jets_internal * inputs.jet_flow_lps
        notes.append(
            f"По указанию: {inputs.n_jets_internal} струй × {inputs.jet_flow_lps} л/с = {q:.1f} л/с"
        )
        return q, notes

    # Иначе — табличный поиск.
    if inputs.occupancy in ("residential", "public"):
        # Берём строку с максимальной floors_min ≤ inputs.floors и V ≤ V_max.
        best = None
        for occ, floors_min, v_max, n_jets, jet_lps in _TABLE_1:
            if occ != inputs.occupancy:
                continue
            if inputs.floors >= floors_min and inputs.volume_m3 <= v_max:
                if best is None or floors_min > best[0]:
                    best = (floors_min, v_max, n_jets, jet_lps)
        if best:
            _, v_max, n_jets, jet_lps = best
            q = n_jets * jet_lps
            notes.append(
                f"СП 10.13130 табл. 1: {n_jets} струи × {jet_lps} л/с = {q:.1f} л/с (V≤{v_max} м³)"
            )
            return q, notes

    elif inputs.occupancy in ("industrial_a", "industrial_b", "industrial_d", "warehouse", "garage"):
        for occ, v_max, n_jets, jet_lps in _TABLE_2:
            if occ != inputs.occupancy:
                continue
            if inputs.volume_m3 <= v_max:
                q = n_jets * jet_lps
                notes.append(
                    f"СП 10.13130 табл. 2: {n_jets} струи × {jet_lps} л/с = {q:.1f} л/с (V≤{v_max} м³)"
                )
                return q, notes

    # Fallback: 2 струи × 2.6 л/с (минимум по СП 10.13130 §4.2)
    q = 2 * 2.6
    notes.append(f"Не найдено в таблицах, fallback минимум: 2×2.6 = {q:.1f} л/с (СП 10.13130 §4.2)")
    return q, notes
