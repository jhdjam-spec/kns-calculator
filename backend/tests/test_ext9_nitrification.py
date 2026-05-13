"""EXT-9 nitrification trigger — точные параметры Monod / Henze IWA 2008 §3.4.

Phase 34+ (2026-05-13): после PhD-Biology audit + Sc.D. cross-domain.
Старая v0.3 срабатывала на любые industrial-стоки → false-positive для
гальваники (Cr⁶⁺ убивает биоту), АЗС (БПК недостаточно), холодных стоков <10°C.

Новый триггер требует AND:
  NH4_in > 20 мг/л
  AND C:N = BOD5/NH4 > 3
  AND 12°C ≤ T ≤ 35°C
  AND not heavy_metals_present
  AND not Ex_required
  AND NH4_in > ПДК(target_discharge)

ПДК NH4:
  fishery_water   = 0.4 мг/л (МУК 4.3.2030-05 + Приказ Росрыболовства №20)
  general_use     = 2.0 мг/л (СанПиН 2.1.5.980-00)
  reuse_irrigation= 10.0 мг/л (СанПиН СЭ 6.04.001)
  municipal_sewage= 40.0 мг/л (городская канализация)
"""
from __future__ import annotations

import pytest

from pump_calculator.matching import (
    _check_ext_9_nitrification,
    _ext_8_uv_dose_required,
    select_pumps,
)
from pump_calculator.schemas import L0Input, L1Input  # noqa: I001

# ---------------------------------------------------------------------------
# Unit-тесты helper-функции
# ---------------------------------------------------------------------------

class TestExt9HelperFunction:
    """Прямые вызовы _check_ext_9_nitrification без полного select_pumps."""

    def test_no_trigger_for_low_nh4(self):
        """NH4=10 мг/л < 20 → нитрификация не нужна (Henze IWA)."""
        L0 = L0Input(Q_m3h=50, wastewater_type="domestic")
        L1 = L1Input(nh4_in_mgL=10.0, bod5_in_mgL=250.0, liquid_temp_c=20.0)
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None

    def test_trigger_domestic_default_nh4_25(self):
        """Бытовые с default NH4=25 → нитрификация нужна (NH4 > 40? нет → но муниц 40)."""
        # Default бытовых nh4=25, bod5=250, C:N=10, T=20, target=municipal limit=40
        # 25 < 40 → нитрификация НЕ нужна для default бытовых в муниципалку.
        # Это правильно: бытовые стоки в гор. канализацию проходят без ЛОС.
        L0 = L0Input(Q_m3h=50, wastewater_type="domestic")
        L1 = L1Input()
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None  # 25 <= 40 (municipal_sewage)

    def test_trigger_domestic_high_nh4_with_general_target(self):
        """Бытовые NH4=50 + target=general_use (limit 2.0) → trigger."""
        L0 = L0Input(Q_m3h=50, wastewater_type="domestic")
        L1 = L1Input(nh4_in_mgL=50.0, target_discharge="general_use")
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is not None
        assert result["nh4"] == 50.0
        assert result["nh4_limit"] == 2.0
        assert result["target"] == "general_use"
        assert result["c_to_n"] == pytest.approx(5.0, abs=0.01)  # 250/50

    def test_no_trigger_heavy_metals(self):
        """Гальваника heavy_metals=True → биология не работает."""
        L0 = L0Input(Q_m3h=30, wastewater_type="industrial")
        L1 = L1Input(
            nh4_in_mgL=200.0,
            bod5_in_mgL=1000.0,
            heavy_metals_present=True,
            liquid_temp_c=20.0,
        )
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None  # Cr/Cd/Pb убивают активный ил

    def test_no_trigger_cold_temp(self):
        """T=8°C < 12 → нитрификаторы не работают."""
        L0 = L0Input(Q_m3h=50, wastewater_type="industrial")
        L1 = L1Input(nh4_in_mgL=100.0, bod5_in_mgL=500.0, liquid_temp_c=8.0)
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None

    def test_no_trigger_hot_temp(self):
        """T=40°C > 35 → нитрификаторы гибнут."""
        L0 = L0Input(Q_m3h=50, wastewater_type="industrial")
        L1 = L1Input(nh4_in_mgL=100.0, bod5_in_mgL=500.0, liquid_temp_c=40.0)
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None

    def test_no_trigger_low_cn_ratio(self):
        """BOD5=40 NH4=25 → C:N=1.6 < 3 — мало углерода для гетеротрофов."""
        L0 = L0Input(Q_m3h=50, wastewater_type="industrial")
        L1 = L1Input(
            nh4_in_mgL=25.0,
            bod5_in_mgL=40.0,
            liquid_temp_c=20.0,
            target_discharge="general_use",
        )
        # nh4=25 > 20 (порог), но C:N = 40/25 = 1.6 < 3 → нитрификация без углерода нерабочая
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None

    def test_no_trigger_ex_required(self):
        """Ex_required=True (АЗС/нефтехимия) → биология не подходит."""
        L0 = L0Input(Q_m3h=50, wastewater_type="industrial")
        L1 = L1Input(
            nh4_in_mgL=200.0,
            bod5_in_mgL=1000.0,
            liquid_temp_c=20.0,
            Ex_required=True,
        )
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is None

    def test_fishery_water_strict_limit(self):
        """target=fishery_water (limit 0.4) — NH4=25 default срабатывает."""
        L0 = L0Input(Q_m3h=50, wastewater_type="domestic")
        L1 = L1Input(target_discharge="fishery_water")
        # Default nh4=25, bod5=250 → C:N=10, T=20, limit=0.4
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is not None
        assert result["nh4"] == 25.0
        assert result["nh4_limit"] == 0.4
        assert result["target"] == "fishery_water"

    def test_srt_correction_at_low_temp(self):
        """T=12°C → SRT_min = 15·1.103^3 ≈ 20 сут (Arrhenius θ=1.103)."""
        L0 = L0Input(Q_m3h=50, wastewater_type="industrial")
        L1 = L1Input(
            nh4_in_mgL=100.0,
            bod5_in_mgL=500.0,
            liquid_temp_c=12.0,
            target_discharge="general_use",
        )
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is not None
        # SRT_min = 15 * 1.103^(15-12) = 15 * 1.342 ≈ 20.1 сут
        assert result["srt_min_d"] == pytest.approx(20.13, abs=0.5)
        assert result["srt_min_d"] > 19.0

    def test_srt_correction_at_high_temp(self):
        """T=25°C → SRT_min = 15·1.103^(-10) ≈ 5.8 сут (нижний край)."""
        L0 = L0Input(Q_m3h=50, wastewater_type="industrial")
        L1 = L1Input(
            nh4_in_mgL=100.0,
            bod5_in_mgL=500.0,
            liquid_temp_c=25.0,
            target_discharge="general_use",
        )
        result = _check_ext_9_nitrification(L0, L1, None)
        assert result is not None
        # SRT_min = 15 * 1.103^(15-25) = 15 / 1.103^10 ≈ 5.77 сут
        assert result["srt_min_d"] < 6.5
        assert result["srt_min_d"] > 5.0


# ---------------------------------------------------------------------------
# Интеграционные тесты через select_pumps()
# ---------------------------------------------------------------------------

class TestExt9Integration:
    """Полный pipeline select_pumps + проверка trigger_reasons / suggestions."""

    @staticmethod
    def _suggestion(result, field_substr: str):
        """Найти InputSuggestion по подстроке в field."""
        for s in result.suggestions:
            if field_substr in s.field:
                return s
        return None

    def test_industrial_default_q80_triggers(self):
        """Industrial Q=80 (PhD scenario): default NH4=100, C:N=5, T=20 → trigger."""
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        r = select_pumps(L0)
        assert "auto_nitrification_check" in r.trigger_reasons
        s = self._suggestion(r, "nitrification_required")
        assert s is not None
        assert "Monod" in s.reason_engineer
        assert "Henze" in s.reason_engineer or "henze" in s.reason_engineer.lower()

    def test_galvanic_heavy_metals_no_trigger(self):
        """Гальваника heavy_metals → НЕ срабатывает (PhD P0)."""
        L0 = L0Input(Q_m3h=30, wastewater_type="industrial")
        L1 = L1Input(heavy_metals_present=True, nh4_in_mgL=200.0)
        r = select_pumps(L0, L1)
        assert "auto_nitrification_check" not in r.trigger_reasons

    def test_azs_ex_required_no_trigger(self):
        """АЗС Ex_required → НЕ срабатывает."""
        L0 = L0Input(Q_m3h=30, wastewater_type="industrial")
        L1 = L1Input(Ex_required=True, nh4_in_mgL=200.0)
        r = select_pumps(L0, L1)
        assert "auto_nitrification_check" not in r.trigger_reasons

    def test_cold_industrial_no_trigger(self):
        """Холодные промстоки T=8°C → НЕ срабатывает (k_AOB → 0)."""
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        L1 = L1Input(liquid_temp_c=8.0)
        r = select_pumps(L0, L1)
        assert "auto_nitrification_check" not in r.trigger_reasons

    def test_fishery_water_domestic_triggers(self):
        """Бытовые в рыбохозяйственный (limit 0.4) → trigger даже на default NH4=25."""
        L0 = L0Input(Q_m3h=50, wastewater_type="domestic")
        L1 = L1Input(target_discharge="fishery_water")
        r = select_pumps(L0, L1)
        assert "auto_nitrification_check" in r.trigger_reasons
        s = self._suggestion(r, "nitrification_required")
        assert s is not None
        assert "fishery_water" in s.reason_engineer
        assert "0.4" in s.reason_engineer

    def test_municipal_sewage_default_domestic_no_trigger(self):
        """Бытовые в гор. канализацию default → НЕ срабатывает (25 < 40)."""
        L0 = L0Input(Q_m3h=50, wastewater_type="domestic")
        L1 = L1Input()  # target=None → municipal_sewage default
        r = select_pumps(L0, L1)
        assert "auto_nitrification_check" not in r.trigger_reasons

    def test_clean_water_no_trigger(self):
        """clean_water (ВНС) → НЕ срабатывает (биология не нужна)."""
        L0 = L0Input(Q_m3h=80, wastewater_type="clean_water")
        L1 = L1Input(nh4_in_mgL=200.0)
        r = select_pumps(L0, L1)
        assert "auto_nitrification_check" not in r.trigger_reasons


# ---------------------------------------------------------------------------
# EXT-8 UV-доза по target_discharge
# ---------------------------------------------------------------------------

class TestExt8UvDose:
    """UV-доза дифференцирована по target_discharge."""

    def test_default_municipal_sewage_25(self):
        dose, target = _ext_8_uv_dose_required(None)
        assert dose == 25
        assert target == "municipal_sewage"

    def test_fishery_water_100(self):
        L1 = L1Input(target_discharge="fishery_water")
        dose, target = _ext_8_uv_dose_required(L1)
        assert dose == 100
        assert target == "fishery_water"

    def test_general_use_30(self):
        L1 = L1Input(target_discharge="general_use")
        dose, target = _ext_8_uv_dose_required(L1)
        assert dose == 30
        assert target == "general_use"

    def test_reuse_irrigation_60(self):
        L1 = L1Input(target_discharge="reuse_irrigation")
        dose, target = _ext_8_uv_dose_required(L1)
        assert dose == 60

    def test_fishery_water_in_suggestion_engineer(self):
        """E2E: sba target_discharge=fishery_water → reason содержит 100 мДж/см²."""
        L0 = L0Input(Q_m3h=150, wastewater_type="domestic")
        L1 = L1Input(target_discharge="fishery_water")
        r = select_pumps(L0, L1)
        assert "auto_disinfection_required" in r.trigger_reasons
        # Найти EXT-8 suggestion
        for s in r.suggestions:
            if "disinfection" in s.field:
                assert "100 мДж/см²" in s.reason_engineer
                assert "fishery_water" in s.reason_engineer
                break
        else:
            pytest.fail("EXT-8 suggestion not found")
