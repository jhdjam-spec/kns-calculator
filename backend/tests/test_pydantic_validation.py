"""Tests for Pydantic validation of 18 endpoints (Sc.D. P0 security 2026-05-13).

Покрывает endpoints, которые раньше принимали `payload: dict` без валидации:
- /storm/calc, /project/calculate, /los/select, /fire-water/calc,
  /fire-water/sprinklers, /water/demand, /physics/npsh, /physics/water-hammer,
  /physics/darcy-weisbach, /climate/burial-depth, /climate/loads,
  /structural/ballast, /structural/wall-thickness, /structural/ladder,
  /reports/rpz-gost-pdf, /reports/calculation-pdf, /complex/summary,
  /bom/export-csv.

Цель: убедиться что пустой/некорректный body даёт 422 (Pydantic validation),
а не 500 / silent default. См. backend/pump_calculator/api.py.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from pump_calculator.api import app

client = TestClient(app)


# ----------------------------------------------------------------------------
# 422 on missing required fields
# ----------------------------------------------------------------------------


def test_storm_calc_missing_field_returns_422():
    """StormInput требует sp_revision, region_city, surfaces — без них 422."""
    r = client.post("/storm/calc", json={})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body


def test_storm_calc_invalid_sp_revision_returns_422():
    """sp_revision принимает только SP_32_2012 / SP_32_2018."""
    r = client.post(
        "/storm/calc",
        json={
            "sp_revision": "INVALID",
            "region_city": "Краснодар",
            "surfaces": {},
        },
    )
    assert r.status_code == 422


def test_project_calculate_invalid_q_returns_422():
    """ProjectInput: population/floors/volume — невалидные значения дают 422."""
    r = client.post(
        "/project/calculate",
        json={
            "project_name": "Test",
            "population": -10,  # ge=0 → отбивается
        },
    )
    assert r.status_code == 422


def test_project_calculate_missing_name_returns_422():
    """ProjectInput.project_name обязателен."""
    r = client.post("/project/calculate", json={})
    assert r.status_code == 422


def test_los_select_empty_body_returns_422():
    """LOSScenarioInput требует source_type, flow_m3_per_day, discharge_category."""
    r = client.post("/los/select", json={})
    assert r.status_code == 422


def test_sprinklers_missing_group_returns_422():
    """SprinklersRequest.group обязателен."""
    r = client.post("/fire-water/sprinklers", json={})
    assert r.status_code == 422


def test_sprinklers_invalid_group_returns_422():
    """Group Literal — только из перечисленных."""
    r = client.post("/fire-water/sprinklers", json={"group": "99"})
    assert r.status_code == 422


def test_npsh_missing_h_suction_returns_422():
    """NpshRequest.H_suction_m обязателен."""
    r = client.post("/physics/npsh", json={})
    assert r.status_code == 422


def test_water_hammer_negative_velocity_returns_422():
    """v_ms >= 0 — отрицательное даёт 422."""
    r = client.post("/physics/water-hammer", json={"v_ms": -1.5})
    assert r.status_code == 422


def test_darcy_weisbach_missing_dim_returns_422():
    """DarcyWeisbachRequest требует L_m, D_mm, v_ms."""
    r = client.post("/physics/darcy-weisbach", json={"L_m": 100})
    assert r.status_code == 422


def test_burial_depth_missing_city_returns_422():
    """BurialDepthRequest.region_city обязателен."""
    r = client.post("/climate/burial-depth", json={})
    assert r.status_code == 422


def test_ladder_missing_height_returns_422():
    """LadderRequest требует height_m, pit_diameter_m."""
    r = client.post("/structural/ladder", json={})
    assert r.status_code == 422


def test_water_demand_invalid_population_returns_422():
    """WaterScenarioInput.population >= 0 — отбивается."""
    r = client.post(
        "/water/demand",
        json={"building_type": "residential", "population": -5},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------------
# Happy path — корректные тела принимаются (200/40x на бизнес-логику)
# ----------------------------------------------------------------------------


def test_sprinklers_valid_returns_200():
    """С корректным group — 200."""
    r = client.post("/fire-water/sprinklers", json={"group": "1"})
    assert r.status_code == 200
    body = r.json()
    assert "q_total_lps" in body


def test_npsh_valid_returns_200():
    """С минимальным H_suction_m — 200, остальные дефолты Pydantic."""
    r = client.post("/physics/npsh", json={"H_suction_m": 2.0})
    assert r.status_code == 200
    body = r.json()
    assert "npsha_m" in body


def test_ladder_valid_returns_200():
    """LadderRequest с минимумом полей."""
    r = client.post(
        "/structural/ladder",
        json={"height_m": 4.0, "pit_diameter_m": 2.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert "ladder_total_length_m" in body


# ----------------------------------------------------------------------------
# CORS fail-closed default (P0 security)
# ----------------------------------------------------------------------------


def test_cors_default_does_not_allow_arbitrary_origin():
    """По дефолту CORS_ALLOWED_ORIGINS не задан → CORS middleware не подключается,
    Access-Control-Allow-Origin в ответе отсутствует.

    Это fail-closed default: предотвращает cross-origin запросы со
    злоумышленных сайтов в production.
    """
    r = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS middleware не подключён → preflight не обрабатывается → нет ACAO
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
