"""Скачивание публичной папки Yandex.Disk с сохранением структуры подпапок.

Использует только публичное API (без OAuth-токена):
GET /v1/disk/public/resources?public_key=...&path=...
GET /v1/disk/public/resources/download?public_key=...&path=...

Идемпотентный: при повторном запуске пропускает файлы где локальный размер совпадает.
"""
from __future__ import annotations
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PUBKEY = "https://disk.yandex.ru/d/WaMoxfAeub_d_w"
ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["/кнс", "/кнс 2", "/кнс 3"]
OUT_BASE = ROOT / "02_dataset" / "_inbox" / "yadisk_kns"
LOG_FILE = OUT_BASE / "download.log"

API_BASE = "https://cloud-api.yandex.net/v1/disk/public/resources"


def api(path: str) -> dict:
    enc_pub = urllib.parse.quote(PUBKEY, safe="")
    enc_path = urllib.parse.quote(path, safe="")
    url = f"{API_BASE}?public_key={enc_pub}&path={enc_path}&limit=500"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def get_download_url(path: str, retries: int = 6) -> str:
    enc_pub = urllib.parse.quote(PUBKEY, safe="")
    enc_path = urllib.parse.quote(path, safe="")
    url = f"{API_BASE}/download?public_key={enc_pub}&path={enc_path}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())["href"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt + 1  # 2, 3, 5, 9, 17, 33 sec
                log(f"  [429] {path[:60]}: rate-limit, sleep {wait}s (att {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"429 too many times for {path}")


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def safe_filename(name: str) -> str:
    # Windows запрещает: \ / : * ? " < > |
    bad = '\\/:*?"<>|'
    out = "".join("_" if c in bad else c for c in name)
    return out.strip().rstrip(".") or "_"


def download_file(remote_path: str, local_path: Path, expected_size: int) -> bool:
    if local_path.exists() and local_path.stat().st_size == expected_size:
        return False  # already done
    try:
        href = get_download_url(remote_path)
    except Exception as exc:
        log(f"  [ERR] get_download_url {remote_path}: {exc}")
        return False
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = local_path.with_suffix(local_path.suffix + ".part")
    try:
        with urllib.request.urlopen(href, timeout=300) as r, tmp.open("wb") as out:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
        tmp.replace(local_path)
        return True
    except Exception as exc:
        log(f"  [ERR] download {remote_path}: {exc}")
        if tmp.exists():
            tmp.unlink()
        return False


def main() -> int:
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    log(f"=== Старт скачивания {PUBKEY} → {OUT_BASE} ===")
    total_files = 0
    total_downloaded = 0
    total_skipped = 0
    total_errors = 0
    total_bytes = 0

    for target in TARGETS:
        log(f"\n--- Папка {target} ---")
        try:
            d = api(target)
        except Exception as exc:
            log(f"  [ERR] api({target}): {exc}")
            total_errors += 1
            continue
        items = d.get("_embedded", {}).get("items", [])
        log(f"  {len(items)} файлов")
        # Локальная подпапка по имени удалённой
        sub_local = OUT_BASE / safe_filename(target.lstrip("/"))
        sub_local.mkdir(parents=True, exist_ok=True)

        for i, item in enumerate(items, 1):
            if item.get("type") != "file":
                continue
            total_files += 1
            name = item["name"]
            size = item.get("size", 0)
            remote_path = item.get("path", "")  # path внутри публичного диска
            local_path = sub_local / safe_filename(name)

            if local_path.exists() and local_path.stat().st_size == size:
                total_skipped += 1
                continue

            ok = download_file(remote_path, local_path, size)
            if ok:
                total_downloaded += 1
                total_bytes += size
                if total_downloaded % 10 == 0:
                    log(f"  [{i}/{len(items)}] {name} ({size/1024:.0f} KB) ✓ "
                        f"[total dl={total_downloaded}, MB={total_bytes/1024/1024:.0f}]")
            else:
                total_errors += 1
                log(f"  [{i}/{len(items)}] {name} — FAILED")
            # Пауза между файлами против Yandex.Disk rate-limit (~30 req/sec на public API)
            time.sleep(0.8)

    log(f"\n=== Готово: files={total_files}, downloaded={total_downloaded}, "
        f"skipped={total_skipped}, errors={total_errors}, "
        f"total MB={total_bytes/1024/1024:.0f} ===")
    return 0 if total_errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
