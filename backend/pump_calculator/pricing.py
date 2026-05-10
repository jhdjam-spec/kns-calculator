"""Первичная оценка цены КНС-комплекта по BOM.

Используется в `/select` и `/select/quick` чтобы менеджер сразу видел ориентировочный бюджет.
Источники: 02_dataset/fittings/fittings_seed.json (АРКАДА КП 29.01.2026 baseline) +
heuristic-оценки для насосов и Серво-Юг корпусов.

Не претендует на коммерческую точность — только для первичного бюджетного сценария.
Финальные цены — в BOM PDF после уточнённого расчёта инженером.
"""

from __future__ import annotations

from typing import Literal

from pump_calculator import catalog
from pump_calculator.pricing_glass import estimate_glass_corpus_price_rub
from pump_calculator.schemas import PriceBreakdown, PriceSegment

CorpusMaterial = Literal["pe", "glass"]

# ---------- НДС и дилерская скидка (2026) ----------
# С 2026 г. ставка НДС в РФ = 22% (повышена с 20%).
# Источник: счета Серво-Юг №94, №161 от 01.01.2026 (Agent C 2026-05-09).
VAT_RATE_2026: float = 0.22

# Медианная дилерская скидка по Серво-Юг (analysis 2026-05-09): -25%
# Применяется к финальной сумме при флаге is_dealer=True.
DEALER_DISCOUNT: float = 0.25


def apply_vat(amount_rub: int, vat_included: bool = True) -> int:
    """Если vat_included=False — амт без НДС, добавить НДС.
    Если True — амт уже с НДС, вернуть как есть.
    """
    if vat_included:
        return amount_rub
    return int(round(amount_rub * (1 + VAT_RATE_2026)))


def apply_dealer_discount(amount_rub: int, is_dealer: bool = False) -> int:
    """При флаге дилера снизить цену на 25% (медиана Серво-Юг 2026)."""
    if is_dealer:
        return int(round(amount_rub * (1 - DEALER_DISCOUNT)))
    return amount_rub


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


def estimate_pump_price_rub(
    P_kW: float,
    segment: PriceSegment,
    explicit_price_rub: int | None = None,
) -> int:
    """Цена одного насоса.

    Если задана `explicit_price_rub` (из поля pump.price_rub_2026 в БД) — используется
    точное значение. Иначе — heuristic от мощности и сегмента с клампами.
    """
    if explicit_price_rub and explicit_price_rub > 0:
        return int(explicit_price_rub)

    rate = PUMP_RUB_PER_KW.get(segment, 50_000)
    raw = max(P_kW, 0.5) * rate
    # Безопасное обращение к min/max (на случай неизвестного segment типа "standard")
    raw = max(raw, PUMP_MIN_RUB.get(segment, 30_000))
    raw = min(raw, PUMP_MAX_RUB.get(segment, 600_000))
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


# ---------- Anti-buoyancy uplift (УГВ → бетонный пригруз) ----------
#
# Архимед + СП 32.13330.2018 §6.3:
#   F_подъёма = ρ_воды · g · V_корпуса_подводой   (ρ=1000 кг/м³, g=9.81)
#   Удержание ж/б пригрузом: V_бетон ≥ F / (ρ_бет · g),  ρ_бет = 2400 кг/м³.
#
# Цена ж/б пригруза = бетон (B20-B25 ~6-8 тыс ₽/м³) + арматура + опалубка +
# усиление обоймы корпуса при затоплении площадки. По эталонам Серво-Юг:
#   • V≈1-3 тонн (УГВ от -2 до 0 м) → 50-150 тыс ₽
#   • V≈10+ тонн (УГВ выше поверхности) → 200-500 тыс ₽
#
# Сегментные множители — учитывают рост качества арматуры/опалубки/обоймы
# (budget=ж/б самосвал + опалубка из доски, premium=арматура А500С + металлическая
# опалубка + ж/б обойма по СП 22 §5.4).

ANTI_BUOYANCY_SEGMENT_MULT: dict[str, float] = {
    "budget": 1.0,
    "mid": 1.3,
    "premium": 1.7,
}


def estimate_anti_buoyancy_uplift_rub(
    groundwater_level_m: float | None,
    corpus_volume_m3: float,
    segment: PriceSegment,
) -> int:
    """Доплата за бетонный пригруз против всплытия КНС при высоком УГВ.

    Параметры:
      groundwater_level_m — отметка УГВ относительно земли, м.
        None → 0 (поле не заполнено, backward compat).
        ≤ -2 м → 0 (УГВ глубоко, корпус выше воды, пригруз не нужен).
        -2…0 м → среднее затопление (ж/б пригруз 1-3 тонны).
        > 0 м → площадка затоплена (большой пригруз + усиление обоймы).
      corpus_volume_m3 — объём корпуса для оценки силы Архимеда (используется
        при УГВ > 0 для масштабирования по реальному объёму).
      segment — budget/mid/premium (множитель ANTI_BUOYANCY_SEGMENT_MULT).

    Возвращает: доплата в ₽ (округлено до тыс).

    Источник: СП 32.13330.2018 §6.3, расчёт из structural/ballast.py.
    """
    if groundwater_level_m is None:
        return 0

    if groundwater_level_m <= -2.0:
        # УГВ глубокий — корпус сухой, пригруз не нужен.
        return 0

    mult = ANTI_BUOYANCY_SEGMENT_MULT.get(segment, 1.0)

    if groundwater_level_m <= 0.0:
        # От -2 до 0: линейная интерполяция в диапазоне 50-150 тыс ₽
        # (бетонный пригруз 1-3 тонны).
        # Чем выше УГВ (ближе к 0) — тем больше затопление.
        frac = (groundwater_level_m + 2.0) / 2.0  # 0…1
        base = 50_000 + frac * 100_000  # 50k…150k
        raw = base * mult
        return int(round(raw / 1000.0) * 1000)

    # УГВ > 0 — площадка затоплена. Большой пригруз + усиление обоймы.
    # Базовая стоимость 200 тыс ₽ при V_корпуса ≈ 5 м³ (малая КНС);
    # масштабируется до 500 тыс ₽ для V ≈ 50 м³ (большая КНС Q≥250).
    # Дополнительный фактор — насколько УГВ выше поверхности (доп. напор воды).
    v_factor = max(0.0, min(1.0, (corpus_volume_m3 - 5.0) / 45.0))  # 0…1
    h_factor = min(1.0, groundwater_level_m / 5.0)  # 0…1 (cap при +5 м)
    combined = 0.5 * v_factor + 0.5 * h_factor  # 0…1
    base = 200_000 + combined * 300_000  # 200k…500k
    raw = base * mult
    return int(round(raw / 1000.0) * 1000)


# ---------- Шкаф управления ----------

def estimate_cabinet_price_rub(P_kW: float, segment: PriceSegment) -> int:
    """ШУ зависит от: суммарной мощности всех насосов и сегмента.

    Базис: реальные КП Серво-Юг 2026:
      budget — простой ШУ для 2×2.2 кВт = 128 000 ₽ (КП инженера 2026-05-04)
      mid — ОНИКС МК4-2×3кВт-АВР = 266 364 ₽ (АРКАДА 29.01.2026)
      premium — Wilo CC-FC: ~750 000 ₽ (для 3×110 кВт = 753 350 ₽)
    Линейная зависимость от P_kW с минимальным порогом.
    """
    base = {"budget": 100_000, "mid": 240_000, "premium": 450_000}[segment]
    extra_per_kw = {"budget": 6_000, "mid": 12_000, "premium": 20_000}[segment]
    raw = base + max(P_kW - 2.2, 0) * extra_per_kw
    return int(round(raw / 1000.0) * 1000)


# ---------- Главная функция оценки BOM ----------

def _estimate_corpus_volume_m3(Q_m3h: float) -> float:
    """Грубая оценка объёма КНС-корпуса по производительности (для anti-buoyancy).

    Эталоны Серво-Юг ПЭ-корпусов:
      Q≤30 → D1.5 × H3.2 ≈ 5.7 м³
      Q≤60 → D1.6 × H3.4 ≈ 6.8 м³
      Q≤130 → D2.0 × H4.0 ≈ 12.6 м³
      Q≤252 → D3.0 × H4.0 ≈ 28.3 м³
      Q>252 → D4.2 × H4.0 ≈ 55.4 м³
    """
    if Q_m3h <= 30:
        return 5.7
    if Q_m3h <= 60:
        return 6.8
    if Q_m3h <= 130:
        return 12.6
    if Q_m3h <= 252:
        return 28.3
    return 55.4


def estimate_kns_kit_price(
    P_kW: float,
    Q_m3h: float,
    discharge_DN_mm: float | None,
    segment: PriceSegment,
    n_pumps: int = 2,  # 1 раб + 1 рез по умолчанию
    corpus_material: CorpusMaterial = "pe",
    explicit_pump_price_rub: int | None = None,
    include_corpus: bool = True,
    include_rails: bool = True,
    groundwater_level_m: float | None = None,
) -> tuple[PriceBreakdown, str]:
    """Полная оценка цены КНС-комплекта.

    Параметры:
      explicit_pump_price_rub — точная цена насоса из поля pump.price_rub_2026 в БД.
          Если задана, перебивает heuristic estimate_pump_price_rub.
      corpus_material: "pe" (Серво-Юг ПЭ) или "glass" (стеклопластик).
      include_corpus / include_rails — для малых КНС с готовым приямком корпус
          и направляющие могут не понадобиться (как в КП 65WQ/S223-2.2 для Q=0.5).

    Возвращает (PriceBreakdown, confidence).
    confidence:
      'high'   — explicit_pump_price + DN-обвязка из fittings_seed.json
      'medium' — частичные точные + heuristic
      'low'    — большинство heuristic
    """
    fittings = catalog._load_fittings()
    obvyazka = fittings.get("kns_obvyazka_template", {}).get("items", [])
    # common items (ШУ, поплавки, корпус) подбираются heuristic-функциями ниже,
    # без обращения к точным ценам из fittings — поэтому common не используем.

    dn = round_to_dn(discharge_DN_mm)
    hits_from_db = 0
    total_db_lookups = 0

    # 1. Насос — точная цена из БД (если есть) или heuristic
    pump_unit = estimate_pump_price_rub(P_kW, segment, explicit_price_rub=explicit_pump_price_rub)
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
        elif pos == 5 and include_rails:  # Направляющие
            rails_rub = item.get("price_typical_rub_2026", 12_000) * n_pumps

    # 5. ШУ (heuristic, attached к фактической мощности насосов рабочих)
    P_total_working = P_kW  # для 1+1 рабочая мощность = одного насоса
    cabinet_rub = estimate_cabinet_price_rub(P_total_working, segment)

    # 6. Поплавки (4 шт по 5000 = 20000)
    floats_rub = 4 * 5_000

    # 7. Цепь
    chain_rub = 4_000 * n_pumps if include_rails else 0

    # 8. Корпус КНС (опционально — для готовых приямков выключить)
    corpus_base_rub = (
        estimate_corpus_price_rub(Q_m3h, material=corpus_material)
        if include_corpus else 0
    )

    # 8b. Anti-buoyancy uplift (СП 32 §6.3): если УГВ выше дна корпуса,
    # требуется бетонный пригруз против всплытия. Прибавляем к corpus_rub
    # с пометкой в poll_notes (дальше matching.py добавит инженерный note).
    # Работает только если корпус включён (для готовых приямков пригруз
    # делается отдельным проектным решением).
    if include_corpus:
        corpus_volume_m3 = _estimate_corpus_volume_m3(Q_m3h)
        anti_buoyancy_rub = estimate_anti_buoyancy_uplift_rub(
            groundwater_level_m=groundwater_level_m,
            corpus_volume_m3=corpus_volume_m3,
            segment=segment,
        )
    else:
        anti_buoyancy_rub = 0

    corpus_rub = corpus_base_rub + anti_buoyancy_rub

    total = (
        pump_total + atm_rub + valve_rub + check_valve_rub
        + rails_rub + cabinet_rub + floats_rub + chain_rub + corpus_rub
    )

    # Confidence:
    # - high: точная цена насоса из БД + точная DN-обвязка
    # - medium: только DN-обвязка точная (heuristic насос)
    # - low: всё heuristic
    has_explicit_pump = bool(explicit_pump_price_rub and explicit_pump_price_rub > 0)
    if total_db_lookups > 0:
        ratio = hits_from_db / total_db_lookups
        if has_explicit_pump and ratio >= 0.66:
            confidence = "high"
        elif ratio >= 0.66:
            confidence = "medium"
        else:
            confidence = "low"
    else:
        confidence = "medium" if has_explicit_pump else "low"

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
        vat_rate=VAT_RATE_2026,
        vat_included=True,
        total_dealer_rub=apply_dealer_discount(total, is_dealer=True),
    )
    return breakdown, confidence


# ---------- Phase 8: Цена СПД-комплекта (booster station) ----------

def estimate_spd_cabinet_price_rub(P_kW: float, segment: PriceSegment) -> int:
    """ШУ для СПД — обычно с ЧРП и контроллером давления (Wilo CC-FC, ОНИКС-PLC).
    Дороже КНС-шкафа на 30-50% за счёт ЧРП.
    """
    base = {"budget": 150_000, "mid": 320_000, "premium": 600_000}[segment]
    extra_per_kw = {"budget": 10_000, "mid": 18_000, "premium": 28_000}[segment]
    raw = base + max(P_kW - 2.2, 0) * extra_per_kw
    return int(round(raw / 1000.0) * 1000)


def estimate_hydroaccumulator_price_rub(Q_m3h: float, segment: PriceSegment) -> int:
    """Мембранный бак / гидроаккумулятор для СПД.

    Объём подбирается грубо по Q (по практике Wilo/Grundfos):
      Q ≤ 5 м³/ч  → 8-24 л   (бытовая СПД)
      Q ≤ 20 м³/ч → 50-100 л
      Q ≤ 50 м³/ч → 200-300 л
      Q > 50      → 500+ л
    Цены примерные по сегментам.
    """
    if Q_m3h <= 5:
        prices = {"budget": 5_000, "mid": 10_000, "premium": 18_000}
    elif Q_m3h <= 20:
        prices = {"budget": 12_000, "mid": 22_000, "premium": 38_000}
    elif Q_m3h <= 50:
        prices = {"budget": 25_000, "mid": 45_000, "premium": 75_000}
    else:
        prices = {"budget": 60_000, "mid": 100_000, "premium": 180_000}
    return prices[segment]


def estimate_spd_kit_price(
    P_kW: float,
    Q_m3h: float,
    discharge_DN_mm: float | None,
    segment: PriceSegment,
    n_pumps: int = 2,  # 1 раб + 1 рез
    explicit_pump_price_rub: int | None = None,
) -> tuple[PriceBreakdown, str]:
    """Оценка цены СПД-комплекта (booster station).

    Состав отличается от КНС:
      - Насосы (вертикальные многоступенчатые) + рама
      - ШУ с ЧРП и контроллером давления
      - Мембранный бак / гидроаккумулятор
      - Датчики давления (4-20 мА), 2 шт
      - Задвижки и обратные клапаны на каждом насосе (без АТМ — сухопостовленные)
      - Без корпуса/направляющих/цепей/поплавков

    **Особенность:** если в БД задан `price_rub_2026` — это цена **готового
    блока «всё включено»** (насосы + ШУ + бак + рама + арматура), как в реальных
    КП производителей (ANTARUS 3 MLV20-5/GPRS = 3 500 650 ₽ за всю станцию).
    В этом случае только насос и не добавляем обвязку.

    Иначе (heuristic) — собираем компоненты по отдельности.

    Используем PriceBreakdown с уже существующими полями:
      - cabinet_rub — ШУ с ЧРП
      - atm_rub — гидроаккумулятор + рама + датчики (нет АТМ как у КНС)
      - valve_rub, check_valve_rub — обвязка по DN
      - corpus_rub = 0 (СПД — модуль, не корпус)
      - rails_rub, chain_rub, floats_rub = 0 (не применяются)
    """
    has_explicit_pump = bool(explicit_pump_price_rub and explicit_pump_price_rub > 0)

    # Если задана точная цена комплекта — это **всё включено**, обвязку не добавляем
    if has_explicit_pump:
        breakdown = PriceBreakdown(
            pump_rub=int(explicit_pump_price_rub) * n_pumps,
            atm_rub=0,
            valve_rub=0,
            check_valve_rub=0,
            rails_rub=0,
            cabinet_rub=0,
            floats_rub=0,
            chain_rub=0,
            corpus_rub=0,
            total_rub=int(explicit_pump_price_rub) * n_pumps,
        )
        return breakdown, "high"

    # Без точной цены — собираем по компонентам
    fittings = catalog._load_fittings()
    obvyazka = fittings.get("kns_obvyazka_template", {}).get("items", [])

    dn = round_to_dn(discharge_DN_mm)
    hits_from_db = 0
    total_db_lookups = 0

    # Насос (heuristic)
    pump_unit = estimate_pump_price_rub(P_kW, segment, explicit_price_rub=None)
    pump_total = pump_unit * n_pumps

    # Задвижки + обратные клапаны (на каждый насос — 2 единицы по DN)
    valve_rub = 0
    check_valve_rub = 0
    for item in obvyazka:
        pos = item.get("position")
        if pos == 3:  # Задвижка
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                # 2 задвижки на каждый насос (до и после)
                valve_rub = price * n_pumps * 2
        elif pos == 4:  # Обратный клапан
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                check_valve_rub = price * n_pumps

    # ШУ с ЧРП
    cabinet_rub = estimate_spd_cabinet_price_rub(P_kW, segment)

    # Гидроаккумулятор + рама — кладём в atm_rub (поле есть)
    hydro_rub = estimate_hydroaccumulator_price_rub(Q_m3h, segment)
    frame_rub = {"budget": 25_000, "mid": 45_000, "premium": 75_000}[segment]
    pressure_sensors_rub = 8_000 * 2  # 2 датчика давления 4-20 мА
    atm_rub = hydro_rub + frame_rub + pressure_sensors_rub

    total = pump_total + atm_rub + valve_rub + check_valve_rub + cabinet_rub

    # confidence: heuristic-ветка без explicit price → medium максимум
    if total_db_lookups > 0:
        ratio = hits_from_db / total_db_lookups
        confidence = "medium" if ratio >= 0.66 else "low"
    else:
        confidence = "low"

    breakdown = PriceBreakdown(
        pump_rub=pump_total,
        atm_rub=atm_rub,  # тут гидроаккумулятор+рама+датчики
        valve_rub=valve_rub,
        check_valve_rub=check_valve_rub,
        rails_rub=0,
        cabinet_rub=cabinet_rub,
        floats_rub=0,
        chain_rub=0,
        corpus_rub=0,
        total_rub=total,
    )
    return breakdown, confidence


# ---------- Phase 11: Цена пожарной СПД (fire_protection) ----------
#
# Особенности по сравнению с обычной СПД:
#   - PN16 арматура (vs PN10 у бытовых СПД) → +30-40% к стоимости задвижек/ОК
#   - ШУ с режимом Sf (Safety/пожарный): ручное включение, без автоотключения,
#     дублирование контактора, аварийный ввод от ДГУ, реле давления —
#     стоимость 2-3× обычного ЧРП-шкафа
#   - 1 рабочий + 1 резервный ОБЯЗАТЕЛЬНО (СП 10.13130 п.6.2)
#   - Жокей-насос с гидробаком 100-500 л для поддержания давления
#   - При категории помещения А/Б/Ex-зоне — ATEX исполнение (+40% к насосу)
#
# **Важно:** цены в этой функции — **только инженерный ориентир**.
# Параметры пожарной СПД сильно зависят от категории помещения, типа спринклеров,
# нормативного расхода — поэтому всегда возвращаем confidence=low и
# triggers=auto_fire_protection (handoff обязателен).

# Множители PN16 vs стандартного PN10 на арматуре — берём верхнюю границу диапазона
PN16_MULTIPLIER = 1.4

# ШУ пожарный (Wilo CC-FC SF, с резервированием) — кратно дороже обычного ЧРП
FIRE_CABINET_BASE_RUB: dict[str, int] = {
    "budget": 350_000,
    "mid": 700_000,
    "premium": 1_400_000,
}
FIRE_CABINET_PER_KW_RUB: dict[str, int] = {
    "budget": 18_000,
    "mid": 30_000,
    "premium": 45_000,
}


def estimate_fire_cabinet_price_rub(P_kW: float, segment: PriceSegment) -> int:
    """ШУ Sf (пожарный) — резервирование по СП 10.13130, ручное включение.

    Базис: типовые прайсы Wilo SCe-FC, ОНИКС-СПДТ, ИНТЕРПОЛ-ПЦН (2026).
    """
    base = FIRE_CABINET_BASE_RUB[segment]
    extra_per_kw = FIRE_CABINET_PER_KW_RUB[segment]
    raw = base + max(P_kW - 5.5, 0) * extra_per_kw
    return int(round(raw / 1000.0) * 1000)


def estimate_jockey_pump_price_rub(segment: PriceSegment) -> int:
    """Жокей-насос (Wilo MHIE 203 / Grundfos CRE 3) для поддержания давления.

    Малый, многоступенчатый, ~1.1 кВт.
    """
    return {"budget": 80_000, "mid": 160_000, "premium": 320_000}[segment]


def estimate_fire_kit_price(
    P_kW: float,
    Q_m3h: float,
    discharge_DN_mm: float | None,
    segment: PriceSegment,
    n_pumps: int = 2,  # 1 раб + 1 рез ОБЯЗАТЕЛЬНО (СП 10.13130 п.6.2)
    explicit_pump_price_rub: int | None = None,
    ex_required: bool = False,
) -> tuple[PriceBreakdown, str]:
    """Оценка цены пожарной насосной (СП 10.13130).

    Возвращает PriceBreakdown с **широким диапазоном** через total_low/high
    (±35% от total_rub) — точные параметры зависят от категории помещения,
    типа спринклеров, нормативного Q пожара (одну сделку нельзя обобщать).

    confidence ВСЕГДА low — пожарная требует индивидуального проектирования.

    Состав:
      - 2 насоса горизонтальные (Wilo BL, КМ, КАМА) — pump_rub
      - Жокей-насос + мини-гидробак — atm_rub (часть)
      - Пожарный гидробак 100-500 л + рама + датчики — atm_rub
      - PN16 задвижки + обратные клапаны — valve_rub, check_valve_rub
      - ШУ Sf с резервированием — cabinet_rub
      - Без корпуса/направляющих/цепей/поплавков (это сухоустановленные)
    """
    has_explicit_pump = bool(explicit_pump_price_rub and explicit_pump_price_rub > 0)

    # Цена насоса. ATEX-наценка +40% если ex_required
    pump_unit = estimate_pump_price_rub(P_kW, segment, explicit_price_rub=explicit_pump_price_rub)
    if ex_required and not has_explicit_pump:
        pump_unit = int(pump_unit * 1.4)
    pump_total = pump_unit * n_pumps

    # PN16 арматура
    fittings = catalog._load_fittings()
    obvyazka = fittings.get("kns_obvyazka_template", {}).get("items", [])
    dn = round_to_dn(discharge_DN_mm)

    valve_rub = 0
    check_valve_rub = 0
    hits_from_db = 0
    total_db_lookups = 0
    for item in obvyazka:
        pos = item.get("position")
        if pos == 3:  # Задвижка
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                # 2 задвижки на каждый насос × PN16
                valve_rub = int(price * n_pumps * 2 * PN16_MULTIPLIER)
        elif pos == 4:  # Обратный клапан
            total_db_lookups += 1
            price = _price_for_dn(item.get("price_examples_rub_2026", {}), dn)
            if price:
                hits_from_db += 1
                check_valve_rub = int(price * n_pumps * PN16_MULTIPLIER)

    # ШУ пожарный
    cabinet_rub = estimate_fire_cabinet_price_rub(P_kW, segment)

    # Жокей + гидробак + рама + 2 датчика давления
    jockey_rub = estimate_jockey_pump_price_rub(segment)
    fire_tank_rub = {"budget": 35_000, "mid": 65_000, "premium": 120_000}[segment]
    frame_rub = {"budget": 40_000, "mid": 70_000, "premium": 110_000}[segment]
    pressure_sensors_rub = 12_000 * 2  # промышленные датчики 4-20 мА с поверкой
    atm_rub = jockey_rub + fire_tank_rub + frame_rub + pressure_sensors_rub

    total = pump_total + atm_rub + valve_rub + check_valve_rub + cabinet_rub

    # Пожарка — confidence ВСЕГДА low (нельзя обобщать одну сделку)
    confidence = "low"
    if has_explicit_pump and total_db_lookups > 0 and hits_from_db / total_db_lookups >= 0.66:
        # Даже с explicit ценой и БД-арматурой — максимум medium
        confidence = "medium"

    breakdown = PriceBreakdown(
        pump_rub=pump_total,
        atm_rub=atm_rub,  # жокей+бак+рама+датчики
        valve_rub=valve_rub,
        check_valve_rub=check_valve_rub,
        rails_rub=0,
        cabinet_rub=cabinet_rub,
        floats_rub=0,
        chain_rub=0,
        corpus_rub=0,
        total_rub=total,
        # Phase 11: широкий диапазон ±35% (пожарная СПД индивидуальна)
        total_low_rub=int(total * 0.65),
        total_high_rub=int(total * 1.35),
    )
    return breakdown, confidence
