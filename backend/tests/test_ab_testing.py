"""Тесты для ``pump_calculator.ab_testing`` (Sc.D. Cross-Domain 2026-05-13).

Цели:
- FeatureFlag.percent читает ENV корректно и clamp'ит.
- is_enabled_for даёт детерминированный bucketing.
- 100% / 0% флаги ведут себя без хэширования (fast-path).
- list_flags_snapshot для /admin/flags endpoint.
- Интеграция с /admin/flags через TestClient.
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from pump_calculator.ab_testing import (
    ALL_FLAGS,
    EN_LOCALIZATION,
    THOMA_CAVITATION,
    FeatureFlag,
    is_flag_on,
    list_flags_snapshot,
)
from pump_calculator.api import app

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────
# Unit-тесты FeatureFlag
# ──────────────────────────────────────────────────────────────────────────


def test_flag_env_var_naming() -> None:
    """Имя ENV var = AB_FLAG_<NAME.upper()>."""
    flag = FeatureFlag("foo_bar", default_pct=0.5)
    assert flag.env_var == "AB_FLAG_FOO_BAR"


def test_flag_default_pct_used_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если ENV не задан → используется default_pct."""
    monkeypatch.delenv("AB_FLAG_TEST_NONE", raising=False)
    flag = FeatureFlag("test_none", default_pct=0.42)
    assert flag.percent == pytest.approx(0.42)


def test_flag_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENV var переопределяет default_pct."""
    monkeypatch.setenv("AB_FLAG_TEST_ENV", "0.7")
    flag = FeatureFlag("test_env", default_pct=0.0)
    assert flag.percent == pytest.approx(0.7)


def test_flag_invalid_env_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если ENV содержит мусор → fallback на default_pct."""
    monkeypatch.setenv("AB_FLAG_TEST_INVALID", "not-a-number")
    flag = FeatureFlag("test_invalid", default_pct=0.3)
    assert flag.percent == pytest.approx(0.3)


def test_flag_clamp_to_unit_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    """percent clamp'ится к [0.0, 1.0]."""
    monkeypatch.setenv("AB_FLAG_TEST_BIG", "1.5")
    monkeypatch.setenv("AB_FLAG_TEST_NEG", "-0.2")
    assert FeatureFlag("test_big").percent == 1.0
    assert FeatureFlag("test_neg").percent == 0.0


def test_flag_100pct_always_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """percent=1.0 → True для любого key (fast-path)."""
    monkeypatch.setenv("AB_FLAG_FULL_ROLLOUT", "1.0")
    flag = FeatureFlag("full_rollout")
    for key in ("req-1", "req-2", "anonymous", ""):
        assert flag.is_enabled_for(key) is True


def test_flag_0pct_always_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """percent=0.0 → False для любого key."""
    monkeypatch.setenv("AB_FLAG_OFF_ROLLOUT", "0.0")
    flag = FeatureFlag("off_rollout", default_pct=0.0)
    for key in ("req-1", "req-2", "anonymous", ""):
        assert flag.is_enabled_for(key) is False


def test_flag_deterministic_bucketing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Один и тот же key → один и тот же bucket (repeat-stable)."""
    monkeypatch.setenv("AB_FLAG_CANARY", "0.5")
    flag = FeatureFlag("canary")
    # Тот же key → тот же ответ при многократных вызовах
    result_1 = flag.is_enabled_for("user-12345")
    result_2 = flag.is_enabled_for("user-12345")
    result_3 = flag.is_enabled_for("user-12345")
    assert result_1 == result_2 == result_3


def test_flag_bucketing_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    """percent=0.5 даёт ~50% включений на большой выборке."""
    monkeypatch.setenv("AB_FLAG_DIST_TEST", "0.5")
    flag = FeatureFlag("dist_test")
    n = 2000
    enabled = sum(1 for i in range(n) if flag.is_enabled_for(f"req-{i}"))
    # Допуск ±10% (200 запросов из 2000) для MD5-bucketing
    assert 800 <= enabled <= 1200, f"Expected ~1000 of {n}, got {enabled}"


def test_is_flag_on_user_id_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """is_flag_on: user_id приоритетнее request_id."""
    monkeypatch.setenv("AB_FLAG_PRIORITY_TEST", "0.5")
    flag = FeatureFlag("priority_test")
    # Если user_id задан — он используется (request_id игнорируется)
    r1 = is_flag_on(flag, request_id="req-A", user_id="user-X")
    r2 = is_flag_on(flag, request_id="req-B", user_id="user-X")
    assert r1 == r2  # одинаковый user_id → одинаковый bucket


def test_is_flag_on_anonymous_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """is_flag_on без ключей → 'anonymous' bucket (детерминирован)."""
    monkeypatch.setenv("AB_FLAG_ANON_TEST", "0.5")
    flag = FeatureFlag("anon_test")
    r1 = is_flag_on(flag)
    r2 = is_flag_on(flag)
    assert r1 == r2  # repeat-stable даже для anonymous


# ──────────────────────────────────────────────────────────────────────────
# Registry / list_flags_snapshot
# ──────────────────────────────────────────────────────────────────────────


def test_all_flags_registered() -> None:
    """ALL_FLAGS содержит все ключевые научные триггеры."""
    expected = {
        "new_ext9_nitrification",
        "thoma_cavitation",
        "groundcontext_lateral",
        "en_localization",
        "motor_thermal_derate",
        "anaerobic_corrosion_risk",
    }
    assert expected.issubset(set(ALL_FLAGS.keys()))


def test_list_flags_snapshot_structure() -> None:
    """list_flags_snapshot возвращает корректную структуру для каждого флага."""
    snapshot = list_flags_snapshot()
    assert "thoma_cavitation" in snapshot
    entry = snapshot["thoma_cavitation"]
    assert "percent" in entry
    assert "env_var" in entry
    assert "default_pct" in entry
    assert "description" in entry
    assert entry["env_var"] == "AB_FLAG_THOMA_CAVITATION"


# ──────────────────────────────────────────────────────────────────────────
# Integration: /admin/flags endpoint
# ──────────────────────────────────────────────────────────────────────────


def _basic_header(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_admin_flags_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """/admin/flags без auth → 401."""
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    r = client.get("/admin/flags")
    assert r.status_code == 401


def test_admin_flags_returns_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """/admin/flags с правильным auth → 200 + JSON со списком флагов."""
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASS", "secret-test-pass")
    r = client.get(
        "/admin/flags",
        headers=_basic_header("admin", "secret-test-pass"),
    )
    assert r.status_code == 200
    payload = r.json()
    assert "flags" in payload
    assert "thoma_cavitation" in payload["flags"]
    assert payload["flags"]["thoma_cavitation"]["env_var"] == "AB_FLAG_THOMA_CAVITATION"


def test_thoma_cavitation_default_on() -> None:
    """THOMA_CAVITATION по умолчанию 100% (полный rollout)."""
    # default_pct=1.0 → is_enabled_for всегда True (при отсутствии ENV override)
    assert THOMA_CAVITATION.default_pct == 1.0


def test_en_localization_default_off() -> None:
    """EN_LOCALIZATION по умолчанию 0% (opt-in)."""
    assert EN_LOCALIZATION.default_pct == 0.0
