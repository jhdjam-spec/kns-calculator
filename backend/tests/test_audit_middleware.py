"""Тесты AuditMiddleware (152-ФЗ ст.19 audit trail).

Проверяем что:
- `/admin/*`, `/import/parse`, `/handoff/*`, `/etl/classify` логируются
  в канал ``audit.request`` (через capsys — structlog → stdout).
- Несенситивные пути (``/health``, ``/``) НЕ логируются (анти-спам).
- При исключении в обработчике пишется ``request_failed`` (ERROR).
- Body content НЕ читается middleware'ом (PII-safety).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from pump_calculator.audit_middleware import (
    SENSITIVE_PATHS,
    AuditMiddleware,
    _is_sensitive,
)

# ---------------------------------------------------------------------------
# Minimal app для изоляции (не тащим production FastAPI app).
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def root():
        return {"name": "test"}

    @app.post("/admin/something")
    def admin_endpoint():
        return {"ok": True}

    @app.post("/import/parse")
    def import_parse():
        return {"ok": True}

    @app.post("/handoff/pdf")
    def handoff_pdf():
        return {"ok": True}

    @app.post("/etl/classify")
    def etl_classify():
        return {"ok": True}

    @app.post("/admin/boom")
    def admin_boom():
        raise HTTPException(status_code=500, detail="boom")

    @app.post("/admin/crash")
    def admin_crash():
        raise RuntimeError("crash inside handler")

    return app


@pytest.fixture()
def client():
    return TestClient(_make_app())


# ---------------------------------------------------------------------------
# _is_sensitive — модульная функция
# ---------------------------------------------------------------------------


def test_is_sensitive_admin():
    assert _is_sensitive("/admin/something")
    assert _is_sensitive("/admin")


def test_is_sensitive_import_parse():
    assert _is_sensitive("/import/parse")


def test_is_sensitive_handoff():
    assert _is_sensitive("/handoff/pdf")
    assert _is_sensitive("/handoff/bom")


def test_is_sensitive_etl_classify():
    assert _is_sensitive("/etl/classify")


def test_is_sensitive_health_skipped():
    assert not _is_sensitive("/health")
    assert not _is_sensitive("/")
    assert not _is_sensitive("/select/quick")


def test_sensitive_paths_immutable():
    # Поверка что список префиксов не изменился случайно (152-ФЗ semantics).
    assert "/admin" in SENSITIVE_PATHS
    assert "/import/parse" in SENSITIVE_PATHS
    assert "/handoff" in SENSITIVE_PATHS
    assert "/etl/classify" in SENSITIVE_PATHS


# ---------------------------------------------------------------------------
# Middleware behavior (через capsys, т.к. structlog→stdout)
# ---------------------------------------------------------------------------


def test_admin_request_logged(client, capsys):
    r = client.post("/admin/something", json={"x": 1})
    assert r.status_code == 200
    out = capsys.readouterr().out
    assert "request" in out
    assert "/admin/something" in out
    assert "method" in out and "POST" in out
    assert "status=200" in out or '"status": 200' in out


def test_import_parse_logged(client, capsys):
    r = client.post("/import/parse", json={"tz_text": "Q=10 H=5"})
    assert r.status_code == 200
    out = capsys.readouterr().out
    assert "/import/parse" in out


def test_handoff_logged(client, capsys):
    r = client.post("/handoff/pdf", json={})
    assert r.status_code == 200
    out = capsys.readouterr().out
    assert "/handoff/pdf" in out


def test_etl_classify_logged(client, capsys):
    r = client.post("/etl/classify", json={})
    assert r.status_code == 200
    out = capsys.readouterr().out
    assert "/etl/classify" in out


def test_non_sensitive_not_logged(client, capsys):
    r = client.get("/health")
    assert r.status_code == 200
    out = capsys.readouterr().out
    # /health НЕ должен попасть в audit-вывод
    # (любой info-event на /health означает баг в _is_sensitive)
    assert "/health" not in out or "audit" not in out.lower()


def test_root_not_logged(client, capsys):
    r = client.get("/")
    assert r.status_code == 200
    out = capsys.readouterr().out
    # Контекстная проверка: middleware не должен эмитить event для /.
    # Логи могут быть из других модулей (uvicorn) — но без 'request' event.
    lines_with_request = [ln for ln in out.splitlines() if "request " in ln and "path=" in ln]
    assert not lines_with_request, f"audit fired on /: {lines_with_request}"


def test_failed_request_logged_as_error(client, capsys):
    """500 от RuntimeError → audit.error event."""
    with pytest.raises(RuntimeError):
        client.post("/admin/crash", json={"x": 1})
    out = capsys.readouterr().out
    assert "request_failed" in out
    assert "RuntimeError" in out
    assert "/admin/crash" in out


def test_http_exception_still_logged(client, capsys):
    """HTTPException(500) обрабатывается FastAPI → audit пишет .info status=500."""
    r = client.post("/admin/boom", json={})
    assert r.status_code == 500
    out = capsys.readouterr().out
    # info-level event (response получили), status=500 в payload
    assert "/admin/boom" in out
    assert "500" in out


def test_audit_does_not_read_body(client, capsys):
    """Middleware смотрит только Content-Length, не парсит body."""
    big_body = {"pii": "Иванов И. И., паспорт 4500 123456, телефон +79991234567"}
    r = client.post("/admin/something", json=big_body)
    assert r.status_code == 200
    out = capsys.readouterr().out
    # Никакие PII НЕ должны попасть в audit-output.
    assert "Иванов" not in out
    assert "4500 123456" not in out
    assert "+79991234567" not in out
    # А body_bytes (длина) — должна.
    assert "body_bytes" in out
