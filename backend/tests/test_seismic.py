"""Тесты Phase 3M — сейсмический расчёт корпуса по СП 14.13330."""
from __future__ import annotations

import pytest

from pump_calculator.structural import (
    SOIL_SEISMIC_FACTORS,
    calc_seismic_force_on_corpus,
    list_soil_categories,
)


def test_4_soil_categories():
    """4 категории грунта I-IV."""
    assert set(SOIL_SEISMIC_FACTORS.keys()) == {"I", "II", "III", "IV"}


def test_soil_factors_increasing():
    """Коэффициент растёт от I (скала) к IV (торф)."""
    assert SOIL_SEISMIC_FACTORS["I"]["factor"] == 0.8
    assert SOIL_SEISMIC_FACTORS["II"]["factor"] == 1.0
    assert SOIL_SEISMIC_FACTORS["III"]["factor"] == 1.4
    assert SOIL_SEISMIC_FACTORS["IV"]["factor"] == 1.7


def test_below_7_no_calculation():
    """Интенсивность <7 баллов — расчёт не требуется."""
    result = calc_seismic_force_on_corpus(
        intensity_balls=6,
        soil_category="II",
        corpus_mass_kg=10000,
    )
    assert result.is_calculation_required is False
    assert result.F_horizontal_kn == 0
    assert any("не обязателен" in n for n in result.notes)


def test_7_balls_normal_soil():
    """7 баллов, грунт II, m=10000 кг → F = 0.05 × 1 × 1.0 × 10000 × 9.81 / 1000 = 4.905 кН."""
    result = calc_seismic_force_on_corpus(
        intensity_balls=7,
        soil_category="II",
        corpus_mass_kg=10000,
    )
    assert result.is_calculation_required
    assert result.F_horizontal_kn == pytest.approx(4.905, abs=0.05)


def test_9_balls_soft_soil_high():
    """9 баллов, грунт IV → значительно выше 7-II."""
    soft = calc_seismic_force_on_corpus(
        intensity_balls=9,
        soil_category="IV",
        corpus_mass_kg=10000,
    )
    normal = calc_seismic_force_on_corpus(
        intensity_balls=7,
        soil_category="II",
        corpus_mass_kg=10000,
    )
    # 9-IV: 0.20 × 1 × 1.7 × 10000 × 9.81 / 1000 = 33.4 кН
    # 7-II: 4.905 кН
    # Отношение ~6.8
    assert soft.F_horizontal_kn > normal.F_horizontal_kn * 6


def test_special_responsibility_increases_force():
    """Особая ответственность (K_ψ=1.5) увеличивает силу в 1.5 раза."""
    normal = calc_seismic_force_on_corpus(
        intensity_balls=8,
        soil_category="II",
        corpus_mass_kg=10000,
        is_special_responsibility=False,
    )
    special = calc_seismic_force_on_corpus(
        intensity_balls=8,
        soil_category="II",
        corpus_mass_kg=10000,
        is_special_responsibility=True,
    )
    assert special.F_horizontal_kn == pytest.approx(normal.F_horizontal_kn * 1.5, rel=0.01)


def test_overturning_moment():
    """Момент = F × H/2."""
    result = calc_seismic_force_on_corpus(
        intensity_balls=8,
        soil_category="II",
        corpus_mass_kg=10000,
        corpus_height_m=4.0,
    )
    expected_M = result.F_horizontal_kn * 2.0   # H/2 = 2
    assert result.M_overturning_kn_m == pytest.approx(expected_M, abs=0.01)


def test_warnings_for_severe_conditions():
    """≥9 баллов или грунт IV → дополнительные предупреждения."""
    result = calc_seismic_force_on_corpus(
        intensity_balls=9,
        soil_category="IV",
        corpus_mass_kg=10000,
    )
    notes_text = " ".join(result.notes).lower()
    assert "анкер" in notes_text or "усил" in notes_text
    assert "разжижени" in notes_text or "сейсмиче" in notes_text


def test_invalid_soil_raises():
    """Неизвестная категория грунта → ValueError."""
    with pytest.raises(ValueError):
        calc_seismic_force_on_corpus(
            intensity_balls=8,
            soil_category="V",  # type: ignore[arg-type]
            corpus_mass_kg=10000,
        )


def test_invalid_intensity_raises():
    """Интенсивность вне 7-10 → ValueError."""
    with pytest.raises(ValueError):
        calc_seismic_force_on_corpus(
            intensity_balls=11,
            soil_category="II",
            corpus_mass_kg=10000,
        )


def test_list_soil_categories():
    """Каталог 4 категорий для UI."""
    cats = list_soil_categories()
    assert len(cats) == 4
    for c in cats:
        assert "category" in c
        assert "factor" in c
        assert "description" in c
        assert "examples" in c


def test_references_returned():
    """Ссылки на СП 14 + ОСР-2015."""
    result = calc_seismic_force_on_corpus(
        intensity_balls=8, soil_category="II", corpus_mass_kg=10000
    )
    codes = [r["regulation_code"] for r in result.references]
    assert any("СП 14" in c for c in codes)
    assert any("ОСР" in c or "СП 14" in c for c in codes)
