"""Глобальный conftest для backend tests.

Изоляция dataset enrichment:
    Эндпоинт `/import/parse` пишет uploaded ТЗ в `02_dataset/etalons/from_uploads/`.
    Чтобы тесты не контаминировали реальный dataset (особенно при прогонах
    `test_tz_parser` / `test_api_smoke`, где /import/parse вызывается), мы:
    1. Перенаправляем `KNS_DATASET_ROOT` на временный путь (auto fixture).
    2. Это позволяет per-session оставить настоящий dataset нетронутым.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolate_dataset_root_from_tests() -> Iterator[None]:
    """Сессионная изоляция: KNS_DATASET_ROOT → tmp dir.

    Запускается один раз на pytest-сессию. ENV не очищается в conftest —
    pytest сам управляет lifetime tmp dir.
    """
    tmp_root = tempfile.mkdtemp(prefix="kns-test-dataset-")
    # Создаём минимальную структуру (etalons/public/ ...)
    (Path(tmp_root) / "etalons" / "public").mkdir(parents=True, exist_ok=True)
    os.environ["KNS_DATASET_ROOT"] = tmp_root
    yield
    # Не удаляем — pytest tmp файлы дешёвые, а если упало — полезно для debug.
