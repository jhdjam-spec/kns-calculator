"""Парсинг прайс-листа PEGAS Engineering из массива КНС 2.

Файл `Цены ПЕГАС ИНЖИНИРИНГ.xlsx` имеет 8 листов с разными линейками
продукции. Скрипт ищет файл по pattern (так как имя в mojibake) и
извлекает структурированные данные.
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl

KNS2_DIR = (
    Path(r"C:\Users\User\Desktop\kns-calculator-repo")
    / "00_research"
    / "kns2_dataset_2026-05-08"
)


def find_pegas_xlsx() -> Path | None:
    """Найти xlsx с PEGAS — имя в mojibake, ищем по размеру (~7.1 МБ)."""
    for path in KNS2_DIR.rglob("*.xlsx"):
        size_mb = path.stat().st_size / 1024 / 1024
        if 6.5 < size_mb < 8.0:
            return path
    return None


def parse_sheet(ws) -> list[dict]:
    """Извлечь строки с непустыми ячейками."""
    rows = []
    for row in ws.iter_rows(values_only=True):
        non_empty = [c for c in row if c not in (None, "")]
        if not non_empty:
            continue
        rows.append({"raw": [str(c) if c is not None else "" for c in row]})
    return rows


def main() -> int:
    pegas_file = find_pegas_xlsx()
    if not pegas_file:
        print("ERROR: PEGAS xlsx not found")
        return 1
    print(f"Found: {pegas_file.name} ({pegas_file.stat().st_size / 1024 / 1024:.1f} MB)")

    wb = openpyxl.load_workbook(pegas_file, data_only=True)
    print(f"Sheets ({len(wb.sheetnames)}): {wb.sheetnames}")

    data = {
        "_source": pegas_file.name,
        "_parsed_at": "2026-05-08",
        "sheets": {},
    }

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = parse_sheet(ws)
        data["sheets"][sheet_name] = {
            "row_count": len(rows),
            "first_5": rows[:5],
            "last_3": rows[-3:],
        }
        print(f"  '{sheet_name}': {len(rows)} non-empty rows")

    out = Path(__file__).parent / "pegas_raw_dump.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Dumped to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
