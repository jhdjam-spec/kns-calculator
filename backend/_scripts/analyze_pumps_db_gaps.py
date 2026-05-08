"""Аналитика БД насосов — найти пробелы в Q-H покрытии и ценовых сегментах.

Цель: понять где у нас «дыры» по которым калькулятор не сможет подобрать
насос или подберёт неоптимальный.

Анализ:
1. **Q-H матрица покрытия:** сетка по Q (5/10/20/40/80/150/300/600/1500 м³/ч)
   и H (5/10/20/40/80 м). Сколько насосов покрывает каждую ячейку?
2. **Brand distribution:** сколько насосов каждого бренда, по типам.
3. **Price segment coverage:** budget/standard/premium и пересечение с типами.
4. **Wastewater compat:** покрытие всех 5 типов стоков.
5. **Free passage range:** для submersible — типичные размеры.
6. **Origin (РФ vs импорт):** в условиях импортозамещения важно знать долю.
7. **Duplicates / suspects:** одинаковые Q_BEP+H_BEP с разными именами.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUMPS_PATH = ROOT / "02_dataset" / "pumps" / "pumps.json"

# Q-H grid для проверки покрытия
Q_GRID = [5, 10, 20, 40, 80, 150, 300, 600, 1500, 3000]   # м³/ч
H_GRID = [5, 10, 20, 40, 80, 150]                          # м


def covers(pump: dict, q: float, h: float) -> bool:
    """Покрывает ли насос точку (Q,H) внутри своего envelope."""
    e = pump.get("envelope") or {}
    if not e:
        return False
    q_min = e.get("Q_min_m3h")
    q_max = e.get("Q_max_m3h")
    h_min = e.get("H_min_m")
    h_max = e.get("H_max_m")
    if None in (q_min, q_max, h_min, h_max):
        return False
    return q_min <= q <= q_max and h_min <= h <= h_max


def main():
    with open(PUMPS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    pumps = data["pumps"]
    print(f"=== Total pumps: {len(pumps)} ===\n")

    # 1. Q-H coverage matrix
    print("=== 1. Q-H coverage matrix (pumps per cell) ===")
    h_header = "Q vs H"
    print(f"{h_header:<8}" + "".join(f"H={h:>4}" for h in H_GRID))
    gaps = []
    for q in Q_GRID:
        row = [f"Q={q:>4}: "]
        for h in H_GRID:
            n = sum(1 for p in pumps if covers(p, q, h))
            row.append(f"{n:>5}")
            if n == 0:
                gaps.append((q, h))
            elif n < 3:
                gaps.append((q, h, "few"))
        print("".join(row))
    print(f"\nEmpty/sparse cells: {len(gaps)}")
    for g in gaps[:10]:
        print(f"  {g}")
    print()

    # 2. Brand distribution by type
    print("=== 2. Brand x Type ===")
    by_brand_type = Counter()
    for p in pumps:
        b = p.get("brand", "?")
        t = p.get("type", "?")
        by_brand_type[(b, t)] += 1
    brands = sorted({b for b, t in by_brand_type})
    types = sorted({t for b, t in by_brand_type})
    print(f"  Brands: {len(brands)}, Types: {len(types)}")
    for t in types:
        total_t = sum(c for (b, tt), c in by_brand_type.items() if tt == t)
        print(f"    {t}: {total_t} pumps")
    print()
    for b in brands:
        total = sum(c for (bb, t), c in by_brand_type.items() if bb == b)
        print(f"    {b:25s} {total:>3}")
    print()

    # 3. Price segment
    print("=== 3. Price segment ===")
    seg = Counter(p.get("price_segment", "?") for p in pumps)
    for s, n in seg.most_common():
        print(f"  {s:12s} {n:>3}")
    print()

    # 4. Wastewater compat
    print("=== 4. Wastewater compat (pump may match multiple) ===")
    wc = Counter()
    for p in pumps:
        for w in p.get("wastewater_compat", []):
            wc[w] += 1
    for w, n in wc.most_common():
        print(f"  {w:25s} {n:>3}")
    print()

    # 5. Free passage by type
    print("=== 5. Free passage by type ===")
    fp_by_type = defaultdict(list)
    for p in pumps:
        fp = p.get("free_passage_mm")
        if fp is not None:
            fp_by_type[p.get("type", "?")].append(fp)
    for t, lst in fp_by_type.items():
        if lst:
            print(f"  {t:30s} min={min(lst):>4} max={max(lst):>4} median={sorted(lst)[len(lst)//2]:>4}  ({len(lst)} samples)")
    print()

    # 6. Origin (РФ vs импорт) — through brand mapping
    print("=== 6. Origin (by distributor status) ===")
    origin_counter = Counter()
    for p in pumps:
        ar = p.get("available_ru") or {}
        st = ar.get("status") or "?"
        origin_counter[st] += 1
    for s, n in origin_counter.most_common():
        print(f"  {s:30s} {n:>3}")
    print()

    # 7. Duplicates by (Q_BEP, H_BEP, P_kW)
    print("=== 7. Duplicate suspects (same Q_BEP, H_BEP, P_kW) ===")
    by_signature = defaultdict(list)
    for p in pumps:
        e = p.get("envelope") or {}
        sig = (
            e.get("Q_BEP_m3h"),
            e.get("H_BEP_m"),
            (p.get("power") or {}).get("P_kW"),
        )
        if all(v is not None for v in sig):
            by_signature[sig].append(p["id"])
    dupes = {sig: ids for sig, ids in by_signature.items() if len(ids) > 1}
    for sig, ids in dupes.items():
        print(f"  Q={sig[0]} H={sig[1]} P={sig[2]}: {ids}")
    if not dupes:
        print("  (none)")
    print()

    # 8. Pumps без NPSHr / без discharge.DN — пробелы в схеме
    print("=== 8. Data gaps ===")
    no_npshr = sum(1 for p in pumps if (p.get("envelope") or {}).get("NPSHr_at_BEP_m") is None)
    no_dn = sum(1 for p in pumps if (p.get("discharge") or {}).get("DN_mm") is None)
    no_eta = sum(1 for p in pumps if (p.get("envelope") or {}).get("eta_BEP_pct") is None)
    no_price = sum(1 for p in pumps if "price_rub_2026" not in p)
    flagged = sum(1 for p in pumps if p.get("_engineer_flag") == "needs_review")
    print(f"  no NPSHr_at_BEP_m: {no_npshr:>3} ({no_npshr*100//len(pumps)}%)")
    print(f"  no discharge.DN_mm: {no_dn:>3} ({no_dn*100//len(pumps)}%)")
    print(f"  no eta_BEP_pct: {no_eta:>3} ({no_eta*100//len(pumps)}%)")
    print(f"  no price_rub_2026: {no_price:>3} ({no_price*100//len(pumps)}%)")
    print(f"  needs_review flagged: {flagged:>3}")


if __name__ == "__main__":
    main()
