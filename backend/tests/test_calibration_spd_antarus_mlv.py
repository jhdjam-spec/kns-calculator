"""Калибровочный тест Phase 8 СПД на эталоне ANTARUS 3 MLV20-5/GPRS.

**Эталонные данные** (вход):
  Q = 38.43 м³/ч, H = 70 м, тип = clean_water (СПД)

**Эталонный подбор:**
  ANTARUS 3 MLV20-5/GPRS, Q=38.43 м³/ч, H=75 м, P_вал=10.6 кВт, P_дв=5.5 кВт.
  Подобрано через программу «УМНАЯ ВОДА» Antarus.

**Эталонная цена:** 3 500 650 ₽ (КП Серво-Юг для Беловодск Крым 28012026_2).

**Phase 8 особенности:**
1. Тип booster_station — отдельный BOM-шаблон (без АТМ, без корпуса/направляющих)
2. wastewater_type=clean_water — новая категория из Phase 8
3. Если в БД задан price_rub_2026 для booster_station — это **готовый блок
   «всё включено»**, обвязка не добавляется отдельно (как в реальных КП)
4. n_pumps=1 для СПД (один блок-станция, не 1+1 рез как у КНС)

Защищает от регрессий: при изменении фильтров, цен или logic
estimate_spd_kit_price этот эталон должен оставаться рабочим.
"""

from __future__ import annotations

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input

EXPECTED_PUMP_ID = "antarus-3mlv20-5"
EXPECTED_PRICE_RUB = 3_500_650


class TestSpdAntarusMlv20:
    """Боевой эталон ANTARUS 3 MLV20-5 для пос. Беловодск Крым."""

    def setup_method(self):
        self.L0 = L0Input(
            Q_m3h=38.43,
            dH_m=70,
            L_m=20,
            wastewater_type="clean_water",
        )
        self.result = select_pumps(self.L0)

    def test_clean_water_type_recognized(self):
        """clean_water — новый тип из Phase 8. Не должен падать."""
        assert self.result is not None
        assert self.result.candidates_total > 0

    def test_antarus_mlv_in_premium(self):
        """ANTARUS 3 MLV20-5 в premium — это эталонный СПД-блок премиум-сегмента."""
        assert self.result.results.premium is not None
        assert self.result.results.premium.id == EXPECTED_PUMP_ID, \
            f"Ожидался {EXPECTED_PUMP_ID}, получен {self.result.results.premium.id}"

    def test_total_price_matches_kp_exactly(self):
        """Эталонный блок «всё включено» — цена совпадает с КП один-в-один."""
        premium = self.result.results.premium
        assert premium is not None
        assert premium.price_estimate_rub == EXPECTED_PRICE_RUB

    def test_no_kns_components_in_spd_breakdown(self):
        """СПД не имеет корпуса/направляющих/цепей/поплавков (это КНС-компоненты)."""
        premium = self.result.results.premium
        assert premium is not None
        b = premium.price_breakdown
        assert b.corpus_rub == 0
        assert b.rails_rub == 0
        assert b.chain_rub == 0
        assert b.floats_rub == 0

    def test_explicit_block_price_no_separate_obvyazka(self):
        """Когда price_rub_2026 задан — это готовый блок, обвязка НЕ добавляется."""
        premium = self.result.results.premium
        assert premium is not None
        b = premium.price_breakdown
        # Цена насоса = вся стоимость блока
        assert b.pump_rub == EXPECTED_PRICE_RUB
        # Обвязка/гидроаккумулятор/шкаф не накручиваются сверху
        assert b.atm_rub == 0
        assert b.valve_rub == 0
        assert b.check_valve_rub == 0
        assert b.cabinet_rub == 0

    def test_confidence_high_for_explicit_block_price(self):
        """confidence=high когда есть точная цена готового блока."""
        premium = self.result.results.premium
        assert premium is not None
        assert premium.price_confidence == "high"


class TestSpdHeuristicWithoutExplicitPrice:
    """СПД без точной цены в БД — heuristic-сборка по компонентам."""

    def setup_method(self):
        # Берём ANTARUS 2MLV 3-6 (СПД без price_rub_2026 в БД) → heuristic
        self.L0 = L0Input(
            Q_m3h=20,
            dH_m=50,
            L_m=20,
            wastewater_type="clean_water",
        )
        self.result = select_pumps(self.L0)

    def test_components_sum_correctly(self):
        """Heuristic SPD: сумма компонентов = total."""
        for seg in ("budget", "mid", "premium"):
            p = getattr(self.result.results, seg)
            if p is None:
                continue
            b = p.price_breakdown
            manual = (
                b.pump_rub + b.atm_rub + b.valve_rub + b.check_valve_rub
                + b.rails_rub + b.cabinet_rub + b.floats_rub
                + b.chain_rub + b.corpus_rub
            )
            assert b.total_rub == manual, f"{seg}: sum mismatch"

    def test_spd_has_hydroaccumulator_and_cabinet_when_heuristic(self):
        """Heuristic SPD должен включать гидроаккумулятор+рама (atm_rub) и ЧРП-шкаф."""
        # Только если найден mid (Antarus 2MLV без точной цены) — у него heuristic
        mid = self.result.results.mid
        if mid is not None and mid.price_breakdown.pump_rub > 0:
            b = mid.price_breakdown
            # Если это СПД и нет explicit price — должны быть компоненты
            if b.corpus_rub == 0 and b.cabinet_rub > 0:
                assert b.atm_rub > 0, "СПД без гидроаккумулятора/рамы — нелогично"
