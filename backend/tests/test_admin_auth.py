"""HTTP Basic auth для /admin/* endpoints (Phase 33+).

Закрываем pen-test finding из Sc.D. audit 2026-05-13:
«/admin/uploads/* без auth — OWASP A01 + 152-ФЗ ст.19».
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from pump_calculator.api import app

client = TestClient(app)


# Список всех admin endpoints + (HTTP method).
# /admin/uploads/merge-internal НЕ входит — у него своя auth-схема
# (X-YC-Internal-Token), проверяется в test_tenancy.py.
ADMIN_ENDPOINTS = [
    ("GET", "/admin/uploads"),
    ("GET", "/admin/uploads/some-id-123"),
    ("POST", "/admin/uploads/some-id-123/approve"),
    ("POST", "/admin/uploads/some-id-123/reject"),
    ("POST", "/admin/uploads/merge"),
    ("GET", "/admin/tenants"),
]


def _basic_header(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_admin_no_auth_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """Без Authorization header — 401 на всех /admin/* (закрыто по умолчанию)."""
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    for method, url in ADMIN_ENDPOINTS:
        r = client.request(method, url)
        assert r.status_code == 401, f"{method} {url} → {r.status_code} (ожидали 401)"


def test_admin_wrong_pass_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """Неверный пароль — 401 + WWW-Authenticate header."""
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    r = client.get("/admin/uploads", headers=_basic_header("admin", "wrong"))
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate", "").lower().startswith("basic")


def test_admin_wrong_user_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """Неверный username — 401, даже если пароль угадан."""
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    r = client.get("/admin/uploads", headers=_basic_header("hacker", "secret-test-pass"))
    assert r.status_code == 401


def test_admin_correct_auth_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """Корректные creds → 200 + JSON ответ.

    /admin/uploads — самый безопасный для positive-теста: всегда возвращает
    {"items": [...], "count": int} даже на пустом S3/queue.
    """
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    r = client.get(
        "/admin/uploads",
        headers=_basic_header("admin", "secret-test-pass"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert "count" in body


def test_admin_pass_not_configured_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если ADMIN_PASS не задан → 503 (fail-closed). Лучше чем silent-open."""
    monkeypatch.delenv("ADMIN_PASS", raising=False)
    r = client.get(
        "/admin/uploads",
        headers=_basic_header("admin", "any-pass"),
    )
    assert r.status_code == 503
    assert "ADMIN_PASS" in r.text or "not configured" in r.text.lower()


def test_privacy_endpoint_open() -> None:
    """/privacy — публичный (152-ФЗ ст.18 — обязан быть доступен)."""
    r = client.get("/privacy")
    assert r.status_code == 200
    text = r.text
    # Ключевые элементы: упоминание 152-ФЗ и DPO contact.
    assert "152-ФЗ" in text or "персональн" in text.lower()
    assert "zakaz@inservo.ru" in text


def test_non_admin_endpoints_remain_open() -> None:
    """Регрессия: /select, /health, /, /privacy — БЕЗ auth (B2B калькулятор)."""
    for url in ("/", "/health", "/privacy"):
        r = client.get(url)
        assert r.status_code == 200, f"{url} стал требовать auth — это регрессия"
