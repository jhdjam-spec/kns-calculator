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
        L0 = L0Input(Q_m3h=10, dH_m=-30)
        r = select_pumps(L0)
        assert "auto_dh_negative" in r.trigger_reasons
        assert r.engineer_handoff_required is True
        neg_warnings = [w for w in r.warnings if "отрицательный геометрический" in w]
        assert len(neg_warnings) > 0

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
        assert hasattr(r, "trigger_reasons")
