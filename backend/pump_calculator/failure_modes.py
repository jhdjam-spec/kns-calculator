"""Загрузчик каталога типовых отказов насосных станций.

Источник: 02_dataset/failure_modes/failure_modes_2026.json — образовательный
каталог 26 типовых отказов (кавитация, сухой ход, износ уплотнений и т.п.)
с симптомами, причинами, профилактикой, стоимостью устранения, downtime,
ссылками на СП/ГОСТ и связями с триггерами калькулятора.

Используется страницей /teach/failure-modes (Phase «Failure Mode Library»).
Также позволяет SuggestionCard / WhyThisPump показывать «связанные риски»
для триггеров.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import structlog

from pump_calculator.catalog import DATASET_ROOT

logger = structlog.get_logger(__name__)

FAILURE_MODES_PATH = DATASET_ROOT / "failure_modes" / "failure_modes_2026.json"


@lru_cache(maxsize=1)
def _load_dataset() -> dict[str, Any]:
    """Загружает failure_modes_2026.json (lazy, кэшируется)."""
    try:
        with open(FAILURE_MODES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("failure_modes_2026.json not found at %s", FAILURE_MODES_PATH)
        return {"failure_modes": []}
    except json.JSONDecodeError as e:
        logger.exception("failure_modes_2026.json malformed: %s", e)
        return {"failure_modes": []}


def list_failure_modes(
    *,
    trigger: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> list[dict[str, Any]]:
    """Все режимы отказа, опционально с фильтрацией.

    Args:
        trigger: фильтр по `trigger_in_calculator` (например `auto_npsh_low`).
        category: фильтр по `category` (hydraulic / mechanical / electrical / operational / environmental).
        severity: фильтр по `severity` (low / medium / high / critical).
    """
    data = _load_dataset()
    modes: list[dict[str, Any]] = list(data.get("failure_modes", []))

    if trigger:
        modes = [m for m in modes if m.get("trigger_in_calculator") == trigger]
    if category:
        modes = [m for m in modes if m.get("category") == category]
    if severity:
        modes = [m for m in modes if m.get("severity") == severity]
    return modes


def get_failure_mode(mode_id: str) -> dict[str, Any] | None:
    """Полная карточка одного режима отказа по id (или None если нет)."""
    if not mode_id:
        return None
    data = _load_dataset()
    for m in data.get("failure_modes", []):
        if m.get("id") == mode_id:
            return m
    return None


def list_categories() -> list[str]:
    """Список уникальных категорий (для фильтра в UI)."""
    data = _load_dataset()
    seen: list[str] = []
    for m in data.get("failure_modes", []):
        cat = m.get("category")
        if cat and cat not in seen:
            seen.append(cat)
    return seen
