"""Тесты Q-H графика для PDF РПЗ (Phase 28)."""
from __future__ import annotations

import pytest


def test_qh_chart_returns_png_bytes():
    """Базовая проверка: функция возвращает PNG-байты валидного размера."""
    from pump_calculator.reports.qh_chart import render_qh_chart_png

    pump = {
        "brand": "KAIQUAN",
        "model": "65WQ/S223-2.2",
        "envelope": {
            "Q_min_m3h": 5,
            "Q_max_m3h": 30,
            "H_min_m": 6,
            "H_max_m": 25,
            "Q_BEP_m3h": 18,
            "H_BEP_m": 18,
        },
    }
    png = render_qh_chart_png(pump, duty_Q_m3h=20, duty_H_m=15)

    assert isinstance(png, bytes)
    assert len(png) > 5_000, "PNG слишком мал"
    # PNG signature
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "Не PNG"


def test_qh_chart_handles_missing_bep():
    """Если Q_BEP/H_BEP не заданы — fallback на середину envelope."""
    from pump_calculator.reports.qh_chart import render_qh_chart_png

    pump = {
        "brand": "Test",
        "model": "no-BEP",
        "envelope": {
            "Q_min_m3h": 10,
            "Q_max_m3h": 50,
            "H_min_m": 5,
            "H_max_m": 20,
        },
    }
    png = render_qh_chart_png(pump, duty_Q_m3h=25, duty_H_m=12)
    assert len(png) > 3_000


def test_qh_chart_with_explicit_curve():
    """Если задана qh_curve — используется напрямую."""
    from pump_calculator.reports.qh_chart import render_qh_chart_png

    pump = {
        "brand": "Test",
        "model": "explicit-curve",
        "envelope": {
            "Q_min_m3h": 0,
            "Q_max_m3h": 100,
            "H_min_m": 0,
            "H_max_m": 50,
            "Q_BEP_m3h": 50,
            "H_BEP_m": 30,
        },
        "qh_curve": [
            {"Q_m3h": 0, "H_m": 50},
            {"Q_m3h": 25, "H_m": 45},
            {"Q_m3h": 50, "H_m": 30},
            {"Q_m3h": 75, "H_m": 15},
            {"Q_m3h": 100, "H_m": 5},
        ],
    }
    png = render_qh_chart_png(pump, duty_Q_m3h=40, duty_H_m=35)
    assert len(png) > 5_000
