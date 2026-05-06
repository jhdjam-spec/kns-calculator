"""Vercel serverless entry for FastAPI.

Vercel `@vercel/python@4.x` runtime ищет ASGI-приложение по переменной `app`
в файле под `api/`. Импортируем существующий `pump_calculator.api:app`.

Routing на Vercel:
  Frontend шлёт `/api/backend/select/quick`.
  `vercel.json` rewrites `/api/backend/:path*` → `/api/index/:path*`.
  Vercel вызывает `api/index.py`, передаёт ASGI-приложению PATH_INFO=`/select/quick`.
  FastAPI обрабатывает запрос обычным образом.

Чтобы pump_calculator увидел dataset, prepend backend/ к sys.path и
прокидываем переменную `KNS_DATASET_ROOT` для загрузки JSON.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("KNS_DATASET_ROOT", str(ROOT / "02_dataset"))

from pump_calculator.api import app  # noqa: E402

__all__ = ["app"]
