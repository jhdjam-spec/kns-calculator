"""Расчёт стоимости стеклопластикового цилиндрического корпуса.

Источник формулы: `00_research/inbox_2026-05-04/калькулятор расчета стоимсти
стеклопластиковой емкости.xlsx` (Серво-Юг, 2026-05-04).

Эталонная проверка: D=2000 мм × L=5000 мм при default-параметрах →
себестоимость материалов 82 025 ₽, коммерческая цена 188 658 ₽
(множитель 1.15 × 2 = 2.3 для перехода нетто→брутто).

Ограничения модели:
- Только цилиндрические корпуса с двумя плоскими торцами
- Стандартный ряд диаметров: 800, 1000, 1500, 2000, 2400 мм
- Расчёт от слоёв нитки/рогожи (default 6/1)
- Цены сырья 2026: смола 225 ₽/кг, нитка 75 ₽/кг, рогожа 450 ₽/кг
- Не учитывает: монтажные элементы, патрубки, люки, теплоизоляцию
"""

from __future__ import annotations

import math

# ----- Стандартный ряд диаметров стеклопластиковых корпусов -----
GLASS_STANDARD_DIAMETERS_MM: list[int] = [800, 1000, 1500, 2000, 2400]

# ----- Default параметры намотки -----
DEFAULT_LAYERS_THREAD = 6     # слои нитки (B4)
DEFAULT_LAYERS_ROVING = 1     # слои рогожи (B5)

# ----- Толщины слоёв (мм/слой) -----
THREAD_THICKNESS_PER_LAYER_MM = 1.15
ROVING_THICKNESS_PER_LAYER_MM = 1.0

# ----- Удельные расходы (кг на 1 м² на 1 мм толщины) -----
RESIN_KG_PER_M2_MM = 0.6
THREAD_KG_PER_M2_MM = 1.17
ROVING_KG_PER_M2_MM = 0.5

# ----- Цены сырья 2026, ₽/кг -----
RESIN_PRICE_RUB_PER_KG = 225
THREAD_PRICE_RUB_PER_KG = 75
ROVING_PRICE_RUB_PER_KG = 450

# ----- Множитель «себестоимость → коммерческая цена» -----
# Из xlsx: cost_pp × 1.15 × 2 (×1.15 — отходы/наценка, ×2 — раскрой/сварка)
COMMERCIAL_MARKUP = 1.15 * 2  # = 2.3

# ----- π как в xlsx (округлённый до 3.14) -----
PI = 3.14


def round_to_glass_standard_d(d_mm: float) -> int:
    """Округление вверх до ближайшего стандартного диаметра стеклопластика."""
    for d in GLASS_STANDARD_DIAMETERS_MM:
        if d >= d_mm:
            return d
    return GLASS_STANDARD_DIAMETERS_MM[-1]


def calc_glass_corpus_cost(
    D_mm: int,
    L_mm: int,
    layers_thread: int = DEFAULT_LAYERS_THREAD,
    layers_roving: int = DEFAULT_LAYERS_ROVING,
) -> dict[str, float]:
    """Расчёт стеклопластикового корпуса.

    Возвращает словарь с массами, себестоимостью и коммерческой ценой.

    Эталон: D=2000, L=5000, layers=6/1 → mass_total≈493 кг, cost_self≈82_025 ₽,
    price_commercial=188_658 ₽.
    """
    D_m = D_mm / 1000.0
    L_m = L_mm / 1000.0

    # Толщины (мм)
    t_thread_total = layers_thread * THREAD_THICKNESS_PER_LAYER_MM
    t_roving_total = layers_roving * ROVING_THICKNESS_PER_LAYER_MM
    t_wall = t_thread_total + t_roving_total

    # Площади (м²) — π как в xlsx (3.14)
    S_cyl = PI * D_m * L_m            # боковая поверхность цилиндра
    S_torc_2 = PI * D_m * D_m / 2.0   # 2 торца = 2 × π·D²/4

    # Массы цилиндра, кг
    m_thread_cyl = THREAD_KG_PER_M2_MM * S_cyl * t_thread_total
    m_roving_cyl = ROVING_KG_PER_M2_MM * S_cyl * t_roving_total
    m_resin_cyl = RESIN_KG_PER_M2_MM * S_cyl * t_wall

    # Массы торцов, кг
    # NB: формула xlsx B12 = B19 + E3·B3 (т.е. 0.6 + t_wall·S_torc_2).
    # Это похоже на ошибку шаблона (× потерян), но именно она даёт реальную цену
    # на эталонной точке, поэтому повторяем 1-в-1.
    m_resin_torc = RESIN_KG_PER_M2_MM + t_wall * S_torc_2
    m_roving_torc = ROVING_KG_PER_M2_MM * S_torc_2 * t_wall

    mass_total = (
        m_thread_cyl + m_roving_cyl + m_resin_cyl
        + m_resin_torc + m_roving_torc
    )

    # Себестоимость, ₽
    cost_thread = m_thread_cyl * THREAD_PRICE_RUB_PER_KG
    cost_roving_cyl = m_roving_cyl * ROVING_PRICE_RUB_PER_KG
    cost_resin_cyl = m_resin_cyl * RESIN_PRICE_RUB_PER_KG
    cost_resin_torc = m_resin_torc * RESIN_PRICE_RUB_PER_KG
    cost_roving_torc = m_roving_torc * ROVING_PRICE_RUB_PER_KG
    cost_self = (
        cost_thread + cost_roving_cyl + cost_resin_cyl
        + cost_resin_torc + cost_roving_torc
    )

    # Коммерческая цена
    price_commercial = cost_self * COMMERCIAL_MARKUP

    # Объём (м³) — для информации
    V_m3 = math.pi * (D_m / 2) ** 2 * L_m

    return {
        "D_mm": D_mm,
        "L_mm": L_mm,
        "V_m3": round(V_m3, 3),
        "t_wall_mm": round(t_wall, 2),
        "mass_thread_kg": round(m_thread_cyl, 2),
        "mass_roving_total_kg": round(m_roving_cyl + m_roving_torc, 2),
        "mass_resin_total_kg": round(m_resin_cyl + m_resin_torc, 2),
        "mass_total_kg": round(mass_total, 2),
        "cost_self_rub": round(cost_self, 2),
        "price_commercial_rub": round(price_commercial),
    }


def estimate_glass_corpus_price_rub(Q_m3h: float) -> int:
    """Оценка цены стеклопластикового корпуса КНС по производительности.

    Эвристика: подбирает D и L из стандартного ряда так, чтобы внутренний объём
    обеспечивал минимум 5 минут аккумулирования при пиковом притоке (V_min = Q × 5/60).

    Default: layers_thread=6, layers_roving=1.
    """
    # Минимальный аккумулирующий объём, м³
    V_min = max(Q_m3h * 5.0 / 60.0, 1.5)

    # Подбираем D и L из стандартного ряда
    for D_mm in GLASS_STANDARD_DIAMETERS_MM:
        D_m = D_mm / 1000.0
        # L достаточная для V_min при выбранном D
        L_m_needed = V_min / (math.pi * (D_m / 2) ** 2)
        # Округляем длину до 500 мм вверх в реалистичных границах 1500–10000
        L_mm = max(1500, min(10_000, int(math.ceil(L_m_needed * 1000 / 500.0) * 500)))

        # Проверяем, что выбранный (D, L) даёт нужный объём
        V_actual = math.pi * (D_m / 2) ** 2 * (L_mm / 1000.0)
        if V_actual >= V_min:
            result = calc_glass_corpus_cost(D_mm, L_mm)
            return int(result["price_commercial_rub"])

    # Если даже максимальный D не справился — берём максимум
    result = calc_glass_corpus_cost(
        GLASS_STANDARD_DIAMETERS_MM[-1], 10_000
    )
    return int(result["price_commercial_rub"])
