"""MLSS-based aerotank sizing (Metcalf & Eddy §8-4 eq. 8-22).

Phase 34+ (2026-05-13): P2 биология. Параллельный метод существующему
aerotank.py (расчёт по нагрузке n × a_i из СП 32).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pump_calculator.api import app
from pump_calculator.los.aerotank_sizing import calculate_aerotank_volume

client = TestClient(app)


class TestCalculateAerotankVolume:
    def test_bod_below_target_returns_zero(self):
        r = calculate_aerotank_volume(
            Q_m3_day=100, bod_in_mgL=10, bod_out_target=15
        )
        assert r["V_m3"] == 0.0
        assert "below target" in r.get("reason", "").lower() or r["bod_remove_mgL"] == 0.0

    def test_domestic_typical_scenario(self):
        """Q=1000 м³/сут, BOD=250→15, SRT=10, MLSS=3.5: V ≈ 224 м³."""
        r = calculate_aerotank_volume(
            Q_m3_day=1000.0, bod_in_mgL=250.0, bod_out_target=15.0,
            srt_days=10.0, mlss_g_L=3.5, Y=0.5, Kd=0.05,
        )
        # V = 1000·10·0.5·235 / (3500·(1+0.5)) = 1_175_000 / 5250 ≈ 223.8
        assert r["V_m3"] == pytest.approx(223.8, abs=1.0)
        assert r["V_with_safety_20pct_m3"] == pytest.approx(r["V_m3"] * 1.2, abs=0.5)

    def test_HRT_within_normal_range(self):
        """HRT норма 4-8 ч для бытовых стоков."""
        r = calculate_aerotank_volume(
            Q_m3_day=1000.0, bod_in_mgL=250.0, srt_days=10.0, mlss_g_L=3.5
        )
        assert 4.0 <= r["HRT_hours"] <= 8.0

    def test_extended_aeration_long_srt(self):
        """SRT=25 сут → V больше, HRT больше."""
        r_short = calculate_aerotank_volume(
            Q_m3_day=1000, bod_in_mgL=250, srt_days=5
        )
        r_long = calculate_aerotank_volume(
            Q_m3_day=1000, bod_in_mgL=250, srt_days=25
        )
        assert r_long["V_m3"] > r_short["V_m3"]
        assert r_long["HRT_hours"] > r_short["HRT_hours"]

    def test_higher_mlss_smaller_volume(self):
        """Больше MLSS → меньший объём аэротенка (V ∝ 1/MLSS)."""
        r_low = calculate_aerotank_volume(
            Q_m3_day=1000, bod_in_mgL=250, mlss_g_L=2.0
        )
        r_high = calculate_aerotank_volume(
            Q_m3_day=1000, bod_in_mgL=250, mlss_g_L=5.0
        )
        assert r_high["V_m3"] < r_low["V_m3"]

    def test_f_to_m_ratio_calculated(self):
        r = calculate_aerotank_volume(
            Q_m3_day=1000, bod_in_mgL=250, srt_days=10, mlss_g_L=3.5
        )
        # F:M в норме 0.2-0.5 для обычных аэротенков
        assert r["f_to_m_ratio"] > 0
        assert r["f_to_m_ratio"] < 1.0

    def test_notes_warn_on_short_HRT(self):
        """Очень высокий MLSS + малый SRT → HRT может быть < 4 ч."""
        r = calculate_aerotank_volume(
            Q_m3_day=1000, bod_in_mgL=250, srt_days=2, mlss_g_L=6.0
        )
        warnings = [n for n in r["notes"] if "HRT" in n and "< 4" in n]
        # SRT=2, MLSS=6: V = 1000·2·0.5·235 / 6000·(1+0.1) = 235_000/6600 = 35.6
        # HRT = 35.6/1000·24 = 0.85 ч < 4 → должна быть warning
        assert r["HRT_hours"] < 4.0
        assert len(warnings) >= 1


class TestAerotankSizingEndpoint:
    def test_endpoint_returns_volume(self):
        resp = client.post(
            "/los/aerotank-sizing",
            json={
                "Q_m3_day": 1000.0,
                "bod_in_mgL": 250.0,
                "bod_out_target": 15.0,
                "srt_days": 10.0,
                "mlss_g_L": 3.5,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "V_m3" in body
        assert body["V_m3"] == pytest.approx(223.8, abs=1.0)
        assert body["V_with_safety_20pct_m3"] > body["V_m3"]
        assert "HRT_hours" in body
        assert "f_to_m_ratio" in body

    def test_endpoint_validation_q_must_be_positive(self):
        resp = client.post(
            "/los/aerotank-sizing",
            json={"Q_m3_day": 0, "bod_in_mgL": 250},
        )
        assert resp.status_code == 422

    def test_endpoint_validation_mlss_range(self):
        resp = client.post(
            "/los/aerotank-sizing",
            json={"Q_m3_day": 1000, "bod_in_mgL": 250, "mlss_g_L": 0.5},
        )
        assert resp.status_code == 422
