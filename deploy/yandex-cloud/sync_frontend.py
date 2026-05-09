"""Sync frontend/out/ → YC Object Storage bucket с правильными path-разделителями.

Использование:
    # Креды берутся из ~/.claude/.secrets/yc-s3.env (AWS-format) или из ENV
    python deploy/yandex-cloud/sync_frontend.py
"""
from __future__ import annotations

import mimetypes
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO_ROOT / "frontend" / "out"
BUCKET = "kns-calculator-frontend"
ENDPOINT = "https://storage.yandexcloud.net"
SECRETS = Path.home() / ".claude" / ".secrets" / "yc-s3.env"


def _load_creds() -> tuple[str, str]:
    if SECRETS.exists():
        for line in SECRETS.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    ak = os.environ.get("AWS_ACCESS_KEY_ID")
    sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not ak or not sk:
        raise SystemExit(f"[!] Не найдены AWS_ACCESS_KEY_ID/SECRET в {SECRETS}")
    return ak, sk


# MIME types: вебу нужны правильные content-type для html/js/css
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/html; charset=utf-8", ".html")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/plain", ".txt")


def main() -> int:
    if not OUT_DIR.exists():
        print(f"[!] {OUT_DIR} не существует — сначала запустите BUILD_TARGET=yc-static npm run build")
        return 1
    ak, sk = _load_creds()

    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name="ru-central1",
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )

    files = [(p, str(p.relative_to(OUT_DIR)).replace("\\", "/"))
             for p in OUT_DIR.rglob("*") if p.is_file()]
    print(f"[*] Загрузка {len(files)} файлов в s3://{BUCKET}/")

    uploaded = 0
    for p, key in files:
        ct, _ = mimetypes.guess_type(p.name)
        if not ct:
            ct = "application/octet-stream"
        # Cache headers: html — short TTL, _next/static — long TTL (immutable)
        cache = "no-cache, no-store, must-revalidate" if p.suffix == ".html" else "public, max-age=31536000, immutable"
        s3.upload_file(
            str(p), BUCKET, key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": ct,
                "CacheControl": cache,
            },
        )
        uploaded += 1
        if uploaded % 25 == 0:
            print(f"  ... {uploaded}/{len(files)}")
    print(f"[+] Загружено {uploaded} файлов")
    print(f"[+] URL: https://{BUCKET}.website.yandexcloud.net/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
