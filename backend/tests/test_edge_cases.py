"""Edge-case тесты: что калькулятор делает с заведомо неправильными или
аномальными входными данными.

Ожидаем:
- Pydantic validation отбивает out-of-range (Q≤0, Q>10000, dH<-50, и т.д.)
- Приёмлемые но аномальные значения (Q<0.1, dH<0, Q>500) генерируют
  trigger_reasons + warning + engineer_handoff_required=True
- Никаких 500-ошибок и тихих "слишком большой насос" без предупреждения
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input, L1Input


class TestPydanticRejection:
    """Pydantic должен отбивать невалидные значения на входе."""

    def test_zero_q_rejected(self):
        with pytest.raises(ValidationError) as exc:
            L0Input(Q_m3h=0)
        assert "greater than 0" in str(exc.value)

    def test_negative_q_rejected(self):
        with pytest.raises(ValidationError):
            L0Input(Q_m3h=-10)

    def test_q_above_limit_rejected(self):
        with pytest.raises(ValidationError) as exc:
            L0Input(Q_m3h=10001)
        assert "less than or equal to 10000" in str(exc.value)

    def test_dh_below_minus_50_rejected(self):
        with pytest.raises(ValidationError):
            L0Input(Q_m3h=10, dH_m=-100)

    def test_dh_above_200_rejected(self):
        with pytest.raises(ValidationError):
            L0Input(Q_m3h=10, dH_m=300)

    def test_l_negative_rejected(self):
        with pytest.raises(ValidationError):
            L0Input(Q_m3h=10, L_m=-1)

    def test_l_above_5000_rejected(self):
        with pytest.raises(ValidationError):
            L0Input(Q_m3h=10, L_m=10000)

    def test_invalid_wastewater_rejected(self):
        with pytest.raises(ValidationError):
            L0Input(Q_m3h=10, wastewater_type="invalid_type")


class TestMicroQHandoff:
    """Q < 0.1 м³/ч (микро) → trigger auto_q_micro + warning + handoff."""

    def test_micro_q_001(self):
        """Q=0.01 (10 мл/час) — pydantic валидно, но логически абсурдно."""
        L0 = L0Input(Q_m3h=0.01)
        r = select_pumps(L0)
        assert "auto_q_micro" in r.trigger_reasons
        assert r.engineer_handoff_required is True
        # Warning должен начинаться с ⚠
        micro_warnings = [w for w in r.warnings if "нереалистично малый" in w]
        assert len(micro_warnings) > 0, "Ожидался warning о микро-Q"

    def test_micro_q_05(self):
        """Q=0.05 — на грани, тоже triggers."""
        L0 = L0Input(Q_m3h=0.05)
        r = select_pumps(L0)
        assert "auto_q_micro" in r.trigger_reasons

    def test_q_01_boundary_no_trigger(self):
        """Q=0.1 — граница, не должно срабатывать."""
        L0 = L0Input(Q_m3h=0.1)
        r = select_pumps(L0)
        assert "auto_q_micro" not in r.trigger_reasons

    def test_q_05_normal_household(self):
        """Q=0.5 (типичный коттедж) — никаких triggers."""
        L0 = L0Input(Q_m3h=0.5)
        r = select_pumps(L0)
        assert "auto_q_micro" not in r.trigger_reasons


class TestNegativeDH:
    """dH < 0 (точка сброса ниже точки забора) → trigger auto_dh_negative."""

    def test_dh_minus_30(self):
        """dH=-30 при L=10 → H_full<=0 → short-circuit с auto_no_head_required + auto_dh_negative."""
        L0 = L0Input(Q_m3h=10, dH_m=-30, L_m=10)
        r = select_pumps(L0)
        # При коротком L и большом отрицательном dH сработает short-circuit
        assert "auto_dh_negative" in r.trigger_reasons or "auto_no_head_required" in r.trigger_reasons
        assert r.engineer_handoff_required is True
        # Warning должен быть либо negative-dh либо no_head_required
        related_warnings = [
            w for w in r.warnings
            if "отрицательный" in w or "не нужен" in w or "≤ 0" in w
        ]
        assert len(related_warnings) > 0

    def test_dh_minus_50_boundary(self):
        L0 = L0Input(Q_m3h=10, dH_m=-50)
        r = select_pumps(L0)
        assert "auto_dh_negative" in r.trigger_reasons

    def test_dh_zero_no_trigger(self):
        L0 = L0Input(Q_m3h=10, dH_m=0)
        r = select_pumps(L0)
        assert "auto_dh_negative" not in r.trigger_reasons

    def test_dh_positive_no_trigger(self):
        L0 = L0Input(Q_m3h=10, dH_m=10)
        r = select_pumps(L0)
        assert "auto_dh_negative" not in r.trigger_reasons


class TestHighQ:
    """Q > 500 м³/ч → auto_q_high + handoff."""

    def test_q_500_boundary(self):
        L0 = L0Input(Q_m3h=500)
        r = select_pumps(L0)
        # 500 — не выше 500
        assert "auto_q_high" not in r.trigger_reasons

    def test_q_501_triggers(self):
        L0 = L0Input(Q_m3h=501)
        r = select_pumps(L0)
        assert "auto_q_high" in r.trigger_reasons

    def test_q_5000_triggers_and_warns(self):
        L0 = L0Input(Q_m3h=5000)
        r = select_pumps(L0)
        assert "auto_q_high" in r.trigger_reasons
        high_warnings = [w for w in r.warnings if "превышает 500" in w]
        assert len(high_warnings) > 0

    def test_q_10000_no_match_handoff(self):
        """Q=10000 — за пределами всех насосов в БД, должен быть auto_no_match."""
        L0 = L0Input(Q_m3h=10000)
        r = select_pumps(L0)
        assert "auto_no_match" in r.trigger_reasons
        assert r.engineer_handoff_required is True


class TestExtremeH:
    """H_full > 80 → auto_h_high."""

    def test_huge_dh_triggers(self):
        L0 = L0Input(Q_m3h=20, dH_m=200)
        r = select_pumps(L0)
        assert "auto_h_high" in r.trigger_reasons


class TestNoMatchScenarios:
    """Когда в БД нет ни одного подходящего насоса — auto_no_match."""

    def test_huge_q_huge_h_no_match(self):
        L0 = L0Input(Q_m3h=10000, dH_m=200)
        r = select_pumps(L0)
        # 10000 м³/ч + 200 м напора — за пределами всех насосов
        assert r.candidates_total == 0
        assert "auto_no_match" in r.trigger_reasons
        assert r.engineer_handoff_required is True
        # Все 3 сегмента должны быть None с warnings
        assert r.results.budget is None
        assert r.results.mid is None
        assert r.results.premium is None


class TestFireProtection:
    """fire_protection как тип стоков — auto_fire_protection + handoff."""

    def test_fire_triggers_handoff(self):
        L0 = L0Input(Q_m3h=20, wastewater_type="fire_protection")
        r = select_pumps(L0)
        assert "auto_fire_protection" in r.trigger_reasons
        assert r.engineer_handoff_required is True


class TestSuggestionsAPI:
    """«Возможно вы имели в виду...» — мягкие предложения исправить вход."""

    def test_q_micro_suggests_unit_confusion(self):
        """Q=0.05 → suggestion 'возможно л/мин или л/с'."""
        L0 = L0Input(Q_m3h=0.05)
        r = select_pumps(L0)
        assert len(r.suggestions) > 0
        q_sugg = [s for s in r.suggestions if s.field == "Q_m3h"]
        assert len(q_sugg) == 1
        assert q_sugg[0].severity == "critical"
        assert "л/мин" in q_sugg[0].reason or "л/с" in q_sugg[0].reason

    def test_dh_negative_suggests_sign_flip(self):
        """dH=-30 → suggestion 'возможно +30'."""
        L0 = L0Input(Q_m3h=20, dH_m=-30)
        r = select_pumps(L0)
        dh_sugg = [s for s in r.suggestions if s.field == "dH_m"]
        assert len(dh_sugg) == 1
        assert dh_sugg[0].suggested_value == "30.0"
        assert dh_sugg[0].severity == "critical"

    def test_huge_pipe_d_suggests_smaller(self):
        """pipe_D_mm=500 для Q=10 → suggestion smaller D."""
        L0 = L0Input(Q_m3h=10)
        L1 = L1Input(pipe_D_mm=500)
        r = select_pumps(L0, L1)
        d_sugg = [s for s in r.suggestions if s.field == "L1.pipe_D_mm"]
        assert len(d_sugg) == 1
        # Suggested value должно быть стандартный DN (50/65/80/100/...)
        suggested_dn = int(d_sugg[0].suggested_value)
        assert suggested_dn in {50, 65, 80, 100, 125, 150, 200, 250, 300}

    def test_pe100_hot_suggests_steel(self):
        """PE100 + 80°C → suggest steel_seamless_new."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(pipe_material="pe100_sdr17", liquid_temp_c=80)
        r = select_pumps(L0, L1)
        mat_sugg = [s for s in r.suggestions if s.field == "L1.pipe_material"]
        assert len(mat_sugg) == 1
        assert mat_sugg[0].suggested_value == "steel_seamless_new"
        assert mat_sugg[0].severity == "critical"

    def test_inflow_exceeds_suggests_higher_q(self):
        """inflow=200 для Q=20 → suggest Q=240."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(inflow_per_hour_m3=200)
        r = select_pumps(L0, L1)
        q_sugg = [s for s in r.suggestions if s.field == "Q_m3h"]
        assert len(q_sugg) == 1
        # Suggested = 200 * 1.2 = 240 (с запасом)
        assert q_sugg[0].suggested_value == "240.0"
        assert q_sugg[0].severity == "critical"

    def test_normal_input_no_suggestions(self):
        """Нормальный ввод не должен генерировать suggestions."""
        L0 = L0Input(Q_m3h=20, dH_m=10, L_m=100, wastewater_type="domestic")
        r = select_pumps(L0)
        assert len(r.suggestions) == 0


class TestSuggestionsDeepReasons:
    """Reasons в suggestions содержат физическое/гидравлическое обоснование."""

    def test_q_micro_reason_includes_units_and_norm(self):
        """Q-suggestion упоминает СНиП норму ≥ 0.5 и единицы л/мин/л/с."""
        L0 = L0Input(Q_m3h=0.05)
        r = select_pumps(L0)
        q_sugg = [s for s in r.suggestions if s.field == "Q_m3h"][0]
        assert "л/мин" in q_sugg.reason
        assert "л/с" in q_sugg.reason
        assert "СНиП" in q_sugg.reason or "0.5" in q_sugg.reason

    def test_dh_negative_reason_includes_bernoulli(self):
        """dH-suggestion упоминает уравнение Бернулли + СП 32."""
        L0 = L0Input(Q_m3h=20, dH_m=-30)
        r = select_pumps(L0)
        dh_sugg = [s for s in r.suggestions if s.field == "dH_m"][0]
        assert "Бернулли" in dh_sugg.reason
        assert "z₁" in dh_sugg.reason or "z₂" in dh_sugg.reason

    def test_velocity_high_reason_includes_zhukovsky(self):
        """Скорость > 3 м/с → reason содержит расчёт Жуковского + давление."""
        L0 = L0Input(Q_m3h=10)
        L1 = L1Input(pipe_D_mm=20)
        r = select_pumps(L0, L1)
        d_sugg = [s for s in r.suggestions if s.field == "L1.pipe_D_mm"][0]
        assert "Жуковский" in d_sugg.reason
        assert "Δp" in d_sugg.reason or "бар" in d_sugg.reason

    def test_pe100_hot_reason_includes_arrhenius(self):
        """PE100 + горячая → reason содержит закон Аррениуса (ползучесть)."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(pipe_material="pe100_sdr17", liquid_temp_c=80)
        r = select_pumps(L0, L1)
        mat_sugg = [s for s in r.suggestions if s.field == "L1.pipe_material"][0]
        assert "Аррениус" in mat_sugg.reason
        assert "ползучесть" in mat_sugg.reason or "50 лет" in mat_sugg.reason

    def test_inflow_exceeds_reason_includes_mass_balance(self):
        """Inflow > Q → reason содержит закон сохранения массы dV/dt."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(inflow_per_hour_m3=200)
        r = select_pumps(L0, L1)
        q_sugg = [s for s in r.suggestions if s.field == "Q_m3h"][0]
        assert "масс" in q_sugg.reason
        assert "dV/dt" in q_sugg.reason


class TestNBendsActivation:
    """n_bends/n_valves в L1 теперь влияют на расчёт sum_zeta (раньше игнорировалось)."""

    def test_zero_bends_uses_typical(self):
        """Без n_bends — fallback на typical_obvyazka."""
        L0 = L0Input(Q_m3h=20, dH_m=10, L_m=50)
        r = select_pumps(L0)
        # typical sum_zeta из catalog (обычно 6.0-8.0)
        assert r.computed.sum_zeta > 0

    def test_explicit_bends_changes_zeta(self):
        """Задание n_bends=10 → sum_zeta растёт."""
        L0 = L0Input(Q_m3h=20, dH_m=10, L_m=50)
        r0 = select_pumps(L0)
        r10 = select_pumps(L0, L1Input(n_bends=10))
        # v0.3 (2026-05-13): 10 отводов × 0.18 (Idelchik 2007) + base 4.5 = 6.3
        # Раньше игнорировалось, теперь sum_zeta меняется
        assert r10.computed.sum_zeta != r0.computed.sum_zeta

    def test_many_bends_increases_h_m(self):
        """50 отводов → H_м больше чем 5 отводов."""
        L0 = L0Input(Q_m3h=20, dH_m=10, L_m=50)
        r5 = select_pumps(L0, L1Input(n_bends=5))
        r50 = select_pumps(L0, L1Input(n_bends=50))
        assert r50.computed.H_m_m > r5.computed.H_m_m
        # v0.3 (2026-05-13): 50 vs 5 отводов: разница (50-5)*0.18 = 8.1 ζ
        # Idelchik 2007 даёт меньший ζ чем 1992 (0.18 vs 0.3)
        assert r50.computed.sum_zeta > r5.computed.sum_zeta + 5


class TestNoExceptionsOnEdgeCases:
    """Никакой edge-case, прошедший Pydantic, не должен ронять select_pumps."""

    @pytest.mark.parametrize("payload", [
        dict(Q_m3h=0.01),
        dict(Q_m3h=0.5),
        dict(Q_m3h=10000),
        dict(Q_m3h=20, dH_m=-50),
        dict(Q_m3h=20, dH_m=200),
        dict(Q_m3h=20, L_m=5000),
        dict(Q_m3h=20, L_m=0),
        dict(Q_m3h=20, dH_m=0.001, L_m=0),
        dict(Q_m3h=20, wastewater_type="clean_water"),
        dict(Q_m3h=20, wastewater_type="fire_protection"),
    ])
    def test_no_exception(self, payload):
        L0 = L0Input(**payload)
        r = select_pumps(L0)
        assert r is not None
        # Никаких 500: SelectionResult всегда возвращён
        assert hasattr(r, "results")


# ──────────────────────────────────────────────────────────────────
# 2026-05-10: 10 научных расширений (СП/ПУЭ/материаловедение/биология)
# ──────────────────────────────────────────────────────────────────


class TestScientificExtensions:
    """10 новых triggers + suggestions с 2-level reasons."""

    def _has_suggestion(self, r, field_substr: str) -> bool:
        return any(field_substr in s.field for s in r.suggestions)

    def _suggestion(self, r, field_substr: str):
        for s in r.suggestions:
            if field_substr in s.field:
                return s
        return None

    def test_ext1_lateral_earth_pressure(self):
        """EXT-1: install_depth>5000 мм → trigger + suggestion + 2-level reason."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(install_depth_inlet_mm=6000)
        r = select_pumps(L0, L1)
        assert "auto_lateral_earth_pressure" in r.trigger_reasons
        assert any("Кулон" in w or "грунта" in w for w in r.warnings)
        s = self._suggestion(r, "install_depth_inlet_mm")
        assert s is not None
        assert s.severity == "critical"
        assert "СП 22.13330" in s.reason_engineer
        assert "тыс ₽" in s.reason_manager or "млн ₽" in s.reason_manager

    def test_ext2_traffic_load_class(self):
        """EXT-2: подземный без павильона + малая глубина → класс крышки."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(above_ground_pavilion=False, install_depth_inlet_mm=500)
        r = select_pumps(L0, L1)
        assert "auto_traffic_load_class" in r.trigger_reasons
        s = self._suggestion(r, "cover_load_class")
        assert s is not None
        assert s.severity == "critical"
        assert "D400" in s.reason_engineer
        assert "тыс ₽" in s.reason_manager

    def test_ext3_grounding_required_ex(self):
        """EXT-3: Ex_required=True → grounding."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(Ex_required=True)
        r = select_pumps(L0, L1)
        assert "auto_grounding_required" in r.trigger_reasons
        s = self._suggestion(r, "grounding_required")
        assert s is not None
        assert s.severity == "critical"
        assert "ПУЭ" in s.reason_engineer
        assert "4 Ом" in s.reason_engineer

    def test_ext3_grounding_required_category_i(self):
        """EXT-3: I категория надёжности → grounding."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(reliability_category="I")
        r = select_pumps(L0, L1)
        assert "auto_grounding_required" in r.trigger_reasons

    def test_ext4_lightning_protection(self):
        """EXT-4: above_ground_pavilion=True → молниезащита."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(above_ground_pavilion=True)
        r = select_pumps(L0, L1)
        assert "auto_lightning_protection_required" in r.trigger_reasons
        s = self._suggestion(r, "lightning_protection")
        assert s is not None
        assert s.severity == "critical"
        assert "СО 153-34.21.122" in s.reason_engineer
        assert "УЗИП" in s.reason_engineer

    def test_ext5_pipe_insulation_hot(self):
        """EXT-5: горячая жидкость > 40°C → утепление."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(liquid_temp_c=55)
        r = select_pumps(L0, L1)
        assert "auto_pipe_insulation_required" in r.trigger_reasons
        s = self._suggestion(r, "pipe_insulation")
        assert s is not None
        assert "СП 41-103" in s.reason_engineer

    def test_ext5_pipe_insulation_cold_altitude(self):
        """EXT-5: высота > 1500 м → утепление (холодный регион)."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(altitude_m=2000)
        r = select_pumps(L0, L1)
        assert "auto_pipe_insulation_required" in r.trigger_reasons

    def test_ext6_heating_cable(self):
        """EXT-6: altitude > 1500 м → греющий кабель 30 Вт/м."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(altitude_m=1800)
        r = select_pumps(L0, L1)
        assert "auto_heating_cable_required" in r.trigger_reasons
        s = self._suggestion(r, "heating_cable")
        assert s is not None
        assert "30 Вт/м" in s.reason_engineer or "30 Вт/м" in s.reason_manager
        assert "₽/п.м" in s.reason_manager

    def test_ext7_sedimentation_industrial(self):
        """EXT-7: industrial + Q < 50 → седиментация Стокса."""
        L0 = L0Input(Q_m3h=20, wastewater_type="industrial")
        r = select_pumps(L0)
        assert "auto_sedimentation_check" in r.trigger_reasons
        s = self._suggestion(r, "sand_separator")
        assert s is not None
        assert "Стокс" in s.reason_engineer
        assert "песколовка" in s.reason_manager.lower()

    def test_ext8_disinfection_domestic_high_q(self):
        """EXT-8: domestic + Q > 100 → УФ/озон."""
        L0 = L0Input(Q_m3h=150, wastewater_type="domestic")
        r = select_pumps(L0)
        assert "auto_disinfection_required" in r.trigger_reasons
        s = self._suggestion(r, "disinfection")
        assert s is not None
        assert "СанПиН" in s.reason_engineer
        assert "30 мДж/см²" in s.reason_engineer or "30 мДж/см" in s.reason_engineer

    def test_ext9_nitrification_industrial(self):
        """EXT-9: industrial → нитри/денитрификация."""
        L0 = L0Input(Q_m3h=80, wastewater_type="industrial")
        r = select_pumps(L0)
        assert "auto_nitrification_check" in r.trigger_reasons
        s = self._suggestion(r, "nitrification_required")
        assert s is not None
        assert "Monod" in s.reason_engineer or "10 сут" in s.reason_engineer
        assert "аэротенк" in s.reason_manager.lower()

    def test_ext10_hydrobak_clean_water(self):
        """EXT-10: clean_water + Q > 50 → гидроаккумулятор."""
        L0 = L0Input(Q_m3h=80, wastewater_type="clean_water")
        r = select_pumps(L0)
        assert "auto_hydrobak_required" in r.trigger_reasons
        s = self._suggestion(r, "hydrobak_volume_l")
        assert s is not None
        assert "СП 30.13330" in s.reason_engineer
        assert "л" in s.suggested_value

    def test_extensions_dont_break_default(self):
        """Без специфичных условий новые triggers не срабатывают."""
        L0 = L0Input(Q_m3h=20, dH_m=10, L_m=50)
        r = select_pumps(L0)
        new_triggers = {
            "auto_lateral_earth_pressure", "auto_traffic_load_class",
            "auto_grounding_required", "auto_lightning_protection_required",
            "auto_pipe_insulation_required", "auto_heating_cable_required",
            "auto_sedimentation_check", "auto_disinfection_required",
            "auto_nitrification_check", "auto_hydrobak_required",
        }
        for t in new_triggers:
            assert t not in r.trigger_reasons, f"{t} не должен срабатывать на дефолтных значениях"
        assert hasattr(r, "trigger_reasons")
