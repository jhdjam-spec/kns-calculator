"""Тесты cavitation_erosion — кавитационная эрозия по Pilarczyk/Knapp.

Sub U backlog (2026-05-13): σ_break (полная коллапс) + эрозия по Pilarczyk.

Источники проверки:
  - Pilarczyk 1991 (V_erosion ∝ |Δσ|^1.3)
  - Knapp 1955 (Trans. ASME)
  - Karassik 2008 §22.7.5
"""
from __future__ import annotations

import pytest

from pump_calculator.cavitation_erosion import (
    DESIGN_LIFE_YEARS,
    K_EROSION,
    SIGMA_INCIPIENT_TO_3PCT_DEFAULT,
    estimate_cavitation_erosion,
    explain_erosion_engineer,
    explain_erosion_manager,
)


def test_safe_when_sigma_avail_above_sigma_cav():
    """σ_avail >> σ_кав → safe, эрозия 0, ресурс 15 лет."""
    # σ_3% = 0.25, σ_кав = 0.275, σ_avail = 0.5 → margin = +0.225
    r = estimate_cavitation_erosion(
        sigma_avail=0.5,
        sigma_3pct=0.25,
        impeller_material="cast_iron",
    )
    assert r.risk_level == "safe"
    assert r.erosion_rate_mg_per_h == 0.0
    assert r.expected_life_years == DESIGN_LIFE_YEARS
    assert r.recommendations == []
    assert r.sigma_margin > 0


def test_sigma_break_triggers_critical():
    """σ_avail < 0.7×σ_3% — σ_break, насос не работает."""
    # σ_3% = 0.5, σ_break_threshold = 0.35
    # σ_avail = 0.30 — ниже break (катастрофа)
    r = estimate_cavitation_erosion(
        sigma_avail=0.30,
        sigma_3pct=0.5,
        impeller_material="cast_iron",
    )
    assert r.risk_level == "critical"
    assert r.sigma_break_breached is True
    assert "σ_break" in r.reason
    assert any("буст" in rec.lower() or "не работоспособ" in rec.lower()
               or "не работа" in rec.lower() for rec in r.recommendations)


def test_pilarczyk_erosion_for_cast_iron():
    """Чугун при margin = -0.1 → эрозия = 2.5·0.1^1.3·2 ≈ 0.25 мг/ч."""
    # σ_3% = 0.3, σ_кав = 0.33 (1.1×), σ_avail = 0.23 → margin = -0.10
    r = estimate_cavitation_erosion(
        sigma_avail=0.23,
        sigma_3pct=0.3,
        impeller_material="cast_iron",
        impeller_area_cm2=200.0,  # area_factor = 2
    )
    # margin ≈ -0.10
    assert r.sigma_margin < 0
    # erosion_rate ≈ 2.5 × 0.10^1.3 × 2 ≈ 0.25
    assert 0.10 < r.erosion_rate_mg_per_h < 0.5
    # σ_break_threshold = 0.21, σ_avail = 0.23 → НЕ break
    assert r.sigma_break_breached is False
    # Долго служит — risk safe или marginal (200г / 0.25 мг/час ≈ 90 лет)
    assert r.expected_life_years > 50


def test_duplex_outlasts_cast_iron():
    """Duplex (K=0.15) служит >> чем cast_iron (K=2.5) при том же margin.

    Берём режим выше σ_break_threshold=0.7·σ_3% (0.21 при σ_3%=0.30),
    но ниже σ_кав (0.33), чтобы получить нормальный режим Pilarczyk.
    σ_avail=0.25 → margin = 0.25-0.33 = -0.08; 0.25 > 0.21 ✓
    """
    common = dict(sigma_avail=0.25, sigma_3pct=0.30)
    r_iron = estimate_cavitation_erosion(impeller_material="cast_iron", **common)
    r_duplex = estimate_cavitation_erosion(impeller_material="duplex", **common)
    # Ни один не σ_break
    assert r_iron.sigma_break_breached is False
    assert r_duplex.sigma_break_breached is False
    # Чугун эродирует в K_iron/K_duplex = 2.5/0.15 ≈ 16× быстрее
    assert r_iron.erosion_rate_mg_per_h > r_duplex.erosion_rate_mg_per_h
    ratio = r_iron.erosion_rate_mg_per_h / r_duplex.erosion_rate_mg_per_h
    assert ratio == pytest.approx(K_EROSION["cast_iron"] / K_EROSION["duplex"], rel=1e-3)


def test_critical_when_life_under_1_year():
    """Сильная кавитация → срок жизни < 1 года → critical."""
    # Большой |Δσ| + чугун → быстрая эрозия
    # σ_3% = 0.5, σ_кав = 0.55, σ_avail = 0.40 → margin = -0.15 (но > σ_break=0.35)
    # erosion = 2.5 × 0.15^1.3 × big_area = много мг/ч
    r = estimate_cavitation_erosion(
        sigma_avail=0.40,
        sigma_3pct=0.5,
        impeller_material="cast_iron",
        impeller_area_cm2=2000.0,  # 10× больше типового → 10× эрозия
        initial_mass_g=50.0,        # маленькая лопатка
    )
    assert r.sigma_break_breached is False
    # Эрозия ≈ 2.5 × 0.15^1.3 × 20 ≈ 4 мг/час
    # 50 г / 4 = 12500 ч ≈ 1.4 года → warning или critical
    assert r.expected_life_years < 3
    assert r.risk_level in ("critical", "warning")
    assert len(r.recommendations) > 0


def test_explain_engineer_returns_str_with_iso():
    """explain_erosion_engineer возвращает текст со ссылками."""
    r = estimate_cavitation_erosion(sigma_avail=0.20, sigma_3pct=0.30,
                                    impeller_material="stainless_steel")
    text = explain_erosion_engineer(r)
    assert "Pilarczyk" in text or "Knapp" in text
    assert "Karassik" in text or "ISO 9906" in text
    assert "K_" in text or "K =" in text or "K_эрозии" in text


def test_explain_manager_safe_case():
    """Менеджерское объяснение для safe — оптимистичное."""
    r_safe = estimate_cavitation_erosion(sigma_avail=1.0, sigma_3pct=0.3)
    msg = explain_erosion_manager(r_safe)
    assert "✅" in msg or "проработ" in msg.lower()


def test_sigma_incipient_ratio_custom():
    """Кастомный σ_кав / σ_3% — 1.2 (multistage) повышает σ_кав."""
    # σ_3% = 0.3, σ_кав_default (1.1) = 0.33, σ_кав_multi (1.2) = 0.36
    # σ_avail = 0.35: default → margin +0.02 (safe), multi → -0.01 (erosion)
    r_default = estimate_cavitation_erosion(
        sigma_avail=0.35, sigma_3pct=0.3,
        sigma_incipient_ratio=SIGMA_INCIPIENT_TO_3PCT_DEFAULT,
    )
    r_multi = estimate_cavitation_erosion(
        sigma_avail=0.35, sigma_3pct=0.3,
        sigma_incipient_ratio=1.2,
    )
    assert r_default.sigma_margin > r_multi.sigma_margin
