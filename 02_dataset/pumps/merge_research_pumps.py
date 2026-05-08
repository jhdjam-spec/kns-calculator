"""ETL: слияние pumps_imported_from_research_*.json в основной pumps.json.

Безопасная стратегия:
- читает оба JSON (основной + импортируемый)
- проверяет на дубли по `id` — если уже есть, пропускает
- добавляет новые в конец массива
- сохраняет обратно с обновлённой меткой _updated

Запуск:
    python merge_research_pumps.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
MAIN_FILE = HERE / "pumps.json"
IMPORTED_FILE = HERE / "pumps_imported_from_research_2026-05-09.json"


def main() -> int:
    main_data = json.loads(MAIN_FILE.read_text(encoding="utf-8"))
    imported_data = json.loads(IMPORTED_FILE.read_text(encoding="utf-8"))

    main_pumps = main_data["pumps"]
    imported_pumps = imported_data["pumps"]

    existing_ids = {p["id"] for p in main_pumps}
    new_pumps = [p for p in imported_pumps if p["id"] not in existing_ids]
    skipped = [p["id"] for p in imported_pumps if p["id"] in existing_ids]

    print(f"Main DB: {len(main_pumps)} pumps")
    print(f"Imported file: {len(imported_pumps)} pumps")
    print(f"New (will be added): {len(new_pumps)}")
    print(f"Skipped (duplicate id): {len(skipped)} — {skipped}")

    if not new_pumps:
        print("\nNothing to import.")
        return 0

    # Добавляем
    main_data["pumps"].extend(new_pumps)
    main_data["_updated"] = "2026-05-09"
    note = main_data.get("_engineer_note", "")
    if "[2026-05-09]" not in note:
        main_data["_engineer_note"] = note + (
            f"\n[2026-05-09] +{len(new_pumps)} models from Agent D/E research "
            f"(Wilo Drain TM, Pedrollo VXm, Grundfos SEG, Fancy WQ, LEO LKS, "
            f"CNP WQ-W, ГНОМ 150-30, KSB Amarex N). Total: {len(main_data['pumps'])}."
        )

    # Бэкап
    backup_path = MAIN_FILE.with_suffix(".json.bak.2026-05-09")
    backup_path.write_text(
        json.dumps(json.loads(MAIN_FILE.read_text(encoding="utf-8")), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nBackup: {backup_path}")

    # Запись
    MAIN_FILE.write_text(
        json.dumps(main_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Updated: {MAIN_FILE} ({len(main_data['pumps'])} pumps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
