"""Сборка zip-пакета для Yandex Cloud Functions (кроссплатформенно).

Использование:
    cd deploy/yandex-cloud
    python build.py

Выход: deploy/yandex-cloud/kns-calculator.zip — готовый артефакт для:
    yc serverless function version create --source-path kns-calculator.zip
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
BUILD_DIR = SCRIPT_DIR / "_build"
OUT_ZIP = SCRIPT_DIR / "kns-calculator.zip"

# Подпапки 02_dataset, которые попадают в production пакет.
# Игнорируются: _inbox, _analysis (gitignore), etalons/downloads_*, etalons/pricelist_*
PUBLIC_DATASET_SUBS = [
    "pumps",
    "fittings",
    "theory",
    "etl_seed",
    "failure_modes",  # Sub P: каталог типовых отказов (26 модов) — endpoint /failure-modes
    "regulations",  # Sub N: climate_cities_2026.json (76 городов СП 131) — endpoint /climate/*
    "storm_research_raw",  # Phase 18: climate_db_36_cities.json + surfaces — endpoint /project (ливнёвка)
]

EXCLUDE_PATTERNS = ["__pycache__", ".ruff_cache", ".pytest_cache", "*.pyc", "*.pyo"]


def _excluded(name: str) -> bool:
    return any(pat.replace("*", "") in name for pat in EXCLUDE_PATTERNS)


def copytree_filtered(src: Path, dst: Path) -> None:
    """Копия дерева с исключением мусорных файлов."""
    if not src.exists():
        return

    def _ignore(_dir, names):
        return [n for n in names if _excluded(n)]

    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def main() -> int:
    print("[*] Очистка предыдущей сборки")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    print("[*] Копирую handler.py + requirements.txt")
    shutil.copy2(SCRIPT_DIR / "handler.py", BUILD_DIR / "handler.py")
    shutil.copy2(SCRIPT_DIR / "requirements.txt", BUILD_DIR / "requirements.txt")

    print("[*] Копирую pump_calculator/ (без __pycache__)")
    src_pump = REPO_ROOT / "backend" / "pump_calculator"
    copytree_filtered(src_pump, BUILD_DIR / "pump_calculator")

    print("[*] Копирую публичные части 02_dataset/")
    dataset_dst = BUILD_DIR / "02_dataset"
    dataset_dst.mkdir(parents=True, exist_ok=True)
    for sub in PUBLIC_DATASET_SUBS:
        src_sub = REPO_ROOT / "02_dataset" / sub
        if src_sub.exists():
            copytree_filtered(src_sub, dataset_dst / sub)
            print(f"    + {sub}")

    # Public etalons (обезличенные)
    src_public = REPO_ROOT / "02_dataset" / "etalons" / "public"
    if src_public.exists():
        copytree_filtered(src_public, dataset_dst / "etalons" / "public")
        print("    + etalons/public")

    # Encyclopedia md-файлы (нужны для /teach/[topic] runtime)
    src_enc = REPO_ROOT / "02_dataset" / "_analysis" / "encyclopedia"
    if src_enc.exists():
        copytree_filtered(src_enc, dataset_dst / "_analysis" / "encyclopedia")
        print("    + _analysis/encyclopedia (7 md-файлов)")

    print("[*] Установка зависимостей под Linux Python 3.11 (manylinux2014_x86_64)")
    # YC Functions runs on Linux Python 3.11 — нужны соответствующие wheels.
    # Windows-binaries (.pyd) НЕ совместимы с Linux runtime!
    pip_cmd = [
        sys.executable, "-m", "pip", "install",
        "-r", str(SCRIPT_DIR / "requirements.txt"),
        "--target", str(BUILD_DIR),
        "--platform", "manylinux2014_x86_64",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--upgrade", "--quiet",
    ]
    rc = subprocess.run(pip_cmd, check=False)
    if rc.returncode != 0:
        print(f"[!] pip install failed (rc={rc.returncode})")
        print("    Возможно, не все wheels доступны. Попробуйте установить вручную:")
        print(f"    pip install -r {SCRIPT_DIR / 'requirements.txt'} --target {BUILD_DIR} \\")
        print("        --platform manylinux2014_x86_64 --python-version 3.11 --only-binary=:all:")
        return rc.returncode

    print("[*] Создаю zip-архив")
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BUILD_DIR):
            # Фильтруем директории на ходу (in-place изменение dirs влияет на os.walk)
            dirs[:] = [d for d in dirs if not _excluded(d)]
            for f in files:
                if _excluded(f):
                    continue
                full = Path(root) / f
                arc = full.relative_to(BUILD_DIR)
                zf.write(full, arc)

    size_mb = OUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"\n[+] Готово: {OUT_ZIP} ({size_mb:.1f} МБ)")
    print()
    print("Следующие команды (yc CLI):")
    print()
    print("  yc init  # один раз; выбрать cloud-servoug, folder kns-calculator")
    print("  yc config set folder-id b1ge2mgg8tgh92uerm9c")
    print()
    print("  # Создать function (один раз)")
    print("  yc serverless function create --name kns-calculator-api \\")
    print("      --folder-id b1ge2mgg8tgh92uerm9c")
    print()
    print("  # Загрузить версию")
    print("  yc serverless function version create \\")
    print("      --function-name kns-calculator-api \\")
    print("      --folder-id b1ge2mgg8tgh92uerm9c \\")
    print("      --runtime python311 \\")
    print("      --entrypoint handler.handler \\")
    print("      --memory 512m \\")
    print("      --execution-timeout 30s \\")
    print("      --service-account-id ajeur7e0n1k1n458t79n \\")
    print(f"      --source-path \"{OUT_ZIP}\" \\")
    print("      --environment KNS_DATASET_ROOT=./02_dataset \\")
    print("      --environment CORS_ALLOWED_ORIGINS=https://kns-calculator-frontend.website.yandexcloud.net")
    print()
    print("  # Сделать публичной")
    print("  yc serverless function allow-unauthenticated-invoke kns-calculator-api \\")
    print("      --folder-id b1ge2mgg8tgh92uerm9c")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
