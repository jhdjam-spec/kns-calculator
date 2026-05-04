"""Phase 9 — тесты прогнозирования диапазона цены и summary.

Проверяет логику:
- completeness_pct корректно считает заполненность L0+L1
- При неполных данных диапазон цены шире, при полных — уже
- summary_text формируется по типу объекта и полноте ввода
- При high confidence + explicit price диапазон сужается до ±3-5%
"""

from __future__ import annotations

from pump_calculator.forecast import (
    calculate_completeness_pct,
    calculate_price_range,
)
from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input, L1Input


class TestCompletenessPct:
    """Подсчёт полноты входных данных."""

    def test_only_q_is_15pct(self):
        """Только Q (минимум) → 15%."""
        L0 = L0Input(Q_m3h=21.2)
        assert calculate_completeness_pct(L0, None) == 15

    def test_full_l0_is_60pct(self):
        """Все 4 поля L0 → 60% (4×15%)."""
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        assert calculate_completeness_pct(L0, None) == 60

    def test_l0_plus_some_l1(self):
        """L0 + 6 полей L1 → 60% + 30% = 90%."""
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        L1 = L1Input(
            pipe_material="pe100_sdr17",
            n_bends=4,
            n_valves=2,
            redundancy="1+1",
            reliability_category="II",
            liquid_temp_c=15,
        )
        assert calculate_completeness_pct(L0, L1) == 90

    def test_l0_plus_all_l1_capped_at_100(self):
        """Перебор не превышает 100%."""
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        L1 = L1Input(
            pipe_material="pe100_sdr17",
            pipe_D_mm=100,
            n_bends=4,
            n_valves=2,
            redundancy="1+1",
            Ex_required=True,
            reliability_category="II",
            liquid_temp_c=15,
        )
        # 60 + 8×5 = 100
        assert calculate_completeness_pct(L0, L1) == 100


class TestPriceRange:
    """Диапазон цены: чем меньше данных, тем шире."""

    def test_full_data_high_confidence_narrow_range(self):
        """100% данных + high confidence + explicit price → диапазон ±3%."""
        low, high = calculate_price_range(
            total_rub=1_000_000,
            completeness_pct=100,
            confidence="high",
            has_explicit_pump_price=True,
        )
        # spread = 0.05 × 0.6 = 0.03
        assert low >= 960_000
        assert high <= 1_040_000

    def test_minimum_data_low_confidence_wide_range(self):
        """15% данных + low confidence → широкий диапазон."""
        low, high = calculate_price_range(
            total_rub=1_000_000,
            completeness_pct=15,
            confidence="low",
            has_explicit_pump_price=False,
        )
        # spread = 0.35 × 1.3 = 0.455
        assert low <= 600_000
        assert high >= 1_400_000

    def test_zero_total_returns_zero(self):
        low, high = calculate_price_range(0, 100, "high", True)
        assert low == 0 and high == 0

    def test_minimum_spread_3pct(self):
        """Даже идеальный кейс не уже ±3%."""
        low, high = calculate_price_range(
            total_rub=1_000_000,
            completeness_pct=100,
            confidence="high",
            has_explicit_pump_price=True,
        )
        # Должна быть какая-то ширина (не точное значение)
        assert high > low
        assert (high - low) / 1_000_000 >= 0.05  # ±3% = 6% общего


class TestSummaryText:
    """Человекочитаемая сводка."""

    def test_summary_mentions_object_type_for_domestic(self):
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        assert "бытовой канализации" in result.summary_text.lower()

    def test_summary_mentions_completeness_for_partial(self):
        """При неполных данных summary упоминает процент заполнения."""
        L0 = L0Input(Q_m3h=21.2)  # только Q
        result = select_pumps(L0)
        assert "минимум данных" in result.summary_text.lower() or "%" in result.summary_text

    def test_summary_mentions_clean_water_for_spd(self):
        L0 = L0Input(Q_m3h=38.43, dH_m=70, L_m=20, wastewater_type="clean_water")
        result = select_pumps(L0)
        assert "повышения давления" in result.summary_text.lower() or "спд" in result.summary_text.lower()

    def test_summary_recommends_kp_when_no_handoff(self):
        """Без триггеров handoff — summary говорит «можно формировать КП»."""
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        if not result.engineer_handoff_required:
            assert "формировать" in result.summary_text.lower() or "коммерческое" in result.summary_text.lower()


class TestSelectionResultIntegration:
    """Интеграция: SelectionResult получает все Phase 9 поля."""

    def test_completeness_in_result(self):
        L0 = L0Input(Q_m3h=21.2)
        result = select_pumps(L0)
        assert result.completeness_pct == 15  # только Q

    def test_summary_text_in_result(self):
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        assert len(result.summary_text) > 50  # осмысленный текст, не пустой

    def test_price_range_in_breakdown(self):
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        for seg in ("budget", "mid", "premium"):
            p = getattr(result.results, seg)
            if p is not None and p.price_estimate_rub > 0:
                b = p.price_breakdown
                assert b.total_low_rub > 0
                assert b.total_high_rub > 0
                assert b.total_low_rub <= b.total_rub <= b.total_high_rub
