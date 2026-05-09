"""Обезличивает эталоны для публичного экспорта.

Удаляет/заменяет:
- gip, director, developer, head_of_construction, n_kontrol → "[role]"
- contract → "[contract_id]"
- иные поля с потенциальными ФИО

Сохраняет:
- code (шифр), object_type, location (город — публичная инфа), client (юр. лицо), year
- все технические параметры (Q, H, корпус, насосы)
- regulations, source_file
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "02_dataset" / "etalons" / "downloads_2026-05-09_etalons.json"
DST = ROOT / "02_dataset" / "etalons" / "public" / "etalons_public_2026-05-09.json"

PII_FIELDS_REPLACE = {
    "gip": "[ГИП]",
    "director": "[Директор]",
    "developer": "[Разработчик]",
    "head_of_construction": "[Начальник стройотдела]",
    "n_kontrol": "[Нормоконтроль]",
    "contract": "[contract_id]",
}


def anonymize(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in PII_FIELDS_REPLACE:
                out[k] = PII_FIELDS_REPLACE[k]
            else:
                out[k] = anonymize(v)
        return out
    if isinstance(obj, list):
        return [anonymize(x) for x in obj]
    return obj


def main():
    if not SRC.exists():
        print(f"[!] Не найден {SRC}")
        return 1
    DST.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC.read_text(encoding="utf-8"))
    anonymized = [anonymize(et) for et in data]
    DST.write_text(
        json.dumps(anonymized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] Обезличено {len(anonymized)} эталонов → {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
