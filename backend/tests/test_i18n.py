"""Тесты для ``pump_calculator.i18n`` (Sc.D. Cross-Domain 2026-05-13).

Цели:
- detect_lang корректно парсит Accept-Language.
- t() подставляет kwargs и не падает при отсутствии плейсхолдера.
- Fallback на DEFAULT_LANG при неизвестных ключах.
- Интеграция с FastAPI dependency через Accept-Language header.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pump_calculator.api import app
from pump_calculator.i18n import MESSAGES, detect_lang, t

client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────
# Unit-тесты модуля i18n
# ──────────────────────────────────────────────────────────────────────────


def test_detect_lang_empty_returns_default() -> None:
    """Пустой/None header → ru (default)."""
    assert detect_lang(None) == "ru"
    assert detect_lang("") == "ru"
    assert detect_lang("   ") == "ru"


def test_detect_lang_en_variants() -> None:
    """en, en-US, EN-GB → en (primary subtag wins)."""
    assert detect_lang("en") == "en"
    assert detect_lang("en-US") == "en"
    assert detect_lang("EN-GB") == "en"
    assert detect_lang("en-US,ru;q=0.5") == "en"


def test_detect_lang_ru_explicit() -> None:
    """ru, ru-RU → ru."""
    assert detect_lang("ru") == "ru"
    assert detect_lang("ru-RU") == "ru"
    assert detect_lang("ru-RU,en;q=0.8") == "ru"


def test_detect_lang_unknown_fallback() -> None:
    """Неизвестный язык (fr, de, zh) → ru (default)."""
    assert detect_lang("fr-FR") == "ru"
    assert detect_lang("de") == "ru"
    assert detect_lang("zh-CN") == "ru"


def test_t_known_key_ru() -> None:
    """t() возвращает русское сообщение по умолчанию."""
    assert "Q" in t("missing_q", "ru")
    assert "расход" in t("missing_q", "ru").lower()


def test_t_known_key_en() -> None:
    """t() возвращает английское сообщение для lang=en."""
    assert "Q" in t("missing_q", "en")
    assert "flow rate" in t("missing_q", "en").lower()


def test_t_unknown_key_returns_key_as_marker() -> None:
    """Неизвестный ключ → возвращается сам ключ (debug marker)."""
    assert t("non_existent_key_12345", "en") == "non_existent_key_12345"
    assert t("non_existent_key_12345", "ru") == "non_existent_key_12345"


def test_t_format_kwargs() -> None:
    """t() подставляет kwargs через str.format."""
    msg = t("body_too_large", "en", max_mb=10)
    assert "10" in msg
    assert "MB" in msg


def test_t_missing_kwargs_no_crash() -> None:
    """t() не падает если плейсхолдер не передан — возвращает raw."""
    # body_too_large требует max_mb. Не передаём.
    result = t("body_too_large", "en")
    assert isinstance(result, str)
    assert "{max_mb}" in result  # raw сообщение без подстановки


def test_t_lang_none_uses_default() -> None:
    """Если lang=None → используется DEFAULT_LANG (обычно ru)."""
    msg = t("missing_q", None)
    assert msg == t("missing_q", "ru")


def test_messages_ru_en_parity() -> None:
    """Все ключи присутствуют и в ru, и в en (нет drift'а)."""
    ru_keys = set(MESSAGES["ru"].keys())
    en_keys = set(MESSAGES["en"].keys())
    missing_in_en = ru_keys - en_keys
    missing_in_ru = en_keys - ru_keys
    assert not missing_in_en, f"Keys missing in 'en': {missing_in_en}"
    assert not missing_in_ru, f"Keys missing in 'ru': {missing_in_ru}"


# ──────────────────────────────────────────────────────────────────────────
# Integration-тесты с FastAPI dependency
# ──────────────────────────────────────────────────────────────────────────


def test_api_pump_not_found_en() -> None:
    """GET /pumps/{unknown} с Accept-Language: en → английское сообщение."""
    r = client.get("/pumps/nonexistent-id-xyz", headers={"Accept-Language": "en"})
    assert r.status_code == 404
    detail = r.json().get("detail", "")
    assert "not found" in detail.lower()
    # Не должно быть русского
    assert "не найден" not in detail.lower()


def test_api_pump_not_found_ru_default() -> None:
    """GET /pumps/{unknown} без header → русское сообщение (default)."""
    r = client.get("/pumps/nonexistent-id-xyz")
    assert r.status_code == 404
    detail = r.json().get("detail", "")
    assert "не найден" in detail.lower()


def test_api_classify_empty_en() -> None:
    """POST /etl/classify с пустым body и Accept-Language: en → en error."""
    r = client.post(
        "/etl/classify",
        json={"subject": "", "body": "", "from_email": ""},
        headers={"Accept-Language": "en"},
    )
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "empty" in detail.lower()


def test_api_import_empty_en() -> None:
    """POST /import/parse с пустым text и Accept-Language: en → en error."""
    r = client.post(
        "/import/parse",
        json={"text": "", "format": "plain"},
        headers={"Accept-Language": "en"},
    )
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "empty" in detail.lower()


def test_env_default_lang_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENV DEFAULT_LANG=en меняет fallback язык."""
    monkeypatch.setenv("DEFAULT_LANG", "en")
    # Пустой Accept-Language → теперь en (из ENV)
    assert detect_lang(None) == "en"
    assert detect_lang("") == "en"
