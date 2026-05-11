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

# CORS — production frontend на YC Object Storage (static hosting)
default_origins = "https://kns-calculator-frontend.website.yandexcloud.net"
if "CORS_ALLOWED_ORIGINS" not in os.environ:
    os.environ["CORS_ALLOWED_ORIGINS"] = default_origins

import asyncio  # noqa: E402
import base64  # noqa: E402
import json as _json  # noqa: E402
from typing import Any  # noqa: E402

from pump_calculator.api import app  # noqa: E402


# YC передаёт event в собственном формате (близком к AWS API Gateway, но НЕ совпадает).
# Делаем тонкий адаптер event → ASGI scope → FastAPI app.
# Документация YC: https://cloud.yandex.ru/docs/functions/concepts/function-invoke

async def _asgi_call(scope: dict, body: bytes) -> dict:
    """Вызывает ASGI app со scope и body, собирает response."""
    received = {"sent": False}

    async def receive() -> dict:
        if not received["sent"]:
            received["sent"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    response: dict[str, Any] = {"status": 500, "headers": [], "body": b""}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response["body"] += message.get("body", b"")

    await app(scope, receive, send)
    return response


def handler(event: dict, context: Any) -> dict:
    """YC Functions HTTP handler.

    YC API Gateway event format отличается от прямого invoke:
        {
            "httpMethod": "POST",
            "path": "/select/quick",
            "url": "...",
            "params": {...},          # path params
            "queryStringParameters": {...},
            "multiValueQueryStringParameters": {...},
            "headers": {...},
            "multiValueHeaders": {...},
            "requestContext": {...},  # содержит httpMethod, путь, identity
            "body": "...",
            "isBase64Encoded": bool
        }

    Response format (YC):
        {
            "statusCode": int,
            "headers": {...},
            "body": str,
            "isBase64Encoded": bool
        }
    """
    # Метод: try several locations
    method: str = (
        event.get("httpMethod")
        or (event.get("requestContext") or {}).get("httpMethod")
        or "GET"
    ).upper()

    # Path: API Gateway передаёт template "/{proxy+}" в event["path"].
    # Реальный путь — в params/pathParams (proxy=...) или requestContext.
    # Приоритет: url → requestContext.path → собрать из proxy → fallback.
    raw_url: str = event.get("url") or ""
    rc_path: str = (event.get("requestContext") or {}).get("path") or ""
    proxy_segment: str = ""
    params = event.get("params") or event.get("pathParams") or {}
    if isinstance(params, dict):
        proxy_segment = str(params.get("proxy") or "")

    # Достаём реальный path
    if raw_url:
        # url обычно содержит полный URI с query — берём path-часть
        from urllib.parse import urlparse
        parsed = urlparse(raw_url)
        path = parsed.path or "/"
    elif rc_path and "{" not in rc_path:
        path = rc_path
    elif proxy_segment:
        path = "/" + proxy_segment.lstrip("/")
    else:
        path = event.get("path") or "/"

    # Если path всё ещё template "/{proxy+}" — fallback к proxy_segment
    if "{" in path and proxy_segment:
        path = "/" + proxy_segment.lstrip("/")

    # Если path начинается без /, добавим
    if path and not path.startswith("/"):
        path = "/" + path

    query_params: dict = event.get("queryStringParameters") or {}
    raw_headers: dict = event.get("headers") or {}

    # Build ASGI scope
    headers_list = [
        (k.lower().encode("latin-1"), str(v).encode("latin-1"))
        for k, v in raw_headers.items()
    ]
    query_string = "&".join(
        f"{k}={v}" for k, v in query_params.items() if v is not None
    ).encode("latin-1")

    body_raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body_raw) if body_raw else b""
    else:
        body = body_raw.encode("utf-8") if isinstance(body_raw, str) else (body_raw or b"")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "root_path": "",
        "headers": headers_list,
        "client": ("0.0.0.0", 0),
        "server": ("functions.yandexcloud.net", 443),
    }

    # Run ASGI app in fresh event loop (YC reuses runtime, but loops bind to thread)
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_asgi_call(scope, body))
    finally:
        loop.close()

    # Build response headers dict for YC
    response_headers: dict[str, str] = {}
    for k, v in result["headers"]:
        try:
            response_headers[k.decode("latin-1")] = v.decode("latin-1")
        except Exception:
            continue

    body_bytes = result["body"]
    # Try to decode as text; if fails — base64
    try:
        body_str = body_bytes.decode("utf-8")
        is_b64 = False
    except UnicodeDecodeError:
        body_str = base64.b64encode(body_bytes).decode("ascii")
        is_b64 = True

    return {
        "statusCode": result["status"],
        "headers": response_headers,
        "body": body_str,
        "isBase64Encoded": is_b64,
    }
