"""Тесты для двух новых фич:

1. Первичная оценка цены КНС-комплекта (pricing.py + price_estimate_rub в PumpResult)
2. Терпимость L0 к неполным данным (apply_l0_defaults + assumptions)

Контракт обоих фич — зафиксирован для frontend, не должен меняться без согласования.
"""

from __future__ import annotations

from pump_calculator import select_pumps
from pump_calculator.pricing import (
    estimate_corpus_price_rub,
    estimate_kns_kit_price,
    estimate_pump_price_rub,
    round_to_dn,
)
from pump_calculator.schemas import L0Input

# ---------- pricing.py unit tests ----------

class TestPumpPriceEstimate:
    """Грубая оценка цены насоса по сегменту и мощности."""

    def test_budget_3kw_around_kaiquan_baseline(self):
        # KAIQUAN 50WQ/S 20-22-3 (3 кВт) в реальной АРКАДА КП — 65 600 ₽
        # Heuristic 25k/kW × 3 = 75k, clamped к min 30k. Допуск ±50%
        price = estimate_pump_price_rub(P_kW=3.0, segment="budget")
        assert 30_000 <= price <= 200_000, f"got {price}"

    def test_premium_8kw_in_realistic_range(self):
        # KSB 8 кВт premium → ~1.4M
        price = estimate_pump_price_rub(P_kW=8.0, segment="premium")
        assert 800_000 <= price <= 2_500_000, f"got {price}"

    def test_min_clamp_works(self):
        # Очень маленький насос — не должен быть дешевле минимума сегмента
        price = estimate_pump_price_rub(P_kW=0.3, segment="budget")
        assert price >= 30_000

    def test_max_clamp_works(self):
        # Очень большой — не должен быть дороже максимума
        price = estimate_pump_price_rub(P_kW=200, segment="budget")
        assert price <= 250_000


class TestCorpusPriceEstimate:
    def test_small_kns(self):
        # Q≤30 → ~350k (D1500/H3200)
        assert estimate_corpus_price_rub(20) == 350_000

    def test_medium_kns_mysxako(self):
        # Q≈21 → 350k (попадает в диапазон ≤30)
        assert estimate_corpus_price_rub(21.2) == 350_000

    def test_large_kns(self):
        # Q≥250 → ~1.5–1.7M
        price = estimate_corpus_price_rub(252)
        assert 1_400_000 <= price <= 1_800_000


class TestRoundToDN:
    def test_rounds_up_to_standard(self):
        assert round_to_dn(50) == "DN50"
        assert round_to_dn(60) == "DN65"
        assert round_to_dn(100) == "DN100"
        assert round_to_dn(125) == "DN150"
        assert round_to_dn(None) == "DN50"
        assert round_to_dn(0) == "DN50"

    def test_caps_at_max(self):
        assert round_to_dn(500) == "DN400"


class TestKnsKitPrice:
    def test_full_kit_breakdown_sums_to_total(self):
        breakdown, _conf = estimate_kns_kit_price(
            P_kW=3.0, Q_m3h=21.2, discharge_DN_mm=50, segment="budget", n_pumps=2
        )
        manual_sum = (
            breakdown.pump_rub + breakdown.atm_rub + breakdown.valve_rub
            + breakdown.check_valve_rub + breakdown.rails_rub
            + breakdown.cabinet_rub + breakdown.floats_rub
            + breakdown.chain_rub + breakdown.corpus_rub
        )
        assert breakdown.total_rub == manual_sum

    def test_arkada_kp_dn50_atm_price_matches(self):
        # АРКАДА КП 29.01.2026: АТМ DN50 = 22 700 ₽; для 2 насосов = 45 400 ₽
        breakdown, _ = estimate_kns_kit_price(
            P_kW=3.0, Q_m3h=21.2, discharge_DN_mm=50, segment="budget", n_pumps=2
        )
        assert breakdown.atm_rub == 22_700 * 2

    def test_confidence_medium_when_dn_known(self):
        _, conf = estimate_kns_kit_price(
            P_kW=3.0, Q_m3h=21.2, discharge_DN_mm=50, segment="budget", n_pumps=2
        )
        assert conf in {"medium", "high"}


# ---------- L0 partial input + assumptions tests ----------

class TestPartialL0Defaults:
    def test_only_q_is_enough(self):
        """Минимальный валидный вход: только Q. Остальное — дефолты."""
        L0 = L0Input(Q_m3h=21.2)
        result = select_pumps(L0)
        # Должны быть подставлены 3 ассампшена (dH, L, ww)
        assert len(result.assumptions) == 3
        # Должны упоминать пропущенные поля
        msgs = " ".join(result.assumptions)
        assert "dH" in msgs
        assert "L" in msgs
        assert "тип стоков" in msgs.lower() or "domestic" in msgs.lower()

    def test_full_l0_no_assumptions(self):
        """Если все 4 поля заданы — assumptions пуст."""
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        assert result.assumptions == []

    def test_partial_only_dh_missing(self):
        L0 = L0Input(Q_m3h=21.2, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        assert len(result.assumptions) == 1
        assert "dH" in result.assumptions[0]

    def test_zero_dh_zero_l_falls_back(self):
        """dH=0 и L=0 — особый кейс: подставляется dH=2 (минимум)."""
        L0 = L0Input(Q_m3h=10, dH_m=0, L_m=0, wastewater_type="domestic")
        result = select_pumps(L0)
        # H_full должен быть как минимум 2 (после дефолта)
        assert result.computed.H_full_m >= 2.0
        # Должна быть assumption про обнуление
        msgs = " ".join(result.assumptions)
        assert "dH" in msgs and "L" in msgs

    def test_partial_input_returns_price(self):
        """Даже на минимальном вводе должна быть оценка цены для найденных насосов."""
        L0 = L0Input(Q_m3h=21.2)
        result = select_pumps(L0)
        # Хотя бы один сегмент должен быть найден на эталонном Q=21.2
        any_found = (
            result.results.budget or result.results.mid or result.results.premium
        )
        assert any_found, f"Ни одного кандидата на Q=21.2; warnings={result.warnings}"
        # У всех найденных должен быть price_estimate_rub > 0
        for seg in ("budget", "mid", "premium"):
            p = getattr(result.results, seg)
            if p:
                assert p.price_estimate_rub > 0, f"{seg}: price=0"
                # И breakdown должен суммироваться к total
                b = p.price_breakdown
                assert b.total_rub == p.price_estimate_rub


class TestPriceConsistencyOnEtalon:
    """На эталонном кейсе Мысхако цены должны попадать в реалистичный диапазон."""

    def test_mysxako_budget_price_in_range(self):
        L0 = L0Input(Q_m3h=21.2, dH_m=15, L_m=50, wastewater_type="domestic")
        result = select_pumps(L0)
        budget = result.results.budget
        assert budget is not None, "На эталонном кейсе должен быть budget кандидат"
        # Реальный КП АртВинд — около 1 млн на полную КНС в budget сегменте.
        # Допуск ±50% (это первичная оценка)
        assert 500_000 <= budget.price_estimate_rub <= 2_000_000, \
            f"price out of realistic range: {budget.price_estimate_rub}"
