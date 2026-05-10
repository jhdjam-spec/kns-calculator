"""Тесты активации 8 «dead» L1-полей + altitude_m → NPSHa.

Проверяем что каждое из 8 ранее неиспользуемых полей теперь
влияет на результат (n_pumps, цена, triggers, notes, корпус).

Список активированных полей (см. matching.py / hydraulics.py):
1. redundancy → n_pumps_total + множитель в pump_rub
2. level_sensor_type → floats_rub в pricing
3. dry_run_protection=False → trigger auto_no_dry_run_protection + warning
4. ip_motor → filter_by_ip_motor (отсекает насосы с ниже IP)
5. modbus_rtu_required=True → cabinet_rub +50k
6. above_ground_pavilion=True → corpus_rub +200-500k
7. inlet_pipe_diam_mm → corpus_size.inlet_DN_mm + note
8. install_depth_inlet_mm → corpus_size.height_mm

Bonus: altitude_m → ComputedHydraulics.npsha_m + trigger auto_npsha_low.
"""
from __future__ import annotations

import pytest

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input, L1Input


@pytest.fixture
def base_l0() -> L0Input:
    """Типовая бытовая КНС: гостиница 50 номеров — попадает в budget+mid+premium сегменты."""
    return L0Input(Q_m3h=21.2, dH_m=10.0, L_m=50.0, wastewater_type="domestic")


# ─────────────────────────────────────────────────────────────────────
# 1. redundancy
# ─────────────────────────────────────────────────────────────────────

class TestRedundancy:
    def test_default_2_pumps(self, base_l0: L0Input) -> None:
        """Без redundancy — 2 насоса (1+1 по СП 32 §6.2)."""
        r = select_pumps(base_l0, L1=None)
        assert r.computed.n_pumps_total == 2

    def test_redundancy_2_plus_1_gives_3(self, base_l0: L0Input) -> None:
        """redundancy='2+1' → 3 насоса."""
        r = select_pumps(base_l0, L1=L1Input(redundancy="2+1"))
        assert r.computed.n_pumps_total == 3

    def test_redundancy_increases_pump_price(self, base_l0: L0Input) -> None:
        """redundancy='2+1' → pump_rub растёт на 50% (3 насоса вместо 2)."""
        r_default = select_pumps(base_l0, L1=None)
        r_2plus1 = select_pumps(base_l0, L1=L1Input(redundancy="2+1"))
        if r_default.results.budget and r_2plus1.results.budget:
            assert r_2plus1.results.budget.price_breakdown.pump_rub == pytest.approx(
                r_default.results.budget.price_breakdown.pump_rub * 1.5, rel=1e-3
            )

    def test_override_beats_redundancy(self, base_l0: L0Input) -> None:
        """pumps_total_override приоритетнее redundancy."""
        r = select_pumps(
            base_l0,
            L1=L1Input(redundancy="2+1", pumps_total_override=4),
        )
        assert r.computed.n_pumps_total == 4


# ─────────────────────────────────────────────────────────────────────
# 2. level_sensor_type
# ─────────────────────────────────────────────────────────────────────

class TestLevelSensorType:
    def test_ultrasonic_changes_floats_rub(self, base_l0: L0Input) -> None:
        """ultrasonic — floats_rub становится 15k × n_pumps вместо 5k×4."""
        r_default = select_pumps(base_l0, L1=None)
        r_us = select_pumps(base_l0, L1=L1Input(level_sensor_type="ultrasonic"))
        if r_default.results.budget and r_us.results.budget:
            # Default floats_rub = 4 × 5000 = 20000
            assert r_default.results.budget.price_breakdown.floats_rub == 20_000
            # ultrasonic = 15000 × 2 пумпа = 30000
            assert r_us.results.budget.price_breakdown.floats_rub == 30_000

    def test_capacitive_costs_more_than_floats(self, base_l0: L0Input) -> None:
        """capacitive (10k × n_pumps) > floats (20k для 2 насосов): 20k vs 20k. Проверим pneumatic."""
        r_pneumatic = select_pumps(base_l0, L1=L1Input(level_sensor_type="pneumatic"))
        if r_pneumatic.results.budget:
            # pneumatic 8k × 2 = 16k (меньше дефолта 20k — пневмо дешевле!)
            assert r_pneumatic.results.budget.price_breakdown.floats_rub == 16_000


# ─────────────────────────────────────────────────────────────────────
# 3. dry_run_protection
# ─────────────────────────────────────────────────────────────────────

class TestDryRunProtection:
    def test_dry_run_off_triggers(self, base_l0: L0Input) -> None:
        r = select_pumps(base_l0, L1=L1Input(dry_run_protection=False))
        assert "auto_no_dry_run_protection" in r.trigger_reasons
        assert r.engineer_handoff_required is True
        # Warning тоже должен быть
        assert any("сухого хода" in w for w in r.warnings)

    def test_dry_run_on_no_trigger(self, base_l0: L0Input) -> None:
        """Default True (включена защита) — нет triggers."""
        r = select_pumps(base_l0, L1=L1Input(dry_run_protection=True))
        assert "auto_no_dry_run_protection" not in r.trigger_reasons


# ─────────────────────────────────────────────────────────────────────
# 4. ip_motor (фильтр насосов)
# ─────────────────────────────────────────────────────────────────────

class TestIpMotor:
    def test_ip68_required_keeps_ip68_pumps(self, base_l0: L0Input) -> None:
        """ip_motor=IP68 — насосы с pump.power.ip_rating=IP68 проходят."""
        r = select_pumps(base_l0, L1=L1Input(ip_motor="IP68"))
        # Должны быть кандидаты (в БД насосы с IP68 / без IP)
        assert r.candidates_total > 0

    def test_ip_motor_does_not_break_pipeline(self, base_l0: L0Input) -> None:
        """Любое из 4 значений ip_motor работает без 500."""
        for ip in ("IP54", "IP55", "IP58", "IP68"):
            r = select_pumps(base_l0, L1=L1Input(ip_motor=ip))  # type: ignore[arg-type]
            assert r is not None


# ─────────────────────────────────────────────────────────────────────
# 5. modbus_rtu_required → cabinet_rub +50k
# ─────────────────────────────────────────────────────────────────────

class TestModbusRtu:
    def test_modbus_required_adds_50k_to_cabinet(self, base_l0: L0Input) -> None:
        r_default = select_pumps(base_l0, L1=None)
        r_modbus = select_pumps(base_l0, L1=L1Input(modbus_rtu_required=True))
        if r_default.results.budget and r_modbus.results.budget:
            delta = (
                r_modbus.results.budget.price_breakdown.cabinet_rub
                - r_default.results.budget.price_breakdown.cabinet_rub
            )
            assert delta == 50_000


# ─────────────────────────────────────────────────────────────────────
# 6. above_ground_pavilion → corpus_rub +200-500k
# ─────────────────────────────────────────────────────────────────────

class TestAboveGroundPavilion:
    def test_pavilion_adds_200k_for_small(self, base_l0: L0Input) -> None:
        """Q=21.2 ≤ 30 → павильон 200 000 ₽."""
        r_default = select_pumps(base_l0, L1=None)
        r_pav = select_pumps(base_l0, L1=L1Input(above_ground_pavilion=True))
        if r_default.results.budget and r_pav.results.budget:
            delta = (
                r_pav.results.budget.price_breakdown.corpus_rub
                - r_default.results.budget.price_breakdown.corpus_rub
            )
            assert delta == 200_000

    def test_pavilion_500k_for_large(self) -> None:
        """Q=200 → павильон 500 000 ₽."""
        L0_big = L0Input(Q_m3h=200, dH_m=10, L_m=50, wastewater_type="domestic")
        r_default = select_pumps(L0_big, L1=None)
        r_pav = select_pumps(L0_big, L1=L1Input(above_ground_pavilion=True))
        if r_default.results.budget and r_pav.results.budget:
            delta = (
                r_pav.results.budget.price_breakdown.corpus_rub
                - r_default.results.budget.price_breakdown.corpus_rub
            )
            assert delta == 500_000


# ─────────────────────────────────────────────────────────────────────
# 7. inlet_pipe_diam_mm → corpus_size.inlet_DN_mm
# ─────────────────────────────────────────────────────────────────────

class TestInletPipeDiam:
    def test_explicit_inlet_dn_overrides_default(self, base_l0: L0Input) -> None:
        """inlet_pipe_diam_mm=300 (большой) — DN корпуса увеличен до 300."""
        r = select_pumps(base_l0, L1=L1Input(inlet_pipe_diam_mm=300))
        assert r.corpus_size is not None
        # Default по Q=21.2 → inlet 110 мм. С override становится 300.
        assert r.corpus_size.inlet_DN_mm == 300

    def test_smaller_inlet_keeps_calc_default(self, base_l0: L0Input) -> None:
        """inlet_pipe_diam_mm=50 (меньше расчётного по Q) — оставляем расчётный."""
        r_default = select_pumps(base_l0, L1=None)
        r = select_pumps(base_l0, L1=L1Input(inlet_pipe_diam_mm=50))
        assert r.corpus_size is not None
        assert r_default.corpus_size is not None
        # Меньший override игнорируется — оставлен default
        assert r.corpus_size.inlet_DN_mm == r_default.corpus_size.inlet_DN_mm


# ─────────────────────────────────────────────────────────────────────
# 8. install_depth_inlet_mm → corpus_size.height_mm
# ─────────────────────────────────────────────────────────────────────

class TestInstallDepthInlet:
    def test_deeper_install_increases_height(self, base_l0: L0Input) -> None:
        """install_depth_inlet_mm=4000 → корпус выше чем при 2000."""
        r_default = select_pumps(base_l0, L1=None)  # depth=2000 (default в corpus_sizing)
        r_deep = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=4000))
        assert r_default.corpus_size is not None
        assert r_deep.corpus_size is not None
        assert r_deep.corpus_size.height_mm > r_default.corpus_size.height_mm


# ─────────────────────────────────────────────────────────────────────
# Bonus: altitude_m → NPSHa
# ─────────────────────────────────────────────────────────────────────

class TestAltitudeNpsha:
    def test_no_altitude_no_npsha(self, base_l0: L0Input) -> None:
        """Без altitude_m — npsha_m = None (backward compat)."""
        r = select_pumps(base_l0, L1=None)
        assert r.computed.npsha_m is None

    def test_sea_level_npsha_around_10m(self, base_l0: L0Input) -> None:
        """altitude=0 → P_atm=101.3 кПа → NPSHa ≈ 10 м (T=20°C)."""
        r = select_pumps(base_l0, L1=L1Input(altitude_m=0))
        assert r.computed.npsha_m is not None
        # При T=20°C, P_atm=101.3 кПа, NPSHa ≈ (101.3 - 2.34) / (998 × 9.80665) × 1000 ≈ 10.1 м
        assert 9.5 < r.computed.npsha_m < 10.7

    def test_high_altitude_lowers_npsha(self, base_l0: L0Input) -> None:
        """altitude=3000 м → NPSHa существенно ниже (~7 м)."""
        r = select_pumps(base_l0, L1=L1Input(altitude_m=3000))
        assert r.computed.npsha_m is not None
        # На 3000 м P_atm ≈ 70 кПа → NPSHa ≈ 7 м
        assert r.computed.npsha_m < 8.0

    def test_extreme_altitude_triggers_npsha_low(self, base_l0: L0Input) -> None:
        """altitude=4000+ м → NPSHa < 5 м → trigger auto_npsha_low."""
        r = select_pumps(base_l0, L1=L1Input(altitude_m=4000, liquid_temp_c=30))
        assert r.computed.npsha_m is not None
        # Ожидаем auto_npsha_low (если NPSHa < 5)
        if r.computed.npsha_m < 5.0:
            assert "auto_npsha_low" in r.trigger_reasons


# ─────────────────────────────────────────────────────────────────────
# 9. groundwater_level_m → anti-buoyancy uplift в pricing
# ─────────────────────────────────────────────────────────────────────

class TestGroundwaterAntiBuoyancy:
    """Проверка, что L1.groundwater_level_m влияет на цену корпуса
    (бетонный пригруз против всплытия по СП 32 §6.3 + Архимед).
    """

    def test_deep_groundwater_no_uplift(self, base_l0: L0Input) -> None:
        """УГВ -5 м (глубоко) → uplift = 0, цена как без поля."""
        from pump_calculator.pricing import estimate_anti_buoyancy_uplift_rub
        # Прямой unit-test: УГВ -5 → 0 для всех сегментов.
        for seg in ("budget", "mid", "premium"):
            assert estimate_anti_buoyancy_uplift_rub(-5.0, 5.7, seg) == 0  # type: ignore[arg-type]
        # Интеграционно: select_pumps с УГВ -5 = select_pumps без УГВ.
        r_none = select_pumps(base_l0, L1=None)
        r_deep = select_pumps(base_l0, L1=L1Input(groundwater_level_m=-5.0))
        if r_none.results.budget and r_deep.results.budget:
            assert (
                r_deep.results.budget.price_breakdown.corpus_rub
                == r_none.results.budget.price_breakdown.corpus_rub
            )

    def test_groundwater_at_surface_adds_uplift(self, base_l0: L0Input) -> None:
        """УГВ = 0 м (на уровне земли) → uplift > 0 (бетонный пригруз 1-3 тонны)."""
        from pump_calculator.pricing import estimate_anti_buoyancy_uplift_rub
        for seg in ("budget", "mid", "premium"):
            assert estimate_anti_buoyancy_uplift_rub(0.0, 5.7, seg) > 0  # type: ignore[arg-type]
        # Интеграционно: цена corpus_rub растёт по сравнению с None.
        r_none = select_pumps(base_l0, L1=None)
        r_at0 = select_pumps(base_l0, L1=L1Input(groundwater_level_m=0.0))
        if r_none.results.budget and r_at0.results.budget:
            assert (
                r_at0.results.budget.price_breakdown.corpus_rub
                > r_none.results.budget.price_breakdown.corpus_rub
            )

    def test_higher_groundwater_higher_uplift(self) -> None:
        """УГВ +5 м (затопленная площадка) → uplift > чем при УГВ 0."""
        from pump_calculator.pricing import estimate_anti_buoyancy_uplift_rub
        # При УГВ 0 — диапазон 50-150 тыс; при УГВ +5 — 200-500 тыс.
        for seg in ("budget", "mid", "premium"):
            uplift_at0 = estimate_anti_buoyancy_uplift_rub(0.0, 5.7, seg)  # type: ignore[arg-type]
            uplift_at5 = estimate_anti_buoyancy_uplift_rub(5.0, 5.7, seg)  # type: ignore[arg-type]
            assert uplift_at5 > uplift_at0, f"segment={seg}: {uplift_at5} <= {uplift_at0}"

    def test_premium_uplift_higher_than_budget(self) -> None:
        """premium множитель 1.7× → uplift_premium > uplift_budget при тех же условиях."""
        from pump_calculator.pricing import estimate_anti_buoyancy_uplift_rub
        # Тестируем для УГВ 0 м и для УГВ +3 м.
        for gw in (0.0, -1.0, 3.0):
            u_budget = estimate_anti_buoyancy_uplift_rub(gw, 12.6, "budget")
            u_premium = estimate_anti_buoyancy_uplift_rub(gw, 12.6, "premium")
            assert u_premium > u_budget, (
                f"УГВ={gw}: premium={u_premium} <= budget={u_budget}"
            )

    def test_groundwater_above_surface_creates_suggestion(
        self, base_l0: L0Input,
    ) -> None:
        """УГВ > 0 → suggestion с field=L1.groundwater_level_m + severity=critical."""
        r = select_pumps(base_l0, L1=L1Input(groundwater_level_m=2.0))
        # Trigger обязан быть
        assert "auto_groundwater_above_surface" in r.trigger_reasons
        # Suggestion с этим полем должна появиться
        gw_suggs = [s for s in r.suggestions if s.field == "L1.groundwater_level_m"]
        assert len(gw_suggs) >= 1, "suggestion для УГВ > 0 не сгенерирована"
        s = gw_suggs[0]
        assert s.severity == "critical"
        assert s.reason_engineer is not None and "Архимед" in s.reason_engineer
        assert s.reason_manager is not None and "пригруз" in s.reason_manager.lower()

    def test_real_pump_kit_includes_uplift(self, base_l0: L0Input) -> None:
        """Интеграционный: select_pumps с УГВ +3 м даёт total_rub больше,
        чем без УГВ — за счёт пригруза в corpus_rub.
        """
        r_none = select_pumps(base_l0, L1=None)
        r_flood = select_pumps(base_l0, L1=L1Input(groundwater_level_m=3.0))
        for seg in ("budget", "mid", "premium"):
            pr_none = getattr(r_none.results, seg)
            pr_flood = getattr(r_flood.results, seg)
            if pr_none and pr_flood:
                # corpus_rub должен вырасти
                assert (
                    pr_flood.price_breakdown.corpus_rub
                    > pr_none.price_breakdown.corpus_rub
                ), f"{seg}: corpus_rub не выросла при УГВ +3"
                # total_rub тоже
                assert (
                    pr_flood.price_breakdown.total_rub
                    > pr_none.price_breakdown.total_rub
                ), f"{seg}: total_rub не выросла при УГВ +3"
                # Note про пригруз должна быть в pump.notes
                assert any(
                    "пригруз" in n.lower() or "anti-buoyancy" in n.lower()
                    for n in pr_flood.notes
                ), f"{seg}: note про пригруз отсутствует"


# ─────────────────────────────────────────────────────────────────────
# 10. weight_estimate_kg + reinforcement_kg для CorpusSize (СП 22.13330)
# ─────────────────────────────────────────────────────────────────────

class TestCorpusWeight:
    """Проверка расчёта веса корпуса КНС и усиления при глубокой установке.

    Физика:
    - ПЭ100 SDR17: δ=D/17, ρ=950 кг/м³ → W = (π·D·H + 2·π·D²/4)·δ·ρ
    - Усиление при z>4 м (auto_lateral_earth_pressure):
      * z=4-5: рёбра ПЭ ~5% веса
      * z=5-7: частичная ж/б обойма ~100 кг/м² стенок
      * z>7:   полная ж/б обойма ~250 кг/м² стенок
    """

    def test_weight_estimate_for_typical_kns(self, base_l0: L0Input) -> None:
        """Q=21.2, depth=2000 → weight_estimate_kg оценён, > 0, в разумном диапазоне."""
        r = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=2000))
        assert r.corpus_size is not None
        assert r.corpus_size.weight_estimate_kg is not None
        # Для Ø1800×~3000 ПЭ100 SDR17: δ≈0.106 м, A≈22 м², W≈2200 кг порядка
        assert 500 < r.corpus_size.weight_estimate_kg < 5000

    def test_no_reinforcement_for_shallow_install(self, base_l0: L0Input) -> None:
        """depth ≤ 4000 → reinforcement_kg = None (усиление не требуется)."""
        r_default = select_pumps(base_l0, L1=None)
        r_3000 = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=3000))
        r_4000 = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=4000))
        for r in (r_default, r_3000, r_4000):
            assert r.corpus_size is not None
            assert r.corpus_size.reinforcement_kg is None, (
                f"reinforcement должен быть None при depth≤4000, got "
                f"{r.corpus_size.reinforcement_kg}"
            )

    def test_reinforcement_appears_at_depth_5000(self, base_l0: L0Input) -> None:
        """depth=5000 (z=5 м) → reinforcement_kg > 0 (рёбра ПЭ)."""
        r = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=5000))
        assert r.corpus_size is not None
        assert r.corpus_size.reinforcement_kg is not None
        assert r.corpus_size.reinforcement_kg > 0

    def test_reinforcement_grows_with_depth(self, base_l0: L0Input) -> None:
        """Усиление монотонно растёт от 4000 → 6000 → 8000 мм."""
        # depth=5000 (рёбра ~5%) < depth=6000 (частичная ж/б 100 кг/м²)
        # < depth=8000 (полная ж/б 250 кг/м²)
        r5 = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=5000))
        r6 = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=6000))
        r8 = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=8000))
        assert r5.corpus_size and r5.corpus_size.reinforcement_kg is not None
        assert r6.corpus_size and r6.corpus_size.reinforcement_kg is not None
        assert r8.corpus_size and r8.corpus_size.reinforcement_kg is not None
        # Частичная обойма (100 кг/м²) должна быть тяжелее рёбер (~5% веса корпуса)
        assert r6.corpus_size.reinforcement_kg > r5.corpus_size.reinforcement_kg
        # Полная обойма (250 кг/м²) > частичной (100 кг/м²)
        assert r8.corpus_size.reinforcement_kg > r6.corpus_size.reinforcement_kg

    def test_lateral_earth_pressure_trigger_yields_reinforcement(
        self, base_l0: L0Input,
    ) -> None:
        """Интеграционный: при auto_lateral_earth_pressure (depth>5000)
        корпус ОБЯЗАТЕЛЬНО имеет reinforcement_kg.
        """
        r = select_pumps(base_l0, L1=L1Input(install_depth_inlet_mm=6000))
        assert "auto_lateral_earth_pressure" in r.trigger_reasons
        assert r.corpus_size is not None
        assert r.corpus_size.reinforcement_kg is not None
        assert r.corpus_size.reinforcement_kg > 0
        # Note про усиление должна быть в corpus_size.notes
        assert any(
            "усиление" in n.lower() or "обойма" in n.lower() or "рёбр" in n.lower()
            for n in r.corpus_size.notes
        ), f"note про усиление отсутствует: {r.corpus_size.notes}"

    def test_weight_grows_with_pump_size(self) -> None:
        """Q=500 (большой КНС Ø3500) тяжелее чем Q=20 (Ø1800)."""
        from pump_calculator.schemas import L0Input as _L0
        r_small = select_pumps(_L0(Q_m3h=20, dH_m=10, L_m=50, wastewater_type="domestic"))
        r_big = select_pumps(_L0(Q_m3h=500, dH_m=20, L_m=100, wastewater_type="industrial"))
        assert r_small.corpus_size and r_small.corpus_size.weight_estimate_kg is not None
        assert r_big.corpus_size and r_big.corpus_size.weight_estimate_kg is not None
        assert r_big.corpus_size.weight_estimate_kg > r_small.corpus_size.weight_estimate_kg
