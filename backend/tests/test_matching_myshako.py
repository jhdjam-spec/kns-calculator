"""Тестовый кейс smoke-check на основе реального проекта АртВинд Мысхако.

Это НЕ эталон верификации — это smoke-test, что алгоритм даёт разумный
результат на типовом входе. Для настоящей верификации нужен калибровочный
набор из десятков размеченных кейсов с известными «правильными» подборами,
которого у нас сейчас нет.

Источник кейса:
  Шифр:    АВ.1382.08.23-М-НК
  Объект:  Здание многофункционального использования, Новороссийск
  Расход:  21.2 м³/ч
  КНС:     BloPlast PV-1590/3400 (H=15 м, P=3 кВт)
  Насос:   KAIQUAN 50WQ/S 20-22-3
  КПД:     46.4 % при Q=22.9, H=17.4

Тесты ниже проверяют:
  1. Алгоритм возвращает что-то осмысленное в сегменте budget (не None).
  2. Гидравлические параметры в физически разумных пределах.
  3. Триггеры hand-off корректно срабатывают на edge cases.
"""

from __future__ import annotations

import pytest

from pump_calculator import select_pumps
from pump_calculator.schemas import L0Input


@pytest.fixture
def myshako_input() -> L0Input:
    """Вход тестового кейса (по реальному объекту АртВинд Мысхако)."""
    return L0Input(
        Q_m3h=21.2,
        dH_m=10.0,
        L_m=0.0,  # компактная КНС внутри корпуса BloPlast
        wastewater_type="domestic",
    )


def test_myshako_returns_kaiquan_in_budget(myshako_input):
    """Алгоритм должен вернуть KAIQUAN 50WQ/S 20-22-3 в сегменте budget."""
    result = select_pumps(myshako_input)
    assert result.results.budget is not None, "Бюджетный сегмент пустой — провал верификации"
    chosen = result.results.budget
    assert chosen.brand == "KAIQUAN"
    assert "50WQ" in chosen.model
    assert chosen.id == "kaiquan-50wqs202-3"


def test_myshako_score_above_threshold(myshako_input):
    """Composite score должен быть выше 0.55 (хороший подбор)."""
    result = select_pumps(myshako_input)
    assert result.results.budget is not None
    assert result.results.budget.score >= 0.55, (
        f"Score {result.results.budget.score} ниже порога 0.55 — алгоритм работает плохо"
    )


def test_myshako_aor_zone_is_por(myshako_input):
    """Q=21.2 при Q_BEP=22.9 → ratio=0.926 → должно быть POR (70-120%)."""
    result = select_pumps(myshako_input)
    assert result.results.budget is not None
    assert result.results.budget.aor_zone == "POR"


def test_myshako_hydraulics_reasonable(myshako_input):
    """Гидравлические параметры должны быть в разумных пределах."""
    result = select_pumps(myshako_input)
    c = result.computed
    # При L=0: H_тр = 0
    assert c.H_tr_m == 0
    # Скорость должна быть в [0.7, 4.0] для пластика
    assert 0.7 <= c.v_ms <= 4.0
    # H_full ≈ dH + H_м (с safety 5%) ≈ 10 + ~0.5 = ~10.5-11
    assert 10.0 <= c.H_full_m <= 13.0
    # D автоподобран — стандартный из ряда
    assert c.D_mm in {50, 63, 75, 90, 110, 125, 140, 160, 180, 200, 225, 250}


def test_myshako_no_critical_handoff_triggers(myshako_input):
    """Для типового кейса domestic / Q=21 / L=0 — handoff не должен быть обязательным."""
    result = select_pumps(myshako_input)
    # Допустимо предупреждение auto_low_match_count или auto_no_match для других сегментов,
    # но industrial / l_long / npsh_hot — НЕ должны срабатывать
    forbidden = {"auto_industrial", "auto_l_long_zhukovsky", "auto_npsh_hot", "auto_q_high", "auto_h_high"}
    intersection = set(result.trigger_reasons) & forbidden
    assert not intersection, f"Не должно быть критичных триггеров: {intersection}"


def test_myshako_industrial_should_handoff():
    """Если тот же кейс перенести на industrial — handoff обязателен."""
    result = select_pumps(L0Input(Q_m3h=21.2, dH_m=10.0, L_m=0.0, wastewater_type="industrial"))
    assert result.engineer_handoff_required
    assert "auto_industrial" in result.trigger_reasons


def test_long_trass_triggers_zhukovsky():
    """L>500 м должно триггерить расчёт гидроудара."""
    result = select_pumps(L0Input(Q_m3h=20.0, dH_m=15.0, L_m=2000.0, wastewater_type="domestic"))
    assert "auto_l_long_zhukovsky" in result.trigger_reasons


def test_high_q_triggers_handoff():
    """Q>500 м³/ч — выход за бюджетные серии, handoff обязателен."""
    result = select_pumps(L0Input(Q_m3h=600.0, dH_m=20.0, L_m=100.0, wastewater_type="domestic"))
    assert "auto_q_high" in result.trigger_reasons


def test_drainage_filter_works():
    """Дренаж: должны проходить насосы с free_passage>=10, не obязательно ≥50 как для domestic."""
    result = select_pumps(L0Input(Q_m3h=15.0, dH_m=8.0, L_m=50.0, wastewater_type="drainage"))
    # Хотя бы один сегмент должен быть заполнен
    assert any([result.results.budget, result.results.mid, result.results.premium])


def test_pumps_db_loads():
    """Sanity check: БД насосов загружается и не пустая."""
    from pump_calculator import catalog
    pumps = catalog.load_pumps()
    assert len(pumps) >= 5
    # Должен быть наш эталон
    ids = {p["id"] for p in pumps}
    assert "kaiquan-50wqs202-3" in ids
