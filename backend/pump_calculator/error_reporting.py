"""Error reporting stub.

В prod: ``SENTRY_DSN`` env → enable ``sentry_sdk`` integrations.
В dev:  no-op (структурированные logs через structlog достаточно).

Зачем
-----
PhD Architecture audit (2026-05-13) указал: «нет single point of error reporting».
Sc.D. подтвердил: для B2B closed-beta достаточно ``logger.exception`` + опционально
Sentry SDK при наличии DSN. ``sentry-sdk`` оставлен опциональной зависимостью,
чтобы не раздувать zip-пакет YC Functions (cap 500 MB на code+layers).

Использование
-------------
.. code-block:: python

    from pump_calculator.error_reporting import init_sentry, capture_exception

    init_sentry()  # один раз при cold start

    try:
        risky()
    except Exception as e:
        capture_exception(e, endpoint="/select", user_q=21.2)
        raise
"""

from __future__ import annotations

import os
from typing import Any

import structlog

_logger = structlog.get_logger("error_reporting")


def init_sentry() -> bool:
    """Initialize Sentry SDK if ``SENTRY_DSN`` configured.

    Returns
    -------
    bool
        True, если Sentry успешно инициализирован; False — DSN не задан
        или ``sentry-sdk`` не установлен.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        _logger.info("sentry_disabled", reason="SENTRY_DSN env not set")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FastApiIntegration(), StarletteIntegration()],
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.environ.get("ENV", "dev"),
            release=os.environ.get("APP_VERSION", "unknown"),
        )
        _logger.info("sentry_initialized", environment=os.environ.get("ENV", "dev"))
        return True
    except ImportError:
        _logger.warning(
            "sentry_unavailable",
            reason="sentry-sdk not installed — error reporting via structlog only",
        )
        return False


def capture_exception(exc: BaseException, **context: Any) -> None:
    """Report exception (Sentry если доступен) + structlog.

    Структурированный log выполняется всегда: важно чтобы хотя бы YC Logging
    видел traceback даже без Sentry. Контекст подсыпается как extra-fields.
    """
    _logger.error(
        "error_captured",
        exc_class=exc.__class__.__name__,
        exc_message=str(exc),
        exc_info=exc,
        **context,
    )
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        # Sentry SDK не установлен — structlog уже залогировал, всё ок.
        pass
