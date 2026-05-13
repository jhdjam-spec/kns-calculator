"""EXT-16 денитрификация — Henze IWA §3.5 + Metcalf & Eddy §8-7.

Phase 34+ (2026-05-13): P2 биология. Срабатывает после EXT-9 (нитрификация).
"""
from __future__ import annotations

import pytest

from pump_calculator.los.denitrification import (
    NO3_LIMITS_BY_DISCHARGE,
    calculate_denitrification,
    get_no3_limit,
)
from pump_calculator.matching import (
    _check_ext_16_denitrification,
    select_pumps,
)
from pump_calculator.schemas import L0Input, L1Input


class TestNo3Limits:
    def test_fishery_water_40(self):
        assert get_no3_limit("fishery_water") == 40.0

    def test_general_use_45(self):
        assert get_no3_limit("general_use") == 45.0

    def test_municipal_sewage_80(self):
        assert get_no3_limit("municipal_sewage") == 80.0

    def test_default_general_use(self):
        assert get_no3_limit(None) == 45.0

    def test_all_targets_in_table(self):
        for k in ("fishery_water", "general_use", "reuse_irrigation", "municipal_sewage"):
            assert k in NO3_LIMITS_BY_DISCHARGE


class TestCalculateDenitrification:
    def test_not_needed_below_limit(self):
        r = calculate_denitrification(
            no3_in_mgL=20.0, target="fishery_water", bod5_in_mgL=200, T_c=20
        )
        assert r["needed"] is False

    def test_high_no3_fishery_triggers(self):
        """NO3=100 > рыбхоз 40 → денитрификация нужна."""
        r = calculate_denitrification(
            no3_in_mgL=100.0, target="fishery_water", bod5_in_mgL=500, T_c=20
        )
        assert r["needed"] is True
        assert r["no3_target_mgL"] == 40.0
        assert r["no3_remove_mgL"] == 60.0
        # C:N = 500/100 = 5 ≥ 4 → метанол не нужен
        assert r["methanol_needed"] is False

    def test_low_cn_ratio_requires_methanol(self):
        """C:N = 100/100 = 1.0 < 4 → дозировать метанол."""
        r = calculate_denitrification(
            no3_in_mgL=100.0, target="fishery_water", bod5_in_mgL=100, T_c=20
        )
        assert r["needed"] is True
        assert r["cn_ratio"] == 1.0
        assert r["methanol_needed"] is True
        # ΔN=60, dose = 60 × 2.47 ≈ 148.2 мг/л
        assert r["methanol_dose_mgL"] == pytest.approx(148.2, abs=0.5)

    def test_recycle_ratio_capped_at_400(self):
        """NO3=1000, limit=40 → recycle=2400% но cap 400%."""
        r = calculate_denitrification(
            no3_in_mgL=1000.0, target="fishery_water", bod5_in_mgL=5000, T_c=20
        )
        assert r["recycle_ratio_pct"] == 400.0

    def test_T_correction_arrhenius(self):
        """θ=1.07: при T=10°C k = 1.07^(-10) ≈ 0.508."""
        r = calculate_denitrification(
            no3_in_mgL=100, target="general_use", bod5_in_mgL=500, T_c=10
        )
        assert r["T_correction"] == pytest.approx(1.07 ** -10, abs=0.01)
        assert r["T_correction"] < 0.6

    def test_no3_target_override(self):
        """Явно заданный no3_target_override перекрывает таблицу."""
        r = calculate_denitrification(
            no3_in_mgL=100, target="municipal_sewage",
            bod5_in_mgL=500, T_c=20, no3_target_override=25.0,
        )
        assert r["needed"] is True
        assert r["no3_target_mgL"] == 25.0


class TestExt16Trigger:
    def test_no_trigger_without_ext9(self):
        """Без нитрификации (heavy_metals) денитрификация невозможна."""
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        L1 = L1Input(heavy_metals_present=True, target_discharge="fishery_water")
        assert _check_ext_16_denitrification(L0, L1, None) is None

    def test_trigger_after_nitrification_fishery(self):
        """Industrial NH4 default=100, target=рыбхоз 40 → DN нужна."""
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        L1 = L1Input(target_discharge="fishery_water")
        r = _check_ext_16_denitrification(L0, L1, None)
        assert r is not None
        assert r["needed"] is True
        assert r["no3_target_mgL"] == 40.0

    def test_no_trigger_municipal_sewage(self):
        """Industrial NH4=100, target=муниц (limit 80) → ΔN=20, нужна DN.
        Но EXT-9 для муниц-сток с NH4=100 default тоже сработает."""
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        L1 = L1Input(target_discharge="municipal_sewage")
        r = _check_ext_16_denitrification(L0, L1, None)
        # NH4=100 > 80 → trigger, EXT-9 тоже да т.к. NH4>40
        assert r is not None

    def test_integration_select_pumps_triggers_denitri(self):
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        L1 = L1Input(target_discharge="fishery_water")
        r = select_pumps(L0, L1)
        # EXT-9 должен сработать (NH4 default 100, рыбхоз limit 0.4)
        assert "auto_nitrification_check" in r.trigger_reasons
        # EXT-16 должен следовать
        assert "auto_denitrification_required" in r.trigger_reasons
