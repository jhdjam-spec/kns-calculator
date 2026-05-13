"""Тесты persistent_queue.py — выбор backend, write_queue/rejected/accepted.

Sc.D. P0: ``/tmp/uploads`` теряется при cold-stop YC Functions → нужен
S3-backed queue. Здесь проверяем что:

- ENV ``KNS_QUEUE_BACKEND`` корректно выбирает backend.
- TmpQueueBackend пишет в filesystem, читаемо обратно.
- S3QueueBackend использует boto3 mock, ключи сложены корректно.
- Fallback на tmp если ``s3`` без credentials.
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock

from pump_calculator.etl.persistent_queue import (
    BACKEND_S3,
    BACKEND_TMP,
    ENV_BACKEND,
    QueueBackend,
    S3QueueBackend,
    TmpQueueBackend,
    get_queue_backend,
)
from pump_calculator.etl.s3_uploader import S3Uploader

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_tmp_backend_default(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_BACKEND, raising=False)
    backend = get_queue_backend(tmp_root=tmp_path)
    assert isinstance(backend, TmpQueueBackend)
    assert isinstance(backend, QueueBackend)


def test_tmp_backend_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_BACKEND, BACKEND_TMP)
    backend = get_queue_backend(tmp_root=tmp_path)
    assert isinstance(backend, TmpQueueBackend)


def test_s3_backend_when_env_set_and_credentials(monkeypatch, tmp_path):
    """ENV=s3 + AWS_* → возвращаем S3QueueBackend."""
    monkeypatch.setenv(ENV_BACKEND, BACKEND_S3)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "fake-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "fake-secret")
    backend = get_queue_backend(tmp_root=tmp_path)
    assert isinstance(backend, S3QueueBackend)


def test_s3_backend_fallback_to_tmp_when_no_credentials(monkeypatch, tmp_path):
    """ENV=s3 но без AWS_* → fallback на TmpQueueBackend (graceful)."""
    monkeypatch.setenv(ENV_BACKEND, BACKEND_S3)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    backend = get_queue_backend(tmp_root=tmp_path)
    assert isinstance(backend, TmpQueueBackend)


def test_backend_override_param(tmp_path):
    backend = get_queue_backend(tmp_root=tmp_path, backend_override="tmp")
    assert isinstance(backend, TmpQueueBackend)


# ---------------------------------------------------------------------------
# TmpQueueBackend
# ---------------------------------------------------------------------------


def test_tmp_write_queue_returns_path(tmp_path):
    backend = TmpQueueBackend(tmp_path)
    record: dict[str, Any] = {"id": "upload-001", "Q_m3h": 50}
    path = backend.write_queue("upload-001", record)
    assert path
    assert os.path.exists(path)
    # Round-trip
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["id"] == "upload-001"
    assert data["Q_m3h"] == 50


def test_tmp_write_rejected(tmp_path):
    backend = TmpQueueBackend(tmp_path)
    record = {"id": "upload-002", "reason": "low_confidence"}
    path = backend.write_rejected("upload-002", record)
    assert path
    assert "_rejected" in path


def test_tmp_append_accepted(tmp_path):
    backend = TmpQueueBackend(tmp_path)
    rec1 = {"id": "a", "Q": 10}
    rec2 = {"id": "b", "Q": 20}
    assert backend.append_accepted(rec1)
    assert backend.append_accepted(rec2)
    # Two lines in jsonl
    lines = backend.jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == "a"
    assert json.loads(lines[1])["id"] == "b"


# ---------------------------------------------------------------------------
# S3QueueBackend (boto3 mocked)
# ---------------------------------------------------------------------------


def _make_mock_s3_uploader() -> tuple[S3Uploader, MagicMock]:
    """Возвращает uploader с инжектированным mock boto3 client."""
    mock_client = MagicMock()
    # NoSuchKey по умолчанию — пустой каталог.
    err = type("NoSuchKey", (Exception,), {})
    mock_client.get_object.side_effect = err("NoSuchKey")
    uploader = S3Uploader(
        bucket="kns-calculator-tz-archive",
        prefix="tz_archive/",
        access_key="fake",
        secret_key="fake",
        client=mock_client,
    )
    return uploader, mock_client


def test_s3_write_queue_uses_correct_key():
    uploader, mock_client = _make_mock_s3_uploader()
    # uploader.upload_text → put_object под капотом
    mock_client.put_object.return_value = {}
    backend = S3QueueBackend(uploader=uploader)
    record = {"id": "upload-007", "Q_m3h": 88}
    key = backend.write_queue("upload-007", record)
    assert key == "tz_archive/queue/upload-007.json"
    # Verify put_object called with proper bucket+key
    call = mock_client.put_object.call_args
    assert call.kwargs["Bucket"] == "kns-calculator-tz-archive"
    assert call.kwargs["Key"] == "tz_archive/queue/upload-007.json"


def test_s3_write_rejected_uses_correct_key():
    uploader, mock_client = _make_mock_s3_uploader()
    mock_client.put_object.return_value = {}
    backend = S3QueueBackend(uploader=uploader)
    key = backend.write_rejected("upload-008", {"id": "upload-008", "status": "rejected"})
    assert key == "tz_archive/rejected/upload-008.json"


def test_s3_append_accepted_read_modify_write():
    uploader, mock_client = _make_mock_s3_uploader()
    # Первый вызов: NoSuchKey (новый каталог)
    err = type("NoSuchKey", (Exception,), {})
    mock_client.get_object.side_effect = err("NoSuchKey")
    mock_client.put_object.return_value = {}
    backend = S3QueueBackend(uploader=uploader)
    ok = backend.append_accepted({"id": "x", "Q": 50})
    assert ok
    # Should have called put_object on accepted.jsonl key
    call = mock_client.put_object.call_args
    assert call.kwargs["Key"].endswith("/_metadata/accepted.jsonl")
    body = call.kwargs["Body"]
    assert b'"id": "x"' in body
    assert body.endswith(b"\n")


def test_s3_backend_unconfigured_returns_empty():
    """Без credentials uploader.is_configured = False → operations no-op."""
    uploader = S3Uploader(bucket="b", access_key=None, secret_key=None)
    backend = S3QueueBackend(uploader=uploader)
    assert not backend.is_configured
    # append_accepted без credentials → False (graceful)
    assert backend.append_accepted({"id": "x"}) is False
    # write_queue → uploader.upload_text returns error, key=""
    key = backend.write_queue("u-1", {"id": "u-1"})
    assert key == ""


def test_protocol_compliance():
    """TmpQueueBackend и S3QueueBackend оба удовлетворяют Protocol."""
    tmp = TmpQueueBackend("/tmp/x")
    uploader, _ = _make_mock_s3_uploader()
    s3 = S3QueueBackend(uploader=uploader)
    assert isinstance(tmp, QueueBackend)
    assert isinstance(s3, QueueBackend)
