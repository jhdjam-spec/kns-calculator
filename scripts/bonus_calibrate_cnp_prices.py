"""Bonus calibration: апплицировать цены 2024-2026 из research на 38 CNP в pumps.json.

Источник: 02_dataset/_analysis/cnp_pumps_2026-05-08.json (Agent C research).
Матчинг: по полю id (или модели).
Сохраняем `_engineer_note` с источником.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "02_dataset" / "pumps" / "pumps.json"
RESEARCH = ROOT / "02_dataset" / "_analysis" / "cnp_pumps_2026-05-08.json"


def main() -> int:
    db = json.loads(DB.read_text(encoding="utf-8"))
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    research_pumps = research["pumps"]
    by_id = {p["id"]: p for p in research_pumps}

    updated = 0
    skipped_already_priced = 0
    not_found_in_research = 0
    for p in db["pumps"]:
        if p.get("brand") != "CNP":
            continue
        rid = p.get("id")
        rp = by_id.get(rid)
        if not rp:
            not_found_in_research += 1
            continue
        old_price = p.get("price_rub_2026")
        new_price = rp.get("price_rub_2026")
        if old_price and old_price == new_price:
            skipped_already_priced += 1
            continue
        if new_price:
            p["price_rub_2026"] = new_price
            # Дополнительные поля из research
            for f in ("price_source", "price_segment", "warranty_months", "_added"):
                v = rp.get(f)
                if v and not p.get(f):
                    p[f] = v
            updated += 1

    db["_updated"] = "2026-05-10T04:30:00+03:00"
    db.setdefault("_changelog", []).append({
        "date": "2026-05-10",
        "phase": "bonus calibrate CNP prices",
        "updated_count": updated,
        "skipped_already_priced": skipped_already_priced,
        "cnp_in_db_not_in_research": not_found_in_research,
        "source": "02_dataset/_analysis/cnp_pumps_2026-05-08.json",
    })

    DB.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ Updated {updated} CNP prices")
    print(f"  skipped (already priced): {skipped_already_priced}")
    print(f"  in DB but not in research: {not_found_in_research}")
    print(f"  saved to {DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
