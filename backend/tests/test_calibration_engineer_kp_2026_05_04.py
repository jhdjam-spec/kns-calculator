"""Калибровочный тест по реальному КП инженера Серво-Юг (фото от 2026-05-04).

**Эталонные данные** (вход):
  Q = 0.5 м³/ч, dH = 1.7 м, L = 230 м, тип стоков = бытовые

**Эталонный подбор инженера:**
  - 2× KAIQUAN 65WQ/S223-2.2 (2.2 кВт, DN65) — 85 384 ₽/шт = 170 768 ₽
  - 2× Трубная муфта DN65 — 28 340 ₽/шт = 56 680 ₽
  - 1× Шкаф управления — 128 280 ₽
  - 4× Поплавки — 5 000 ₽/шт = 20 000 ₽
  - 2× Задвижка DN65 шиберная — 15 400 ₽/шт = 30 800 ₽
  - 2× Обратный клапан DN65 шаровый — 7 700 ₽/шт = 15 400 ₽
  - **Итого: 421 928 ₽**

**Калькулятор должен:**
1. Подобрать KAIQUAN 65WQ/S223-2.2 в budget сегменте
2. НЕ включать корпус КНС в малый комплект (Q<5 м³/ч → готовый приямок)
3. Цена комплекта в пределах ±20% от эталона (типично 380–500k)

Этот тест защищает от регрессий — если кто-то поменяет фильтры, AOR-логику
или цены — этот кейс должен оставаться рабочим.
"""

from __future__ import annotations

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input

EXPECTED_PUMP_ID = "kaiquan-65wqs223-22"
EXPECTED_TOTAL_RUB = 421_928
EXPECTED_PUMP_PRICE_RUB = 85_384
EXPECTED_TOLERANCE_PCT = 0.20  # ±20% для первичной оценки


class TestEngineerKpQ05CaseDomestic:
    """Боевой эталон от инженера Серво-Юг 2026-05-04."""

    def setup_method(self):
        self.L0 = L0Input(Q_m3h=0.5, dH_m=1.7, L_m=230, wastewater_type="domestic")
        self.result = select_pumps(self.L0)

    def test_calculator_does_not_crash_on_micro_q(self):
        """При Q=0.5 м³/ч калькулятор должен работать (не падать на envelope-фильтре)."""
        assert self.result is not None
        assert self.result.candidates_total > 0

    def test_kaiquan_65wqs223_22_is_in_budget(self):
        """Эталонный насос инженера — в бюджетном сегменте."""
        assert self.result.results.budget is not None, \
            f"Budget сегмент пуст. Warnings: {self.result.warnings}"
        assert self.result.results.budget.id == EXPECTED_PUMP_ID, \
            f"Ожидался {EXPECTED_PUMP_ID}, получен {self.result.results.budget.id}"

    def test_pump_price_matches_engineer_kp(self):
        """Цена насоса в БД = реальная цена из КП инженера 85 384 ₽."""
        budget = self.result.results.budget
        assert budget is not None
        # 2 насоса × 85 384 = 170 768
        assert budget.price_breakdown.pump_rub == EXPECTED_PUMP_PRICE_RUB * 2, \
            f"Ожидалось {EXPECTED_PUMP_PRICE_RUB * 2}, получено {budget.price_breakdown.pump_rub}"

    def test_kit_total_within_tolerance(self):
        """Цена комплекта в пределах ±20% от эталона."""
        budget = self.result.results.budget
        assert budget is not None
        total = budget.price_estimate_rub
        lower = EXPECTED_TOTAL_RUB * (1 - EXPECTED_TOLERANCE_PCT)
        upper = EXPECTED_TOTAL_RUB * (1 + EXPECTED_TOLERANCE_PCT)
        assert lower <= total <= upper, \
            f"Total {total} вне допуска [{lower:.0f}, {upper:.0f}] от эталона {EXPECTED_TOTAL_RUB}"

    def test_no_corpus_for_micro_kns(self):
        """Для Q<5 м³/ч корпус КНС не включается (используется готовый приямок)."""
        budget = self.result.results.budget
        assert budget is not None
        assert budget.price_breakdown.corpus_rub == 0, \
            "Для Q=0.5 м³/ч (частный коттедж) корпус КНС не нужен"
        assert budget.price_breakdown.rails_rub == 0
        assert budget.price_breakdown.chain_rub == 0

    def test_confidence_high_when_explicit_pump_price(self):
        """Когда в БД есть price_rub_2026 → confidence = high."""
        budget = self.result.results.budget
        assert budget is not None
        assert budget.price_confidence == "high", \
            f"Ожидалась 'high' (точная цена насоса в БД), получено '{budget.price_confidence}'"

    def test_floats_count_4(self):
        """4 поплавка по 5000 ₽ = 20 000 ₽ (как в КП инженера)."""
        budget = self.result.results.budget
        assert budget is not None
        assert budget.price_breakdown.floats_rub == 4 * 5_000

    def test_all_segments_have_pump_or_explanation(self):
        """Mid и Premium должны быть либо найдены, либо иметь warning."""
        for seg_name in ("mid", "premium"):
            seg = getattr(self.result.results, seg_name)
            if seg is None:
                # Должна быть warning о пустом сегменте
                assert any(seg_name in w.lower() for w in self.result.warnings), \
                    f"{seg_name} пуст без объяснения в warnings"
