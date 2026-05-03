"""Тесты Phase 4: генерация PDF hand-off пакетов."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pump_calculator import select_pumps
from pump_calculator.api import app
from pump_calculator.handoff import generate_bom_pdf, generate_questionnaire_pdf
from pump_calculator.schemas import L0Input

client = TestClient(app)


@pytest.fixture
def sample_result():
    """Базовый случай — Мысхако-подобный вход."""
    return select_pumps(L0Input(Q_m3h=21.2, dH_m=10.0, L_m=0.0, wastewater_type="domestic"))


# ------------- questionnaire PDF -------------


def test_questionnaire_pdf_returns_bytes(sample_result):
    """Опросник генерится и возвращает bytes больше 1 кБ."""
    pdf = generate_questionnaire_pdf(sample_result)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf.startswith(b"%PDF-")


def test_questionnaire_pdf_contains_metadata(sample_result):
    """PDF содержит signature и нужные заголовки в metadata."""
    pdf = generate_questionnaire_pdf(sample_result, object_name="Тестовый объект")
    # PDF имеет хвост %%EOF
    assert b"%%EOF" in pdf


def test_questionnaire_pdf_with_full_metadata(sample_result):
    """Передаём все опциональные поля шапки."""
    pdf = generate_questionnaire_pdf(
        sample_result,
        object_name="Здание ТРЦ",
        client_company="ООО Ромашка",
        client_contact="Иванов И.И., +7-900-123-45-67",
        city="Москва",
        kp_number="КП-2026-0042",
    )
    assert len(pdf) > 1000


# ------------- BOM PDF -------------


def test_bom_pdf_returns_bytes(sample_result):
    """BOM генерится и возвращает bytes."""
    pdf = generate_bom_pdf(sample_result)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf.startswith(b"%PDF-")


def test_bom_pdf_for_industrial(sample_result):
    """BOM для другого типа стоков тоже должен генериться."""
    res = select_pumps(L0Input(Q_m3h=50, dH_m=20, L_m=200, wastewater_type="industrial"))
    pdf = generate_bom_pdf(res)
    assert len(pdf) > 1000


def test_bom_pdf_handles_empty_segments():
    """Если в каком-то сегменте нет насосов — PDF всё равно генерится."""
    # Очень специфический Q — может быть пустой premium
    res = select_pumps(L0Input(Q_m3h=8, dH_m=5, L_m=0, wastewater_type="domestic"))
    pdf = generate_bom_pdf(res)
    assert len(pdf) > 1000


# ------------- API endpoints -------------


def test_api_handoff_questionnaire_endpoint():
    """POST /handoff/questionnaire возвращает PDF."""
    # Сначала получаем результат подбора
    sel_response = client.post(
        "/select/quick",
        json={"Q_m3h": 21.2, "dH_m": 10, "L_m": 0, "wastewater_type": "domestic"},
    )
    assert sel_response.status_code == 200
    selection = sel_response.json()

    # Генерим опросник
    response = client.post(
        "/handoff/questionnaire",
        json={"selection": selection, "object_name": "Тестовый КНС"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1000


def test_api_handoff_bom_endpoint():
    """POST /handoff/bom возвращает PDF."""
    sel_response = client.post(
        "/select/quick",
        json={"Q_m3h": 21.2, "dH_m": 10, "L_m": 0, "wastewater_type": "domestic"},
    )
    selection = sel_response.json()

    response = client.post("/handoff/bom", json=selection)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1000


def test_api_handoff_minimal_request():
    """Минимальный запрос на questionnaire — без шапки."""
    sel_response = client.post(
        "/select/quick",
        json={"Q_m3h": 30, "dH_m": 15, "L_m": 100, "wastewater_type": "drainage"},
    )
    selection = sel_response.json()

    response = client.post("/handoff/questionnaire", json={"selection": selection})
    assert response.status_code == 200
