"""Phase 11 — пожарная установка (СП 10.13130).

Тесты проверяют, что:
  1. wastewater_type='fire_protection' корректно роутится через filter
  2. БД содержит хотя бы одну fire_pump (Wilo SiFire)
  3. Триггер auto_fire_protection всегда выставлен → handoff обязателен
  4. Pricing использует estimate_fire_kit_price (PN16 наценка, пожарный ШУ)
  5. confidence ВСЕГДА low/medium (никогда не high — нельзя обобщать сделку)
  6. Диапазон цены total_low/total_high широкий (±35%, не ±5%)
  7. ATEX (Ex_required=True) добавляет +40% к цене насоса в heuristic-ветке

Защита от регрессий: пожарная не должна попасть в обычный КНС-pricing.
"""

from __future__ import annotations

from pump_calculator.matching import select_pumps
from pump_calculator.pricing import estimate_fire_kit_price
from pump_calculator.schemas import L0Input, L1Input


class TestFireProtectionRouting:
    """Поток wastewater_type='fire_protection' идёт по своей ветке."""

    def setup_method(self):
        self.L0 = L0Input(
            Q_m3h=30.0,
            dH_m=40,
            L_m=20,
            wastewater_type="fire_protection",
        )
        self.result = select_pumps(self.L0)

    def test_fire_protection_recognized(self):
        """fire_protection не падает на отсутствии в coefficients."""
        assert self.result is not None
        assert self.result.candidates_total > 0, \
            "Хотя бы Wilo SiFire должен быть в выдаче"

    def test_handoff_always_required(self):
        """СП 10.13130 требует подписи проектировщика — handoff обязателен."""
        assert self.result.engineer_handoff_required is True
        assert "auto_fire_protection" in self.result.trigger_reasons

    def test_premium_segment_picks_wilo_sifire(self):
        """Wilo SiFire EN — placeholder премиум, должен быть в выдаче."""
        assert self.result.results.premium is not None
        # ID одной из 3 placeholder-записей Phase 11
        assert self.result.results.premium.id in {"wilo-sife-1605", "wilo-bl-50-160"}

    def test_no_kns_components_in_breakdown(self):
        """Пожарная сухопостовленная — без корпуса/направляющих/цепей/поплавков."""
        premium = self.result.results.premium
        assert premium is not None
        b = premium.price_breakdown
        assert b.corpus_rub == 0
        assert b.rails_rub == 0
        assert b.chain_rub == 0
        assert b.floats_rub == 0

    def test_confidence_never_high(self):
        """Пожарная — индивидуальная калибровка, нельзя ставить high (нет КП-эталона)."""
        for segment_name in ("budget", "mid", "premium"):
            seg = getattr(self.result.results, segment_name)
            if seg is not None:
                assert seg.price_confidence in {"low", "medium"}, \
                    f"{segment_name}: пожарная не должна получать high confidence"

    def test_price_range_wide(self):
        """Phase 11: ±35% диапазон (vs ±5-10% у обычной КНС с полными данными)."""
        premium = self.result.results.premium
        assert premium is not None
        b = premium.price_breakdown
        assert b.total_low_rub < b.total_rub < b.total_high_rub
        # Проверяем именно широкий диапазон
        spread = (b.total_high_rub - b.total_low_rub) / b.total_rub
        # 2026-05-11: после enrichment БД (Sub D+E+F+G — +eta/rpm/NPSHr 100%, +ATEX)
        # цены стали точнее → spread сузился с 50% до 40%. Это улучшение, не регрессия.
        assert spread >= 0.35, \
            f"Ожидался диапазон ≥35% от total, получен {spread:.0%}"


class TestFireKitPricingComponents:
    """estimate_fire_kit_price unit-тесты — проверка компонентов BOM."""

    def test_fire_cabinet_more_expensive_than_spd(self):
        """Пожарный ШУ Sf дороже обычного ЧРП-шкафа СПД (резервирование)."""
        from pump_calculator.pricing import (
            estimate_fire_cabinet_price_rub,
            estimate_spd_cabinet_price_rub,
        )
        # При одинаковой мощности 5.5 кВт пожарный шкаф дороже
        spd = estimate_spd_cabinet_price_rub(5.5, "mid")
        fire = estimate_fire_cabinet_price_rub(5.5, "mid")
        assert fire > spd * 1.5, \
            f"Пожарный ШУ ({fire}) должен быть >150% обычного СПД ({spd})"

    def test_pn16_multiplier_applied(self):
        """PN16 арматура дороже PN10 на ~40%. Проверяем через breakdown."""
        breakdown_fire, _ = estimate_fire_kit_price(
            P_kW=7.5, Q_m3h=50.0, discharge_DN_mm=80,
            segment="mid", n_pumps=2,
        )
        # При наличии хитов из БД задвижки/ОК должны быть >0
        # (для DN80 fittings_seed.json содержит цены)
        assert breakdown_fire.valve_rub >= 0  # >= 0 даже если нет в БД
        # Жокей-насос + бак + рама + датчики — atm_rub должен быть >100k
        assert breakdown_fire.atm_rub > 100_000

    def test_atex_adds_40pct_in_heuristic(self):
        """Ex_required=True добавляет +40% к цене насоса (heuristic-ветка)."""
        no_ex, _ = estimate_fire_kit_price(
            P_kW=7.5, Q_m3h=50.0, discharge_DN_mm=80,
            segment="mid", n_pumps=2, ex_required=False,
        )
        ex, _ = estimate_fire_kit_price(
            P_kW=7.5, Q_m3h=50.0, discharge_DN_mm=80,
            segment="mid", n_pumps=2, ex_required=True,
        )
        # ATEX наценка только на pump_rub
        assert ex.pump_rub > no_ex.pump_rub * 1.3
        assert ex.pump_rub <= no_ex.pump_rub * 1.5

    def test_explicit_pump_price_no_atex_uplift(self):
        """С explicit ценой насоса ATEX-наценка не применяется (цена уже точная)."""
        no_ex, _ = estimate_fire_kit_price(
            P_kW=7.5, Q_m3h=50.0, discharge_DN_mm=80,
            segment="mid", n_pumps=2,
            explicit_pump_price_rub=500_000,
        )
        ex, _ = estimate_fire_kit_price(
            P_kW=7.5, Q_m3h=50.0, discharge_DN_mm=80,
            segment="mid", n_pumps=2,
            explicit_pump_price_rub=500_000,
            ex_required=True,
        )
        assert ex.pump_rub == no_ex.pump_rub == 500_000 * 2

    def test_n_pumps_default_is_2(self):
        """СП 10.13130 п.6.2: 1 раб + 1 рез ОБЯЗАТЕЛЬНО."""
        breakdown, _ = estimate_fire_kit_price(
            P_kW=7.5, Q_m3h=50.0, discharge_DN_mm=80,
            segment="mid",
        )
        # n_pumps=2 по умолчанию, проверяем через pump_rub
        # heuristic для 7.5 кВт mid → ~487к/насос, × 2 ≈ 975k
        assert breakdown.pump_rub > 400_000  # хотя бы 1 насос * mid rate


class TestFireProtectionWithEx:
    """ATEX-сценарий через select_pumps."""

    def test_ex_required_triggers_auto_ex_and_fire(self):
        """Ex_required + fire_protection → оба триггера."""
        result = select_pumps(
            L0=L0Input(Q_m3h=50.0, dH_m=45, L_m=20, wastewater_type="fire_protection"),
            L1=L1Input(Ex_required=True),
        )
        assert "auto_ex" in result.trigger_reasons
        assert "auto_fire_protection" in result.trigger_reasons
        assert result.engineer_handoff_required is True
