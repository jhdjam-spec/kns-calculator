"""Строит индекс файлов в 02_dataset для дедупликации против входящего IMAP-импорта.

Что считаем:
- normalized_name → имя файла, нормализованное (нижний регистр, без пробелов/скобок/дат)
- size → точный размер
- sha1 → хеш содержимого

Зачем три ключа:
1. По sha1 — точное совпадение (письмо переслали тот же pdf, что уже в датасете).
2. По size+name_norm — устойчиво к переименованиям ("КП-001.pdf" vs "КП-001 (1).pdf").
3. Только по name_norm — слабый сигнал, но для редких имён работает.

Результат: 02_dataset/_inbox/mail_ru_imap/dataset_fingerprint.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATASET = REPO / "02_dataset"
OUT_FILE = DATASET / "_inbox" / "mail_ru_imap" / "dataset_fingerprint.json"
UNPACK_ROOT = DATASET / "_inbox" / "_unpacked"
SEVENZIP = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".local" / "7zip" / "full" / "7z.exe"
ARCHIVE_EXT = {".rar", ".7z", ".zip"}

# Расширения, которые отслеживаем (совпадает с ATTACH_EXT в импорте)
TRACKED_EXT = {
    ".pdf", ".dwg", ".dxf", ".docx", ".doc", ".xlsx", ".xls",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".txt", ".csv", ".rtf", ".odt",
}

# Пропускаем подпапки, не несущие "пользовательских" файлов.
# ВАЖНО: _inbox/ (массивы, которые пользователь грузил ручками) — индексируем,
# чтобы IMAP-импорт мог дедуплицироваться против них. Пропускаем только
# результаты самого IMAP-импорта и служебные каталоги.
SKIP_REL_PREFIXES = (
    "02_dataset/_inbox/mail_ru_imap",
)
# При первом проходе мы НЕ скипаем _unpacked — её мы сами создаём ниже.
SKIP_DIR_PARTS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
}


def norm_name(name: str) -> str:
    """Нормализуем имя для матчинга по человеческому названию."""
    n = name.lower()
    # отрезаем расширение
    if "." in n:
        n = n.rsplit(".", 1)[0]
    # убираем "(1)", "(копия)" и подобные суффиксы
    n = re.sub(r"\s*\(\d+\)\s*$", "", n)
    n = re.sub(r"\s*копия\s*\d*\s*$", "", n)
    # все пробелы/подчёркивания/дефисы — в один пробел
    n = re.sub(r"[\s_\-‐-―]+", " ", n)
    # убираем даты вида 2024-01-15, 15.01.2024, 15_01_24
    n = re.sub(r"\b\d{2,4}[._\-]\d{1,2}[._\-]\d{2,4}\b", "", n)
    # лишние пробелы
    n = re.sub(r"\s+", " ", n).strip()
    return n


def sha1_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def find_archives(root: Path) -> list[Path]:
    """Все .rar/.7z/.zip внутри _dated/ — реальные архивы пользователя."""
    out: list[Path] = []
    for p in root.rglob("*"):
        if (p.is_file() and p.suffix.lower() in ARCHIVE_EXT
                and "_dated" in p.parts):
            out.append(p)
    return out


def unpack_archive(archive: Path, dest: Path) -> tuple[bool, str]:
    """Распаковывает архив в dest через 7z.exe. Возвращает (ok, message)."""
    if not SEVENZIP.exists():
        return False, f"нет {SEVENZIP}"
    if dest.exists() and any(dest.iterdir()):
        return True, "уже распакован"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [str(SEVENZIP), "x", "-y", f"-o{dest}", str(archive)],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            return False, result.stderr.strip()[:200]
        return True, f"распакован → {dest.name}"
    except subprocess.TimeoutExpired:
        return False, "таймаут 10 минут"
    except OSError as exc:
        return False, str(exc)


def prepare_unpacked(verbose: bool = True) -> int:
    """Распаковывает архивы из _dated/ в _inbox/_unpacked/<имя_архива>/.

    Возвращает количество успешно подготовленных архивов.
    Уже распакованные не перепаковываем.
    """
    archives = find_archives(DATASET / "_inbox")
    if not archives:
        return 0
    UNPACK_ROOT.mkdir(parents=True, exist_ok=True)
    ready = 0
    for arc in archives:
        # имя слота — (название_архива)_(parent_dir), чтобы избежать коллизий
        slot = UNPACK_ROOT / f"{arc.parent.name}__{arc.stem}"
        ok, msg = unpack_archive(arc, slot)
        if verbose:
            mark = "OK" if ok else "FAIL"
            print(f"  [{mark}] {arc.name} — {msg}", file=sys.stderr)
        if ok:
            ready += 1
    return ready


def main() -> int:
    if not DATASET.exists():
        print(f"Нет {DATASET}", file=sys.stderr)
        return 1
    started = time.time()
    print("→ Распаковка архивов из _dated/ ...", file=sys.stderr)
    ready = prepare_unpacked()
    print(f"  готово {ready} архивов", file=sys.stderr)
    by_sha1: dict[str, list[str]] = {}
    by_size_name: dict[str, list[str]] = {}
    by_name: dict[str, list[str]] = {}
    total = 0
    skipped = 0

    for path in DATASET.rglob("*"):
        if not path.is_file():
            continue
        rel_posix = path.relative_to(REPO).as_posix()
        if rel_posix.startswith(SKIP_REL_PREFIXES):
            skipped += 1
            continue
        if any(part in SKIP_DIR_PARTS for part in path.parts):
            skipped += 1
            continue
        ext = path.suffix.lower()
        if ext not in TRACKED_EXT:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size == 0:
            continue
        try:
            digest = sha1_of(path)
        except OSError:
            continue
        rel = str(path.relative_to(REPO))
        nm = norm_name(path.name)
        key_sn = f"{size}::{nm}"
        by_sha1.setdefault(digest, []).append(rel)
        by_size_name.setdefault(key_sn, []).append(rel)
        by_name.setdefault(nm, []).append(rel)
        total += 1
        if total % 50 == 0:
            print(f"  {total} файлов проиндексировано...", file=sys.stderr)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(
            {
                "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "root": str(DATASET),
                "total_files": total,
                "skipped_dirs": skipped,
                "by_sha1": by_sha1,
                "by_size_name": by_size_name,
                "by_name": by_name,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    elapsed = time.time() - started
    print(
        f"OK: {total} файлов, {len(by_sha1)} уникальных sha1, "
        f"{len(by_name)} уникальных имён за {elapsed:.1f} с",
        file=sys.stderr,
    )
    print(f"→ {OUT_FILE}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
