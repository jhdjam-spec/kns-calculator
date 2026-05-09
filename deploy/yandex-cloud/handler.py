"""Yandex Cloud Functions entry для FastAPI приложения kns-calculator.

YC Functions использует ASGI-handler через адаптер. Для runtime python311
ставим mangum-обёртку: YC передаёт event/context → Mangum конвертирует в ASGI
scope → FastAPI обрабатывает и возвращает HTTP response.

Структура деплой-пакета:
    handler.py                — этот файл (entry point)
    requirements.txt          — fastapi + pydantic + mangum + reportlab + python-docx
    pump_calculator/          — копия из backend/pump_calculator
    02_dataset/               — копия dataset (или загрузка из S3 при cold start)

Переменные окружения YC Function:
    KNS_DATASET_ROOT       — путь к dataset (default: ./02_dataset)
    YC_S3_BUCKET           — опционально, если dataset в Object Storage
    CORS_ALLOWED_ORIGINS   — список origins через запятую
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# YC Functions распаковывает код в /tmp или /function/code/
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Dataset находится рядом с handler.py
os.environ.setdefault("KNS_DATASET_ROOT", str(_HERE / "02_dataset"))

# CORS — origins для Vercel preview/staging + production frontend
default_origins = "https://kns-calc-test.vercel.app,https://kns-calculator.vercel.app"
if "CORS_ALLOWED_ORIGINS" not in os.environ:
    os.environ["CORS_ALLOWED_ORIGINS"] = default_origins

from mangum import Mangum  # noqa: E402

from pump_calculator.api import app  # noqa: E402

# Mangum-адаптер: ASGI ↔ Yandex Cloud Functions / AWS Lambda format
asgi_handler = Mangum(app, lifespan="off")


def handler(event, context):
    """YC Functions invoke handler.

    YC передаёт event в формате AWS API Gateway v2 (HTTP event).
    Mangum принимает его и проксирует в FastAPI.

    Логирование cold-start:
        Первый вызов после деплоя: ~500ms-1s.
        Тёплые вызовы: <50ms.
    """
    return asgi_handler(event, context)
