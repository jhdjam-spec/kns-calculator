"""CLI для ETL.

Команды:
    import   импорт raw-записей из JSON в pumps.json (Phase 5 функционал)
    parse    PDF-каталог → run-dir с артефактами (Phase 6.4)
    review   показать diff-отчёт прогона
    merge    влить validated.json прогона в pumps.json

Примеры:
    python -m pump_calculator.etl.cli import data/new_pumps.json
    python -m pump_calculator.etl.cli import data/new_pumps.json --merge --overwrite
    python -m pump_calculator.etl.cli parse tests/fixtures/pedrollo_vx_50hz.pdf --brand Pedrollo
    python -m pump_calculator.etl.cli review runs/20260503-180000-abc123
    python -m pump_calculator.etl.cli merge  runs/20260503-180000-abc123 --overwrite

Формат входного JSON для `import` — массив объектов RawPumpRecord. Минимальный пример:

    [
      {
        "brand": "KAIQUAN",
        "model": "65WQ/S 30-22-5.5",
        "type": "submersible_sewage",
        "impeller": "single-channel",
        "free_passage_mm": 65,
        "qh_curve": [
          {"Q_m3h": 0,  "H_m": 30, "eta_pct": 0,    "NPSHr_m": 1.5},
          {"Q_m3h": 15, "H_m": 28, "eta_pct": 35.0, "NPSHr_m": 1.8},
          {"Q_m3h": 30, "H_m": 25, "eta_pct": 50.0, "NPSHr_m": 2.5},
          {"Q_m3h": 45, "H_m": 20, "eta_pct": 48.0, "NPSHr_m": 4.0},
          {"Q_m3h": 60, "H_m": 12, "eta_pct": 32.0, "NPSHr_m": 6.0}
        ],
        "P_kW": 5.5,
        "voltage_v": 380, "phase": 3, "ip_rating": "IP68",
        "discharge_DN_mm": 65,
        "wastewater_compat": ["domestic", "industrial"],
        "price_segment": "budget",
        "available_ru_status": "official",
        "distributor": "АСО (acorussia.ru)",
        "warranty_months": 18,
        "source": "manual-entry-2026-05"
      }
    ]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pump_calculator.etl.importer import import_raw_pumps_from_json, merge_into_pumps_json


def _default_pumps_json_target() -> Path:
    """Дефолтный путь к pumps.json (../../02_dataset/pumps/pumps.json)."""
    return Path(__file__).resolve().parents[3] / "02_dataset" / "pumps" / "pumps.json"


def _default_runs_root() -> Path:
    """Дефолтная директория для прогонов: backend/runs/."""
    return Path(__file__).resolve().parents[3] / "backend" / "runs"


def main() -> int:
    # На Windows консоль по умолчанию cp1251 — '→', '—', '₽' и др. падают
    # с UnicodeEncodeError. Принудительно ставим UTF-8 для stdout/stderr.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass

    parser = argparse.ArgumentParser(
        prog="pump_calculator.etl.cli",
        description="ETL для импорта raw-записей насосов в pumps.json",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ----- import (Phase 5) -----------------------------------------------
    p_import = sub.add_parser("import", help="Импорт raw-записей в pumps.json формат")
    p_import.add_argument("input", help="Путь к JSON-файлу с массивом raw-записей")
    p_import.add_argument(
        "--merge", action="store_true",
        help="Слить с существующим pumps.json вместо вывода в stdout",
    )
    p_import.add_argument(
        "--overwrite", action="store_true",
        help="При --merge: перезаписывать существующие id (по умолчанию — пропускать)",
    )
    p_import.add_argument(
        "--target",
        help="Путь к pumps.json (по умолчанию ../02_dataset/pumps/pumps.json)",
    )

    # ----- parse (Phase 6.4) ----------------------------------------------
    p_parse = sub.add_parser(
        "parse",
        help="Прогнать PDF-каталог через ETL pipeline (PDF → validated JSON)",
    )
    p_parse.add_argument("pdf", help="Путь к PDF-каталогу (Pedrollo, KSB, KAIQUAN, ...)")
    p_parse.add_argument(
        "--brand", required=True,
        help="Бренд (Pedrollo, Wilo, KSB, KAIQUAN, ...) — попадёт в RawPumpRecord.brand",
    )
    p_parse.add_argument(
        "--runner", choices=["pdfplumber", "docling"], default="pdfplumber",
        help="PDF-парсер. pdfplumber — vector-text (default); docling — сканы/OCR",
    )
    p_parse.add_argument(
        "--pages-per-chunk", type=int, default=4,
        help="Размер чанка для splitter (default 4 — обычно весь datasheet целиком)",
    )
    p_parse.add_argument(
        "--runs-root",
        help=f"Корневая директория прогонов (default {_default_runs_root()})",
    )

    # ----- review ---------------------------------------------------------
    p_review = sub.add_parser("review", help="Вывести 07_diff.md прогона в stdout")
    p_review.add_argument("run_dir", help="Путь к runs/<run_id>/")

    # ----- merge ----------------------------------------------------------
    p_merge = sub.add_parser(
        "merge", help="Влить 05_validated.json прогона в pumps.json",
    )
    p_merge.add_argument("run_dir", help="Путь к runs/<run_id>/")
    p_merge.add_argument(
        "--overwrite", action="store_true",
        help="Перезаписывать существующие id (по умолчанию — пропускать)",
    )
    p_merge.add_argument(
        "--target",
        help="Путь к pumps.json (по умолчанию ../02_dataset/pumps/pumps.json)",
    )

    args = parser.parse_args()

    # ----- import handler ------------------------------------------------
    if args.cmd == "import":
        result = import_raw_pumps_from_json(args.input)
        print(f"Imported {len(result)} record(s) from {args.input}", file=sys.stderr)

        if args.merge:
            target = Path(args.target) if args.target else _default_pumps_json_target()
            added, skipped = merge_into_pumps_json(
                result, target, overwrite=args.overwrite,
            )
            print(f"Merged into {target}: added={added}, skipped={skipped}", file=sys.stderr)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # ----- parse handler -------------------------------------------------
    if args.cmd == "parse":
        # Импорт здесь, чтобы команды import/review/merge не тащили docling/pdfplumber
        from pump_calculator.etl.pipeline import parse_catalog

        runs_root = Path(args.runs_root) if args.runs_root else _default_runs_root()
        result = parse_catalog(
            pdf_path=args.pdf,
            brand=args.brand,
            runs_root=runs_root,
            runner=args.runner,
            pages_per_chunk=args.pages_per_chunk,
        )
        print(f"Run dir: {result.run_dir}", file=sys.stderr)
        print(
            f"Validated: {len(result.validated)}, "
            f"Quarantine: {len(result.quarantine)}, "
            f"Errors: {len(result.errors)}, "
            f"Runtime: {result.runtime_sec}s",
            file=sys.stderr,
        )
        if result.errors:
            print("\nErrors:", file=sys.stderr)
            for err in result.errors:
                print(f"  - {err}", file=sys.stderr)
        # В stdout — путь к run_dir (для пайпов)
        print(str(result.run_dir))
        return 0 if not result.errors else 2

    # ----- review handler ------------------------------------------------
    if args.cmd == "review":
        run_dir = Path(args.run_dir)
        diff_md = run_dir / "07_diff.md"
        if not diff_md.exists():
            print(f"ERROR: {diff_md} не найден", file=sys.stderr)
            return 1
        print(diff_md.read_text(encoding="utf-8"))
        return 0

    # ----- merge handler -------------------------------------------------
    if args.cmd == "merge":
        run_dir = Path(args.run_dir)
        validated_path = run_dir / "05_validated.json"
        if not validated_path.exists():
            print(f"ERROR: {validated_path} не найден", file=sys.stderr)
            return 1

        raw_records = json.loads(validated_path.read_text(encoding="utf-8"))
        if not isinstance(raw_records, list):
            print(f"ERROR: {validated_path} должен быть JSON-массивом", file=sys.stderr)
            return 1

        # Для merge нам нужен формат pumps.json (с envelope). Прогоним через
        # импортер: import_raw_pump делает parabolic fit Q-H и собирает запись.
        from pump_calculator.etl.importer import import_raw_pump
        from pump_calculator.etl.schemas import RawPumpRecord

        pumps_records: list[dict] = []
        for raw in raw_records:
            try:
                rpr = RawPumpRecord.model_validate(raw)
                pumps_records.append(import_raw_pump(rpr))
            except Exception as e:  # noqa: BLE001
                print(f"WARN: skipping {raw.get('model')}: {e}", file=sys.stderr)

        target = Path(args.target) if args.target else _default_pumps_json_target()
        added, skipped = merge_into_pumps_json(
            pumps_records, target, overwrite=args.overwrite,
        )
        print(
            f"Merged into {target}: added={added}, skipped={skipped} "
            f"(from {len(raw_records)} raw, {len(pumps_records)} valid)",
            file=sys.stderr,
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
