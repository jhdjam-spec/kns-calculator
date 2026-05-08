"""Тесты Phase 24 — электрические расчёты."""
from __future__ import annotations

import pytest

from pump_calculator.electrical import (
    CABLE_SECTIONS_MM2,
    calc_full_load_current,
    calc_motor_power_required,
    select_cable_section,
    select_circuit_breaker,
    select_control_panel,
)

# ──────────────────────────────────────────────────────────────────────────
# Расчёт мощности двигателя
# ──────────────────────────────────────────────────────────────────────────


def test_motor_power_typical_kns():
    """Типовая КНС: Q=20 м³/ч, H=15 м, η_насос=0.65 → P_мотор ≈ 2-3 кВт."""
    result = calc_motor_power_required(Q_m3h=20, H_m=15, pump_efficiency=0.65)
    # P_hyd = 1000·9.81·(20/3600)·15/1000 = 0.818 кВт
    assert result.P_hydraulic_kw == pytest.approx(0.82, abs=0.05)
    # P_shaft = 0.818/0.65 = 1.26 кВт
    assert result.P_shaft_kw == pytest.approx(1.26, abs=0.05)
    # P_motor = 1.26/0.90×1.15 = 1.61 → округление вверх до 2.2 кВт
    assert result.P_motor_nominal_kw == 2.2


def test_motor_power_large_kns():
    """Крупная КНС: Q=200 м³/ч, H=30."""
    result = calc_motor_power_required(Q_m3h=200, H_m=30, pump_efficiency=0.70)
    # P_hyd = 1000·9.81·(200/3600)·30/1000 = 16.35 кВт
    # P_shaft = 23.36, P_mot = 29.85 → 30 кВт
    assert result.P_motor_nominal_kw == pytest.approx(30, abs=0.5)


def test_full_load_current_3phase():
    """Ток для 7.5 кВт, 400 В, cos=0.85, η=0.90: I ≈ 14 А."""
    current = calc_full_load_current(P_motor_kw=7.5, U_v=400, cos_phi=0.85, motor_efficiency=0.90)
    assert 13 < current < 15


def test_motor_starting_current_VFD():
    """VFD пуск — ток только 1.2× номинала."""
    result = calc_motor_power_required(Q_m3h=50, H_m=20, starting_method="VFD")
    ratio = result.starting_current_a / result.nominal_current_a
    assert ratio == pytest.approx(1.2, abs=0.05)


def test_motor_starting_current_DOL():
    """Прямой пуск — ток 7× номинала."""
    result = calc_motor_power_required(Q_m3h=20, H_m=15, starting_method="direct")
    ratio = result.starting_current_a / result.nominal_current_a
    assert ratio == pytest.approx(7.0, abs=0.1)


# ──────────────────────────────────────────────────────────────────────────
# Кабель
# ──────────────────────────────────────────────────────────────────────────


def test_cable_small_load():
    """I=20 А, L=50 м → S=2.5 мм² (по нагреву хватает 2.5)."""
    cable = select_cable_section(I_load_a=20, L_m=50, U_v=400)
    assert cable.section_mm2 == 2.5
    assert cable.delta_u_percent < 5.0


def test_cable_long_distance_increases_section():
    """Длинная линия — может потребовать большее сечение."""
    cable_short = select_cable_section(I_load_a=30, L_m=10, U_v=400)
    cable_long = select_cable_section(I_load_a=30, L_m=500, U_v=400)
    assert cable_long.section_mm2 >= cable_short.section_mm2


def test_cable_section_in_standard_range():
    """Подобранное сечение всегда из стандартной сетки."""
    cable = select_cable_section(I_load_a=100, L_m=100)
    assert cable.section_mm2 in CABLE_SECTIONS_MM2


# ──────────────────────────────────────────────────────────────────────────
# Автомат
# ──────────────────────────────────────────────────────────────────────────


def test_breaker_rating_above_load():
    """I_ном автомата всегда ≥ K·I_нагрузки."""
    cb = select_circuit_breaker(I_load_a=20, motor_duty="S3")
    # K=1.4 для S3 → I_расч = 28 → ближайшее стандарт ≥28 = 32А
    assert cb.breaker_rating_a == 32


def test_breaker_curve_VFD_is_B():
    """VFD пуск → кривая B."""
    cb = select_circuit_breaker(I_load_a=20, starting_method="VFD")
    assert cb.curve == "B"


def test_breaker_curve_DOL_is_D():
    """Прямой пуск → кривая D."""
    cb = select_circuit_breaker(I_load_a=20, starting_method="direct")
    assert cb.curve == "D"


def test_breaker_icu_above_short_circuit():
    """Icu автомата ≥ ожидаемому току КЗ."""
    cb = select_circuit_breaker(I_load_a=50, short_circuit_ka=8)
    assert cb.icu_ka >= 8


# ──────────────────────────────────────────────────────────────────────────
# Шкаф управления
# ──────────────────────────────────────────────────────────────────────────


def test_panel_mini_for_small_kns():
    """P=2.2 кВт, без диспетчеризации → МИНИ."""
    panel = select_control_panel(
        P_motor_kw=2.2, n_pumps=2, reliability_category=3, needs_dispatch=False
    )
    assert panel.level == "mini"
    assert panel.starting_method == "direct"
    assert not panel.has_plc


def test_panel_opti_for_medium():
    """P=11 кВт → ОПТИ с софтстартом и GSM."""
    panel = select_control_panel(P_motor_kw=11, reliability_category=2)
    assert panel.level == "opti"
    assert panel.has_plc
    assert panel.has_gsm
    assert panel.starting_method == "soft_start"


def test_panel_max_for_large():
    """P=45 кВт → МАКС с VFD."""
    panel = select_control_panel(P_motor_kw=45, reliability_category=1)
    assert panel.level == "max"
    assert panel.has_vfd
    assert panel.has_avr
    assert panel.has_scada


def test_panel_atex_when_atex_zone():
    """Если ATEX зона — независимо от мощности → ATEX."""
    panel = select_control_panel(P_motor_kw=2.2, is_atex_zone=True)
    assert panel.level == "atex"
    assert panel.has_atex


def test_panel_fire_for_fire_pump():
    """Пожарный насос → ШУПН с АВР."""
    panel = select_control_panel(P_motor_kw=15, is_fire_pump=True)
    assert panel.level == "fire"
    assert panel.has_avr
    assert panel.starting_method == "direct"  # Пож. — DOL по СП 6.13130
    assert not panel.has_vfd


def test_panel_price_range_increases_with_complexity():
    """Цена МИНИ < ОПТИ < МАКС < ATEX."""
    mini = select_control_panel(P_motor_kw=2.2, reliability_category=3)
    opti = select_control_panel(P_motor_kw=11)
    maxx = select_control_panel(P_motor_kw=45, reliability_category=1)
    atex = select_control_panel(P_motor_kw=2.2, is_atex_zone=True)

    assert mini.estimated_price_rub_2026[1] <= opti.estimated_price_rub_2026[1]
    assert opti.estimated_price_rub_2026[1] <= maxx.estimated_price_rub_2026[1]
    assert maxx.estimated_price_rub_2026[1] <= atex.estimated_price_rub_2026[1]
