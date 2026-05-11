"""Извлечение текста из 326 файлов yadisk_kns/ для обучения и анализа.

Для каждого файла:
- pdf  → pdfplumber или pypdf
- docx → python-docx
- doc  → попытка pypandoc; иначе пометить как needs_manual
- xlsx → openpyxl
- xls  → xlrd (если есть)
- zip/rar/7z → распаковка во временную папку, рекурсивный extract
- jpg/jpeg/png/tiff → пометить как image (без OCR — не ставим тяжёлые зависимости)

Выход: 02_dataset/_inbox/yadisk_kns/extracted_text.jsonl (по строке на файл)
       со схемой: {path, name, ext, size, text, error, attachments?}
"""
from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YA = ROOT / "02_dataset" / "_inbox" / "yadisk_kns"
OUT = YA / "extracted_text.jsonl"
LOG = YA / "extract.log"


def log(msg: str) -> None:
    print(msg, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def extract_pdf(path: Path) -> tuple[str, str | None]:
    """pypdf — встроен в backend/.venv, попробуем."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return "", "no_pdf_lib"
    try:
        r = PdfReader(str(path))
        chunks = []
        for i, page in enumerate(r.pages[:50]):  # первые 50 стр.
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(chunks).strip(), None
    except Exception as e:
        return "", f"pdf_err:{type(e).__name__}:{str(e)[:80]}"


def extract_docx(path: Path) -> tuple[str, str | None]:
    try:
        import docx  # python-docx
    except ImportError:
        return "", "no_docx_lib"
    try:
        d = docx.Document(str(path))
        text = "\n".join(p.text for p in d.paragraphs if p.text.strip())
        for t in d.tables:
            for row in t.rows:
                line = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if line:
                    text += "\n" + line
        return text.strip(), None
    except Exception as e:
        return "", f"docx_err:{type(e).__name__}:{str(e)[:80]}"


def extract_xlsx(path: Path) -> tuple[str, str | None]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return "", "no_openpyxl"
    try:
        wb = load_workbook(str(path), read_only=True, data_only=True)
        chunks = []
        for sn in wb.sheetnames[:10]:
            ws = wb[sn]
            chunks.append(f"=== {sn} ===")
            for row in ws.iter_rows(max_row=200, values_only=True):
                line = " | ".join(str(c) for c in row if c is not None)
                if line.strip():
                    chunks.append(line)
        wb.close()
        return "\n".join(chunks).strip(), None
    except Exception as e:
        return "", f"xlsx_err:{type(e).__name__}:{str(e)[:80]}"


def extract_zip(path: Path) -> tuple[str, str | None, list[str]]:
    """Возвращает текст всех вложенных файлов (PDF/DOCX/XLSX) + список имён."""
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            chunks = [f"ZIP CONTAINS {len(names)} FILES:"]
            for n in names[:80]:
                try:
                    info = zf.getinfo(n)
                    chunks.append(f"  {n} ({info.file_size} B)")
                except Exception:
                    chunks.append(f"  {n}")
            # Извлекаем текст из вложенных pdf/docx/xlsx
            import tempfile
            for n in names[:30]:
                ext = Path(n).suffix.lower()
                if ext not in (".pdf", ".docx", ".xlsx"):
                    continue
                try:
                    data = zf.read(n)
                    if len(data) > 50 * 1024 * 1024:
                        continue
                    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
                        tf.write(data)
                        tp = Path(tf.name)
                    try:
                        if ext == ".pdf":
                            t, _ = extract_pdf(tp)
                        elif ext == ".docx":
                            t, _ = extract_docx(tp)
                        else:
                            t, _ = extract_xlsx(tp)
                        if t:
                            chunks.append(f"\n--- {n} ---\n{t[:5000]}")
                    finally:
                        try:
                            tp.unlink()
                        except OSError:
                            pass
                except Exception:
                    pass
            return "\n".join(chunks).strip(), None, names
    except Exception as e:
        return "", f"zip_err:{type(e).__name__}:{str(e)[:80]}", []


def main() -> int:
    if not YA.exists():
        log(f"[ERR] {YA} not found")
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for sub in ["кнс", "кнс 2", "кнс 3"]:
        d = YA / sub
        if d.exists():
            files.extend(sorted(f for f in d.iterdir() if f.is_file()))
    log(f"=== Старт извлечения текста: {len(files)} файлов ===")

    written = 0
    errors = 0
    with OUT.open("w", encoding="utf-8") as fout:
        for i, p in enumerate(files, 1):
            ext = p.suffix.lower()
            entry = {
                "path": str(p.relative_to(YA)),
                "name": p.name,
                "ext": ext,
                "size": p.stat().st_size,
                "text": "",
                "error": None,
            }
            try:
                if ext == ".pdf":
                    entry["text"], entry["error"] = extract_pdf(p)
                elif ext in (".docx",):
                    entry["text"], entry["error"] = extract_docx(p)
                elif ext == ".doc":
                    entry["error"] = "doc_legacy_format_skip"
                elif ext == ".xlsx":
                    entry["text"], entry["error"] = extract_xlsx(p)
                elif ext == ".xls":
                    entry["error"] = "xls_legacy_format_skip"
                elif ext == ".zip":
                    entry["text"], entry["error"], entry["zip_contents"] = extract_zip(p)
                elif ext in (".rar", ".7z"):
                    entry["error"] = f"{ext[1:]}_archive_skip_no_lib"
                elif ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"):
                    entry["error"] = "image_no_ocr"
                elif ext in (".dwg", ".dxf"):
                    entry["error"] = "cad_skip"
                else:
                    entry["error"] = f"unsupported_ext:{ext}"
            except Exception as e:
                entry["error"] = f"exception:{type(e).__name__}:{str(e)[:120]}"
                errors += 1

            # Trim text to 50k chars max
            if entry["text"] and len(entry["text"]) > 50000:
                entry["text"] = entry["text"][:50000] + "...[TRUNCATED]"

            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fout.flush()
            written += 1

            if i % 30 == 0:
                txt_len = len(entry["text"]) if entry["text"] else 0
                log(f"  [{i}/{len(files)}] {p.name[:50]} ({entry['size']//1024} KB) "
                    f"text={txt_len} chars err={entry['error']}")

    log(f"=== Готово: written={written}, errors={errors}, out={OUT} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
