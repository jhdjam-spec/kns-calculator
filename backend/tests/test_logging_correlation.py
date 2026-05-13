"""Tests для observability: structlog + correlation IDs + Sentry stub.

Покрывают:
1. CorrelationIdMiddleware генерит request_id если клиент не прислал.
2. Middleware пробрасывает входящий X-Request-ID без изменения.
3. Response всегда содержит X-Request-ID header.
4. ``init_sentry()`` возвращает False, если SENTRY_DSN не задан.
5. ``capture_exception()`` всегда работает (даже без sentry-sdk) — пишет в structlog.
"""
from __future__ import annotations

import re
import uuid

import structlog
from fastapi.testclient import TestClient

from pump_calculator.api import app
from pump_calculator.error_reporting import capture_exception, init_sentry

client = TestClient(app)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def test_request_id_generated_when_not_provided() -> None:
    """Без X-Request-ID header → middleware генерит валидный UUID4."""
    r = client.get("/health")
    assert r.status_code in (200, 503)  # 503 если pumps.json не загружен
    rid = r.headers.get("X-Request-ID")
    assert rid, "X-Request-ID header missing on response"
    assert _UUID_RE.match(rid), f"X-Request-ID не UUID-формат: {rid!r}"


def test_request_id_preserved_when_provided() -> None:
    """Клиентский X-Request-ID должен пройти насквозь (для frontend ↔ backend трассировки)."""
    incoming = "client-trace-" + uuid.uuid4().hex[:12]
    r = client.get("/health", headers={"X-Request-ID": incoming})
    assert r.headers.get("X-Request-ID") == incoming


def test_each_request_has_unique_request_id() -> None:
    """Два запроса без header → два разных request_id."""
    r1 = client.get("/")
    r2 = client.get("/")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


def test_sentry_no_dsn_returns_false(monkeypatch) -> None:
    """Без SENTRY_DSN env → init_sentry() = False (graceful no-op)."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry() is False


def test_sentry_empty_dsn_returns_false(monkeypatch) -> None:
    """Пустая строка в SENTRY_DSN не считается валидной конфигурацией."""
    monkeypatch.setenv("SENTRY_DSN", "   ")
    assert init_sentry() is False


def test_capture_exception_logs_without_sentry(capsys) -> None:
    """capture_exception работает даже если sentry-sdk не установлен.

    Главное — exception не теряется: structlog пишет error_captured event.
    """
    try:
        raise ValueError("boom test")
    except ValueError as e:
        capture_exception(e, endpoint="/test", q_m3h=21.2)

    out = capsys.readouterr().out
    assert "error_captured" in out
    # Структурированный лог должен включать класс исключения как поле / часть строки.
    assert "ValueError" in out
    # Контекст должен попасть в JSON / pretty-output.
    assert "endpoint" in out or "/test" in out


def test_contextvars_cleared_between_requests() -> None:
    """После запроса structlog.contextvars пуст — иначе утечка request_id в фоновые таски."""
    client.get("/health")
    # После запроса contextvars должны быть очищены middleware finally-блоком.
    ctx = structlog.contextvars.get_contextvars()
    assert "request_id" not in ctx
    assert "method" not in ctx
    assert "path" not in ctx
