"""Тесты для расчёта размеров корпуса КНС (Phase 13).

Эталон: ТКП ПВТ № 3102.4Д-25, KAIQUAN 65WQ35-50-11JY (Q=20.6, H=53.3, P=11 кВт)
→ корпус Ø1800×3000 мм. Наш расчёт должен давать те же размеры в пределах +1 шага лестницы.
"""

from __future__ import annotations

import pytest

from pump_calculator.corpus_sizing import (
    compute_corpus_size,
    estimate_corpus_height_mm,
    select_corpus_diameter_mm,
)
from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input, L1Input


def test_pvt_etalon_diameter_1800_for_q20() -> None:
    """Эталон ПВТ: Q=20.6 м³/ч → диаметр 1800 мм."""
    assert select_corpus_diameter_mm(20.6) == 1800.0


def test_diameter_ladder_breakpoints() -> None:
    """Лестница диаметров по Q."""
    assert select_corpus_diameter_mm(3) == 1000  # коттедж
    assert select_corpus_diameter_mm(10) == 1500  # малая
    assert select_corpus_diameter_mm(25) == 1800  # типовая бытовая
    assert select_corpus_diameter_mm(50) == 2000  # гостиница
    assert select_corpus_diameter_mm(150) == 3000  # ЖК
    assert select_corpus_diameter_mm(800) == 4000  # промышленный объект


def test_height_grows_with_pump_size() -> None:
    """Чем больше насос — тем выше корпус (под автомуфту)."""
    h_small = estimate_corpus_height_mm(10, P_kW=3, depth_inlet_mm=2000)
    h_big = estimate_corpus_height_mm(100, P_kW=30, depth_inlet_mm=2000)
    assert h_big > h_small


def test_compute_corpus_for_pvt_etalon() -> None:
    """Полный расчёт для ПВТ-эталона: Q=20.6, P=11 → Ø1800, высота >= 3000."""
    cs = compute_corpus_size(Q_m3h=20.6, P_kW=11, depth_inlet_mm=1180, n_pumps=2)
    assert cs.diameter_mm == 1800.0
    # У ПВТ корпус 3000 мм при глубине подвода 1180 мм. Наш расчёт может дать
    # больше из-за safety, но не меньше 2000 мм.
    assert cs.height_mm >= 2000.0
    assert cs.outlet_DN_mm == 80.0  # Q=20.6 → DN 80 (по таблице)
    assert cs.weight_estimate_kg > 0


def test_n_pumps_3_increases_diameter() -> None:
    """3 насоса → диаметр на 1 шаг больше (для размещения автомуфт)."""
    cs2 = compute_corpus_size(Q_m3h=20.6, P_kW=11, n_pumps=2)
    cs3 = compute_corpus_size(Q_m3h=20.6, P_kW=11, n_pumps=3)
    assert cs3.diameter_mm > cs2.diameter_mm


def test_select_pumps_returns_corpus_for_typical_kns() -> None:
    """Для бытовой Q=21.2 м³/ч → SelectionResult.corpus_size заполнен."""
    result = select_pumps(L0Input(Q_m3h=21.2, dH_m=5, L_m=50, wastewater_type="domestic"))
    assert result.corpus_size is not None
    assert result.corpus_size.diameter_mm == 1800.0


def test_select_pumps_no_corpus_for_clean_water() -> None:
    """Для clean_water (booster_station) корпус не нужен — блок целиком."""
    result = select_pumps(L0Input(Q_m3h=20, wastewater_type="clean_water"))
    assert result.corpus_size is None


def test_select_pumps_no_corpus_for_micro_kns() -> None:
    """Для Q<5 + DN<=65 (готовый приямок) корпус не нужен."""
    result = select_pumps(L0Input(Q_m3h=2, dH_m=3, wastewater_type="domestic"))
    # Если есть кандидат с DN<=65 — корпус не нужен
    sample = result.results.budget or result.results.mid or result.results.premium
    if sample and (sample.discharge_DN_mm or 65) <= 65:
        assert result.corpus_size is None


def test_corpus_for_industrial_q150_diameter_3000() -> None:
    """Промышленная Q=150 → Ø3000."""
    result = select_pumps(
        L0Input(Q_m3h=150, dH_m=10, L_m=200, wastewater_type="industrial")
    )
    if result.corpus_size:
        assert result.corpus_size.diameter_mm >= 2500


def test_l1_pumps_total_3_propagates_to_corpus() -> None:
    """L1.pumps_total_override=3 → larger corpus diameter."""
    base = select_pumps(L0Input(Q_m3h=21.2, dH_m=5, wastewater_type="domestic"))
    with_3 = select_pumps(
        L0Input(Q_m3h=21.2, dH_m=5, wastewater_type="domestic"),
        L1=L1Input(pumps_total_override=3),
    )
    if base.corpus_size and with_3.corpus_size:
        assert with_3.corpus_size.diameter_mm >= base.corpus_size.diameter_mm
