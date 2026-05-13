"""EXT-15 P_removal — Metcalf & Eddy §8-3.

Phase 34+ (2026-05-13): P2 биология. Закрывает PhD-Biology backlog по
удалению фосфора. Связан с EXT-9/EXT-16 (общий приёмник target_discharge).
"""
from __future__ import annotations

import pytest

from pump_calculator.los.phosphorus import (
    P_LIMITS_BY_DISCHARGE,
    al2so4_3_dose_mg_per_mg_p_removed,
    calculate_p_removal,
    fecl3_dose_mg_per_mg_p_removed,
    get_p_default,
    get_p_limit,
)
from pump_calculator.matching import _check_ext_15_phosphorus, select_pumps
from pump_calculator.schemas import L0Input, L1Input


class TestStoichiometry:
    def test_fecl3_dose_approx_785(self):
        """1.5 моль Fe / 1 моль P × 162.2/30.97 ≈ 7.85 мг FeCl3 / мг P."""
        dose = fecl3_dose_mg_per_mg_p_removed()
        assert dose == pytest.approx(7.85, abs=0.05)

    def test_al2so4_3_dose_in_expected_range(self):
        """Al2(SO4)3: 0.75 моль соли на 1 моль P × 342.15 / 30.97."""
        dose = al2so4_3_dose_mg_per_mg_p_removed()
        assert dose == pytest.approx(8.28, abs=0.1)


class TestPLimits:
    def test_fishery_water_strict_005(self):
        assert get_p_limit("fishery_water") == 0.05

    def test_general_use_02(self):
        assert get_p_limit("general_use") == 0.2

    def test_municipal_sewage_lenient(self):
        assert get_p_limit("municipal_sewage") == 5.0

    def test_default_general_use_when_none(self):
        assert get_p_limit(None) == 0.2

    def test_all_limits_in_table(self):
        for k in ("fishery_water", "general_use", "reuse_irrigation", "municipal_sewage"):
            assert k in P_LIMITS_BY_DISCHARGE


class TestPDefaults:
    def test_domestic_default_8(self):
        assert get_p_default("domestic") == 8.0

    def test_industrial_default_20(self):
        assert get_p_default("industrial") == 20.0


class TestCalculatePRemoval:
    def test_not_needed_when_below_target(self):
        r = calculate_p_removal(p_in_mgL=0.1, target_p_mgL=0.2)
        assert r["needed"] is False
        assert r["dose_mg_per_L"] == 0.0

    def test_fecl3_dose_for_domestic_fishery(self):
        """P_in=8, target=0.05 (рыбхоз) → ΔP=7.95, FeCl3 ≈ 62.4 мг/л."""
        r = calculate_p_removal(p_in_mgL=8.0, target_p_mgL=0.05, method="fecl3")
        assert r["needed"] is True
        assert r["method"] == "fecl3"
        assert r["p_remove_mgL"] == pytest.approx(7.95, abs=0.01)
        # 7.95 × 7.85 ≈ 62.4
        assert r["dose_mg_per_L"] == pytest.approx(62.4, abs=0.5)

    def test_ebpr_returns_zero_dose(self):
        r = calculate_p_removal(p_in_mgL=8.0, target_p_mgL=0.2, method="ebpr")
        assert r["needed"] is True
        assert r["method"] == "ebpr"
        assert r["dose_mg_per_L"] == 0.0

    def test_yearly_dose_calculation(self):
        """Q=10 м³/ч, P=8→0.2, FeCl3 ≈ 61.2 мг/л → ~5.36 кг/год.

        61.2 мг/л × 10 м³/ч × 24 × 365 = 5_361_120 мг = 5.36 кг
        (для тонн нужен Q≥1000 м³/ч либо очень высокие дозы)."""
        r = calculate_p_removal(
            p_in_mgL=8.0, target_p_mgL=0.2, method="fecl3", Q_m3_h=10.0
        )
        assert r["yearly_dose_kg_per_year"] == pytest.approx(5.36, rel=0.05)

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError):
            calculate_p_removal(p_in_mgL=8.0, target_p_mgL=0.2, method="unknown")


class TestExt15Trigger:
    def test_trigger_domestic_fishery(self):
        """Бытовые Q=100, default P=8, target=рыбхоз (0.05) → trigger."""
        L0 = L0Input(Q_m3h=100, wastewater_type="domestic")
        L1 = L1Input(target_discharge="fishery_water")
        result = _check_ext_15_phosphorus(L0, L1)
        assert result is not None
        assert result["needed"] is True
        assert result["method"] == "fecl3"

    def test_no_trigger_municipal_sewage(self):
        """target=муниципалка (ПДК 5 мг/л) — P_in=8 не должен срабатывать
        (правило: для гор. канализации EXT-15 отключён)."""
        L0 = L0Input(Q_m3h=100, wastewater_type="domestic")
        L1 = L1Input(target_discharge="municipal_sewage")
        result = _check_ext_15_phosphorus(L0, L1)
        assert result is None

    def test_no_trigger_small_q(self):
        """Q=30 м³/ч < 50 → не срабатывает (экономически невыгодно)."""
        L0 = L0Input(Q_m3h=30, wastewater_type="domestic")
        L1 = L1Input(target_discharge="fishery_water")
        assert _check_ext_15_phosphorus(L0, L1) is None

    def test_no_trigger_heavy_metals(self):
        L0 = L0Input(Q_m3h=100, wastewater_type="industrial")
        L1 = L1Input(target_discharge="fishery_water", heavy_metals_present=True)
        assert _check_ext_15_phosphorus(L0, L1) is None

    def test_no_trigger_ex_required(self):
        L0 = L0Input(Q_m3h=100, wastewater_type="industrial")
        L1 = L1Input(target_discharge="fishery_water", Ex_required=True)
        assert _check_ext_15_phosphorus(L0, L1) is None

    def test_integration_select_pumps_triggers_p_removal(self):
        """E2E: select_pumps должен добавить auto_phosphorus_removal."""
        L0 = L0Input(Q_m3h=100, wastewater_type="domestic")
        L1 = L1Input(target_discharge="fishery_water")
        r = select_pumps(L0, L1)
        assert "auto_phosphorus_removal" in r.trigger_reasons
