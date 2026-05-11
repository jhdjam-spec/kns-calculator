"""Smoke-тесты POST /etl/classify (CRM-light классификатор писем).

Покрывает:
- success: типичный кейс ОЛ + КНС + шифр
- success: КП с производителем + домен trusted
- success: только subject без body
- 400: все три поля пустые
- success: незнакомый домен → trusted=False
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from pump_calculator.api import app

client = TestClient(app)


def test_classify_ol_kns_with_project_code():
    """Самый частый кейс — ОЛ на КНС с цифровым шифром."""
    r = client.post(
        "/etl/classify",
        json={
            "subject": "ОЛ на КНС-2 для жилого комплекса",
            "body": "Прошу подобрать оборудование по шифру 2799289. Спасибо.",
            "from_email": "zakaz@inservo.ru",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "ОЛ"
    assert body["object"] == "КНС"
    assert "2799289" in body["project_codes"]
    assert body["is_trusted_sender"] is True


def test_classify_kp_los_with_manufacturer():
    """КП на ЛОС с указанием Grundfos — все три маркера + trusted-домен."""
    r = client.post(
        "/etl/classify",
        json={
            "subject": "КП по ЛОС с насосами Grundfos",
            "body": "Шифр БСВП0001809, срок до конца месяца.",
            "from_email": "manager@mail.ru",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "КП"
    assert body["object"] == "ЛОС"
    assert body["manufacturer"] == "GRUNDFOS"
    assert "БСВП0001809" in body["project_codes"]
    assert body["is_trusted_sender"] is True


def test_classify_subject_only_no_body():
    """Только subject — должно работать (body опциональный)."""
    r = client.post(
        "/etl/classify",
        json={
            "subject": "ТЗ на ВНС от ANTARUS",
            "body": "",
            "from_email": "",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "ТЗ"
    assert body["object"] == "ВНС"
    assert body["manufacturer"] == "ANTARUS"
    assert body["is_trusted_sender"] is False


def test_classify_empty_body_returns_400():
    """Все три поля пустые → 400."""
    r = client.post(
        "/etl/classify",
        json={"subject": "", "body": "", "from_email": ""},
    )
    assert r.status_code == 400
    assert "пуст" in r.json()["detail"].lower()


def test_classify_unknown_domain_not_trusted():
    """Незнакомый домен → trusted=False, но классификация работает."""
    r = client.post(
        "/etl/classify",
        json={
            "subject": "Заявка с сайта",
            "body": "Проект 1578-22-НК",
            "from_email": "spam@evil.example.com",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "ЗАЯВКА"
    assert body["is_trusted_sender"] is False
    assert any("1578-22-НК" in c for c in body["project_codes"])
