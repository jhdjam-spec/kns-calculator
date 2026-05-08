"""Тесты Phase 25 — климатические расчёты."""
from __future__ import annotations

import pytest

from pump_calculator.climate import (
    FROST_DEPTH_BY_CITY_M,
    SOIL_FROST_FACTORS,
    calc_frost_depth_normative,
    calc_pipe_burial_depth,
    calc_seismic_load,
    calc_snow_load_pavilion,
    calc_wind_load_pavilion,
)

# ─── Глубина промерзания ────────────────────────────────────────────


def test_frost_depth_known_city():
    """Москва — 1.4 м, Краснодар — 0.8 м, Якутск — 3.0 м."""
    assert calc_frost_depth_normative("Москва")[0] == 1.4
    assert calc_frost_depth_normative("Краснодар")[0] == 0.8
    assert calc_frost_depth_normative("Якутск")[0] == 3.0


def test_frost_depth_unknown_city_fallback():
    """Неизвестный город → fallback 1.5 с предупреждением."""
    depth, source = calc_frost_depth_normative("Несуществующий")
    assert depth == 1.5
    assert "не найден" in source.lower()


def test_pipe_burial_typical_kns():
    """Краснодар, суглинок, DN200, без УГВ → ~0.8·1.0 + 0.3 = 1.1 м."""
    result = calc_pipe_burial_depth("Краснодар", "clay_loam", 200, has_groundwater=False)
    assert result.burial_depth_m == pytest.approx(1.1, abs=0.05)
    assert not result.insulation_required


def test_pipe_burial_large_dn_extra_margin():
    """DN>500 → +0.5 м запаса."""
    small = calc_pipe_burial_depth("Москва", "clay_loam", 200)
    large = calc_pipe_burial_depth("Москва", "clay_loam", 600)
    assert large.burial_depth_m == small.burial_depth_m + 0.2


def test_pipe_burial_yakutsk_insulation_required():
    """Якутск (d_fn=3.0) → требует утепления."""
    result = calc_pipe_burial_depth("Якутск", "clay_loam", 200)
    assert result.insulation_required
    assert result.insulation_thickness_mm >= 50


# ─── Нагрузки ────────────────────────────────────────────────────────


def test_snow_load_krasnodar_low():
    """Краснодар — снеговой район II, S_0=1.2 кПа, 50 м² крыши → 60 кН."""
    s, total, region, notes = calc_snow_load_pavilion("Краснодар", 50.0, "flat")
    assert s == pytest.approx(1.2, abs=0.05)
    assert total == pytest.approx(60, abs=2)


def test_snow_load_pitched_lower():
    """Двускатная крыша даёт μ=0.75 → нагрузка меньше плоской."""
    flat_s, _, _, _ = calc_snow_load_pavilion("Москва", 50.0, "flat")
    pitched_s, _, _, _ = calc_snow_load_pavilion("Москва", 50.0, "double_pitch")
    assert pitched_s < flat_s


def test_wind_load_increases_with_height():
    """С высотой павильона ветровая нагрузка растёт."""
    _, low_total, _, _ = calc_wind_load_pavilion("Москва", 3.0, 12.0)
    _, high_total, _, _ = calc_wind_load_pavilion("Москва", 12.0, 12.0)
    assert high_total > low_total


def test_seismic_low_intensity_ignored():
    """6 баллов — расчёт не обязателен."""
    K, F, notes = calc_seismic_load(6, 5000)
    assert any("не обязателен" in n for n in notes)


def test_seismic_high_intensity_force():
    """9 баллов, m=10000 кг → F = 0.20·10000·9.81/1000 = 19.62 кН."""
    K, F, notes = calc_seismic_load(9, 10_000)
    assert K == 0.20
    assert F == pytest.approx(19.62, abs=0.5)


def test_soil_factor_table():
    """Таблица k_h содержит все типы грунтов."""
    for soil in ("sand_dry", "sand_wet", "clay_loam", "clay", "rocky", "peat"):
        assert soil in SOIL_FROST_FACTORS
        assert SOIL_FROST_FACTORS[soil] > 0


def test_frost_db_has_major_cities():
    """Все ключевые города России в БД."""
    expected = ["Москва", "Санкт-Петербург", "Краснодар", "Екатеринбург", "Новосибирск", "Якутск"]
    for city in expected:
        assert city in FROST_DEPTH_BY_CITY_M
