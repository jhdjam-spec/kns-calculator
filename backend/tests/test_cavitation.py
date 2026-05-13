"""Тесты модуля cavitation — Thoma σ + σ_3% по ISO 9906:2024.

Sc.D. audit 2026-05-13: заменяем примитивный `NPSHa - NPSHr >= 0.5`
полным анализом по ISO 9906:2024 + Karassik §22.7.
"""
from __future__ import annotations

import math

import pytest

from pump_calculator.cavitation import (
    THRESHOLD_MARGINAL_SUBMERSIBLE,
    THRESHOLD_MARGINAL_SURFACE,
    THRESHOLD_SAFE_SUBMERSIBLE,
    THRESHOLD_SAFE_SURFACE,
    analyze_cavitation,
    explain_cavitation_engineer,
    explain_cavitation_manager,
)


def test_safe_margin_2_0_submersible():
    """margin = 2.0 — безусловно safe для submersible (>1.3)."""
    # NPSHa=10, NPSHr=2.5, H=10 → σ_avail=1.0, σ_req=0.25 → margin=4.0
    r = analyze_cavitation(
        NPSHa_m=10.0, NPSHr_3pct_m=2.5, H_full_m=10.0,
        pump_type="submersible",
    )
    assert r.risk == "safe"
    assert r.margin == pytest.approx(4.0, abs=0.01)
    assert r.sigma_avail == pytest.approx(1.0, abs=0.01)
    assert r.sigma_req_3pct == pytest.approx(0.25, abs=0.01)
    assert r.recommendations == []
    assert "ISO 9906:2024" in r.risk_reason


def test_marginal_surface_vs_submersible():
    """margin 1.35 — surface marginal, submersible safe (разные пороги)."""
    # margin = 1.35 ровно между порогами:
    #   surface:    safe >= 1.5, marginal >= 1.3 → marginal
    #   submersible: safe >= 1.3, marginal >= 1.1 → safe
    # NPSHa = 1.35 * NPSHr → подобрать
    # H=10, NPSHr=3 → σ_req=0.3; нужен σ_avail=0.3*1.35=0.405 → NPSHa=4.05
    r_surface = analyze_cavitation(
        NPSHa_m=4.05, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="surface",
    )
    r_sub = analyze_cavitation(
        NPSHa_m=4.05, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="submersible",
    )
    assert r_surface.risk == "marginal"
    assert r_sub.risk == "safe"
    assert r_surface.margin == pytest.approx(1.35, abs=0.01)
    assert r_sub.margin == pytest.approx(1.35, abs=0.01)
    assert len(r_surface.recommendations) > 0


def test_warning_margin_1_1_surface():
    """margin 1.1 surface — warning (< 1.3)."""
    # NPSHa=3.3, NPSHr=3.0, H=10 → margin = 1.1
    r = analyze_cavitation(
        NPSHa_m=3.3, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="surface",
    )
    assert r.risk == "warning"
    assert r.margin == pytest.approx(1.1, abs=0.01)
    assert len(r.recommendations) >= 2
    # Должны быть рекомендации по увеличению NPSHa
    assert any("NPSHa" in rec for rec in r.recommendations)


def test_critical_margin_0_8():
    """margin 0.8 < 1.0 — critical (кавитация неизбежна)."""
    # NPSHa=2.4, NPSHr=3.0, H=10 → margin = 0.8
    r = analyze_cavitation(
        NPSHa_m=2.4, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="submersible",
    )
    assert r.risk == "critical"
    assert r.margin == pytest.approx(0.8, abs=0.01)
    assert any("КРИТИЧНО" in rec for rec in r.recommendations)
    # Должна быть подсказка по max NPSHr (NPSHa * 0.7)
    assert any("0.7" in rec or "1.7" in rec for rec in r.recommendations)


def test_hot_liquid_50c_reduces_margin():
    """T=50°C → margin × 0.9 (conservative P_vapor correction)."""
    # Без коррекции: NPSHa=5, NPSHr=3, H=10 → margin = (5/10)/(3/10) = 1.667
    # С T=50°C: × 0.9 → 1.5
    r_cold = analyze_cavitation(
        NPSHa_m=5.0, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="submersible",
        liquid_temp_c=20.0,
    )
    r_hot = analyze_cavitation(
        NPSHa_m=5.0, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="submersible",
        liquid_temp_c=50.0,
    )
    assert r_cold.margin == pytest.approx(1.667, abs=0.01)
    assert r_hot.margin == pytest.approx(1.667 * 0.9, abs=0.01)
    # Cold safe для submersible (>=1.3), hot всё ещё safe (1.5 >= 1.3)
    assert r_cold.risk == "safe"
    assert r_hot.risk == "safe"


def test_h_full_zero_returns_safe_edge():
    """H_full = 0 — статика, кавитация невозможна (edge case)."""
    r = analyze_cavitation(
        NPSHa_m=5.0, NPSHr_3pct_m=3.0, H_full_m=0.0,
        pump_type="submersible",
    )
    assert r.risk == "safe"
    assert r.H_full_m == 0.0
    assert math.isinf(r.margin)
    assert "статика" in r.risk_reason.lower() or "H_full" in r.risk_reason


def test_npshr_zero_backward_compat():
    """NPSHr=0 (нет в паспорте) — marginal с рекомендациями (backward compat)."""
    r = analyze_cavitation(
        NPSHa_m=5.0, NPSHr_3pct_m=0.0, H_full_m=10.0,
        pump_type="submersible",
    )
    assert r.risk == "marginal"
    assert math.isinf(r.margin)
    assert "NPSHr" in r.risk_reason
    # должна быть рекомендация запросить NPSH-кривую
    assert any("NPSH" in rec for rec in r.recommendations)


def test_multistage_strict_threshold():
    """Multistage насос использует строгие пороги (1.5/1.3) как surface."""
    # margin 1.4 → surface marginal, multistage marginal, submersible safe
    r_multi = analyze_cavitation(
        NPSHa_m=4.2, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="multistage",
    )
    r_sub = analyze_cavitation(
        NPSHa_m=4.2, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="submersible",
    )
    assert r_multi.margin == pytest.approx(1.4, abs=0.01)
    assert r_multi.risk == "marginal"  # < 1.5 для multistage
    assert r_sub.risk == "safe"  # >= 1.3 для submersible


def test_thresholds_constants():
    """Sanity-check на константы: surface строже submersible."""
    assert THRESHOLD_SAFE_SURFACE > THRESHOLD_SAFE_SUBMERSIBLE
    assert THRESHOLD_MARGINAL_SURFACE > THRESHOLD_MARGINAL_SUBMERSIBLE
    assert THRESHOLD_SAFE_SURFACE == 1.5
    assert THRESHOLD_SAFE_SUBMERSIBLE == 1.3


def test_explain_engineer_contains_iso_citation():
    """explain_cavitation_engineer возвращает текст с формулой и ISO."""
    r = analyze_cavitation(
        NPSHa_m=3.3, NPSHr_3pct_m=3.0, H_full_m=10.0,
        pump_type="surface",
    )
    text = explain_cavitation_engineer(r, "surface")
    assert "ISO 9906:2024" in text
    assert "σ_avail" in text or "sigma" in text.lower()
    assert "Margin" in text or "margin" in text.lower()
    assert "3.30" in text or "3.3" in text  # NPSHa value
    # инженерный текст содержит цифры
    assert f"{r.margin:.2f}" in text


def test_explain_manager_differentiates_by_risk():
    """explain_cavitation_manager даёт разный текст для разных risks."""
    # critical
    r_crit = analyze_cavitation(
        NPSHa_m=2.0, NPSHr_3pct_m=3.0, H_full_m=10.0, pump_type="submersible",
    )
    assert r_crit.risk == "critical"
    mgr_crit = explain_cavitation_manager(r_crit)
    assert "колес" in mgr_crit.lower() or "ремонт" in mgr_crit.lower()

    # safe
    r_safe = analyze_cavitation(
        NPSHa_m=10.0, NPSHr_3pct_m=2.0, H_full_m=10.0, pump_type="submersible",
    )
    assert r_safe.risk == "safe"
    mgr_safe = explain_cavitation_manager(r_safe)
    assert "норм" in mgr_safe.lower() or "паспортн" in mgr_safe.lower()


def test_realistic_case_high_altitude_kns():
    """Реалистичный кейс: КНС в горах, NPSHa упал, насос с обычным NPSHr.

    Эльбрус 4000 м: P_atm ≈ 60 кПа, NPSHa ≈ 6 м (вместо 10).
    Канализационный насос submersible NPSHr=4 м, H=15 м.
    σ_avail=6/15=0.4, σ_req=4/15=0.267, margin=1.5 → safe submersible.
    """
    r = analyze_cavitation(
        NPSHa_m=6.0, NPSHr_3pct_m=4.0, H_full_m=15.0,
        pump_type="submersible",
        liquid_temp_c=15.0,
    )
    assert r.risk == "safe"
    assert r.margin == pytest.approx(1.5, abs=0.01)


def test_realistic_case_multistage_critical():
    """Многоступенчатый насос: ISO 9906 более строг.

    Surface multistage, NPSHa=3.5, NPSHr_3% = 3.0 м, H=50.
    margin = (3.5/50) / (3.0/50) = 1.167 < 1.5 (multistage safe порог) → warning.
    """
    r = analyze_cavitation(
        NPSHa_m=3.5, NPSHr_3pct_m=3.0, H_full_m=50.0,
        pump_type="multistage",
    )
    assert r.risk == "warning"
    assert r.margin == pytest.approx(1.167, abs=0.01)
