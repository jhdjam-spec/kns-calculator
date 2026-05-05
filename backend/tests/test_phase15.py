"""Phase 8.5 — тесты формул §15 из formulas.md.

Проверяет:
- §15.1 V_min
- §15.5 S/D = 1 + 2.3·Fr (минимальное погружение по HI 9.8)
- §15.6 Specific Speed Ns + score_ns_compatibility
- §15.7 NPSH margin (HI 9.6.1-2024)
- §15.9 v_min фильтр в auto_select_diameter_mm
"""

from __future__ import annotations

from pump_calculator.hydraulics import auto_select_diameter_mm, calc_velocity_ms
from pump_calculator.phase15 import (
    calc_min_submergence_m,
    calc_npsh_margin_m,
    calc_specific_speed_ns,
    calc_v_min_pool_m3,
    get_v_min_for_wastewater,
    score_ns_compatibility,
)


class TestVminPool:
    """§15.1 — V_min приёмного резервуара."""

    def test_basic_calculation(self):
        """Q=21.2 м³/ч × 5 мин / 60 = 1.77 м³."""
        assert calc_v_min_pool_m3(21.2) == 1.77

    def test_zero_returns_zero(self):
        assert calc_v_min_pool_m3(0) == 0.0

    def test_negative_returns_zero(self):
        assert calc_v_min_pool_m3(-5) == 0.0

    def test_custom_t_min(self):
        """3 минуты вместо дефолтных 5: Q=60 × 3/60 = 3 м³."""
        assert calc_v_min_pool_m3(60, t_min_run_min=3) == 3.0

    def test_large_pump(self):
        """Уташ-кейс: Q=530 × 5/60 = 44.17 м³."""
        assert calc_v_min_pool_m3(530.45) == 44.2


class TestMinSubmergence:
    """§15.5 — S/D = 1 + 2.3·Fr (HI 9.8)."""

    def test_typical_dn50_pump(self):
        """Q=21.2 м³/ч, DN50: ожидаем S_min ≈ 0.30-0.40 м."""
        result = calc_min_submergence_m(21.2, 50)
        # v = Q/A: A=π·0.025² ≈ 1.96e-3 → v ≈ 3.0 м/с
        assert result["v_ms"] > 2.5
        # Fr = v/√(g·D) ≈ 3.0/√(9.81·0.05) ≈ 4.28
        assert 4.0 < result["Fr"] < 4.5
        # S/D = 1 + 2.3·4.28 ≈ 10.84 → S_min ≈ 0.54 м
        assert result["S_min_m"] > 0.4

    def test_zero_inputs(self):
        result = calc_min_submergence_m(0, 50)
        assert result["S_min_m"] == 0.0

    def test_uташ_dn250(self):
        """Уташ SW250: Q=530.45 м³/ч, DN250.
        v = 530.45/3600 / (π·0.125²) ≈ 3.0 м/с
        Fr ≈ 3.0/√(9.81·0.25) ≈ 1.91
        S_min/D = 1 + 2.3·1.91 ≈ 5.40
        S_min ≈ 5.40 × 0.25 ≈ 1.35 м
        """
        result = calc_min_submergence_m(530.45, 250)
        assert 1.2 < result["S_min_m"] < 1.5
        assert result["Fr"] < 2.5

    def test_low_velocity_low_submergence(self):
        """Большой раструб → малая скорость → малое S_min."""
        result = calc_min_submergence_m(50, 200)
        # v = 50/3600 / (π·0.1²) ≈ 0.44 м/с → Fr низкое
        assert result["S_min_m"] < 0.5


class TestSpecificSpeed:
    """§15.6 — Ns в SI системе (n·√Q/H^0.75)."""

    def test_typical_sewage_pump(self):
        """1450 об/мин, Q=100 м³/ч, H=10 м.
        Q_si = 100/3600 = 0.0278 м³/с, √Q ≈ 0.167
        H^0.75 = 10^0.75 ≈ 5.62
        Ns = 1450 × 0.167 / 5.62 ≈ 43.1
        """
        ns = calc_specific_speed_ns(1450, 100, 10)
        assert 40 < ns < 50

    def test_radial_pump_low_ns(self):
        """Высоконапорный радиальный: Ns низкий."""
        ns = calc_specific_speed_ns(2900, 10, 100)
        # Q_si=0.00278, √Q≈0.0527, H^0.75=31.6 → Ns ≈ 4.8
        assert ns < 15

    def test_axial_pump_high_ns(self):
        """Низконапорный осевой: Ns высокий."""
        ns = calc_specific_speed_ns(1450, 1000, 5)
        # Q_si=0.278, √Q≈0.527, H^0.75≈3.34 → Ns ≈ 229
        assert ns > 100

    def test_invalid_inputs_return_zero(self):
        assert calc_specific_speed_ns(0, 100, 10) == 0
        assert calc_specific_speed_ns(1450, 0, 10) == 0
        assert calc_specific_speed_ns(1450, 100, 0) == 0


class TestNsCompatibility:
    """§15.6 — score_ns_compatibility множитель."""

    def test_in_optimal_range(self):
        """15-80 — оптимально."""
        assert score_ns_compatibility(20) == 1.0
        assert score_ns_compatibility(50) == 1.0
        assert score_ns_compatibility(80) == 1.0

    def test_at_boundaries(self):
        """10-15, 80-100 — penalty 0.7."""
        assert score_ns_compatibility(12) == 0.7
        assert score_ns_compatibility(90) == 0.7

    def test_far_outside(self):
        """<10 или >100 — penalty 0.4."""
        assert score_ns_compatibility(5) == 0.4
        assert score_ns_compatibility(150) == 0.4

    def test_no_data_no_penalty(self):
        """Ns=0 (нет данных) → не штрафуем."""
        assert score_ns_compatibility(0) == 1.0


class TestNpshMargin:
    """§15.7 — NPSH margin по HI 9.6.1-2024."""

    def test_small_pump_min_1m(self):
        """NPSHR=5 м → 0.1×5=0.5, max(1.0, 0.5)=1.0."""
        assert calc_npsh_margin_m(5) == 1.0

    def test_large_pump_proportional(self):
        """NPSHR=15 м → 0.1×15=1.5 м."""
        assert calc_npsh_margin_m(15) == 1.5

    def test_borderline_10m(self):
        """NPSHR=10 м → max(1, 1)=1.0."""
        assert calc_npsh_margin_m(10) == 1.0

    def test_zero_returns_default(self):
        """NPSHR=0 (нет данных) → консервативный 1.0."""
        assert calc_npsh_margin_m(0) == 1.0


class TestVminWastewater:
    """§15.9 — v_min по типу стоков."""

    def test_domestic_strict(self):
        assert get_v_min_for_wastewater("domestic") == 1.0

    def test_drainage_relaxed(self):
        assert get_v_min_for_wastewater("drainage") == 0.7

    def test_clean_water(self):
        assert get_v_min_for_wastewater("clean_water") == 0.6

    def test_unknown_default(self):
        assert get_v_min_for_wastewater(None) == 1.0
        assert get_v_min_for_wastewater("unknown_type") == 1.0


class TestAutoSelectDiameterVmin:
    """§15.9 — auto_select_diameter_mm с v_min фильтром."""

    def test_normal_case_returns_initial(self):
        """Q=21.2 м³/ч с v_target=1.2 → D≈80 мм, v на 80=1.17 м/с.
        v_min=1.0 → удовлетворяет, возвращаем D_initial.
        """
        D = auto_select_diameter_mm(21.2)
        v = calc_velocity_ms(21.2, D)
        assert v >= 1.0

    def test_velocity_meets_v_min_for_typical_q(self):
        """Для типичных Q (10-100 м³/ч) скорость должна быть ≥ 1 м/с."""
        for Q in [10, 21.2, 50, 100]:
            D = auto_select_diameter_mm(Q)
            v = calc_velocity_ms(Q, D)
            assert v >= 1.0, f"Q={Q}: v={v:.2f} < 1.0 на D={D}"

    def test_drainage_lower_v_min(self):
        """Дождевая: можно v=0.7. Меньший Q → больший D разрешён."""
        D_strict = auto_select_diameter_mm(50, v_min_ms=1.0)
        D_relaxed = auto_select_diameter_mm(50, v_min_ms=0.7)
        # При более мягком v_min можно выбрать D ≥ D_strict
        assert D_relaxed >= D_strict
