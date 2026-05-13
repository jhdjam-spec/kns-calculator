"""Structured logging via structlog.

Outputs JSON в production (для YC Logging parsing) и pretty-print в dev.

Env vars
--------
- ``LOG_LEVEL``      : DEBUG / INFO / WARNING / ERROR (default INFO).
- ``ENV``            : ``prod`` → JSONRenderer; иначе ConsoleRenderer (dev).

Зачем
-----
PhD Architecture audit (2026-05-13) указал: «нет structured logging, нет
correlation IDs». Для closed-beta B2B (10-50 пользователей) достаточно
``logger.exception``; structlog поверх ``logging`` даёт лучшую трассировку
без потери совместимости со stdlib-логгерами (slowapi, uvicorn, boto3).

Использование
-------------
.. code-block:: python

    from pump_calculator.logging_config import configure_logging
    import structlog

    configure_logging(level="INFO")
    log = structlog.get_logger(__name__)
    log.info("pumps_loaded", count=494, source="catalog.json")
"""

from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Initialize structlog для всего приложения.

    Идемпотентно: можно вызывать многократно (например, при reload в tests).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Stdlib logging — принимает финальный (уже отрендеренный) message от structlog.
    # ``force=True`` чтобы перенастройка при тестах не игнорировалась.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    # Detect environment (dev vs prod).
    is_prod = os.environ.get("ENV", "dev").lower() == "prod"

    # NB: ``format_exc_info`` подключаем только в prod (JSONRenderer); в dev
    # ConsoleRenderer сам красиво форматирует traceback, а ``format_exc_info``
    # выдаёт UserWarning при наличии ConsoleRenderer.
    shared_processors: list = [
        # Подмешивает contextvars (request_id, method, path) из middleware.
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_prod:
        # JSON-строки в stdout → YC Logging парсит автоматически.
        shared_processors.append(structlog.processors.format_exc_info)
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Цветной читаемый вывод для local dev (включает свой exception formatter).
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def reset_logging() -> None:
    """Полный reset structlog state — нужен между тестами."""
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()
