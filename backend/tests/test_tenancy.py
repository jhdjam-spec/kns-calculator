"""Tests для multi-tenancy stub + /admin/uploads/merge-internal.

Sc.D. Architecture audit 2026-05-13: «multi-tenancy при дилерах».
Закрываем тестами:
1. get_tenant_id() возвращает DEFAULT_TENANT без header.
2. Невалидный X-Tenant-ID → fallback на DEFAULT_TENANT.
3. Валидный X-Tenant-ID → возвращается as-is.
4. /admin/tenants — список allow-list.
5. /admin/uploads/merge-internal — auth по X-YC-Internal-Token.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pump_calculator.api import app
from pump_calculator.rate_limiter import limiter
from pump_calculator.tenancy import (
    ALLOWED_TENANTS,
    DEFAULT_TENANT,
    get_tenant_label,
    is_allowed_tenant,
    list_allowed_tenants,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Сбрасываем slowapi storage между тестами — /import/parse имеет лимит 10/min.

    Иначе наши 4 вызова к /import/parse оставят след в глобальном limiter
    и сломают test_rate_limit.py::test_import_parse_rate_limit при последовательном
    прогоне всего suite.
    """
    try:
        limiter._storage.reset()
    except AttributeError:  # pragma: no cover
        pass
    yield
    try:
        limiter._storage.reset()
    except AttributeError:  # pragma: no cover
        pass


# ──────────────────────────────────────────────────────────────────────────
# Unit-тесты на helper-функции
# ──────────────────────────────────────────────────────────────────────────


def test_default_tenant_is_servoyug() -> None:
    """servoyug — главный tenant, должен быть в allow-list."""
    assert DEFAULT_TENANT == "servoyug"
    assert is_allowed_tenant("servoyug")


def test_demo_tenant_in_allow_list() -> None:
    """demo — показательный tenant, должен быть в allow-list для тестов."""
    assert is_allowed_tenant("demo")


def test_unknown_tenant_rejected() -> None:
    """Любой случайный slug НЕ должен быть в allow-list."""
    assert not is_allowed_tenant("hacker-tenant")
    assert not is_allowed_tenant("")


def test_get_tenant_label_returns_label() -> None:
    """Известный tenant → русскоязычная подпись."""
    label = get_tenant_label("servoyug")
    assert "Серво-Юг" in label


def test_get_tenant_label_unknown_returns_id() -> None:
    """Неизвестный tenant → fallback на сам ID (не падаем)."""
    assert get_tenant_label("unknown-xyz") == "unknown-xyz"


def test_list_allowed_tenants_includes_default() -> None:
    """list_allowed_tenants() возвращает структурированный список."""
    tenants = list_allowed_tenants()
    ids = [t["id"] for t in tenants]
    assert DEFAULT_TENANT in ids
    assert all("label" in t for t in tenants)


# ──────────────────────────────────────────────────────────────────────────
# /import/parse + tenant_id (HTTP-уровень)
# ──────────────────────────────────────────────────────────────────────────


def test_import_parse_no_header_uses_default_tenant() -> None:
    """Без X-Tenant-ID → response.tenant.id = DEFAULT_TENANT."""
    r = client.post(
        "/import/parse",
        json={"text": "КНС Q=20 м³/ч H=15м г.Краснодар хозбытовые стоки"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tenant", {}).get("id") == DEFAULT_TENANT


def test_import_parse_valid_header_uses_tenant() -> None:
    """X-Tenant-ID: demo (из allow-list) → response.tenant.id = demo."""
    r = client.post(
        "/import/parse",
        json={"text": "КНС Q=20 м³/ч H=15м г.Краснодар хозбытовые стоки"},
        headers={"X-Tenant-ID": "demo"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tenant", {}).get("id") == "demo"


def test_import_parse_invalid_header_falls_back() -> None:
    """X-Tenant-ID: hacker (не в allow-list) → fallback на DEFAULT_TENANT."""
    r = client.post(
        "/import/parse",
        json={"text": "КНС Q=20 м³/ч H=15м г.Краснодар хозбытовые стоки"},
        headers={"X-Tenant-ID": "hacker-tenant"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tenant", {}).get("id") == DEFAULT_TENANT


def test_import_parse_tenant_case_insensitive() -> None:
    """X-Tenant-ID: SERVOYUG (верхний регистр) → нормализуется на servoyug."""
    r = client.post(
        "/import/parse",
        json={"text": "КНС Q=20 м³/ч H=15м г.Краснодар хозбытовые стоки"},
        headers={"X-Tenant-ID": "SERVOYUG"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tenant", {}).get("id") == "servoyug"


# ──────────────────────────────────────────────────────────────────────────
# /admin/tenants — list endpoint (требует HTTP Basic)
# ──────────────────────────────────────────────────────────────────────────


def test_admin_tenants_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """/admin/tenants без auth → 401."""
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    r = client.get("/admin/tenants")
    assert r.status_code == 401


def test_admin_tenants_returns_allow_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """С правильным HTTP Basic → 200 + список tenants."""
    import base64

    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    auth = base64.b64encode(b"admin:secret-test-pass").decode()
    r = client.get(
        "/admin/tenants",
        headers={"Authorization": f"Basic {auth}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == len(ALLOWED_TENANTS)
    assert body["default"] == DEFAULT_TENANT
    ids = [t["id"] for t in body["tenants"]]
    assert "servoyug" in ids


# ──────────────────────────────────────────────────────────────────────────
# /admin/uploads/merge-internal — YC Trigger endpoint
# ──────────────────────────────────────────────────────────────────────────


def test_merge_internal_no_token_env_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если YC_INTERNAL_TOKEN не задан → 503 (fail-closed)."""
    monkeypatch.delenv("YC_INTERNAL_TOKEN", raising=False)
    r = client.post("/admin/uploads/merge-internal")
    assert r.status_code == 503
    assert "YC_INTERNAL_TOKEN" in r.text or "not configured" in r.text.lower()


def test_merge_internal_no_header_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENV задан, но header отсутствует → 401."""
    monkeypatch.setenv("YC_INTERNAL_TOKEN", "test-secret-token-12345")
    r = client.post("/admin/uploads/merge-internal")
    assert r.status_code == 401


def test_merge_internal_wrong_token_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Неверный токен → 401."""
    monkeypatch.setenv("YC_INTERNAL_TOKEN", "test-secret-token-12345")
    r = client.post(
        "/admin/uploads/merge-internal",
        headers={"X-YC-Internal-Token": "wrong-token"},
    )
    assert r.status_code == 401


def test_merge_internal_correct_token_runs_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Правильный токен → 200 + merged_count в ответе."""
    monkeypatch.setenv("YC_INTERNAL_TOKEN", "test-secret-token-12345")
    # Изолируем dataset writes в tmp_path, чтобы не трогать реальный 02_dataset.
    monkeypatch.setenv("KNS_DATASET_ROOT", str(tmp_path))
    r = client.post(
        "/admin/uploads/merge-internal",
        headers={"X-YC-Internal-Token": "test-secret-token-12345"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("trigger") == "yc-cron"
    # merge_to_etalons возвращает merged_count даже на пустом jsonl.
    assert "merged_count" in body or "output_path" in body
