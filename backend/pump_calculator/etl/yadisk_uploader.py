"""Yandex.Disk uploader — архив оригиналов ТЗ для Серво-Юг.

Назначение
==========
После того, как менеджер парсит ТЗ через `POST /import/parse`, оригинал
текста должен попадать в архив на Яндекс.Диске Серво-Юг. Это позволяет:

1. Иметь полный аудит-trail входящих заявок (когда, что вставили).
2. Возвращаться к исходнику если парсер пропустил что-то.
3. Делиться оригиналом ТЗ с инженером без поиска в почте.

Структура архива
================
- Корень: `/inservo_tz_archive/`
- Подпапки по дате: `/inservo_tz_archive/2026-05-11/`
- Имя файла: `{date}_{time}_Q{Q}_{type}_{city}.txt`
  (или оригинальное имя если original_filename задан)

API
===
Yandex.Disk REST: https://yandex.ru/dev/disk/api/reference/all-files.html

Загрузка делается в 2 шага:
1. `GET /v1/disk/resources/upload?path=...&overwrite=true` — получаем upload_url.
2. `PUT <upload_url>` — кладём bytes контента.

Авторизация
===========
OAuth token в env `YANDEX_DISK_TOKEN`. Если токена нет → upload
выполняется как **no-op** (graceful degradation), вызывающий код
получает `archive_path=None, archive_error="...not configured"`.

Не используем httpx ради zero-deps (YC Functions cold-start) —
stdlib `urllib.request` достаточно для PUT/GET с заголовками.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

YADISK_API_BASE = "https://cloud-api.yandex.net/v1/disk"
# Корень архива на Я.Диске. По умолчанию /Parser_Project_KNS (2026-05-11
# по требованию заказчика). Можно переопределить через ENV YANDEX_DISK_ARCHIVE_ROOT.
DEFAULT_ARCHIVE_ROOT = os.environ.get("YANDEX_DISK_ARCHIVE_ROOT", "/Parser_Project_KNS")
DEFAULT_TIMEOUT_S = 15.0  # короткий, чтобы не блокировать /import/parse


class YaDiskError(Exception):
    """Базовая ошибка для всех проблем с Яндекс.Диск API."""


class YaDiskAuthError(YaDiskError):
    """401/403 — невалидный/просроченный токен или нет прав."""


class YaDiskQuotaError(YaDiskError):
    """507 — диск переполнен."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SAFE_FILENAME_RE = re.compile(r"[^A-Za-zА-Яа-яЁё0-9._-]+")


def safe_filename(name: str) -> str:
    """Заменить недопустимые символы в имени файла на «_».

    Я.Диск принимает unicode, но `/` `\\` `:` запрещены. Чистим всё кроме
    букв/цифр/`.`/`_`/`-`. Без agressive lowercasing — сохраняем регистр.
    """
    cleaned = _SAFE_FILENAME_RE.sub("_", name.strip())
    return cleaned[:200] if len(cleaned) > 200 else cleaned


def build_archive_filename(
    parsed: dict[str, Any] | None = None,
    *,
    original_filename: str | None = None,
    timestamp: datetime | None = None,
    extension: str = "txt",
) -> str:
    """Собрать каноническое имя файла в архиве.

    Приоритеты:
    1. Если задан `original_filename` — используем его как есть (safe-cleaned).
    2. Иначе — `{date}_{time}_Q{Q}_{type}_{city}.{ext}`,
       пропуская пустые поля.
    """
    if original_filename:
        return safe_filename(original_filename)

    ts = timestamp or datetime.now(UTC)
    parts: list[str] = [ts.strftime("%Y-%m-%d_%H-%M-%S")]

    if parsed:
        q = parsed.get("Q_m3h")
        if q is not None:
            parts.append(f"Q{q}")
        obj_type = parsed.get("object_type")
        if obj_type:
            parts.append(str(obj_type).lower())
        city = parsed.get("city")
        if city:
            parts.append(str(city))

    base = "_".join(parts)
    return safe_filename(f"{base}.{extension}")


def today_subfolder(timestamp: datetime | None = None) -> str:
    """`/inservo_tz_archive/2026-05-11`."""
    ts = timestamp or datetime.now(UTC)
    return f"{DEFAULT_ARCHIVE_ROOT}/{ts.strftime('%Y-%m-%d')}"


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class YaDiskUploader:
    """Тонкий клиент Яндекс.Диск REST для архивирования ТЗ.

    Не stateful — каждый upload делает 2 запроса (get-upload-url + PUT).
    Errors не throw'ятся наружу: вызывающий код получает dict с error-полем
    либо `None` для path при отсутствии токена.

    Examples
    --------
    >>> uploader = YaDiskUploader.from_env()
    >>> if uploader.is_configured:
    ...     result = uploader.upload_text("Q=88 м³/ч ...", "tz.txt")
    ...     # result["path"] == "/inservo_tz_archive/2026-05-11/tz.txt"
    """

    def __init__(
        self,
        token: str | None,
        *,
        api_base: str = YADISK_API_BASE,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self._token = (token or "").strip() or None
        self._api_base = api_base.rstrip("/")
        self._timeout_s = timeout_s
        # Тестам удобно подменить opener
        self._opener = opener or urllib.request.build_opener()

    @classmethod
    def from_env(cls, env_var: str = "YANDEX_DISK_TOKEN") -> YaDiskUploader:
        """Конструктор по умолчанию — берёт токен из ENV."""
        return cls(token=os.environ.get(env_var))

    @property
    def is_configured(self) -> bool:
        """`True` если задан токен — можно делать upload."""
        return self._token is not None

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            raise YaDiskError("YANDEX_DISK_TOKEN not configured")
        return {
            "Authorization": f"OAuth {self._token}",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> tuple[int, bytes]:
        """Сырой HTTP запрос с проброшенным opener'ом — для unit-mock."""
        req = urllib.request.Request(url=url, data=data, method=method, headers=headers or {})
        try:
            with self._opener.open(req, timeout=self._timeout_s) as resp:
                body = resp.read()
                return resp.status, body
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read() or b""
            except Exception:  # noqa: BLE001
                pass
            return e.code, body
        except urllib.error.URLError as e:
            raise YaDiskError(f"Network error: {e.reason}") from e
        except TimeoutError as e:
            raise YaDiskError(f"Timeout after {self._timeout_s}s") from e

    @staticmethod
    def _raise_for_status(code: int, body: bytes) -> None:
        if code == 401:
            raise YaDiskAuthError("Unauthorized — token invalid or expired")
        if code == 403:
            raise YaDiskAuthError("Forbidden — token has no disk:write scope")
        if code == 507:
            raise YaDiskQuotaError("Insufficient storage — disk full")
        if code >= 400:
            try:
                payload = json.loads(body.decode("utf-8", errors="replace"))
                msg = payload.get("message") or payload.get("description") or body[:200]
            except Exception:  # noqa: BLE001
                msg = body[:200].decode("utf-8", errors="replace")
            raise YaDiskError(f"HTTP {code}: {msg}")

    # ------------------------------------------------------------------
    # Folder management
    # ------------------------------------------------------------------

    def ensure_folder(self, path: str) -> bool:
        """Создать папку если её нет. `True` если создали или уже была.

        Я.Диск возвращает:
        - 201 — папка создана.
        - 409 — уже существует (нормально).
        - 401/403 — ошибка авторизации (raise).
        """
        if not self._token:
            return False
        url = f"{self._api_base}/resources?{urllib.parse.urlencode({'path': path})}"
        code, body = self._request("PUT", url, headers=self._auth_headers())
        if code in (201, 409):
            return True
        self._raise_for_status(code, body)
        return False

    def ensure_folder_chain(self, path: str) -> bool:
        """Создать всю цепочку папок (`/a/b/c` → `/a`, `/a/b`, `/a/b/c`)."""
        if not self._token:
            return False
        parts = [p for p in path.strip("/").split("/") if p]
        cur = ""
        for p in parts:
            cur = f"{cur}/{p}"
            try:
                self.ensure_folder(cur)
            except YaDiskError:
                # последний уровень мог упасть — пробрасываем выше
                raise
        return True

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def _get_upload_url(self, target_path: str, overwrite: bool = True) -> str:
        params = urllib.parse.urlencode(
            {"path": target_path, "overwrite": "true" if overwrite else "false"}
        )
        url = f"{self._api_base}/resources/upload?{params}"
        code, body = self._request("GET", url, headers=self._auth_headers())
        if code != 200:
            self._raise_for_status(code, body)
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise YaDiskError(f"Bad upload_url JSON: {e}") from e
        href = payload.get("href")
        if not href:
            raise YaDiskError("Yandex.Disk did not return upload href")
        return href

    def upload_bytes(
        self,
        content: bytes,
        filename: str,
        folder: str | None = None,
        *,
        content_type: str = "application/octet-stream",
        ensure_folder: bool = True,
    ) -> dict[str, Any]:
        """Универсальный upload bytes → возвращает {path, size_bytes, public_url}.

        При отсутствии токена возвращает `{"path": None, "error": "..."}`
        — это **не** raises, чтобы /import/parse не падал.
        """
        if not self._token:
            return {
                "path": None,
                "public_url": None,
                "size_bytes": len(content),
                "error": "YANDEX_DISK_TOKEN not configured",
            }

        target_folder = (folder or today_subfolder()).rstrip("/")
        target_path = f"{target_folder}/{filename}"

        try:
            if ensure_folder:
                self.ensure_folder_chain(target_folder)

            upload_url = self._get_upload_url(target_path, overwrite=True)
            code, body = self._request(
                "PUT",
                upload_url,
                headers={"Content-Type": content_type},
                data=content,
            )
            if code not in (201, 202):
                self._raise_for_status(code, body)
        except YaDiskError as e:
            logger.warning("Yandex.Disk upload failed: %s", e)
            return {
                "path": None,
                "public_url": None,
                "size_bytes": len(content),
                "error": str(e),
            }

        return {
            "path": target_path,
            "public_url": None,
            "size_bytes": len(content),
            "error": None,
        }

    def upload_text(
        self,
        content: str,
        filename: str,
        folder: str | None = None,
        *,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Загрузить plain-text. UTF-8 BOM не добавляем."""
        return self.upload_bytes(
            content.encode(encoding),
            filename=filename,
            folder=folder,
            content_type=f"text/plain; charset={encoding}",
        )

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str | None = None,
        *,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Загрузить любой бинарный файл (DOCX/PDF)."""
        return self.upload_bytes(
            file_bytes,
            filename=filename,
            folder=folder,
            content_type=content_type,
        )


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def archive_tz_text(
    text: str,
    parsed: dict[str, Any] | None = None,
    *,
    original_filename: str | None = None,
    uploader: YaDiskUploader | None = None,
) -> dict[str, Any]:
    """High-level: положить текст ТЗ в архив `/inservo_tz_archive/<date>/`.

    Возвращает dict вида:
        {"archive_path": "/inservo_tz_archive/.../file.txt" | None,
         "archive_error": "..." | None,
         "archive_size_bytes": 1024}
    """
    up = uploader or YaDiskUploader.from_env()
    filename = build_archive_filename(parsed=parsed, original_filename=original_filename)
    result = up.upload_text(text, filename=filename)
    return {
        "archive_path": result.get("path"),
        "archive_error": result.get("error"),
        "archive_size_bytes": result.get("size_bytes", 0),
    }
