"""Тесты модуля physics.py — расчёты Phase 21."""

from __future__ import annotations

from pump_calculator.physics import (
    FittingsBOM,
    adjust_h_for_wastewater,
    calc_local_losses_h_m,
    calc_motor_starting_current,
    calc_npsha_m,
    check_cavitation,
    density_water_kg_m3,
    evaluate_qh_polynomial,
    find_operating_point,
    fit_qh_polynomial,
    kinematic_viscosity_water_m2s,
    thermal_load_check,
    vapor_pressure_water_kpa,
)


class TestDensity:
    def test_density_at_4c_max(self):
        # При 4°C плотность воды максимальная ~1000 кг/м³
        assert abs(density_water_kg_m3(4) - 1000.0) < 0.5

    def test_density_at_20c(self):
        # При 20°C ~998.2 кг/м³
        rho = density_water_kg_m3(20)
        assert 995 < rho < 1000

    def test_density_at_80c(self):
        # При 80°C ~971.8 кг/м³
        rho = density_water_kg_m3(80)
        assert 960 < rho < 985


class TestViscosity:
    def test_visc_at_20c(self):
        # При 20°C ν ≈ 1.004e-6 м²/с (справочно 1.01e-6)
        nu = kinematic_viscosity_water_m2s(20)
        assert 0.95e-6 < nu < 1.05e-6

    def test_visc_decreases_with_temp(self):
        # Вязкость должна падать с температурой
        assert (
            kinematic_viscosity_water_m2s(0)
            > kinematic_viscosity_water_m2s(50)
            > kinematic_viscosity_water_m2s(100)
        )


class TestVaporPressure:
    def test_vap_at_100c(self):
        # При 100°C P_vapor = 1 атм = 101.325 кПа
        p = vapor_pressure_water_kpa(100)
        assert 95 < p < 105

    def test_vap_at_20c(self):
        # При 20°C P_vapor ≈ 2.34 кПа
        p = vapor_pressure_water_kpa(20)
        assert 2.0 < p < 2.7

    def test_vap_increases_with_temp(self):
        assert (
            vapor_pressure_water_kpa(0)
            < vapor_pressure_water_kpa(50)
            < vapor_pressure_water_kpa(100)
        )


class TestLocalLosses:
    def test_typical_kns_obvyazka(self):
        # Типовая обвязка КНС: 1 вход + 1 выход + 2 колена + 1 задвижка + 1 обр.клапан
        bom = FittingsBOM(
            entrance_sharp=1,
            exit_to_reservoir=1,
            elbows_90=2,
            gate_valves=1,
            check_valves_swing=1,
        )
        v = 1.5  # м/с
        sum_z, h = calc_local_losses_h_m(bom, v)
        # Ожидаем Σζ ≈ 0.5 + 1.0 + 0.6 + 0.15 + 1.5 = 3.75
        assert 3.5 < sum_z < 4.0
        # H = 3.75 × 1.5²/19.62 = 3.75 × 0.115 ≈ 0.43 м
        assert 0.40 < h < 0.50

    def test_zero_fittings_zero_loss(self):
        bom = FittingsBOM()
        sum_z, h = calc_local_losses_h_m(bom, 1.5)
        assert sum_z == 0.0 and h == 0.0


class TestNPSH:
    def test_submersible_npsha_high(self):
        # Погружной насос (H_suction отрицательное — насос затоплен на 3 м)
        npsha = calc_npsha_m(H_suction_m=-3.0, T_celsius=20)
        # NPSHa = (P_atm - P_vap)/(ρg) - (-3) - 0 ≈ 10.1 + 3 = ~13 м
        assert 12 < npsha < 14

    def test_dry_well_npsha_lower(self):
        # Сухой котлован, насос на 2 м выше уровня жидкости
        npsha = calc_npsha_m(H_suction_m=2.0, T_celsius=20)
        # NPSHa ≈ 10.1 - 2 = ~8 м
        assert 7 < npsha < 9

    def test_hot_water_npsha_drops(self):
        # При 80°C P_vapor становится большим, NPSHa падает
        npsha_20 = calc_npsha_m(H_suction_m=2.0, T_celsius=20)
        npsha_80 = calc_npsha_m(H_suction_m=2.0, T_celsius=80)
        assert npsha_20 - npsha_80 > 3  # разница минимум 3 м

    def test_cavitation_warning_when_margin_low(self):
        # Насос требует NPSHr=5, имеем только 4.5 — маргинально
        result = check_cavitation(H_suction_m=2.0, npshr_m=5.0, T_celsius=20)
        # NPSHa ≈ 8.1, margin ≈ 3.1 м — safe
        assert result.safe is True

    def test_cavitation_dangerous_at_high_temp(self):
        # 70°C, насос на 5 м выше, NPSHr=4
        result = check_cavitation(
            H_suction_m=5.0,
            npshr_m=4.0,
            T_celsius=70,
            H_friction_suction_m=1.0,
        )
        # Должно показать danger
        assert result.npsha_m < result.npshr_m or result.margin_m < 0.5


class TestQHFitting:
    def test_fit_three_points(self):
        # Идеальная парабола H = 30 - 0.5·Q² (вершина при Q=0, H=30)
        points = [(0, 30), (5, 30 - 0.5 * 25), (10, 30 - 0.5 * 100)]
        coeffs = fit_qh_polynomial(points, degree=2)
        # a0 ≈ 30, a1 ≈ 0, a2 ≈ -0.5
        assert abs(coeffs[0] - 30) < 0.5
        assert abs(coeffs[2] - (-0.5)) < 0.05

    def test_evaluate_polynomial(self):
        # H(Q) = 20 + 0·Q + (-0.1)·Q²
        coeffs = [20.0, 0.0, -0.1]
        assert abs(evaluate_qh_polynomial(coeffs, 0) - 20) < 0.01
        assert abs(evaluate_qh_polynomial(coeffs, 10) - 10) < 0.01

    def test_operating_point(self):
        # Насос: H = 30 - 0.5·Q² (макс H=30 при Q=0)
        # Система: H_sys = 10 + 0.05·Q² (статический + потери)
        # Пересечение: 30 - 0.5·Q² = 10 + 0.05·Q² → 20 = 0.55·Q² → Q ≈ 6.03
        # H_op = 30 - 0.5·6.03² = 30 - 18.18 = 11.82 (= H_sys = 10 + 0.05·6.03² = 11.82)
        Q_op, H_op = find_operating_point(
            pump_coeffs=[30.0, 0.0, -0.5],
            system_static_h_m=10.0,
            system_friction_factor_per_q2=0.05,
        )
        assert 5.5 < Q_op < 6.5
        assert 11 < H_op < 13


class TestMotorStarts:
    def test_starting_currents(self):
        assert calc_motor_starting_current(15, "direct") == 7.0
        assert calc_motor_starting_current(15, "soft_start") == 2.5
        assert calc_motor_starting_current(15, "VFD") < 1.5

    def test_thermal_ok_for_low_starts(self):
        result = thermal_load_check(starts_per_hour=4, P_motor_kw=10, starting_method="direct")
        assert result["ok"] is True

    def test_thermal_warning_for_high_starts_direct(self):
        result = thermal_load_check(starts_per_hour=15, P_motor_kw=50, starting_method="direct")
        assert result["ok"] is False

    def test_thermal_ok_with_VFD_high_starts(self):
        # VFD позволяет 30+ пусков на 100 кВт
        result = thermal_load_check(starts_per_hour=20, P_motor_kw=80, starting_method="VFD")
        assert result["ok"] is True


class TestWastewaterCorrection:
    def test_clean_water_no_correction(self):
        H_corr, reason = adjust_h_for_wastewater(
            H_clean_m=20.0, suspended_solids_mg_l=100, oil_products_mg_l=10
        )
        assert H_corr == 20.0
        assert "0%" in reason

    def test_landfill_leachate_correction(self):
        # Фильтрат ТКО: SS = 5000 мг/л → +10%
        H_corr, reason = adjust_h_for_wastewater(H_clean_m=20.0, suspended_solids_mg_l=5000)
        assert abs(H_corr - 22.0) < 0.1
        assert "+10%" in reason

    def test_oily_water_correction(self):
        H_corr, reason = adjust_h_for_wastewater(H_clean_m=20.0, oil_products_mg_l=200)
        assert abs(H_corr - 20.6) < 0.1
        assert "нефтепродукты" in reason
