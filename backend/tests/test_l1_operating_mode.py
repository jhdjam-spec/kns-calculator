"""Тесты для новых L1-полей: operating_mode, inflow_per_hour_m3, pumps_total_override.

Зависимости:
- inflow_per_hour_m3 + Q_pump → sump_volume_min_m3 + cycles_per_hour_estimate
- operating_mode → operating_mode_effective (с учётом фактического inflow vs Q_pump)
- pumps_total_override → n_pumps_total в ComputedHydraulics + множитель в pricing
"""

from __future__ import annotations

import pytest

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input, L1Input


@pytest.fixture
def base_l0() -> L0Input:
    """Типовой бытовой кейс — гостиница 50 номеров."""
    return L0Input(Q_m3h=21.2, dH_m=5.0, L_m=50.0, wastewater_type="domestic")


def test_no_l1_extras_returns_none_sump(base_l0: L0Input) -> None:
    """Без operating_mode/inflow → sump/cycles/mode = None, n_pumps_total = 2."""
    result = select_pumps(base_l0, L1=None)
    assert result.computed.sump_volume_min_m3 is None
    assert result.computed.cycles_per_hour_estimate is None
    assert result.computed.operating_mode_effective is None
    assert result.computed.n_pumps_total == 2


def test_inflow_only_computes_sump_and_cycles(base_l0: L0Input) -> None:
    """inflow=10 м³/ч + Q_pump=21.2 → насос пульсирует, есть cycles_per_hour."""
    l1 = L1Input(inflow_per_hour_m3=10.0)
    result = select_pumps(base_l0, L1=l1)
    # V_min = 21.2 × 5 / 60 = 1.767 м³
    assert result.computed.sump_volume_min_m3 == pytest.approx(1.767, rel=1e-2)
    # Циклы: t_fill = 1.767 × 60 / 10 = 10.6 мин, t_pump = 1.767 × 60 / 11.2 = 9.46 мин,
    # cycle = 20.06 мин → 60 / 20.06 ≈ 2.99 циклов/час
    assert result.computed.cycles_per_hour_estimate == pytest.approx(2.99, abs=0.1)
    # Режим эффективный = level_based (когда inflow задан без явного operating_mode)
    assert result.computed.operating_mode_effective == "level_based"


def test_inflow_equal_or_above_pump_continuous(base_l0: L0Input) -> None:
    """inflow=22 (>= Q_pump=21.2) → continuous, циклов нет (=0)."""
    l1 = L1Input(inflow_per_hour_m3=22.0)
    result = select_pumps(base_l0, L1=l1)
    assert result.computed.cycles_per_hour_estimate == 0.0
    assert result.computed.operating_mode_effective == "continuous"


def test_explicit_continuous_mode(base_l0: L0Input) -> None:
    """operating_mode=continuous → cycles_per_hour = 0 даже без inflow."""
    l1 = L1Input(operating_mode="continuous")
    result = select_pumps(base_l0, L1=l1)
    assert result.computed.cycles_per_hour_estimate == 0.0
    assert result.computed.operating_mode_effective == "continuous"


def test_pumps_total_override_2_unchanged(base_l0: L0Input) -> None:
    """pumps_total_override=2 → n_pumps_total=2 (как дефолт), цена та же."""
    l1 = L1Input(pumps_total_override=2)
    result = select_pumps(base_l0, L1=l1)
    assert result.computed.n_pumps_total == 2


def test_pumps_total_override_3_increases_price(base_l0: L0Input) -> None:
    """pumps_total_override=3 → n_pumps_total=3, цена насосов выросла на ~50%."""
    result_default = select_pumps(base_l0, L1=None)
    result_override = select_pumps(base_l0, L1=L1Input(pumps_total_override=3))
    assert result_override.computed.n_pumps_total == 3

    # Сравниваем pump_rub в budget-сегменте
    if result_default.results.budget and result_override.results.budget:
        default_pump = result_default.results.budget.price_breakdown.pump_rub
        override_pump = result_override.results.budget.price_breakdown.pump_rub
        # 3 насоса вместо 2 → ровно ×1.5 на pump_rub
        assert override_pump == pytest.approx(default_pump * 1.5, rel=1e-3)


def test_periodic_mode_with_inflow(base_l0: L0Input) -> None:
    """operating_mode=periodic + inflow=5 → sump_min рассчитан, cycles считаются."""
    l1 = L1Input(operating_mode="periodic", inflow_per_hour_m3=5.0)
    result = select_pumps(base_l0, L1=l1)
    assert result.computed.sump_volume_min_m3 is not None
    assert result.computed.sump_volume_min_m3 > 0
    assert result.computed.cycles_per_hour_estimate is not None
    assert result.computed.operating_mode_effective == "periodic"
