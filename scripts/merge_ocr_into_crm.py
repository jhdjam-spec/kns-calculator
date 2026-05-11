"""Merge OCR-text в CRM JSON: проходим regex'ом по distilled OCR text,
добавляем найденные параметры в crm_extracted_params_2026-05-10.json как новые лиды
с source='yadisk_ocr'.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Импортируем regex'ы
from extract_qh_params import parse_qh, detect_types, detect_city  # noqa

OCR = ROOT / "02_dataset" / "_inbox" / "yadisk_kns" / "extracted_text_ocr.jsonl"
CRM = ROOT / "02_dataset" / "_analysis" / "crm_extracted_params_2026-05-10.json"


def main() -> int:
    if not OCR.exists():
        print("[ERR] OCR jsonl not found")
        return 1
    crm = json.loads(CRM.read_text(encoding="utf-8"))

    new_leads = []
    n_total = 0
    n_with_text = 0
    for line in OCR.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        n_total += 1
        text = (e.get("ocr_text") or "").strip()
        if not text:
            continue
        n_with_text += 1
        params = parse_qh(text)
        if not params:
            continue
        types = detect_types(text[:5000])
        city = detect_city(text[:5000])
        new_leads.append({
            "source": "yadisk_ocr",
            "id": e.get("path"),
            "name": e.get("name", ""),
            "ext": e.get("ext", ""),
            "size": e.get("size", 0),
            "ocr_pages": e.get("ocr_pages_recognized", 0),
            "city": city,
            "types": types,
            "params": params,
            "text_excerpt": text[:500].replace("\n", " "),
        })

    print(f"OCR jsonl: {n_total} entries, {n_with_text} с текстом")
    print(f"Найдено лидов с параметрами: {len(new_leads)}")

    # Дописываем
    crm["leads"].extend(new_leads)
    by_source = Counter(l["source"] for l in crm["leads"])
    by_type = Counter()
    for l in crm["leads"]:
        for t in l.get("types", []):
            by_type[t] += 1
    by_city = Counter(l["city"] for l in crm["leads"] if l.get("city"))
    with_q = sum(1 for l in crm["leads"] if "Q_m3h" in l["params"] or "Q_ls" in l["params"])
    with_h = sum(1 for l in crm["leads"] if "H_m" in l["params"])
    with_v = sum(1 for l in crm["leads"] if "V_m3" in l["params"])
    with_qh = sum(1 for l in crm["leads"] if (("Q_m3h" in l["params"]) or ("Q_ls" in l["params"])) and "H_m" in l["params"])

    crm["total_leads"] = len(crm["leads"])
    crm["by_source"] = dict(by_source)
    crm["by_type"] = dict(by_type.most_common())
    crm["by_city_top20"] = dict(by_city.most_common(20))
    crm["with_Q"] = with_q
    crm["with_H"] = with_h
    crm["with_V"] = with_v
    crm["with_Q_and_H_both"] = with_qh
    crm["ocr_added_at"] = "2026-05-10T15:30:00+03:00"
    CRM.write_text(json.dumps(crm, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== Merged ===")
    print(f"  total_leads = {crm['total_leads']}")
    print(f"  by_source = {dict(by_source)}")
    print(f"  with_Q={with_q} with_H={with_h} with_V={with_v} with_Q+H={with_qh}")
    print(f"  by_type top-10:")
    for t, c in by_type.most_common(10):
        print(f"    {c:4d}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
