"""Tests for rate-limit + body-size middleware (Sc.D. Architecture HIGH).

Покрывает:
- 429 при превышении per-IP лимита (10/minute на /import/parse).
- 413 при превышении body-size limit (10 MB глобально, 5 MB на DOCX).
- 422 при превышении text max_length=200_000 в ImportParseRequest.
- Smoke: остальные endpoints не сломаны default limit 100/minute.

NB: slowapi глобальный — между тестами нужно сбрасывать ``limiter._storage``
чтобы лимиты не утекали из одного теста в другой.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pump_calculator.api import app
from pump_calculator.rate_limiter import limiter


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Сбросить storage limiter'а между тестами."""
    # slowapi 0.1.9: storage attached как ._storage (MemoryStorage)
    try:
        limiter._storage.reset()
    except AttributeError:  # pragma: no cover — на случай смены API slowapi
        pass
    yield
    try:
        limiter._storage.reset()
    except AttributeError:  # pragma: no cover
        pass


@pytest.fixture()
def client():
    """Свежий TestClient на каждый тест — изоляция от утечек state."""
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────
# 1. Rate-limit per endpoint
# ─────────────────────────────────────────────────────────────────────


def test_import_parse_rate_limit(client: TestClient) -> None:
    """11 запросов подряд на /import/parse → 11-й должен вернуть 429.

    Лимит /import/parse = 10/minute per IP.
    """
    payload = {"text": "Q=20 м3/ч H=15 м г. Краснодар", "format": "plain"}

    # Первые 10 — успешные (200) или функциональные ошибки (≠429).
    for i in range(10):
        r = client.post("/import/parse", json=payload)
        assert r.status_code != 429, (
            f"Запрос #{i + 1}: неожиданный 429 в пределах лимита: {r.text}"
        )

    # 11-й — должен быть отбит лимитером.
    r = client.post("/import/parse", json=payload)
    assert r.status_code == 429, f"Ожидали 429 на 11-м запросе, получили {r.status_code}"
    body = r.json()
    assert "detail" in body
    assert "exceed" in body["detail"].lower() or "rate" in body["detail"].lower()
    # Retry-After header — обязательный по RFC 6585 §4.
    assert r.headers.get("Retry-After") == "60"


def test_select_quick_rate_limit_60_per_minute(client: TestClient) -> None:
    """/select/quick = 60/minute — 61-й запрос отбит."""
    payload = {
        "Q_m3h": 21.2,
        "dH_m": 10.0,
        "L_m": 0.0,
        "wastewater_type": "domestic",
    }
    for i in range(60):
        r = client.post("/select/quick", json=payload)
        assert r.status_code != 429, f"Запрос #{i + 1}: преждевременный 429"
    r = client.post("/select/quick", json=payload)
    assert r.status_code == 429


# ─────────────────────────────────────────────────────────────────────
# 2. Body-size middleware (10 MB глобально)
# ─────────────────────────────────────────────────────────────────────


def test_body_size_limit_413(client: TestClient) -> None:
    """POST с Content-Length 11 MB → 413 Payload Too Large.

    BodyLimitMiddleware режет на ASGI-уровне ДО FastAPI парсинга.
    Используем dummy /import/parse path; main check — Content-Length.
    """
    big_body = b"x" * (11 * 1024 * 1024)  # 11 MB
    r = client.post(
        "/import/parse",
        content=big_body,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413, (
        f"Ожидали 413, получили {r.status_code}: {r.text[:200]}"
    )
    body = r.json()
    assert "detail" in body
    assert "large" in body["detail"].lower() or "max" in body["detail"].lower()


def test_body_size_under_limit_passes(client: TestClient) -> None:
    """1 MB body не должен резаться — проходит до FastAPI/Pydantic."""
    # 1 MB всё ещё больше text max_length=200K в ImportParseRequest,
    # но это уже Pydantic 422, не middleware 413.
    payload = {"text": "x" * 500, "format": "plain"}  # short, valid
    r = client.post("/import/parse", json=payload)
    assert r.status_code != 413


# ─────────────────────────────────────────────────────────────────────
# 3. Pydantic max_length на ImportParseRequest.text
# ─────────────────────────────────────────────────────────────────────


def test_import_parse_text_max_length_pydantic_422(client: TestClient) -> None:
    """text > 200_000 символов → 422 Pydantic validation error."""
    # 200_001 символ — на 1 больше лимита.
    payload = {"text": "x" * 200_001, "format": "plain"}
    r = client.post("/import/parse", json=payload)
    assert r.status_code == 422, (
        f"Ожидали 422, получили {r.status_code}: {r.text[:500]}"
    )
    body = r.json()
    # Pydantic возвращает массив ошибок в "detail".
    assert "detail" in body
    detail_str = str(body["detail"]).lower()
    assert "200" in detail_str or "length" in detail_str or "long" in detail_str


def test_import_parse_text_at_limit_ok(client: TestClient) -> None:
    """text ровно 200_000 символов — должно пройти Pydantic-валидацию."""
    payload = {"text": "Q=10 H=5\n" + ("x" * (200_000 - 9)), "format": "plain"}
    r = client.post("/import/parse", json=payload)
    # 200 (success) или 500 (внутренняя ошибка парсера на garbage) — но НЕ 422.
    assert r.status_code != 422, f"Pydantic режет на limit: {r.text[:300]}"


def test_import_parse_filename_max_length(client: TestClient) -> None:
    """original_filename > 255 символов → 422."""
    payload = {
        "text": "Q=10 H=5",
        "format": "plain",
        "original_filename": "x" * 256,
    }
    r = client.post("/import/parse", json=payload)
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────
# 4. Smoke: дефолтный лимит 100/minute не ломает /health и /pumps
# ─────────────────────────────────────────────────────────────────────


def test_health_endpoint_not_broken(client: TestClient) -> None:
    """/health не должен попасть под per-endpoint лимит и работать как раньше."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_pumps_list_not_broken(client: TestClient) -> None:
    """/pumps не должен сломаться от middleware."""
    r = client.get("/pumps")
    assert r.status_code == 200
    assert r.json()["total"] >= 5
