"""Комбинаторные тесты входов: правильные + неправильные значения вместе.

Реальные сценарии менеджера ОП — типичные опечатки и несогласованные данные:
- Q правильный, dH опечатка (200 вместо 20)
- Q правильный, L нереалистичная (5000 м для бытового домика)
- Q правильный, pipe_D_mm задан невпопад (огромный или крошечный)
- Q+H разумные, но L1 содержит конфликты (altitude=4500 + liquid_temp=100)

Цель: КАЛИБРОВКА. Калькулятор должен давать осмысленные warning'и для
каждого класса опечатки, а не молча возвращать абсурд.
"""
from __future__ import annotations

import pytest

from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input, L1Input


# ─── 4-цифр: только Q (минимум обязательного) ───────────────────────────


class TestSingleField:
    """L0.Q_m3h единственное обязательное."""

    def test_q_alone_with_defaults(self):
        """Только Q → calculator подставляет defaults для dH/L/wastewater."""
        L0 = L0Input(Q_m3h=20)
        r = select_pumps(L0)
        assert r is not None
        assert r.input.L0.dH_m == 5.0  # default
        assert r.input.L0.L_m == 50.0  # default
        assert r.input.L0.wastewater_type == "domestic"  # default
        assert r.candidates_total > 0


# ─── 2 цифры: 1 правильная + 1 опечатка ─────────────────────────────────


class TestTwoFieldsOneError:
    """Q правильный + dH/L/wastewater опечатка."""

    def test_q_ok_dh_typo_200_instead_20(self):
        """Q=20 норма, но dH=200 (опечатка, должно быть 20)."""
        L0 = L0Input(Q_m3h=20, dH_m=200)
        r = select_pumps(L0)
        # dH=200 → H_full > 80 → auto_h_high trigger
        assert "auto_h_high" in r.trigger_reasons
        assert r.engineer_handoff_required is True

    def test_q_ok_dh_negative_typo(self):
        """Q=20 норма, dH=-25 (минус — опечатка вместо +25)."""
        L0 = L0Input(Q_m3h=20, dH_m=-25)
        r = select_pumps(L0)
        assert "auto_dh_negative" in r.trigger_reasons

    def test_q_ok_l_too_long(self):
        """Q=20 норма, L=2000 (магистральный, не объектный)."""
        L0 = L0Input(Q_m3h=20, L_m=2000)
        r = select_pumps(L0)
        assert "auto_l_long_zhukovsky" in r.trigger_reasons

    def test_q_ok_wastewater_industrial(self):
        """Q=20 норма, тип industrial — handoff обязателен."""
        L0 = L0Input(Q_m3h=20, wastewater_type="industrial")
        r = select_pumps(L0)
        assert "auto_industrial" in r.trigger_reasons


# ─── 3 цифры: 2 правильные + 1 неправильная ─────────────────────────────


class TestThreeFieldsOneError:
    """L0 (Q+dH+L) корректный + L1 опечатка."""

    @pytest.mark.parametrize("l1_payload,expected_trigger", [
        ({"pipe_D_mm": 500}, "auto_velocity_low"),  # огромная труба → v→0
        ({"pipe_D_mm": 20}, "auto_velocity_high"),  # узкая труба → v→большая
        ({"altitude_m": 4500}, "auto_altitude_extreme"),  # Эльбрус
        ({"altitude_m": -400}, "auto_altitude_extreme"),  # Мёртвое море
        ({"groundwater_level_m": 5}, "auto_groundwater_above_surface"),
        ({"liquid_temp_c": 60}, "auto_npsh_hot"),
        ({"reliability_category": "I"}, "auto_category_I"),
        ({"Ex_required": True}, "auto_ex"),
        ({"inflow_per_hour_m3": 1000}, "auto_inflow_exceeds_pump"),
    ])
    def test_l0_ok_l1_field_triggers(self, l1_payload, expected_trigger):
        """L0 норма (Q=20, dH=10, L=100) + 1 проблемное L1 поле."""
        L0 = L0Input(Q_m3h=20, dH_m=10, L_m=100, wastewater_type="domestic")
        L1 = L1Input(**l1_payload)
        r = select_pumps(L0, L1)
        assert expected_trigger in r.trigger_reasons, \
            f"Expected {expected_trigger} for {l1_payload}, got {r.trigger_reasons}"


# ─── 4 цифры: всё «правильно», но цифры противоречат ────────────────────


class TestFourFieldsContradictions:
    """L0 (Q+dH+L+wastewater) сами по себе валидные, но в комбинации абсурд."""

    def test_q_micro_with_long_l(self):
        """Q=0.05 (микро) + L=600 (длинная для микро Q) — абсурд."""
        L0 = L0Input(Q_m3h=0.05, dH_m=5, L_m=600, wastewater_type="domestic")
        r = select_pumps(L0)
        # Должны быть 2 trigger'а
        assert "auto_q_micro" in r.trigger_reasons
        assert "auto_l_long_zhukovsky" in r.trigger_reasons

    def test_q_high_with_short_l_no_dh(self):
        """Q=600 (магистральный) + L=10 + dH=0 — несоразмерно."""
        L0 = L0Input(Q_m3h=600, dH_m=0, L_m=10, wastewater_type="domestic")
        r = select_pumps(L0)
        assert "auto_q_high" in r.trigger_reasons

    def test_clean_water_with_industrial_volume(self):
        """clean_water (питьевая вода) + Q=2000 м³/ч — это уже водопровод города,
        а не объектный калькулятор."""
        L0 = L0Input(Q_m3h=2000, dH_m=20, L_m=100, wastewater_type="clean_water")
        r = select_pumps(L0)
        assert "auto_q_high" in r.trigger_reasons
        assert r.engineer_handoff_required is True

    def test_fire_protection_with_micro_q(self):
        """fire_protection + Q=0.5 — пожарка с микро-расходом? Бессмыслица."""
        L0 = L0Input(Q_m3h=0.5, dH_m=5, L_m=10, wastewater_type="fire_protection")
        r = select_pumps(L0)
        # fire_protection всегда handoff
        assert "auto_fire_protection" in r.trigger_reasons


# ─── Множественные ошибки разом (3+ trigger'а) ──────────────────────────


class TestMultipleErrors:
    """Реальные «опечатки в спешке»: несколько полей сразу неправильны."""

    def test_q_micro_and_dh_negative(self):
        """Q=0.01 + dH=-30: short-circuit при H_full<=0 (no_head + dh_negative).

        После short-circuit auto_q_micro не вычисляется (расчёт остановлен),
        но auto_dh_negative ставится явно. Главное — что калькулятор НЕ
        возвращает «успешный» подбор и handoff обязателен.
        """
        L0 = L0Input(Q_m3h=0.01, dH_m=-30)
        r = select_pumps(L0)
        # Short-circuit case
        assert "auto_no_head_required" in r.trigger_reasons
        assert "auto_dh_negative" in r.trigger_reasons
        assert r.engineer_handoff_required is True
        # Suggestions включают подсказку про Q и про dH
        assert len(r.suggestions) >= 2  # Q_m3h + dH_m
        # Suggestions содержат Q и dH
        fields = {s.field for s in r.suggestions}
        assert "Q_m3h" in fields
        assert "dH_m" in fields

    def test_q_high_and_l_long_and_h_high(self):
        """Q=1000 + L=3000 + dH=150 — большая магистраль с большим напором."""
        L0 = L0Input(Q_m3h=1000, dH_m=150, L_m=3000, wastewater_type="industrial")
        r = select_pumps(L0)
        # Минимум 4 trigger: q_high + l_long + h_high + industrial
        triggers_we_care = {"auto_q_high", "auto_l_long_zhukovsky", "auto_h_high", "auto_industrial"}
        assert triggers_we_care.issubset(set(r.trigger_reasons))
        assert r.engineer_handoff_required is True

    def test_l1_overload_4_triggers(self):
        """L1: горячая жидкость + Эльбрус + I категория + Ex."""
        L0 = L0Input(Q_m3h=20)
        L1 = L1Input(
            liquid_temp_c=80,
            altitude_m=3000,
            reliability_category="I",
            Ex_required=True,
        )
        r = select_pumps(L0, L1)
        triggers_expected = {
            "auto_npsh_hot", "auto_altitude_extreme",
            "auto_category_I", "auto_ex",
        }
        assert triggers_expected.issubset(set(r.trigger_reasons)), \
            f"Expected {triggers_expected}, got {r.trigger_reasons}"


# ─── Реалистичные сценарии менеджера ОП (из памяти эталонов) ──────────


class TestRealisticScenarios:
    """Эталонные кейсы из реальных КП, без trigger'ов."""

    def test_engineer_kp_q05_domestic(self):
        """Q=0.5 м³/ч коттедж — один из самых частых сценариев Серво-Юг."""
        L0 = L0Input(Q_m3h=0.5, dH_m=4, L_m=12, wastewater_type="domestic")
        r = select_pumps(L0)
        # Не должно быть micro-trigger (0.5 > 0.1)
        assert "auto_q_micro" not in r.trigger_reasons
        assert r.candidates_total > 0
        # Должен найти хотя бы budget вариант
        assert r.results.budget is not None

    def test_etalon_vbd_ekb_q540(self):
        """Эталон ВБД Екб К2=540 л/с (ливневая)."""
        L0 = L0Input(Q_m3h=540 * 3.6, dH_m=10, L_m=200, wastewater_type="drainage")
        r = select_pumps(L0)
        # Q≈1944 — должен быть q_high
        assert "auto_q_high" in r.trigger_reasons


# ─── Все trigger'ы в одной функции (smoke) ──────────────────────────


def test_all_known_triggers_can_fire():
    """Sanity: каждый из известных триггеров должен срабатывать на каком-то input."""
    known_triggers = {
        "auto_q_high": L0Input(Q_m3h=600),
        "auto_q_micro": L0Input(Q_m3h=0.01),
        "auto_h_high": L0Input(Q_m3h=20, dH_m=200),
        "auto_dh_negative": L0Input(Q_m3h=20, dH_m=-10),
        "auto_l_long_zhukovsky": L0Input(Q_m3h=20, L_m=600),
        "auto_industrial": L0Input(Q_m3h=20, wastewater_type="industrial"),
        "auto_fire_protection": L0Input(Q_m3h=20, wastewater_type="fire_protection"),
    }
    for trigger_name, l0 in known_triggers.items():
        r = select_pumps(l0)
        assert trigger_name in r.trigger_reasons, \
            f"Expected {trigger_name} to fire on {l0}, got {r.trigger_reasons}"


def test_all_l1_triggers_can_fire():
    """Sanity: L1-зависимые триггеры тоже должны срабатывать."""
    L0_base = L0Input(Q_m3h=20)
    cases = {
        "auto_velocity_low": L1Input(pipe_D_mm=500),
        "auto_velocity_high": L1Input(pipe_D_mm=20),
        "auto_altitude_extreme": L1Input(altitude_m=4500),
        "auto_groundwater_above_surface": L1Input(groundwater_level_m=5),
        "auto_npsh_hot": L1Input(liquid_temp_c=60),
        "auto_category_I": L1Input(reliability_category="I"),
        "auto_ex": L1Input(Ex_required=True),
        "auto_inflow_exceeds_pump": L1Input(inflow_per_hour_m3=1000),
    }
    for trigger_name, l1 in cases.items():
        r = select_pumps(L0_base, l1)
        assert trigger_name in r.trigger_reasons, \
            f"Expected {trigger_name} for {l1}, got {r.trigger_reasons}"
