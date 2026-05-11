"""S3 (Yandex Object Storage) uploader — primary архив ТЗ.

Назначение
==========
После `POST /import/parse` оригинал ТЗ + результат парсинга должны
архивироваться в **S3 (primary)** — это даёт нам:

1. Полный audit-trail входящих заявок (когда, что, какой parsed JSON).
2. Возможность построить dataset enrichment pipeline
   (см. ``dataset_enrichment.py``) — переносить высокоуверенные
   заявки в эталоны.
3. Source-of-truth для будущей review-UI (`/admin/uploads`).

Параллельно работает ``yadisk_uploader`` (mirror): Я.Диск держим для
менеджеров Серво-Юг (привычный интерфейс), S3 — для backend pipeline.

Структура S3
============
Bucket: ``kns-calculator-tz-archive`` (приватный, env ``KNS_S3_BUCKET_TZ``).

::

    tz_archive/
        <YYYY>/<MM>/<DD>/
            <HH-MM-SS>_Q<Q>_<type>_<city>_<hash>.txt
            <HH-MM-SS>_Q<Q>_<type>_<city>_<hash>.parsed.json
        _metadata/
            catalog.jsonl    — append-only лог всех uploads

Каждый upload даёт **2 объекта** (raw + parsed) + одну строку в каталоге.

Зависимости
===========
``boto3`` импортируется лениво внутри методов — package не обязателен в
YC Functions runtime. Если ``boto3`` нет, ``is_configured`` возвращает
``False`` и все uploads — no-op (graceful degradation, как у Я.Диска).

ENV
===
- ``KNS_S3_BUCKET_TZ`` — имя bucket (default ``kns-calculator-tz-archive``).
- ``KNS_S3_ENDPOINT`` — endpoint (default ``https://storage.yandexcloud.net``).
- ``KNS_S3_PREFIX`` — корневой префикс (default ``tz_archive/``).
- ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY`` — креды (формат
  совместим с YC статическими ключами для S3-совместимого API).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

DEFAULT_BUCKET = "kns-calculator-tz-archive"
DEFAULT_ENDPOINT = "https://storage.yandexcloud.net"
DEFAULT_PREFIX = "tz_archive/"
DEFAULT_REGION = "ru-central1"
CATALOG_KEY_TEMPLATE = "{prefix}_metadata/catalog.jsonl"

# Limits
DEFAULT_TIMEOUT_S = 15.0
MAX_FILENAME_PART_LEN = 60


class S3UploadError(Exception):
    """Базовая ошибка S3 uploader."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _slugify_part(value: Any) -> str:
    """Безопасное представление поля для имени S3-ключа.

    S3 принимает большинство символов, но для предсказуемых URL и
    audit-trail чистим всё кроме ASCII букв/цифр/`.`/`_`/`-`.
    Кириллица транслитерируется упрощённо (для простоты — отбрасываем).
    """
    s = str(value).strip()
    # Простая транслитерация кириллицы → ASCII для S3-ключей.
    # Дублирование оригинального названия едет в metadata.
    table = str.maketrans(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
        "abvgdeezzijklmnoprstufhccssxyxeuyABVGDEEZZIJKLMNOPRSTUFHCCSSXYXEUY",
    )
    s = s.translate(table)
    s = _SAFE_NAME_RE.sub("_", s)
    return s[:MAX_FILENAME_PART_LEN].strip("_") or "x"


def build_s3_key(
    parsed: dict[str, Any] | None,
    *,
    prefix: str = DEFAULT_PREFIX,
    timestamp: datetime | None = None,
    extension: str = "txt",
    content_hash: str | None = None,
) -> str:
    """Собрать каноничный S3-ключ для оригинала ТЗ.

    Формат: ``{prefix}{YYYY}/{MM}/{DD}/{HH-MM-SS}_Q{Q}_{type}_{city}_{hash6}.{ext}``

    ``content_hash`` — короткий sha256[:6] от тела (для defence-in-depth
    против коллизий имён при одновременной вставке двух разных ТЗ).
    """
    ts = timestamp or datetime.now(UTC)
    date_part = ts.strftime("%Y/%m/%d")
    time_part = ts.strftime("%H-%M-%S")

    name_parts: list[str] = [time_part]
    if parsed:
        q = parsed.get("Q_m3h")
        if q is not None:
            name_parts.append(f"Q{q}")
        obj_type = parsed.get("object_type")
        if obj_type:
            name_parts.append(_slugify_part(obj_type).lower())
        city = parsed.get("city")
        if city:
            name_parts.append(_slugify_part(city))
    if content_hash:
        name_parts.append(content_hash[:6])

    base = "_".join(p for p in name_parts if p)
    return f"{prefix.rstrip('/')}/{date_part}/{base}.{extension}"


def _hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def make_upload_id(timestamp: datetime, content_hash: str) -> str:
    """Стабильный ID upload-операции — используется как ключ в каталоге.

    Формат: ``upload-YYYY-MM-DD-HHMMSS-<hash6>``
    """
    return f"upload-{timestamp.strftime('%Y-%m-%d-%H%M%S')}-{content_hash[:6]}"


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class S3Uploader:
    """Тонкий клиент S3 для архивирования ТЗ.

    Использует ``boto3`` (если установлен). Если ``boto3`` или credentials
    отсутствуют — все uploads no-op возвращают ``{"key": None, "error": ...}``,
    чтобы /import/parse не падал.

    Examples
    --------
    >>> up = S3Uploader.from_env()
    >>> if up.is_configured:
    ...     res = up.upload_text("Q=88 ...", "tz_archive/2026/05/11/tz.txt", {})
    ...     # res["key"], res["bucket"], res["size_bytes"]
    """

    def __init__(
        self,
        *,
        bucket: str | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
        prefix: str = DEFAULT_PREFIX,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = DEFAULT_REGION,
        client: Any = None,
    ) -> None:
        self.bucket = bucket or DEFAULT_BUCKET
        self.endpoint = endpoint
        self.prefix = prefix if prefix.endswith("/") else prefix + "/"
        self._access_key = (access_key or "").strip() or None
        self._secret_key = (secret_key or "").strip() or None
        self._region = region
        # Тесты могут подменить boto3 client напрямую.
        self._client = client

    @classmethod
    def from_env(cls) -> S3Uploader:
        """Конструктор по умолчанию — все настройки берёт из ENV."""
        return cls(
            bucket=os.environ.get("KNS_S3_BUCKET_TZ", DEFAULT_BUCKET),
            endpoint=os.environ.get("KNS_S3_ENDPOINT", DEFAULT_ENDPOINT),
            prefix=os.environ.get("KNS_S3_PREFIX", DEFAULT_PREFIX),
            access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region=os.environ.get("KNS_S3_REGION", DEFAULT_REGION),
        )

    # ------------------------------------------------------------------
    # Lazy client
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Ленивая инициализация boto3-клиента.

        Returns None если креды/boto3 не доступны (тогда вызывающий код
        должен сделать graceful degradation).
        """
        if self._client is not None:
            return self._client
        if not (self._access_key and self._secret_key):
            return None
        try:
            import boto3  # noqa: PLC0415

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
            )
            return self._client
        except ImportError:
            logger.warning("boto3 not installed — S3 archive disabled")
            return None
        except Exception as e:  # noqa: BLE001
            logger.warning("S3 client init failed: %s", e)
            return None

    @property
    def is_configured(self) -> bool:
        """``True`` если есть креды (boto3 проверяется при первом upload).

        Без вызова _get_client() — иначе проверка имеет side effect.
        """
        return bool(self._access_key and self._secret_key)

    # ------------------------------------------------------------------
    # Internal HTTP
    # ------------------------------------------------------------------

    def _put_object(
        self,
        key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Низкоуровневый put_object с graceful failure."""
        client = self._get_client()
        if client is None:
            return {
                "bucket": self.bucket,
                "key": None,
                "size_bytes": len(body),
                "url": None,
                "error": "S3 not configured (boto3/AWS_ACCESS_KEY missing)",
            }
        # boto3 metadata должна быть строками ASCII (S3 спецификация).
        # Не-ASCII значения base64-кодируем в JSON-строку.
        safe_meta: dict[str, str] = {}
        for k, v in (metadata or {}).items():
            try:
                v_str = "" if v is None else str(v)
                v_str.encode("ascii")
                safe_meta[k] = v_str[:256]
            except UnicodeEncodeError:
                # Fallback: упаковываем в hex чтобы остаться в ASCII
                safe_meta[k] = "hex:" + str(v).encode("utf-8").hex()[:256]
        try:
            client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                Metadata=safe_meta,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("S3 put_object failed (key=%s): %s", key, e)
            return {
                "bucket": self.bucket,
                "key": None,
                "size_bytes": len(body),
                "url": None,
                "error": f"S3 upload failed: {e.__class__.__name__}: {e}",
            }
        url = f"{self.endpoint.rstrip('/')}/{self.bucket}/{key}"
        return {
            "bucket": self.bucket,
            "key": key,
            "size_bytes": len(body),
            "url": url,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Public upload
    # ------------------------------------------------------------------

    def upload_text(
        self,
        content: str,
        filename: str,
        metadata: dict[str, Any] | None = None,
        *,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Загрузить plain-text ТЗ. ``filename`` — это **полный key** или хвост.

        Если ``filename`` начинается с ``self.prefix`` — используется как
        полный key. Иначе считается «именем» и кладётся в текущий
        ``{prefix}{YYYY/MM/DD}/`` (для совместимости с произвольным API).
        """
        body = content.encode(encoding)
        key = self._normalize_key(filename)
        return self._put_object(
            key, body, content_type=f"text/plain; charset={encoding}", metadata=metadata
        )

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Загрузить произвольный binary (DOCX/PDF/etc)."""
        key = self._normalize_key(filename)
        return self._put_object(key, file_bytes, content_type=content_type, metadata=metadata)

    def _normalize_key(self, name_or_key: str) -> str:
        """Если ``name_or_key`` уже содержит prefix — оставить, иначе
        положить в ``{prefix}{YYYY/MM/DD}/``."""
        if name_or_key.startswith(self.prefix):
            return name_or_key
        ts = datetime.now(UTC)
        return f"{self.prefix}{ts.strftime('%Y/%m/%d')}/{name_or_key.lstrip('/')}"

    # ------------------------------------------------------------------
    # Catalog (append-only log)
    # ------------------------------------------------------------------

    def append_catalog(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Дозаписать запись в ``{prefix}_metadata/catalog.jsonl``.

        S3 не поддерживает append → читаем существующий объект, добавляем
        строку, перезаписываем. Для production — стоит уметь partition'ить
        по дате (catalog-YYYY-MM.jsonl), но для MVP объём не критичен.
        """
        client = self._get_client()
        catalog_key = CATALOG_KEY_TEMPLATE.format(prefix=self.prefix)
        if client is None:
            return {
                "key": None,
                "error": "S3 not configured — catalog skipped",
            }
        existing = b""
        try:
            obj = client.get_object(Bucket=self.bucket, Key=catalog_key)
            existing = obj["Body"].read()
        except Exception as e:  # noqa: BLE001
            # NoSuchKey — нормально, ещё не было записей.
            err_name = e.__class__.__name__
            if err_name not in ("NoSuchKey", "ClientError"):
                logger.warning("catalog read failed (%s): %s — start fresh", err_name, e)
        new_line = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
        body = existing + new_line
        try:
            client.put_object(
                Bucket=self.bucket,
                Key=catalog_key,
                Body=body,
                ContentType="application/x-ndjson; charset=utf-8",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("catalog put failed: %s", e)
            return {"key": None, "error": f"catalog put failed: {e}"}
        return {"key": catalog_key, "error": None, "size_bytes": len(body)}

    def read_catalog(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Прочитать catalog.jsonl и распарсить N последних записей.

        Возвращает пустой list если каталога ещё нет.
        """
        client = self._get_client()
        if client is None:
            return []
        catalog_key = CATALOG_KEY_TEMPLATE.format(prefix=self.prefix)
        try:
            obj = client.get_object(Bucket=self.bucket, Key=catalog_key)
            raw = obj["Body"].read().decode("utf-8")
        except Exception:  # noqa: BLE001
            return []
        entries: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if limit is not None and limit > 0:
            entries = entries[-limit:]
        return entries

    def get_object_text(self, key: str) -> str | None:
        """Прочитать объект как text. None если нет/ошибка."""
        client = self._get_client()
        if client is None:
            return None
        try:
            obj = client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            logger.warning("S3 get %s failed: %s", key, e)
            return None


# ---------------------------------------------------------------------------
# High-level convenience
# ---------------------------------------------------------------------------


def archive_tz_to_s3(
    text: str,
    parsed: dict[str, Any],
    *,
    uploader: S3Uploader | None = None,
    original_filename: str | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Положить оригинал ТЗ + parsed JSON в S3 + дописать catalog entry.

    Returns
    -------
    dict с ключами:
        - ``bucket``, ``key``, ``size_bytes``, ``url`` — для raw text upload
        - ``parsed_key`` — ключ ``.parsed.json``
        - ``upload_id`` — стабильный ID (``upload-YYYY-MM-DD-...``)
        - ``error`` — None при успехе, иначе строка-описание
        - ``configured`` — был ли uploader сконфигурирован (False → no-op)

    Никогда не throws — graceful degradation.
    """
    up = uploader or S3Uploader.from_env()
    ts = timestamp or datetime.now(UTC)
    body_bytes = text.encode("utf-8")
    content_hash = _hash_content(body_bytes)
    upload_id = make_upload_id(ts, content_hash)

    if not up.is_configured:
        return {
            "bucket": up.bucket,
            "key": None,
            "parsed_key": None,
            "upload_id": upload_id,
            "size_bytes": len(body_bytes),
            "url": None,
            "configured": False,
            "error": "S3 not configured (AWS_ACCESS_KEY_ID missing)",
        }

    # 1. Raw text
    raw_key = build_s3_key(
        parsed, prefix=up.prefix, timestamp=ts, extension="txt", content_hash=content_hash
    )
    confidence = parsed.get("confidence", 0.0)
    metadata = {
        "upload-id": upload_id,
        "confidence": str(confidence),
        "q-m3h": str(parsed.get("Q_m3h") or ""),
        "dh-m": str(parsed.get("dH_m") or ""),
        "wastewater-type": str(parsed.get("wastewater_type") or ""),
        "object-type": str(parsed.get("object_type") or ""),
        "original-filename": _slugify_part(original_filename or "manual_paste"),
        "content-hash": content_hash[:32],
    }
    raw_res = up.upload_text(text, raw_key, metadata=metadata)
    if raw_res.get("error"):
        return {
            **raw_res,
            "parsed_key": None,
            "upload_id": upload_id,
            "configured": True,
        }

    # 2. Parsed JSON
    parsed_key = raw_key.removesuffix(".txt") + ".parsed.json"
    parsed_body = json.dumps(parsed, ensure_ascii=False, indent=2)
    parsed_res = up.upload_file(
        parsed_body.encode("utf-8"),
        parsed_key,
        content_type="application/json; charset=utf-8",
        metadata={"upload-id": upload_id},
    )

    # 3. Catalog
    catalog_entry = {
        "upload_id": upload_id,
        "uploaded_at": ts.isoformat(),
        "raw_key": raw_res["key"],
        "parsed_key": parsed_res.get("key"),
        "bucket": up.bucket,
        "size_bytes": raw_res["size_bytes"],
        "content_hash": content_hash,
        "confidence": confidence,
        "Q_m3h": parsed.get("Q_m3h"),
        "dH_m": parsed.get("dH_m"),
        "city": parsed.get("city"),
        "wastewater_type": parsed.get("wastewater_type"),
        "object_type": parsed.get("object_type"),
        "project_code": parsed.get("project_code"),
        "original_filename": original_filename,
    }
    catalog_res = up.append_catalog(catalog_entry)

    return {
        "bucket": raw_res["bucket"],
        "key": raw_res["key"],
        "parsed_key": parsed_res.get("key"),
        "upload_id": upload_id,
        "size_bytes": raw_res["size_bytes"],
        "url": raw_res["url"],
        "configured": True,
        "catalog_key": catalog_res.get("key"),
        "error": parsed_res.get("error") or catalog_res.get("error"),
    }
