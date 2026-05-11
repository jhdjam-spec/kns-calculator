"""Тесты S3 uploader — primary архив ТЗ в Yandex Object Storage.

Покрывает:
- Graceful degradation без креденшалов (is_configured == False)
- Сборка ключа `tz_archive/YYYY/MM/DD/HH-MM-SS_Q..._..._<hash6>.txt`
- Mock boto3 client → put_object вызывается с правильными аргументами
- catalog.jsonl append (read existing → append → put back)
- archive_tz_to_s3 high-level: 2 объекта + catalog
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from pump_calculator.etl.s3_uploader import (
    S3Uploader,
    archive_tz_to_s3,
    build_s3_key,
    make_upload_id,
)

# ---------------------------------------------------------------------------
# build_s3_key — pure
# ---------------------------------------------------------------------------


def test_build_s3_key_structure():
    """Ключ должен иметь формат `<prefix>/YYYY/MM/DD/HH-MM-SS_Q<Q>_<type>_<city>_<h>.txt`."""
    ts = datetime(2026, 5, 11, 14, 30, 22, tzinfo=UTC)
    key = build_s3_key(
        {"Q_m3h": 88.6, "object_type": "КНС", "city": "Краснодар"},
        prefix="tz_archive/",
        timestamp=ts,
        content_hash="a1b2c3d4e5f6",
    )
    assert key.startswith("tz_archive/2026/05/11/14-30-22")
    assert "Q88.6" in key
    assert key.endswith(".txt")
    # Cyrillic city транслитерирован → ascii
    assert "Krasnodar".lower() in key.lower() or "krasnodar" in key.lower()
    # Hash добавлен
    assert "a1b2c3" in key


def test_build_s3_key_no_parsed():
    """Без parsed — только timestamp в имени."""
    ts = datetime(2026, 5, 11, 10, 0, 0, tzinfo=UTC)
    key = build_s3_key(None, timestamp=ts, content_hash="abcdef0123")
    assert key == "tz_archive/2026/05/11/10-00-00_abcdef.txt"


# ---------------------------------------------------------------------------
# S3Uploader — graceful degradation
# ---------------------------------------------------------------------------


def test_uploader_not_configured_when_no_creds(monkeypatch):
    """Без AWS_ACCESS_KEY_ID — is_configured = False."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    up = S3Uploader.from_env()
    assert up.is_configured is False
    # Upload должен вернуть error, а не throw
    res = up.upload_text("hello", "test.txt", {})
    assert res["key"] is None
    assert "not configured" in res["error"].lower()


def test_uploader_configured_with_mock_client():
    """С mock client'ом put_object вызывается."""
    mock_client = MagicMock()
    up = S3Uploader(
        bucket="test-bucket",
        prefix="tz_archive/",
        access_key="AK",
        secret_key="SK",
        client=mock_client,
    )
    assert up.is_configured is True
    res = up.upload_text("hello world", "tz_archive/2026/05/11/t.txt", {"upload-id": "u1"})
    assert res["key"] == "tz_archive/2026/05/11/t.txt"
    assert res["bucket"] == "test-bucket"
    assert res["size_bytes"] == len("hello world")
    assert res["error"] is None
    mock_client.put_object.assert_called_once()
    kwargs = mock_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "test-bucket"
    assert kwargs["Key"] == "tz_archive/2026/05/11/t.txt"
    assert kwargs["Body"] == b"hello world"
    assert "text/plain" in kwargs["ContentType"]
    assert kwargs["Metadata"]["upload-id"] == "u1"


# ---------------------------------------------------------------------------
# catalog.jsonl append
# ---------------------------------------------------------------------------


class _FakeNoSuchKey(Exception):
    """Mimics botocore NoSuchKey class name without importing botocore."""


def test_catalog_append_starts_fresh_then_appends():
    """Первый append — пустой existing; второй — конкатенация."""
    mock_client = MagicMock()
    # 1-й get_object выбрасывает NoSuchKey-подобное исключение
    mock_client.get_object.side_effect = [
        _FakeNoSuchKey("not found"),
        {"Body": MagicMock(read=lambda: b'{"upload_id":"u1"}\n')},
    ]
    up = S3Uploader(
        bucket="b",
        prefix="tz_archive/",
        access_key="AK",
        secret_key="SK",
        client=mock_client,
    )
    # 1-й append: existing пустой
    res1 = up.append_catalog({"upload_id": "u1"})
    assert res1["error"] is None
    assert res1["key"] == "tz_archive/_metadata/catalog.jsonl"
    body1 = mock_client.put_object.call_args.kwargs["Body"]
    assert body1 == b'{"upload_id": "u1"}\n'

    # 2-й append: existing с u1, теперь добавляем u2
    res2 = up.append_catalog({"upload_id": "u2"})
    assert res2["error"] is None
    body2 = mock_client.put_object.call_args.kwargs["Body"]
    assert b'{"upload_id":"u1"}' in body2
    assert b'{"upload_id": "u2"}' in body2


# ---------------------------------------------------------------------------
# archive_tz_to_s3 — end-to-end
# ---------------------------------------------------------------------------


def test_archive_tz_to_s3_full_flow():
    """High-level archive: загружает raw + parsed + catalog (3 put_object total)."""
    mock_client = MagicMock()
    # catalog.get_object: первый раз нет (NoSuchKey)
    mock_client.get_object.side_effect = _FakeNoSuchKey("not found")

    up = S3Uploader(
        bucket="kns-test",
        prefix="tz_archive/",
        access_key="AK",
        secret_key="SK",
        client=mock_client,
    )
    parsed = {
        "Q_m3h": 88.6,
        "dH_m": 39.0,
        "city": "Krasnodar",
        "wastewater_type": "domestic",
        "object_type": "КНС",
        "confidence": 1.0,
        "project_code": "1578-22-НК",
    }
    ts = datetime(2026, 5, 11, 14, 30, 22, tzinfo=UTC)
    res = archive_tz_to_s3("Q=88.6 м³/ч ...", parsed=parsed, uploader=up, timestamp=ts)

    assert res["configured"] is True
    assert res["error"] is None
    assert res["bucket"] == "kns-test"
    assert res["key"].startswith("tz_archive/2026/05/11/14-30-22")
    assert res["key"].endswith(".txt")
    assert res["parsed_key"].endswith(".parsed.json")
    assert res["upload_id"].startswith("upload-2026-05-11-")

    # 3 put_object: raw text, parsed json, catalog
    assert mock_client.put_object.call_count == 3
    calls = mock_client.put_object.call_args_list
    keys = [c.kwargs["Key"] for c in calls]
    assert any(k.endswith(".txt") for k in keys)
    assert any(k.endswith(".parsed.json") for k in keys)
    assert any(k.endswith("catalog.jsonl") for k in keys)


def test_archive_tz_to_s3_not_configured_returns_graceful():
    """Без creds — returns dict с configured=False, не throws."""
    up = S3Uploader(access_key=None, secret_key=None)
    parsed = {"Q_m3h": 50, "confidence": 0.5}
    res = archive_tz_to_s3("test text", parsed=parsed, uploader=up)
    assert res["configured"] is False
    assert res["key"] is None
    assert res["upload_id"].startswith("upload-")
    assert "not configured" in (res["error"] or "").lower()


# ---------------------------------------------------------------------------
# make_upload_id — stable for same hash + timestamp
# ---------------------------------------------------------------------------


def test_make_upload_id_format():
    ts = datetime(2026, 5, 11, 14, 30, 22, tzinfo=UTC)
    uid = make_upload_id(ts, "a1b2c3deadbeef")
    assert uid == "upload-2026-05-11-143022-a1b2c3"
