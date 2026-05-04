"""Первичная оценка цены КНС-комплекта по BOM.

Используется в `/select` и `/select/quick` чтобы менеджер сразу видел ориентировочный бюджет.
Источники: 02_dataset/fittings/fittings_seed.json (АРКАДА КП 29.01.2026 baseline) +
heuristic-оценки для насосов и Серво-Юг корпусов.

Не претендует на коммерческую точность — только для первичного бюджетного сценария.
Финальные цены — в BOM PDF после уточнённого расчёта инженером.
"""

from __future__ import annotations

from typing import Any, Literal

from pump_calculator import catalog
from pump_calculator.pricing_glass import estimate_glass_corpus_price_rub
from pump_calculator.schemas import PriceBreakdown, PriceSegment

CorpusMaterial = Literal["pe", "glass"]

# ---------- Heuristic: цена насоса ----------
# Базис: АРКАДА КП 29.01.2026 + публичные прайсы 2026
# KAIQUAN 50WQ/S 20-22-3 (3 кВт, budget): 65 600 ₽; YW2368-8157-400 (premium): 1 352 052 ₽

# ₽ за кВт по сегментам — грубая регрессия по реальным точкам
PUMP_RUB_PER_KW: dict[str, float] = {
    "budget": 25_000,   # KAIQUAN, LEO бюджет
    "mid": 65_000,      # Antarus, Pedrollo, Иртыш-серия
    "premium": 180_000,  # KSB, Wilo, Grundfos
}

# Минимальная и максимальная цена на любой насос — клампим
PUMP_MIN_RUB: dict[str, int] = {"budget": 30_000, "mid": 90_000, "premium": 250_000}
PUMP_MAX_RUB: dict[str, int] = {"budget": 250_000, "mid": 600_000, "premium": 2_500_000}


def estimate_pump_price_rub(P_kW: float, segment: PriceSegment) -> int:
    """Оценка цены одного насоса по мощности и ценовому сегменту.

    Линейная регрессия от мощности с клампами по сегменту.
    """
    rate = PUMP_RUB_PER_KW.get(segment, 50_000)
    raw = max(P_kW, 0.5) * rate
    raw = max(raw, PUMP_MIN_RUB[segment])
    raw = min(raw, PUMP_MAX_RUB[segment])
    # Округление до 1000 ₽
    return int(round(raw / 1000.0) * 1000)


# ---------- DN-обвязка ----------

DN_LADDER: list[int] = [50, 65, 80, 100, 150, 200, 250, 300, 400]


def round_to_dn(dn_mm: float | None) -> str:
    """Округление DN до ближайшего стандартного из лестницы."""
    if not dn_mm or dn_mm <= 0:
        return "DN50"
    for s in DN_LADDER:
        if dn_mm <= s:
            return f"DN{s}"
    return f"DN{DN_LADDER[-1]}"


def _price_for_dn(price_examples: dict[str, int], dn: str) -> int | None:
    """Точная цена для DN или ближайшая снизу."""
    if not price_examples:
        return None
    if dn in price_examples:
        return price_examples[dn]
    if not dn.startswith("DN"):
        return None
    try:
        target = int(dn[2:])
    except ValueError:
        return None
    available = [(int(k[2:]), v) for k, v in price_examples.items() if k.startswith("DN") and v]
    if not available:
        return None
    closest = min(available, key=lambda kv: abs(kv[0] - target))
    return closest[1]


# ---------- Корпус КНС: подбор по Q ----------

def estimate_corpus_price_rub(Q_m3h: float, material: CorpusMaterial = "pe") -> int:
    """Грубая оценка цены корпуса КНС по производительности и материалу.

    material="pe" (default) — ПЭ-корпус Серво-Юг (heuristic от Q):
      Q≤30 → ~350 000 ₽ (D1500/H3200)
      Q≈21–60 → ~400 000 ₽ (D1590/H3400 — АртВинд)
      Q≥250 → ~1 500 000 ₽ (D4200/H4010)
    material="glass" — стеклопластик (точная формула из калькулятора Серво-Юг,
      см. pricing_glass.py).
    """
    if material == "glass":
        return estimate_glass_corpus_price_rub(Q_m3h)

    # ПЭ — кусочно-линейная интерполяция по эталонным точкам
    if Q_m3h <= 30:
        return 350_000
    if Q_m3h <= 60:
        return 400_000
    if Q_m3h <= 130:
        # Линейно между 400 000 и 800 000
        frac = (Q_m3h - 60) / 70.0
        return int(round((400_000 + frac * 400_000) / 1000.0) * 1000)
    if Q_m3h <= 252:
        frac = (Q_m3h - 130) / 122.0
        return int(round((800_000 + frac * 700_000) / 1000.0) * 1000)
    return 1_700_000


# ---------- Шкаф управления ----------

def estimate_cabinet_price_rub(P_kW: float, segment: PriceSegment) -> int:
    """ШУ зависит от: суммарной мощности всех насосов и сегмента.

    Базис fittings_seed.json::kns_common_items[ШУ]:
      budget — ОНИКС МК4-2×3кВт-АВР: 266 364 ₽
      premium — Wilo CC-FC: ~750 000 ₽ (для 3×110 кВт = 753 350 ₽)
    Линейная зависимость от P_kW с минимальным порогом.
    """
    base = {"budget": 200_000, "mid": 320_000, "premium": 500_000}[segment]
    extra_per_kw = {"budget": 8_000, "mid": 12_000, "premium": 20_000}[segment]
    raw = base + max(P_kW - 3, 0) * extra_per_kw
    return int(round(raw / 1000.0) * 1000)


# ---------- Главная функция оценки BOM ----------

def estimate_kns_kit_price(
    P_kW: float,
    Q_m3h: float,
    discharge_DN_mm: float | None,
    segment: PriceSegment,
    n_pumps: int = 2,  # 1 раб + 1 рез по умолчанию
    corpus_material: CorpusMaterial = "pe",
) -> tuple[PriceBreakdown, str]:
    """Полная оценка цены КНС-комплекта.

    corpus_material:
      "pe" (default) — ПЭ-корпус Серво-Юг
      "glass" — стеклопластиковый корпус (точная формула из калькулятора Серво-Юг)

    Возвращает (PriceBreakdown, confidence).
    confidence:
      'high'   — все позиции из fittings_seed.json (DN-точная цена)
      'medium' — частичные точные + heuristic для насоса/корпуса
      'low'    — большинство heuristic
    """
    fittings = catalog._load_fittings()
    obvyazka = fittings.get("kns_obvyazka_template", {}).get("items", [])
    common = fittings.get("kns_common_items", {}).get("items", [])

    dn = round_to_dn(discharge_DN_mm)
    hits_from_db = 0
    total_db_lookups = 0

    # 1. Насос (heuristic — нет в БД)
    pump_unit = estimate_pump_price_rub(P_kW, segment)
    pump_total = pump_unit * n_pumps

    # 2-4. АТМ + задвижка + обр.клапан (по DN)
    atm_rub = 0
    valve_rub = 0
    check_valve_rub = 0
    rails_rub = 0
    for item in obvyazka:
        pos = item.get("position")
        if pos == 2:  # АТМ
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                atm_rub = price * n_pumps
        elif pos == 3:  # Задвижка
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                valve_rub = price * n_pumps
        elif pos == 4:  # Обр.клапан
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                check_valve_rub = price * n_pumps
        elif pos == 5:  # Направляющие
            rails_rub = item.get("price_typical_rub_2026", 12_000) * n_pumps

    # 5. ШУ (heuristic, attached к фактической мощности насосов рабочих)
    P_total_working = P_kW  # для 1+1 рабочая мощность = одного насоса
    cabinet_rub = estimate_cabinet_price_rub(P_total_working, segment)

    # 6. Поплавки (4 шт по 5000 = 20000)
    floats_rub = 4 * 5_000

    # 7. Цепь
    chain_rub = 4_000 * n_pumps

    # 8. Корпус КНС (heuristic от Q + материал)
    corpus_rub = estimate_corpus_price_rub(Q_m3h, material=corpus_material)

    total = (
        pump_total + atm_rub + valve_rub + check_valve_rub
        + rails_rub + cabinet_rub + floats_rub + chain_rub + corpus_rub
    )

    # Confidence: если все 3 fitting-DN из БД — medium, иначе low
    if total_db_lookups > 0:
        ratio = hits_from_db / total_db_lookups
        confidence = "medium" if ratio >= 0.66 else "low"
    else:
        confidence = "low"

    breakdown = PriceBreakdown(
        pump_rub=pump_total,
        atm_rub=atm_rub,
        valve_rub=valve_rub,
        check_valve_rub=check_valve_rub,
        rails_rub=rails_rub,
        cabinet_rub=cabinet_rub,
        floats_rub=floats_rub,
        chain_rub=chain_rub,
        corpus_rub=corpus_rub,
        total_rub=total,
    )
    return breakdown, confidence
