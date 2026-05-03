"""CLI для ETL.

Использование:
    python -m pump_calculator.etl.cli import data/new_pumps.json
    python -m pump_calculator.etl.cli import data/new_pumps.json --merge --overwrite

Формат входного JSON — массив объектов RawPumpRecord. Минимальный пример:

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


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pump_calculator.etl.cli",
        description="ETL для импорта raw-записей насосов в pumps.json",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

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

    args = parser.parse_args()

    if args.cmd == "import":
        result = import_raw_pumps_from_json(args.input)
        print(f"Imported {len(result)} record(s) from {args.input}", file=sys.stderr)

        if args.merge:
            target = Path(args.target) if args.target else (
                Path(__file__).resolve().parents[3] / "02_dataset" / "pumps" / "pumps.json"
            )
            added, skipped = merge_into_pumps_json(
                result, target, overwrite=args.overwrite,
            )
            print(f"Merged into {target}: added={added}, skipped={skipped}", file=sys.stderr)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
