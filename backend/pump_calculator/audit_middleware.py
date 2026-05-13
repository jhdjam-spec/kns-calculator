"""Audit log middleware для 152-ФЗ compliance.

Записывает все state-changing операции, имеющие потенциальный риск утечки
персональных данных или модификации каталога:

- ``/admin/*``         — кто, когда, что изменил (PII-аудит admin-панели)
- ``/import/parse``    — приём ТЗ от клиента (архив /Parser_Project_KNS)
- ``/handoff/*``       — генерация PDF/DOCX (опросники с ФИО клиента)
- ``/etl/classify``    — загрузка чужих PDF на парсинг

Output: structlog JSON в канал ``audit.request``. В YC Logging этот канал
отправляется в **отдельный** retention bucket (5 лет согласно 152-ФЗ ст.19
п.7 + ст.21).

Middleware регистрируется ПОСЛЕ ``CorrelationIdMiddleware``: так
``request_id`` уже в contextvars и попадает в audit-запись через bind.

Sc.D. audit 2026-05-13: «закрытый бета без audit-trail = нарушение 152-ФЗ
ст.19, штраф до 18 млн ₽ за инцидент → block public release».

Reference:
- 152-ФЗ ст.19 (требования к защите ПДн)
- OWASP A09:2021 — Security Logging and Monitoring Failures
- ГОСТ Р 57580.1-2017 п.7.2 (логирование критичных операций)
"""

from __future__ import annotations

import time
from collections.abc import Iterable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

audit_log = structlog.get_logger("audit.request")

# Каждый префикс пути считается «sensitive»: state-change или PII.
# Любой запрос, начинающийся с одного из этих префиксов, логируется.
SENSITIVE_PATHS: tuple[str, ...] = (
    "/admin",
    "/import/parse",
    "/handoff",
    "/etl/classify",
)


def _is_sensitive(path: str, prefixes: Iterable[str] = SENSITIVE_PATHS) -> bool:
    """True если путь подпадает под audit-логирование.

    Вынесено в отдельную функцию для unit-тестируемости.
    """
    return any(path.startswith(p) for p in prefixes)


class AuditMiddleware(BaseHTTPMiddleware):
    """Логирует sensitive-запросы как structlog JSON-events.

    Поля события:
    - ``event``        — ``"request"`` (успех) / ``"request_failed"`` (исключение)
    - ``method``       — HTTP метод
    - ``path``         — URL path (без query — query может содержать ПДн)
    - ``status``       — HTTP status code (только для success)
    - ``ip``           — client IP (или ``"unknown"``)
    - ``ua``           — User-Agent (обрезан до 200 символов)
    - ``request_id``   — X-Request-ID header (если CorrelationId middleware
                         работает раньше — поле дублируется через contextvars)
    - ``body_bytes``   — Content-Length (НЕ body content — может быть ПДн!)
    - ``duration_ms``  — время обработки в мс
    """

    def __init__(self, app: ASGIApp, sensitive_paths: tuple[str, ...] | None = None):
        super().__init__(app)
        self._prefixes: tuple[str, ...] = (
            tuple(sensitive_paths) if sensitive_paths is not None else SENSITIVE_PATHS
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not _is_sensitive(path, self._prefixes):
            return await call_next(request)

        start = time.monotonic()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        # X-Request-ID может быть установлен внешним CorrelationIdMiddleware.
        # Если его нет — пустая строка, не None (упрощает структуру JSON).
        request_id = request.headers.get("x-request-id", "")

        # Body может содержать ПДн (ФИО клиента в опроснике, e-mail в /admin).
        # ЛОГИРУЕМ ТОЛЬКО ДЛИНУ через Content-Length — никогда не читаем body.
        body_len_raw = request.headers.get("content-length", "0")
        try:
            body_len = int(body_len_raw)
        except (TypeError, ValueError):
            body_len = 0

        try:
            response: Response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 — мы хотим залогировать ЛЮБУЮ ошибку
            duration_ms = int((time.monotonic() - start) * 1000)
            audit_log.error(
                "request_failed",
                method=request.method,
                path=path,
                ip=client_ip,
                ua=user_agent[:200],
                request_id=request_id,
                body_bytes=body_len,
                error=str(exc)[:500],
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        audit_log.info(
            "request",
            method=request.method,
            path=path,
            status=response.status_code,
            ip=client_ip,
            ua=user_agent[:200],
            request_id=request_id,
            body_bytes=body_len,
            duration_ms=duration_ms,
        )
        return response


__all__ = ["AuditMiddleware", "SENSITIVE_PATHS", "_is_sensitive", "audit_log"]
