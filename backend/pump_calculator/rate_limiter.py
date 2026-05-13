"""Rate limiter и body-size middleware для public endpoints kns-calculator.

Реализовано после Sc.D. Architecture аудита 2026-05-13:
- «POST 100MB на /import/parse = OOM на YC 512MB cap»
- «bot 1000 RPS положит счёт YC»

Архитектура
-----------
slowapi (FastAPI-compatible, in-memory) per-IP лимиты + кастомный
``BodyLimitMiddleware`` для отсечки crazy-large payloads до того как
FastAPI начнёт парсить body в RAM.

NB: slowapi in-memory storage. YC Functions concurrency=1 + cold start
= limits per warm-container, не глобальные. Для глобальных limits
(защита от distributed-атаки 1000 IP × 100 req/min) — заменить
``key_func`` на Redis-backed storage (``slowapi.Limiter(storage_uri=
"redis://...")``). Для текущего MVP scope warm-container защиты достаточно.

Лимиты подобраны исходя из:
- /import/parse: 10/minute (heavy parsing + S3 upload + Y.Disk mirror, ~1-3 sec)
- /select, /select/quick: 60/minute (typical inference, ~50-200 ms)
- /handoff/*: 20/minute (PDF/DOCX generation, ~500-1500 ms)
- /project/calculate: 30/minute (full orchestrator, ~300-800 ms)
- /etl/classify: 30/minute (regex/parsing, ~10-50 ms)
- default: 100/minute (всё остальное)
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Глобальный limiter; импортируется в api.py и используется как декоратор:
#   @limiter.limit("10/minute")
#   async def import_parse(request: Request, ...):
#       ...
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    # storage_uri="memory://"  # дефолт; для глобального лимита — redis://...
    # headers_enabled=False (дефолт): slowapi пытается мутировать Response.headers
    # внутри обёртки, но наши endpoint'ы возвращают dict / Pydantic-модель
    # (FastAPI оборачивает их в Response позже). Включение даёт
    # "parameter `response` must be an instance of starlette.responses.Response".
    # Retry-After мы ставим вручную в `_rate_limit_exceeded_handler` в api.py.
    headers_enabled=False,
)


# ─────────────────────────────────────────────────────────────────────────
# Body size middleware
# ─────────────────────────────────────────────────────────────────────────


class BodyLimitMiddleware:
    """ASGI middleware: 413 Payload Too Large для запросов больше ``max_size``.

    Проверяет ``Content-Length`` header ДО того как FastAPI начнёт парсить
    body — предотвращает OOM на YC Functions (512MB cap) при попытке
    POST 100MB на ``/import/parse``.

    Parameters
    ----------
    app : ASGI application
    max_size : int
        Максимальный размер body в байтах. По умолчанию 10 MiB.
    """

    def __init__(self, app, max_size: int = 10 * 1024 * 1024) -> None:
        self.app = app
        self.max_size = int(max_size)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # scope["headers"] — list[tuple[bytes, bytes]] в ASGI
        content_length = 0
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    content_length = int(value)
                except (ValueError, TypeError):
                    content_length = 0
                break

        if content_length > self.max_size:
            logger.warning(
                "BodyLimitMiddleware: rejected %d bytes > %d max (path=%s)",
                content_length,
                self.max_size,
                scope.get("path", "?"),
            )
            # Минимальный ASGI 413 response — не вызываем FastAPI вообще.
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": (
                        b'{"detail":"Request body too large. '
                        b'Max allowed size is '
                        + str(self.max_size).encode()
                        + b' bytes."}'
                    ),
                }
            )
            return

        await self.app(scope, receive, send)
