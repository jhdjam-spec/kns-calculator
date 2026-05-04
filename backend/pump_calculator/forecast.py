"""Phase 9: прогноз диапазона цены и человекочитаемая сводка результата.

Логика: чем меньше входных данных задано — тем шире диапазон цены и тем
осторожнее формулировка. При полном вводе (L0 + ключевые L1-параметры)
диапазон сужается до ±5-10%, при минимальном (только Q) — расширяется
до ±25-35%.

Используется в `matching.select_pumps` для финального обогащения
SelectionResult полями `completeness_pct`, `summary_text`, и для каждого
PumpResult.price_breakdown — `total_low_rub` / `total_high_rub`.
"""

from __future__ import annotations

from pump_calculator.schemas import (
    L0Input,
    L1Input,
    PumpResult,
    SelectionResultsBySegment,
)


def calculate_completeness_pct(L0: L0Input, L1: L1Input | None) -> int:
    """Оценка полноты входных данных в процентах.

    L0 (4 поля × 15% = 60%):
      - Q_m3h (обязателен — всегда даёт 15%)
      - dH_m (15%)
      - L_m (15%)
      - wastewater_type (15%)

    L1 (8 опциональных полей × 5% = 40%):
      - pipe_material, pipe_D_mm, n_bends, n_valves, redundancy,
        Ex_required, reliability_category, liquid_temp_c
        (corpus_material не считается — он не влияет на надёжность подбора)

    Возвращает 0-100. 100 = всё задано (можно делать точную смету).
    """
    pct = 0
    # L0
    pct += 15  # Q_m3h всегда задан (обязателен)
    if L0.dH_m is not None:
        pct += 15
    if L0.L_m is not None:
        pct += 15
    if L0.wastewater_type is not None:
        pct += 15

    # L1 (опционально)
    if L1 is not None:
        if L1.pipe_material is not None:
            pct += 5
        if L1.pipe_D_mm is not None:
            pct += 5
        if L1.n_bends is not None:
            pct += 5
        if L1.n_valves is not None:
            pct += 5
        if L1.redundancy is not None:
            pct += 5
        if L1.Ex_required:  # explicit True (default False считается «не задано»)
            pct += 5
        if L1.reliability_category is not None:
            pct += 5
        if L1.liquid_temp_c is not None:
            pct += 5

    return min(pct, 100)


def calculate_price_range(
    total_rub: int,
    completeness_pct: int,
    confidence: str,
    has_explicit_pump_price: bool,
) -> tuple[int, int]:
    """Диапазон цены total_low / total_high зависит от полноты ввода + confidence.

    Логика:
      - completeness 100% + explicit price + confidence=high → ±3% (точная смета)
      - completeness 70-99% + medium → ±10-15%
      - completeness 40-69% → ±20-25%
      - completeness <40% (только Q) → ±30-35%

    Не уходим в отрицательные значения и округляем до 1000 ₽.
    """
    if total_rub <= 0:
        return 0, 0

    # Базовая ширина диапазона по completeness
    if completeness_pct >= 90:
        spread = 0.05  # ±5% — очень полные данные
    elif completeness_pct >= 70:
        spread = 0.12
    elif completeness_pct >= 50:
        spread = 0.20
    elif completeness_pct >= 30:
        spread = 0.28
    else:
        spread = 0.35  # очень мало данных

    # Корректировка по confidence
    if confidence == "high" and has_explicit_pump_price:
        # Точная цена насоса из БД — сужаем диапазон в 1.5 раза
        spread *= 0.6
    elif confidence == "low":
        # Heuristic — расширяем в 1.3 раза
        spread *= 1.3

    # Минимальный спред 3% (даже идеальный кейс — оценка ±3%)
    spread = max(spread, 0.03)

    low = int(total_rub * (1 - spread))
    high = int(total_rub * (1 + spread))

    # Округление до 1000 ₽
    low = (low // 1000) * 1000
    high = ((high + 999) // 1000) * 1000

    return low, high


def fill_price_ranges(
    results: SelectionResultsBySegment,
    completeness_pct: int,
) -> None:
    """In-place: заполняет total_low_rub / total_high_rub для всех найденных кандидатов."""
    for seg in ("budget", "mid", "premium"):
        pump: PumpResult | None = getattr(results, seg)
        if pump is None or pump.price_estimate_rub <= 0:
            continue

        # Точная цена насоса в БД? — узнаём по pump_rub > 0 и confidence=high
        has_explicit = pump.price_confidence == "high"

        low, high = calculate_price_range(
            total_rub=pump.price_estimate_rub,
            completeness_pct=completeness_pct,
            confidence=pump.price_confidence,
            has_explicit_pump_price=has_explicit,
        )
        pump.price_breakdown.total_low_rub = low
        pump.price_breakdown.total_high_rub = high


def format_rub(value: int) -> str:
    """Форматирование числа в рубли по-русски: 1234567 → '1 234 567'."""
    s = str(abs(value))
    parts = []
    while s:
        parts.insert(0, s[-3:])
        s = s[:-3]
    return ("-" if value < 0 else "") + " ".join(parts)


def format_rub_short(value: int) -> str:
    """Краткое форматирование: 1234567 → '1.2 млн', 421928 → '420 тыс'."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн".replace(".0 ", " ")
    if value >= 1_000:
        # Округление до 10к
        rounded = int(round(value / 10_000) * 10)
        return f"{rounded} тыс"
    return str(value)


def build_summary_text(
    L0: L0Input,
    L1: L1Input | None,
    results: SelectionResultsBySegment,
    completeness_pct: int,
    candidates_total: int,
    handoff_required: bool,
) -> str:
    """Человекочитаемая сводка результата подбора.

    Формирует 2-3 предложения для отображения над карточками результатов:
    1. Что подобрано (диапазон цен)
    2. Уровень уверенности (полнота ввода)
    3. Рекомендация (готов КП или нужен инженер)

    Примеры:
      "Для бытовой канализации Q=21 м³/ч подобрано 3 варианта: от 380 тыс до
       4.4 млн ₽ в зависимости от сегмента. Заполнено 60% параметров — точную
       цену согласует инженер."

      "Подобрана 1 модель в премиум-сегменте по 3.5 млн ₽ (точная цена из
       реального КП поставщика). Можно формировать коммерческое предложение."
    """
    # Найдём минимальную и максимальную цену по всем сегментам
    prices = []
    found_segments = []
    for seg in ("budget", "mid", "premium"):
        p: PumpResult | None = getattr(results, seg)
        if p is not None and p.price_estimate_rub > 0:
            prices.append(p.price_estimate_rub)
            found_segments.append(seg)

    if not prices:
        return (
            f"По вашим параметрам (Q={L0.Q_m3h:g} м³/ч, "
            f"тип = {L0.wastewater_type or 'не указан'}) подходящих насосов в "
            f"базе не найдено. Передайте инженеру для индивидуального подбора."
        )

    # Тип объекта по wastewater_type
    type_human = {
        "domestic": "бытовой канализации",
        "drainage": "дождевой канализации/дренажа",
        "industrial": "промышленных стоков",
        "clean_water": "повышения давления (СПД)",
    }.get(L0.wastewater_type or "domestic", "канализации")

    # Часть 1: что подобрано
    n_found = len(found_segments)
    if n_found == 1:
        part1 = (
            f"Для {type_human} Q={L0.Q_m3h:g} м³/ч подобрана 1 модель в "
            f"{_segment_ru(found_segments[0])}-сегменте — около "
            f"{format_rub_short(prices[0])} ₽."
        )
    else:
        part1 = (
            f"Для {type_human} Q={L0.Q_m3h:g} м³/ч подобрано {n_found} "
            f"варианта: от {format_rub_short(min(prices))} до "
            f"{format_rub_short(max(prices))} ₽ в зависимости от сегмента."
        )

    # Часть 2: уровень уверенности
    if completeness_pct >= 80:
        part2 = "Параметры заполнены детально — оценка цены точная."
    elif completeness_pct >= 50:
        part2 = (
            f"Заполнено {completeness_pct}% параметров — оценка ориентировочная, "
            f"точную цену согласует инженер."
        )
    else:
        part2 = (
            f"Минимум данных ({completeness_pct}% параметров) — диапазон цен широкий, "
            f"для точной сметы нужны: глубина приёмной камеры, материал труб, категория надёжности."
        )

    # Часть 3: рекомендация
    if handoff_required:
        part3 = "Условия требуют дополнительного расчёта инженером."
    elif candidates_total == 1:
        part3 = "Кандидат единственный — рекомендуем уточнить альтернативы у инженера."
    else:
        part3 = "Можно формировать коммерческое предложение по выбранному варианту."

    return f"{part1} {part2} {part3}"


def _segment_ru(seg: str) -> str:
    return {
        "budget": "бюджетном",
        "mid": "среднем",
        "premium": "премиум",
    }.get(seg, seg)
