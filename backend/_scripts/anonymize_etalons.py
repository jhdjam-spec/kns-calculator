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
SOURCES = [
    ROOT / "02_dataset" / "etalons" / "downloads_2026-05-09_etalons.json",
    ROOT / "02_dataset" / "etalons" / "downloads_2026-05-09_etalons_agent.json",
]
DST = ROOT / "02_dataset" / "etalons" / "public" / "etalons_public_2026-05-09.json"

import re

PII_FIELDS_REPLACE = {
    "gip": "[ГИП]",
    "director": "[Директор]",
    "developer": "[Разработчик]",
    "head_of_construction": "[Начальник стройотдела]",
    "n_kontrol": "[Нормоконтроль]",
    "chief_engineer": "[Главный инженер]",
    "designer_address": "[адрес проектанта]",
    "designer_contact": "[контакты проектанта]",
    "contract": "[contract_id]",
    "sro": "[СРО]",
}

# Удаляем из строковых значений: телефоны +7..., email, ИНН (10/12 цифр), ОГРН, KPP
TEL_RE = re.compile(r"\+?\d?\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
INN_RE = re.compile(r"\bИНН\s*\d{10,12}\b|\b\d{10}\b(?=\D|$)")
OGRN_RE = re.compile(r"\b(?:ОГРН|ОГРНИП)\s*\d{13,15}\b|\b\d{13}\b")
ADDR_RE = re.compile(r"\b\d{6},?\s+[гГ]\.?\s*[А-Я][а-я]+[^,]*?,\s*ул\.?[^,]*", re.UNICODE)


def _redact_string(s: str) -> str:
    s = TEL_RE.sub("[тел]", s)
    s = EMAIL_RE.sub("[email]", s)
    s = INN_RE.sub("[ИНН]", s)
    s = OGRN_RE.sub("[ОГРН]", s)
    s = ADDR_RE.sub("[адрес]", s)
    return s


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
    if isinstance(obj, str):
        return _redact_string(obj)
    return obj


def main():
    DST.parent.mkdir(parents=True, exist_ok=True)
    all_anonymized = []
    for src in SOURCES:
        if not src.exists():
            print(f"[-] Пропущен (нет файла): {src.name}")
            continue
        data = json.loads(src.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for et in data:
                all_anonymized.append(anonymize(et))
            print(f"[+] {src.name}: {len(data)} эталонов")
        else:
            all_anonymized.append(anonymize(data))
            print(f"[+] {src.name}: 1 эталон")
    DST.write_text(
        json.dumps(all_anonymized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] ИТОГО обезличено {len(all_anonymized)} эталонов → {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
