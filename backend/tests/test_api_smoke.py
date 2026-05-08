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
    """Эталонный Мысхако-кейс: Q=21.2, H=10. Должен подобрать насос в budget-сегменте.

    Не закрепляем конкретный бренд (после расширения БД до 284 насосов
    могут конкурировать LEO/Fancy/KAIQUAN/Pedrollo). Главное —
    алгоритм находит подходящий вариант с разумной ценой.
    """
    r = client.post(
        "/select/quick",
        json={"Q_m3h": 21.2, "dH_m": 10.0, "L_m": 0.0, "wastewater_type": "domestic"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["results"]["budget"] is not None
    # Бренд может быть из топ-конкурентов в budget сегменте
    brand = body["results"]["budget"]["brand"]
    assert brand in ("KAIQUAN", "LEO Group", "Fancy", "Pedrollo", "ANTARUS"), \
        f"Неожиданный бренд в budget: {brand}"


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


# ---------------------- Phase 12: DOCX опросник ----------------------


def test_empty_questionnaire_docx_generates():
    r = client.post("/handoff/empty-questionnaire-docx")
    assert r.status_code == 200
    # DOCX = ZIP, заголовок PK
    assert r.content[:2] == b"PK"
    assert len(r.content) > 5000


def test_select_from_file_rejects_non_docx():
    r = client.post(
        "/select/from-file",
        files={"file": ("test.pdf", b"not docx", "application/pdf")},
    )
    assert r.status_code == 400


def test_select_from_file_empty_returns_missing_fields():
    """Пустой DOCX → нет L0, missing_fields содержит Q_M3H."""
    empty = client.post("/handoff/empty-questionnaire-docx").content
    r = client.post(
        "/select/from-file",
        files={
            "file": (
                "empty.docx",
                empty,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["L0"] is None
    assert "Q_M3H" in body["missing_fields"]
    assert body["selection"] is None


def test_select_from_file_with_prefilled_runs_selection():
    """Опросник с предзаполнением через /handoff/questionnaire-docx → /select/from-file → подбор."""
    # Шаг 1: первичный подбор
    quick = client.post(
        "/select/quick",
        json={"Q_m3h": 21.2, "dH_m": 15.0, "L_m": 120.0, "wastewater_type": "domestic"},
    ).json()

    # Шаг 2: получить DOCX с предзаполнением
    r_docx = client.post(
        "/handoff/questionnaire-docx",
        json={
            "selection": quick,
            "object_name": "Test object",
            "city": "Сочи",
        },
    )
    assert r_docx.status_code == 200

    # Шаг 3: вернуть тот же DOCX как «заполненный клиентом»
    r_select = client.post(
        "/select/from-file",
        files={
            "file": (
                "filled.docx",
                r_docx.content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        },
    )
    assert r_select.status_code == 200
    body = r_select.json()
    assert body["L0"]["Q_m3h"] == 21.2
    assert body["L0"]["wastewater_type"] == "domestic"
    assert body["metadata"]["OBJECT_NAME"] == "Test object"
    assert body["selection"] is not None
    assert body["selection"]["results"]["budget"] is not None
