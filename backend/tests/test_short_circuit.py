"""Тесты Phase 3K — расчёт тока КЗ для подбора Icu."""
from __future__ import annotations

import pytest

from pump_calculator.electrical import (
    TRANSFORMER_IMPEDANCES_MOHM,
    calc_short_circuit,
)


def test_8_standard_transformers():
    """Стандартные мощности трансформаторов 100..2500 кВА."""
    expected = {100, 160, 250, 400, 630, 1000, 1600, 2500}
    assert set(TRANSFORMER_IMPEDANCES_MOHM.keys()) == expected


def test_kz_on_busbars_250kva():
    """КЗ на шинах ТП 250 кВА: I_кз ≈ 9.2 кА."""
    result = calc_short_circuit(transformer_kva=250, cable_length_m=0)
    # Z = √(12² + 22²) ≈ 25.06 мОм = 0.02506 Ом
    # I = 400 / (√3 × 0.02506) = 400 / 0.0434 ≈ 9216 А ≈ 9.2 кА
    assert result.I_kz_ka == pytest.approx(9.2, abs=0.5)


def test_kz_on_busbars_1000kva():
    """1000 кВА: I_кз ≈ 30 кА."""
    result = calc_short_circuit(transformer_kva=1000, cable_length_m=0)
    assert result.I_kz_ka == pytest.approx(30.0, abs=2.0)


def test_kz_decreases_with_cable_length():
    """С удлинением кабеля I_кз падает."""
    short = calc_short_circuit(transformer_kva=400, cable_length_m=0)
    long_ = calc_short_circuit(transformer_kva=400, cable_length_m=200, cable_section_mm2=50)
    assert long_.I_kz_ka < short.I_kz_ka


def test_recommended_icu_with_reserve():
    """Icu выбирается с запасом 25%."""
    result = calc_short_circuit(transformer_kva=400)
    # I_кз ≈ 13.6 кА, target = 17 кА → Icu = 25
    assert result.recommended_icu_ka == 25


def test_nearest_kva_chosen():
    """Нестандартная мощность → ближайший стандарт."""
    result = calc_short_circuit(transformer_kva=500)    # ближайший 630 (отстояние 130 vs 100 → 630)
    assert result.transformer_kva in (400, 630)
    assert any("ближайший" in n.lower() for n in result.notes)


def test_notes_contain_calculation():
    """Notes содержат пошаговый расчёт."""
    result = calc_short_circuit(transformer_kva=250)
    assert any("Z_сум" in n for n in result.notes)
    assert any("I_кз" in n for n in result.notes)
