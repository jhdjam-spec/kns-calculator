"""Строит индекс имён файлов, которые пользователь скачал вручную.

Источники: 02_dataset/_inbox/2026-05-04_evening и 02_dataset/_inbox/2026-05-09_archives
(включая распакованные архивы из _unpacked/).

Зачем нужен: targeted-импорт писем должен искать письма, к которым были
прикреплены ИМЕННО эти файлы — чтобы получить тела с контекстом, который
пользователь раньше не видел (он скачивал только pdf, тела не читал).

Структура wanted_filenames.json:
{
  "exact_names": ["20-П_23-АР_изм.5_19.12.25.pdf", ...],   # точные имена
  "normalized": ["20 п 23 ар изм 5", ...],                  # для fuzzy
  "tokens": [                                               # токенизированные
    {"file": "20-П_23-АР_изм.5_19.12.25.pdf",
     "tokens": ["20-П", "23-АР", "изм.5"], ...}
  ],
  "by_stem": {"20-П_23-АР_изм.5_19.12.25": ["02_dataset/_inbox/..."]},
}

Поиск в письме: для каждого attachment в письме нормализуем имя и сверяем
против normalized — если совпало, письмо «попадает в цель».
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATASET = REPO / "02_dataset"
INBOX = DATASET / "_inbox"
OUT = INBOX / "mail_ru_imap" / "wanted_filenames.json"

# Папки с «ручными» загрузками + распакованные архивы из них
SOURCES = [
    INBOX / "2026-05-04_evening",
    INBOX / "2026-05-09_archives",
    INBOX / "_unpacked",
]

TRACKED_EXT = {
    ".pdf", ".dwg", ".dxf", ".docx", ".doc", ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",
    ".zip", ".rar", ".7z",
    ".csv", ".rtf",
    # ".txt" исключён — почти всегда служебные манифесты архивов
}


def normalize(name: str) -> str:
    """Та же нормализация, что и в build_dataset_fingerprint.norm_name —
    устойчива к "(1)", "Копия", разным датам."""
    n = name.lower()
    if "." in n:
        n = n.rsplit(".", 1)[0]
    n = re.sub(r"\s*\(\d+\)\s*$", "", n)
    n = re.sub(r"\s*копия\s*\d*\s*$", "", n)
    n = re.sub(r"[\s_\-‐-―]+", " ", n)
    n = re.sub(r"\b\d{2,4}[._\-]\d{1,2}[._\-]\d{2,4}\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def tokenize(name: str) -> list[str]:
    """Извлечь значимые токены — для поиска даже если имя письма-вложения слегка отличается."""
    base = name.lower()
    if "." in base:
        base = base.rsplit(".", 1)[0]
    # split по любым не-словам, оставим только токены ≥3 символов
    tokens = re.split(r"[\s_\-‐-―.,()]+", base)
    return [t for t in tokens if len(t) >= 3 and not t.isdigit()]


def main() -> int:
    exact: set[str] = set()
    normalized: set[str] = set()
    by_stem: dict[str, list[str]] = {}
    items: list[dict] = []

    for src in SOURCES:
        if not src.exists():
            print(f"  [skip] {src}", file=sys.stderr)
            continue
        for p in src.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in TRACKED_EXT:
                continue
            rel = str(p.relative_to(REPO))
            name = p.name
            exact.add(name)
            nm = normalize(name)
            if nm:
                normalized.add(nm)
            stem = p.stem.lower()
            by_stem.setdefault(stem, []).append(rel)
            items.append({
                "file": name,
                "rel_path": rel,
                "normalized": nm,
                "tokens": tokenize(name),
                "size": p.stat().st_size,
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({
            "exact_names": sorted(exact),
            "normalized": sorted(normalized),
            "by_stem": by_stem,
            "items": items,
            "total_files": len(items),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"OK: {len(items)} файлов, {len(exact)} уникальных имён, "
        f"{len(normalized)} нормализованных",
        file=sys.stderr,
    )
    print(f"→ {OUT}", file=sys.stderr)
    # Топ-20 примеров — для глаз
    print("\nПримеры (первые 20):", file=sys.stderr)
    for it in items[:20]:
        print(f"  {it['file']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
