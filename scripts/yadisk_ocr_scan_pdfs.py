"""OCR-pipeline для скан-PDF которые pypdf не извлёк.

Шаги:
1. Загрузить список 41 PDF из extracted_text.jsonl где text=0 и нет error.
2. Перекачать каждый с Я.Диска (используя yadisk_kns/inventory.json для имён).
3. Конвертировать каждую страницу в PNG через PyMuPDF (300 dpi).
4. Отправить PNG в Yandex Vision OCR (/ocr/v1/recognizeText).
5. Сохранить распознанный текст в extracted_text_ocr.jsonl.
6. Удалить временный PDF после OCR.

Yandex Vision OCR:
  POST https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText
  Headers: Authorization: Bearer <yc.token>, x-folder-id: kns-calc
  Body: {"mimeType":"image/png","languageCodes":["ru","en"],"model":"page","content":"<base64>"}
"""
from __future__ import annotations
import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YA = ROOT / "02_dataset" / "_inbox" / "yadisk_kns"
JSONL = YA / "extracted_text.jsonl"
INV = YA / "inventory.json"
OUT = YA / "extracted_text_ocr.jsonl"
LOG = YA / "ocr.log"
TMP_DIR = YA / "_ocr_tmp"

PUBKEY = "https://disk.yandex.ru/d/WaMoxfAeub_d_w"
TOKEN_FILE = Path.home() / ".claude" / ".secrets" / "yc.token"
FOLDER_ID = "b1ge2mgg8tgh92uerm9c"

OCR_URL = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"
IAM_EXCHANGE_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"


def get_iam_token(oauth_token: str) -> str:
    """Обменивает OAuth-токен на IAM-токен (живёт 12 часов)."""
    body = json.dumps({"yandexPassportOauthToken": oauth_token}).encode("utf-8")
    req = urllib.request.Request(IAM_EXCHANGE_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["iamToken"]


def log(msg: str) -> None:
    print(msg, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def yadisk_download(remote_path: str, local_path: Path) -> bool:
    enc_pub = urllib.parse.quote(PUBKEY, safe="")
    enc_path = urllib.parse.quote(remote_path, safe="")
    href_url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={enc_pub}&path={enc_path}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(href_url, timeout=60) as r:
                href = json.loads(r.read())["href"]
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt + 1)
                continue
            raise
        except Exception as e:
            log(f"  [ERR] href {remote_path}: {e}")
            return False
    else:
        return False
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(href, timeout=300) as r, local_path.open("wb") as out:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
        return True
    except Exception as e:
        log(f"  [ERR] dl {remote_path}: {e}")
        return False


def pdf_to_png_bytes(pdf_path: Path, max_pages: int = 30, dpi: int = 200) -> list[bytes]:
    import fitz  # PyMuPDF
    doc = fitz.open(str(pdf_path))
    out = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png = pix.tobytes("png")
        out.append(png)
    doc.close()
    return out


def yandex_ocr(png_bytes: bytes, token: str) -> tuple[str, str | None]:
    """OCR одной страницы. Возвращает (text, error)."""
    body = json.dumps({
        "mimeType": "image/png",
        "languageCodes": ["ru", "en"],
        "model": "page",
        "content": base64.b64encode(png_bytes).decode("ascii"),
    }).encode("utf-8")
    req = urllib.request.Request(OCR_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("x-folder-id", FOLDER_ID)
    req.add_header("x-data-logging-enabled", "false")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        # Структура: { "result": { "textAnnotation": { "fullText": "..." } } }
        text = data.get("result", {}).get("textAnnotation", {}).get("fullText", "")
        return text, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        return "", f"http_{e.code}:{body[:200]}"
    except Exception as e:
        return "", f"err:{type(e).__name__}:{str(e)[:120]}"


def main() -> int:
    LOG.unlink(missing_ok=True)
    OUT.unlink(missing_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    if not TOKEN_FILE.exists():
        log("[ERR] yc.token not found")
        return 2
    raw = TOKEN_FILE.read_text(encoding="utf-8").lstrip("﻿")
    # Берём первую непустую строку как OAuth-токен
    oauth_token = ""
    for line in raw.splitlines():
        line = line.strip()
        if line and line.startswith("y0_"):
            oauth_token = line
            break
    if not oauth_token:
        log("[ERR] no y0_ OAuth token found in yc.token")
        return 2
    log(f"=== Старт OCR ===")
    log(f"  oauth: {oauth_token[:20]}...")
    try:
        token = get_iam_token(oauth_token)
        log(f"  iam: {token[:25]}... (exchanged successfully)")
    except Exception as e:
        log(f"[ERR] IAM exchange: {e}")
        return 2

    # 1. Кандидаты для OCR из jsonl
    candidates = []
    for line in JSONL.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (e.get("text") or "").strip()
        ext = e.get("ext", "")
        # text=0 + нет ошибки + это PDF (доступный для OCR)
        if not text and ext == ".pdf" and not e.get("error"):
            candidates.append(e)
        # PDF с очень малым текстом (<200) - тоже возможно scan
        elif ext == ".pdf" and 0 < len(text) < 200:
            candidates.append(e)
    log(f"  кандидаты: {len(candidates)} PDF")

    # 2. Inventory для проверки размеров (skip если >50 МБ)
    inv = json.loads(INV.read_text(encoding="utf-8"))
    inv_by_path = {}
    for sub, files in inv.get("folders", {}).items():
        for f in files:
            inv_by_path[f"{sub}\\{f['name']}"] = f["size"]

    # Filter: skip files too large
    cand2 = []
    for c in candidates:
        path = c.get("path", "")
        size = inv_by_path.get(path, 0) or c.get("size", 0)
        if size > 30 * 1024 * 1024:
            log(f"  SKIP large: {path} ({size//1024//1024} MB)")
            continue
        cand2.append((c, path, size))
    log(f"  после фильтра размера: {len(cand2)}")

    out_entries = []
    fout = OUT.open("w", encoding="utf-8")
    started = time.time()

    for i, (c, path, size) in enumerate(cand2, 1):
        # remote_path: "/кнс/имя.pdf" — path хранится с "\\" Windows-сепаратором
        remote_path = "/" + path.replace("\\", "/")
        local = TMP_DIR / Path(path).name
        log(f"\n[{i}/{len(cand2)}] {path} ({size//1024} KB)")

        # Download
        if not yadisk_download(remote_path, local):
            entry = {**c, "ocr_error": "download_failed", "ocr_text": ""}
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fout.flush()
            continue
        time.sleep(0.5)  # anti-rate-limit

        # PDF → PNG страницы
        try:
            pngs = pdf_to_png_bytes(local, max_pages=15)
        except Exception as e:
            log(f"  [ERR] pdf→png: {e}")
            entry = {**c, "ocr_error": f"pdf_render:{type(e).__name__}", "ocr_text": ""}
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fout.flush()
            try: local.unlink()
            except: pass
            continue

        # OCR каждой страницы
        page_texts = []
        ocr_errors = []
        for j, png in enumerate(pngs):
            t, err = yandex_ocr(png, token)
            if err:
                ocr_errors.append(f"p{j}:{err}")
                if "http_401" in err or "http_403" in err:
                    log(f"  [FATAL] auth error: {err}")
                    break
                # Retry on 429
                if "http_429" in err:
                    time.sleep(5)
                    t, err = yandex_ocr(png, token)
                    if err:
                        ocr_errors.append(f"p{j}-retry:{err}")
                        continue
            if t:
                page_texts.append(t)
            time.sleep(0.3)  # rate-limit pause

        full_text = "\n=== --- ===\n".join(page_texts).strip()
        entry = {
            **c,
            "ocr_pages_total": len(pngs),
            "ocr_pages_recognized": len(page_texts),
            "ocr_text_chars": len(full_text),
            "ocr_text": full_text[:50000],
            "ocr_error": "; ".join(ocr_errors) if ocr_errors else None,
        }
        fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fout.flush()
        out_entries.append(entry)
        log(f"  ✓ pages={len(pngs)} text={len(full_text)} errs={len(ocr_errors)}")

        # Cleanup PDF
        try:
            local.unlink()
        except OSError:
            pass

    fout.close()
    elapsed = time.time() - started
    total_text = sum(e.get("ocr_text_chars", 0) for e in out_entries)
    log(f"\n=== Готово за {elapsed:.0f}s ===")
    log(f"  files OCR'ed: {len(out_entries)}")
    log(f"  total OCR text: {total_text:,} chars")
    log(f"  out: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
