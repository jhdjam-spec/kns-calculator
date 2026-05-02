"""Smoke-тесты FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pump_calculator.api import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "name" in r.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["pumps_in_db"] >= 5


def test_select_quick_myshako():
    r = client.post(
        "/select/quick",
        json={"Q_m3h": 21.2, "dH_m": 10.0, "L_m": 0.0, "wastewater_type": "domestic"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["results"]["budget"] is not None
    assert body["results"]["budget"]["brand"] == "KAIQUAN"


def test_select_full():
    r = client.post(
        "/select",
        json={
            "L0": {"Q_m3h": 21.2, "dH_m": 10.0, "L_m": 0.0, "wastewater_type": "domestic"},
            "L1": {"reliability_category": "II", "Ex_required": False},
        },
    )
    assert r.status_code == 200


def test_pumps_list():
    r = client.get("/pumps")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 5
    assert any(p["brand"] == "KAIQUAN" for p in body["pumps"])


def test_get_specific_pump():
    r = client.get("/pumps/kaiquan-50wqs202-3")
    assert r.status_code == 200
    assert r.json()["model"].startswith("50WQ")


def test_get_pump_not_found():
    r = client.get("/pumps/nonexistent")
    assert r.status_code == 404


def test_coefficients():
    r = client.get("/coefficients")
    assert r.status_code == 200
    body = r.json()
    assert "pipe_roughness_mm" in body
    assert "K_gen_max" in body


def test_validation_invalid_Q():
    """Q=0 запрещено по схеме (gt=0)."""
    r = client.post(
        "/select/quick",
        json={"Q_m3h": 0, "dH_m": 10, "L_m": 0, "wastewater_type": "domestic"},
    )
    assert r.status_code == 422


def test_validation_invalid_wastewater():
    r = client.post(
        "/select/quick",
        json={"Q_m3h": 20, "dH_m": 10, "L_m": 0, "wastewater_type": "invalid"},
    )
    assert r.status_code == 422
