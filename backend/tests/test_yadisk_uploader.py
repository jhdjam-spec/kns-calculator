"""Unit-тесты для `pump_calculator.etl.yadisk_uploader`.

Покрытие
========
- `safe_filename` / `build_archive_filename` — без сети.
- Поведение при отсутствии токена → no-op + понятный error message.
- Mock `urllib.request.build_opener()` для проверки правильных URL/headers/methods.
- Обработка 401 / 403 / 507 → graceful failure (без exception наружу).
- Успешный сценарий: ensure_folder_chain → get_upload_url → PUT bytes.

Tests не делают реальных сетевых запросов — все ответы статичные.
"""
from __future__ import annotations

import json
from datetime import UTC
from typing import Any
from unittest.mock import MagicMock

import pytest

from pump_calculator.etl.yadisk_uploader import (
    YADISK_API_BASE,
    YaDiskAuthError,
    YaDiskQuotaError,
    YaDiskUploader,
    archive_tz_text,
    build_archive_filename,
    safe_filename,
    today_subfolder,
)

# ---------------------------------------------------------------------------
# Helpers — mock opener
# ---------------------------------------------------------------------------


def _make_response(status: int, body: bytes = b""):
    """Mock объекта context-manager, который возвращает opener.open()."""
    resp = MagicMock()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    resp.status = status
    resp.read = MagicMock(return_value=body)
    return resp


def _make_opener(responses: list[Any]):
    """Opener, который по очереди возвращает заранее заготовленные ответы.

    Сохраняет список Request-объектов в `calls`.
    """
    opener = MagicMock()
    iter_resp = iter(responses)
    calls: list[Any] = []

    def _open(req, timeout=None):  # noqa: ARG001
        calls.append(req)
        return next(iter_resp)

    opener.open = MagicMock(side_effect=_open)
    opener.calls = calls
    return opener


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestPureHelpers:
    def test_safe_filename_keeps_cyrillic(self):
        assert safe_filename("Краснодар_КНС.txt") == "Краснодар_КНС.txt"

    def test_safe_filename_replaces_slashes(self):
        assert safe_filename("a/b\\c:d?e") == "a_b_c_d_e"

    def test_safe_filename_trims_to_200_chars(self):
        long = "x" * 300
        assert len(safe_filename(long)) <= 200

    def test_build_archive_filename_with_parsed_dict(self):
        from datetime import datetime

        ts = datetime(2026, 5, 11, 14, 30, 22, tzinfo=UTC)
        name = build_archive_filename(
            parsed={"Q_m3h": 88.6, "object_type": "КНС", "city": "Краснодар"},
            timestamp=ts,
        )
        assert name.startswith("2026-05-11_14-30-22_Q88.6_кнс_Краснодар")
        assert name.endswith(".txt")

    def test_build_archive_filename_uses_original_when_given(self):
        name = build_archive_filename(
            original_filename="техзадание_крокус.pdf",
            parsed={"Q_m3h": 100},
        )
        assert name == "техзадание_крокус.pdf"

    def test_today_subfolder_format(self):
        from datetime import datetime

        ts = datetime(2026, 5, 11, tzinfo=UTC)
        assert today_subfolder(ts) == "/Parser_Project_KNS/2026-05-11"


# ---------------------------------------------------------------------------
# No-token (graceful degradation)
# ---------------------------------------------------------------------------


class TestNoToken:
    def test_is_configured_false(self):
        up = YaDiskUploader(token=None)
        assert up.is_configured is False

    def test_is_configured_false_for_blank_string(self):
        up = YaDiskUploader(token="   ")
        assert up.is_configured is False

    def test_upload_text_skips_with_error_message(self):
        up = YaDiskUploader(token=None)
        result = up.upload_text("hello", "test.txt")
        assert result["path"] is None
        assert result["error"] == "YANDEX_DISK_TOKEN not configured"
        assert result["size_bytes"] == 5  # len("hello")

    def test_upload_file_skips_with_error_message(self):
        up = YaDiskUploader(token=None)
        result = up.upload_file(b"\x00\x01\x02", "binary.bin")
        assert result["path"] is None
        assert result["error"] == "YANDEX_DISK_TOKEN not configured"

    def test_ensure_folder_returns_false_without_token(self):
        up = YaDiskUploader(token=None)
        assert up.ensure_folder("/foo") is False

    def test_archive_tz_text_no_token(self, monkeypatch):
        monkeypatch.delenv("YANDEX_DISK_TOKEN", raising=False)
        info = archive_tz_text("Q=88 м³/ч ...", parsed={"Q_m3h": 88})
        assert info["archive_path"] is None
        assert "not configured" in info["archive_error"]


# ---------------------------------------------------------------------------
# Successful upload flow
# ---------------------------------------------------------------------------


class TestUploadFlow:
    def test_get_upload_url_uses_oauth_header_and_correct_endpoint(self):
        upload_url_body = json.dumps(
            {"href": "https://uploader.disk.yandex.net/upload?key=xxx"}
        ).encode("utf-8")
        opener = _make_opener(
            [
                _make_response(200, upload_url_body),
            ]
        )
        up = YaDiskUploader(token="t0k3n", opener=opener)
        url = up._get_upload_url("/Parser_Project_KNS/foo.txt")
        assert url == "https://uploader.disk.yandex.net/upload?key=xxx"

        req = opener.calls[0]
        assert req.full_url.startswith(f"{YADISK_API_BASE}/resources/upload?")
        assert "path=" in req.full_url
        assert "overwrite=true" in req.full_url
        assert req.headers["Authorization"] == "OAuth t0k3n"

    def test_upload_text_full_flow(self):
        upload_url_body = json.dumps(
            {"href": "https://uploader.disk.yandex.net/upload?key=abc"}
        ).encode("utf-8")
        opener = _make_opener(
            [
                # ensure_folder_chain step 1: /Parser_Project_KNS
                _make_response(201, b""),
                # ensure_folder_chain step 2: /Parser_Project_KNS/2026-05-11
                _make_response(201, b""),
                # GET upload url
                _make_response(200, upload_url_body),
                # PUT bytes
                _make_response(201, b""),
            ]
        )
        up = YaDiskUploader(token="t0k3n", opener=opener)
        result = up.upload_text(
            "Q=88 м³/ч",
            filename="test.txt",
            folder="/Parser_Project_KNS/2026-05-11",
        )
        assert result["path"] == "/Parser_Project_KNS/2026-05-11/test.txt"
        assert result["error"] is None
        assert result["size_bytes"] > 0

        # PUT кладёт UTF-8 bytes
        put_req = opener.calls[-1]
        assert put_req.method == "PUT"
        assert put_req.data == "Q=88 м³/ч".encode()

    def test_folder_already_exists_409_is_ok(self):
        opener = _make_opener(
            [
                _make_response(409, b""),  # PUT /resources?path=... → 409
            ]
        )
        up = YaDiskUploader(token="t0k3n", opener=opener)
        assert up.ensure_folder("/already_there") is True


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_401_token_invalid_returns_error_dict_no_raise(self):
        opener = _make_opener(
            [
                _make_response(201, b""),  # ensure root
                _make_response(201, b""),  # ensure date
                _make_response(401, b'{"message": "invalid token"}'),
            ]
        )
        up = YaDiskUploader(token="bad", opener=opener)
        result = up.upload_text("hi", "f.txt")
        assert result["path"] is None
        assert "Unauthorized" in result["error"]

    def test_403_forbidden_returns_error_dict(self):
        opener = _make_opener(
            [
                _make_response(201, b""),
                _make_response(201, b""),
                _make_response(403, b'{"message": "no scope"}'),
            ]
        )
        up = YaDiskUploader(token="t", opener=opener)
        result = up.upload_text("hi", "f.txt")
        assert result["path"] is None
        assert "Forbidden" in result["error"]

    def test_507_quota_returns_error_dict(self):
        upload_url_body = json.dumps({"href": "https://uploader.example/u"}).encode()
        opener = _make_opener(
            [
                _make_response(201, b""),  # ensure root
                _make_response(201, b""),  # ensure date
                _make_response(200, upload_url_body),  # get upload url ok
                _make_response(507, b'{"message": "disk full"}'),
            ]
        )
        up = YaDiskUploader(token="t", opener=opener)
        result = up.upload_text("hi", "f.txt")
        assert result["path"] is None
        assert "disk full" in result["error"].lower() or "Insufficient" in result["error"]

    def test_raise_for_status_classes(self):
        with pytest.raises(YaDiskAuthError):
            YaDiskUploader._raise_for_status(401, b"")
        with pytest.raises(YaDiskAuthError):
            YaDiskUploader._raise_for_status(403, b"")
        with pytest.raises(YaDiskQuotaError):
            YaDiskUploader._raise_for_status(507, b"")


# ---------------------------------------------------------------------------
# High-level archive_tz_text
# ---------------------------------------------------------------------------


class TestArchiveTzText:
    def test_returns_three_keys_always(self, monkeypatch):
        monkeypatch.delenv("YANDEX_DISK_TOKEN", raising=False)
        info = archive_tz_text("text body", parsed={"Q_m3h": 1.0})
        assert set(info.keys()) == {
            "archive_path",
            "archive_error",
            "archive_size_bytes",
        }

    def test_uses_injected_uploader(self):
        fake = MagicMock()
        fake.upload_text.return_value = {
            "path": "/Parser_Project_KNS/2026-05-11/x.txt",
            "error": None,
            "size_bytes": 9,
        }
        info = archive_tz_text("text body", parsed=None, uploader=fake)
        assert info["archive_path"].startswith("/Parser_Project_KNS")
        assert info["archive_error"] is None
        fake.upload_text.assert_called_once()
