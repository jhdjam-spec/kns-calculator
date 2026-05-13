"""Persistent queue backends для dataset enrichment.

Проблема
========
``DatasetEnricher`` пишет queued/rejected/accepted записи в filesystem
(на YC Functions это ``/tmp/uploads``, ephemeral). После cold-stop
контейнера queue теряется → upload, ожидавший admin-approve, исчезает.

Sc.D. audit 2026-05-13 (P0 public release blocker):
    «`/tmp/uploads` — ephemeral. После cold-stop контейнера queue
     теряется. Нужен persistent backend (S3 / DB).»

Решение
=======
Вводим **Protocol** ``QueueBackend`` с тремя операциями:

- ``write_queue(upload_id, record)`` — положить в очередь
- ``write_rejected(upload_id, record)`` — переместить в rejected
- ``append_accepted(record)`` — добавить в JSONL accepted

Две реализации:

- ``TmpQueueBackend`` — текущее поведение (filesystem,
  ``/tmp/uploads`` на YC). Default для dev / local.
- ``S3QueueBackend`` — пишет в bucket ``kns-calculator-tz-archive``
  под ключами ``queue/``, ``rejected/`` и ``_metadata/accepted.jsonl``.
  Production-default после миграции.

Выбор бэкенда через ENV ``KNS_QUEUE_BACKEND=tmp|s3`` (default ``tmp``,
чтобы не сломать существующие развёртывания).

Реализация append_accepted в S3
================================
S3 не поддерживает native append → читаем-добавляем-перезаписываем.
Для accepted.jsonl можно дополнительно включить S3 Object Versioning
на bucket — тогда каждая перезапись = новая версия, безопасно от race
(только последний writer выиграет, но история сохранится).

Reference:
- 152-ФЗ ст.19 — требования к сохранности ПДн
- AWS S3 Versioning — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- YC Object Storage — https://yandex.cloud/ru/docs/storage/concepts/versioning
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import structlog

from pump_calculator.etl.s3_uploader import S3Uploader

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENV_BACKEND = "KNS_QUEUE_BACKEND"
BACKEND_TMP = "tmp"
BACKEND_S3 = "s3"

# S3 key layout
S3_QUEUE_PREFIX = "queue/"
S3_REJECTED_PREFIX = "rejected/"
S3_ACCEPTED_JSONL_KEY = "_metadata/accepted.jsonl"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class QueueBackend(Protocol):
    """Abstract storage для upload queue.

    Все методы возвращают строку — путь / S3-key куда записали (для логов),
    или пустую строку при ошибке. ``append_accepted`` возвращает bool —
    проще для интеграции с существующим DatasetEnricher.

    Реализации НЕ raise — graceful degradation (как у S3Uploader).
    """

    def write_queue(self, upload_id: str, record: dict[str, Any]) -> str:
        """Положить ``record`` в очередь на ручной review."""
        ...

    def write_rejected(self, upload_id: str, record: dict[str, Any]) -> str:
        """Переместить ``record`` в rejected (admin отверг)."""
        ...

    def append_accepted(self, record: dict[str, Any]) -> bool:
        """Добавить ``record`` в JSONL auto-accepted."""
        ...


# ---------------------------------------------------------------------------
# TmpQueueBackend — текущее поведение
# ---------------------------------------------------------------------------


class TmpQueueBackend:
    """Filesystem backend (default).

    ВНИМАНИЕ: на YC Functions ``/tmp`` ephemeral — данные теряются при
    cold-stop. Для production используйте ``S3QueueBackend``.

    Структура:
        <root>/etalons/from_uploads/_queue/<id>.json
        <root>/etalons/from_uploads/_rejected/<id>.json
        <root>/etalons/from_uploads/etalons_uploaded.jsonl
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.queue_dir = self.root / "etalons" / "from_uploads" / "_queue"
        self.rejected_dir = self.root / "etalons" / "from_uploads" / "_rejected"
        self.jsonl_path = self.root / "etalons" / "from_uploads" / "etalons_uploaded.jsonl"

    def _ensure(self, d: Path) -> bool:
        try:
            d.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            logger.warning("tmp_queue_mkdir_failed", path=str(d), error=str(e))
            return False

    def write_queue(self, upload_id: str, record: dict[str, Any]) -> str:
        if not self._ensure(self.queue_dir):
            return ""
        p = self.queue_dir / f"{upload_id}.json"
        try:
            p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("tmp_queue_write_failed", path=str(p), error=str(e))
            return ""
        return str(p)

    def write_rejected(self, upload_id: str, record: dict[str, Any]) -> str:
        if not self._ensure(self.rejected_dir):
            return ""
        p = self.rejected_dir / f"{upload_id}.json"
        try:
            p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("tmp_rejected_write_failed", path=str(p), error=str(e))
            return ""
        return str(p)

    def append_accepted(self, record: dict[str, Any]) -> bool:
        if not self._ensure(self.jsonl_path.parent):
            return False
        try:
            line = json.dumps(record, ensure_ascii=False) + "\n"
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(line)
            return True
        except OSError as e:
            logger.warning("tmp_accepted_append_failed", path=str(self.jsonl_path), error=str(e))
            return False


# ---------------------------------------------------------------------------
# S3QueueBackend — persistent
# ---------------------------------------------------------------------------


class S3QueueBackend:
    """S3-based queue (persistent через cold-stop YC Functions).

    Хранит:
        - ``{prefix}queue/<id>.json``      — queue items
        - ``{prefix}rejected/<id>.json``   — admin-rejected
        - ``{prefix}_metadata/accepted.jsonl`` — append JSONL для auto-accepted

    Append-семантика для accepted.jsonl: S3 не имеет native append, поэтому
    делаем read-modify-write. Race protection — включить **S3 Versioning**
    на bucket (YC Object Storage: ``yc storage bucket update --versioning enabled``).
    """

    def __init__(self, uploader: S3Uploader | None = None) -> None:
        self._uploader = uploader or S3Uploader.from_env()

    @property
    def is_configured(self) -> bool:
        return self._uploader.is_configured

    def _key(self, suffix: str) -> str:
        prefix = self._uploader.prefix.rstrip("/") + "/"
        return f"{prefix}{suffix}"

    def write_queue(self, upload_id: str, record: dict[str, Any]) -> str:
        key = self._key(f"{S3_QUEUE_PREFIX}{upload_id}.json")
        return self._put_json(key, record)

    def write_rejected(self, upload_id: str, record: dict[str, Any]) -> str:
        key = self._key(f"{S3_REJECTED_PREFIX}{upload_id}.json")
        return self._put_json(key, record)

    def _put_json(self, key: str, record: dict[str, Any]) -> str:
        body = json.dumps(record, ensure_ascii=False, indent=2)
        res = self._uploader.upload_text(
            body,
            key,
            metadata={
                "upload-id": record.get("id") or record.get("upload_id") or "",
                "status": record.get("status") or "",
            },
        )
        if res.get("error"):
            logger.warning("s3_queue_put_failed", key=key, error=res["error"])
            return ""
        return res.get("key") or ""

    def append_accepted(self, record: dict[str, Any]) -> bool:
        """Read-modify-write для JSONL.

        На bucket рекомендуется S3 Object Versioning: если две lambda
        одновременно append'нут, обе версии сохранятся в истории,
        а в текущей видна последняя — частичная потеря, но не silent.
        Для full safety используйте отдельный SQS / SNS pipeline.
        """
        client = self._uploader._get_client()  # noqa: SLF001 — controlled internal access
        if client is None:
            logger.warning("s3_accepted_append_no_client")
            return False
        key = self._key(S3_ACCEPTED_JSONL_KEY)
        existing = b""
        try:
            obj = client.get_object(Bucket=self._uploader.bucket, Key=key)
            existing = obj["Body"].read()
        except Exception as e:  # noqa: BLE001 — NoSuchKey ожидаем при первом запросе
            err_name = e.__class__.__name__
            if err_name not in ("NoSuchKey", "ClientError"):
                logger.warning("s3_accepted_read_failed", key=key, error=str(e))
        new_line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        body = existing + new_line
        try:
            client.put_object(
                Bucket=self._uploader.bucket,
                Key=key,
                Body=body,
                ContentType="application/x-ndjson; charset=utf-8",
            )
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("s3_accepted_put_failed", key=key, error=str(e))
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_queue_backend(
    *,
    tmp_root: Path | str | None = None,
    backend_override: str | None = None,
) -> QueueBackend:
    """Выбрать backend через ENV ``KNS_QUEUE_BACKEND``.

    - ``tmp`` (default) — ``TmpQueueBackend`` (filesystem, /tmp на YC).
    - ``s3``           — ``S3QueueBackend`` (persistent, требует AWS_ACCESS_KEY).

    Если ``s3`` запрошен, но uploader не сконфигурирован → fallback к
    ``TmpQueueBackend`` с warning (чтобы /import/parse не падал в проде
    при отсутствии S3 кред).

    Parameters
    ----------
    tmp_root
        Корневая директория для tmp backend. Если None — берём из ENV
        ``KNS_DATASET_UPLOADS_ROOT`` или ``/tmp/uploads``.
    backend_override
        Явное значение backend (для тестов).
    """
    backend = (backend_override or os.environ.get(ENV_BACKEND, BACKEND_TMP)).lower().strip()

    if backend == BACKEND_S3:
        s3_backend = S3QueueBackend()
        if s3_backend.is_configured:
            return s3_backend
        logger.warning(
            "queue_backend_s3_unconfigured_fallback_tmp",
            reason="AWS_ACCESS_KEY_ID/SECRET missing — using tmp backend",
        )

    # tmp default
    root = (
        Path(tmp_root)
        if tmp_root
        else Path(os.environ.get("KNS_DATASET_UPLOADS_ROOT", "/tmp/uploads"))
    )
    return TmpQueueBackend(root=root)


__all__ = [
    "BACKEND_S3",
    "BACKEND_TMP",
    "ENV_BACKEND",
    "QueueBackend",
    "S3QueueBackend",
    "TmpQueueBackend",
    "get_queue_backend",
]
