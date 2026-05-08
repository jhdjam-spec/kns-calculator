"""Расчёт расхода на наружное пожаротушение по СП 8.13130.2020.

Главные таблицы:
- Табл. 1: расход воды на пожаротушение для жилых и общественных зданий — функция
  объёма здания и степени огнестойкости.
- Табл. 2: расход для производственных и складских — функция объёма, категории
  и степени огнестойкости.

Ссылки в коде идут на пункты СП 8.13130.2020.
"""
from __future__ import annotations

from .models import BuildingClass, FireScenarioInput, OccupancyType

# Табл. 1 СП 8.13130.2020 — наружное пожаротушение жилых и общественных зданий, л/с.
# Ключи: (occupancy, volume_max_m3) → расход в л/с при I-II степени огнестойкости.
# Для III и IV степеней — повышающие коэффициенты K_class.
# Эти значения выверены по сводке Справочника проектировщика (2018) и СП 8.13130
# приложения А.
_TABLE_1_LPS: dict[tuple[OccupancyType, int], float] = {
    # Жилые / общественные при V ≤ N (м³)
    ("residential", 1_000): 5.0,
    ("residential", 5_000): 10.0,
    ("residential", 25_000): 15.0,
    ("residential", 50_000): 20.0,
    ("residential", 150_000): 25.0,
    ("residential", 1_000_000): 30.0,

    ("public", 1_000): 5.0,
    ("public", 5_000): 10.0,
    ("public", 25_000): 15.0,
    ("public", 50_000): 20.0,
    ("public", 150_000): 25.0,
    ("public", 1_000_000): 30.0,

    # Сельхоз
    ("agricultural", 1_000): 5.0,
    ("agricultural", 5_000): 10.0,
    ("agricultural", 25_000): 15.0,
}

# Табл. 2 — производственные/складские, л/с (I-II степень огнестойкости).
# Категории: А/Б — наиболее опасные, Д — негорючие.
_TABLE_2_LPS: dict[tuple[OccupancyType, int], float] = {
    # Категории А, Б, В1-В2 (горючие, повышенный класс пожарной опасности)
    ("industrial_a", 3_000): 10.0,
    ("industrial_a", 5_000): 15.0,
    ("industrial_a", 20_000): 20.0,
    ("industrial_a", 50_000): 30.0,
    ("industrial_a", 200_000): 35.0,
    ("industrial_a", 400_000): 40.0,
    ("industrial_a", 600_000): 45.0,

    # Категории В3-В4 (умеренно горючие)
    ("industrial_b", 3_000): 10.0,
    ("industrial_b", 5_000): 10.0,
    ("industrial_b", 20_000): 15.0,
    ("industrial_b", 50_000): 20.0,
    ("industrial_b", 200_000): 25.0,
    ("industrial_b", 400_000): 30.0,

    # Категория Д (негорючие)
    ("industrial_d", 3_000): 10.0,
    ("industrial_d", 5_000): 10.0,
    ("industrial_d", 20_000): 10.0,
    ("industrial_d", 50_000): 15.0,
    ("industrial_d", 200_000): 20.0,
    ("industrial_d", 400_000): 25.0,

    # Склады (как В по умолчанию)
    ("warehouse", 3_000): 10.0,
    ("warehouse", 5_000): 10.0,
    ("warehouse", 20_000): 15.0,
    ("warehouse", 50_000): 20.0,
    ("warehouse", 200_000): 25.0,

    # Гаражи и автостоянки (СП 8.13130 п. 6.5)
    ("garage", 5_000): 10.0,
    ("garage", 20_000): 15.0,
    ("garage", 50_000): 20.0,
}

# Коэффициент по степени огнестойкости (для III и IV степени — повышение).
# Источник: СП 8.13130 §6, прим. к табл. 1, 2.
_CLASS_COEFFICIENT: dict[BuildingClass, float] = {
    "I": 1.0,
    "III": 1.1,    # +10%
    "IV": 1.25,    # +25%
}


def _lookup_step(table: dict[tuple[OccupancyType, int], float], occupancy: OccupancyType, volume_m3: float) -> tuple[float | None, str]:
    """Возвращает (расход, описание) для ближайшего верхнего шага объёма."""
    matched = [(v, q) for (occ, v), q in table.items() if occ == occupancy]
    if not matched:
        return None, ""
    matched.sort(key=lambda x: x[0])
    for v_max, q in matched:
        if volume_m3 <= v_max:
            return q, f"V ≤ {v_max} м³"
    # больше последнего шага — берём максимальный с предупреждением
    v_max, q = matched[-1]
    return q, f"V > {v_max} м³ (внеплан., прим. к табл.)"


def calc_external_demand(inputs: FireScenarioInput) -> tuple[float, str, list[str]]:
    """Рассчитывает расход наружного пожаротушения по СП 8.13130.

    Returns:
        (расход_лс, источник_таблица, замечания)
    """
    notes: list[str] = []

    # Табл. 1 — жилые/общественные/сельхоз
    if inputs.occupancy in ("residential", "public", "agricultural"):
        q_base, step_desc = _lookup_step(_TABLE_1_LPS, inputs.occupancy, inputs.volume_m3)
        table_ref = "СП 8.13130.2020 табл. 1"
    # Табл. 2 — производственные/склад/гаражи
    elif inputs.occupancy in ("industrial_a", "industrial_b", "industrial_d", "warehouse", "garage"):
        q_base, step_desc = _lookup_step(_TABLE_2_LPS, inputs.occupancy, inputs.volume_m3)
        table_ref = "СП 8.13130.2020 табл. 2"
    else:
        raise ValueError(f"Неизвестный тип здания: {inputs.occupancy}")

    if q_base is None:
        raise ValueError(f"Нет табличных данных для {inputs.occupancy}, V={inputs.volume_m3} м³")

    # Коэффициент огнестойкости
    k = _CLASS_COEFFICIENT.get(inputs.building_class, 1.0)
    q_with_class = q_base * k

    if k > 1.0:
        notes.append(
            f"Коэф. огнестойкости K={k} (степень {inputs.building_class}); "
            f"базовый расход {q_base} л/с → {q_with_class:.1f} л/с"
        )

    notes.append(f"Шаг таблицы: {step_desc}")
    notes.append(f"Источник: {table_ref}")

    # Жилые здания низкие (≤2 этажа, V≤1000): прим. 1 к табл. 1 — расход 5 л/с минимум.
    # Это уже учтено в табличных значениях.

    return q_with_class, table_ref, notes
