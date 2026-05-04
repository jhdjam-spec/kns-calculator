"""Тесты для расчёта стеклопластикового корпуса.

Эталонная точка из xlsx Серво-Юг (`калькулятор расчета стоимсти стеклопластиковой
емкости.xlsx`): D=2000 мм × L=5000 мм, default-параметры намотки →
mass_total=493.05 кг, cost_self=82 025.41 ₽, price_commercial=188 658 ₽.

Эта точка покрывает всю формулу полностью — если она проходит, значит
все коэффициенты, площади, толщины и множитель воспроизведены 1-в-1.
"""

from __future__ import annotations

import pytest

from pump_calculator.pricing import estimate_corpus_price_rub
from pump_calculator.pricing_glass import (
    GLASS_STANDARD_DIAMETERS_MM,
    calc_glass_corpus_cost,
    estimate_glass_corpus_price_rub,
    round_to_glass_standard_d,
)


class TestGlassEtalon:
    """Проверка точного совпадения с эталонной xlsx-точкой Серво-Юг."""

    def test_etalon_d2000_l5000(self):
        """D=2000 × L=5000, layers=6/1 → mass=493.05 кг, cost_self=82025.41 ₽."""
        r = calc_glass_corpus_cost(D_mm=2000, L_mm=5000)

        assert r["V_m3"] == pytest.approx(15.708, abs=0.01)
        assert r["t_wall_mm"] == pytest.approx(7.9, abs=0.01)
        assert r["mass_thread_kg"] == pytest.approx(253.49, abs=0.5)
        assert r["mass_total_kg"] == pytest.approx(493.05, abs=1.0)
        assert r["cost_self_rub"] == pytest.approx(82025.41, abs=10)
        assert r["price_commercial_rub"] == pytest.approx(188658, abs=5)

    def test_smaller_d800_cheaper(self):
        """Меньший корпус — дешевле."""
        small = calc_glass_corpus_cost(D_mm=800, L_mm=2000)
        large = calc_glass_corpus_cost(D_mm=2400, L_mm=8000)
        assert small["price_commercial_rub"] < large["price_commercial_rub"]

    def test_more_layers_increase_cost(self):
        """Больше слоёв — больше масса и цена."""
        thin = calc_glass_corpus_cost(D_mm=2000, L_mm=5000, layers_thread=4)
        thick = calc_glass_corpus_cost(D_mm=2000, L_mm=5000, layers_thread=10)
        assert thick["mass_total_kg"] > thin["mass_total_kg"]
        assert thick["cost_self_rub"] > thin["cost_self_rub"]


class TestGlassStandardD:
    def test_round_up_to_standard(self):
        assert round_to_glass_standard_d(700) == 800
        assert round_to_glass_standard_d(800) == 800
        assert round_to_glass_standard_d(900) == 1000
        assert round_to_glass_standard_d(1500) == 1500
        assert round_to_glass_standard_d(2400) == 2400

    def test_above_max_returns_max(self):
        assert round_to_glass_standard_d(3000) == 2400


class TestEstimateByQ:
    """Эвристика подбора корпуса по Q (для интеграции в pricing.py)."""

    def test_small_q_gets_small_corpus(self):
        small = estimate_glass_corpus_price_rub(10)
        large = estimate_glass_corpus_price_rub(500)
        assert small < large

    def test_returns_realistic_range(self):
        # Q=50 м³/ч → 5/60 × 50 = 4.17 м³ V_min → должен поместиться в D=1500 коротко
        price = estimate_glass_corpus_price_rub(50)
        # Реалистичный диапазон: 50–200k ₽ для малой стеклопластиковой ёмкости
        assert 50_000 <= price <= 250_000


class TestPricingIntegration:
    """estimate_corpus_price_rub теперь принимает material."""

    def test_default_is_pe(self):
        # Default material="pe" — старая heuristic
        pe_price = estimate_corpus_price_rub(20)
        assert pe_price == 350_000

    def test_glass_path(self):
        # Через явный параметр material="glass"
        glass_price = estimate_corpus_price_rub(20, material="glass")
        # Стеклопластик для Q=20 м³/ч — компактный и дешевле, чем 350k ПЭ
        assert glass_price < 200_000

    def test_glass_for_large_q(self):
        # Для Q=252 м³/ч стеклопластик может быть сопоставим с ПЭ
        pe = estimate_corpus_price_rub(252, material="pe")
        glass = estimate_corpus_price_rub(252, material="glass")
        # Оба в реалистичном диапазоне (>100k и <2.5M)
        assert 100_000 <= pe <= 2_500_000
        assert 100_000 <= glass <= 2_500_000
