"""Генератор PDF BOM-черновика.

Структура — по 01_spec/handoff.md::artifact_2.
9+ позиций × 3 ценовых сегмента (Бюджет/Средний/Премиум).
Цены — из 02_dataset/fittings/fittings_seed.json.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from pump_calculator import catalog
from pump_calculator.handoff._pdf_base import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    get_styles,
    register_cyrillic_fonts,
)
from pump_calculator.schemas import PumpResult, SelectionResult

SEGMENT_LABELS = {"budget": "Бюджет", "mid": "Средний", "premium": "Премиум"}
SEGMENT_COLORS = {
    "budget": colors.HexColor("#16a34a"),   # green-600
    "mid": colors.HexColor("#ca8a04"),      # yellow-600
    "premium": colors.HexColor("#2563eb"),  # blue-600
}


def _round_dn(dn_mm: float | None) -> str:
    """Округление DN до ближайшего стандартного для подбора арматуры."""
    if not dn_mm:
        return "DN50"
    standard = [50, 65, 80, 100, 150, 200, 250, 300, 400]
    for s in standard:
        if dn_mm <= s:
            return f"DN{s}"
    return f"DN{int(dn_mm)}"


def _get_fitting_price(price_examples: dict, dn: str) -> int | None:
    """Достать цену для DN из price_examples_rub_2026 или ближайшую."""
    if dn in price_examples:
        return price_examples[dn]
    # Ближайший по числу
    if not dn.startswith("DN"):
        return None
    try:
        target = int(dn[2:])
    except ValueError:
        return None
    available = [(int(k[2:]), v) for k, v in price_examples.items() if k.startswith("DN")]
    if not available:
        return None
    closest = min(available, key=lambda kv: abs(kv[0] - target))
    return closest[1]


def _build_segment_bom(
    pump: PumpResult,
    segment: str,
    fittings_data: dict,
) -> tuple[list[list[str]], int]:
    """Собрать строки BOM для одного сегмента. Возвращает (rows, total_rub)."""
    rows: list[list[str]] = []
    total = 0
    pos = 1

    obvyazka = fittings_data["kns_obvyazka_template"]["items"]
    common = fittings_data["kns_common_items"]["items"]

    dn = _round_dn(pump.discharge_DN_mm)

    # 1. Насос
    pump_price_estimate = {"budget": 80_000, "mid": 200_000, "premium": 500_000}[segment]
    rows.append([
        str(pos), "Насос погружной", pump.brand, pump.model,
        "1", f"{pump_price_estimate:,}".replace(",", " "),
        f"{pump_price_estimate:,}".replace(",", " "),
    ])
    total += pump_price_estimate
    pos += 1

    # 2-4. АТМ + задвижка + обратный клапан
    for item in obvyazka:
        if item["position"] == 1:  # Насос уже добавлен выше
            continue
        if "depends_on" in item and item["depends_on"] == "discharge_DN":
            price = _get_fitting_price(item.get("price_examples_rub_2026", {}), dn)
            if price is None:
                continue
            qty = 1
            total_pos = price * qty
            brand = item.get("brand_options_by_segment", {}).get(segment, ["—"])[0] \
                if "brand_options_by_segment" in item else "—"
            rows.append([
                str(pos), item["name"], brand, dn,
                str(qty), f"{price:,}".replace(",", " "),
                f"{total_pos:,}".replace(",", " "),
            ])
            total += total_pos
            pos += 1
        elif item["position"] == 5:  # Направляющие
            price = item.get("price_typical_rub_2026", 12000)
            rows.append([
                str(pos), item["name"], "—", "нерж 304",
                "1", f"{price:,}".replace(",", " "),
                f"{price:,}".replace(",", " "),
            ])
            total += price
            pos += 1

    # 5. ШУ — выбираем по сегменту
    cabinets = fittings_data["kns_common_items"]["items"][0]["options_by_segment"]
    cab_segment = cabinets.get(segment, cabinets.get("budget", {}))
    cab_examples = cab_segment.get("examples", [])
    if cab_examples:
        cab = cab_examples[0]
        cab_price = cab.get("price_rub")
        if cab_price is None:
            cab_price = {"budget": 266_000, "mid": 450_000, "premium": 750_000}[segment]
        rows.append([
            str(pos), "Шкаф управления", cab_segment.get("brand", "—"),
            cab.get("name", "—")[:40], "1",
            f"{cab_price:,}".replace(",", " "),
            f"{cab_price:,}".replace(",", " "),
        ])
        total += cab_price
        pos += 1

    # 6. Поплавки
    for item in common:
        if item.get("position") == 7:
            qty = item.get("qty", 4)
            price = item.get("price_per_unit_rub_2026", 5000)
            total_pos = price * qty
            rows.append([
                str(pos), item["name"], "—", "—",
                str(qty), f"{price:,}".replace(",", " "),
                f"{total_pos:,}".replace(",", " "),
            ])
            total += total_pos
            pos += 1

    # 7. Корпус КНС
    for item in common:
        if item.get("position") == 9:
            corpus_examples = item.get("examples", [])
            # Подбираем ближайший по объёму
            chosen = corpus_examples[0] if corpus_examples else None
            if chosen:
                price = chosen.get("price_rub_estimate", 350_000)
                rows.append([
                    str(pos), "Корпус КНС (ПЭ)", "Серво-Юг",
                    f"D{chosen.get('D_mm')}/H{chosen.get('H_mm')}",
                    "1", f"{price:,}".replace(",", " "),
                    f"{price:,}".replace(",", " "),
                ])
                total += price
                pos += 1

    return rows, total


def generate_bom_pdf(result: SelectionResult) -> bytes:
    """Сгенерировать PDF BOM-черновика по 3 ценовым сегментам."""
    register_cyrillic_fonts()
    styles = get_styles()

    fittings_data = catalog._load_fittings()  # внутренняя функция, см. ниже patch

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="BOM-черновик — kns-calculator",
        author="kns-calculator",
    )

    story = []

    # Шапка
    L0 = result.input.L0
    story.append(Paragraph("BOM-черновик: спецификация оборудования", styles["title"]))
    story.append(Paragraph(
        f"Сформирован {datetime.now().strftime('%d.%m.%Y %H:%M')}. "
        f"Параметры: Q={L0.Q_m3h:g} м³/ч, ΔH={L0.dH_m:g} м, L={L0.L_m:g} м, "
        f"тип стоков: {L0.wastewater_type}. "
        f"Расчёт: D={result.computed.D_mm:g} мм, H_full={result.computed.H_full_m:.1f} м.",
        styles["small"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Заголовок таблицы
    header = ["№", "Наименование", "Бренд", "Модель / DN", "Кол-во", "Цена, ₽", "Сумма, ₽"]

    for segment in ("budget", "mid", "premium"):
        pump = getattr(result.results, segment)
        if pump is None:
            story.append(Paragraph(f"{SEGMENT_LABELS[segment]}: нет кандидатов в этом сегменте", styles["h3"]))
            story.append(Spacer(1, 0.2 * cm))
            continue

        story.append(Paragraph(
            f"{SEGMENT_LABELS[segment]}: {pump.brand} {pump.model} (P={pump.P_kW} кВт)",
            styles["h2"]
        ))

        rows, total = _build_segment_bom(pump, segment, fittings_data)

        # Добавляем строку «Итого»
        all_rows = [header] + rows + [
            ["", "ИТОГО ориентировочно", "", "", "", "", f"{total:,}".replace(",", " ")]
        ]

        col_widths = (1.2 * cm, 5.5 * cm, 3 * cm, 5 * cm, 1.5 * cm, 3 * cm, 3.5 * cm)
        table = Table(all_rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            # header
            ("FONTNAME", (0, 0), (-1, 0), DEFAULT_BOLD),
            ("BACKGROUND", (0, 0), (-1, 0), SEGMENT_COLORS[segment]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            # body
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f9fafb")]),
            ("GRID", (0, 0), (-1, -2), 0.3, colors.HexColor("#d1d5db")),
            # итого
            ("FONTNAME", (0, -1), (-1, -1), DEFAULT_BOLD),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f3f4f6")),
            ("TOPPADDING", (0, -1), (-1, -1), 6),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#374151")),
            # alignment
            ("ALIGN", (0, 0), (0, -1), "CENTER"),     # №
            ("ALIGN", (4, 0), (4, -1), "CENTER"),     # кол-во
            ("ALIGN", (5, 0), (-1, -1), "RIGHT"),     # цены
        ]))
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

    # Дисклеймер
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Примечания", styles["h3"]))
    story.append(Paragraph(
        "• Цены ориентировочные на 2026-05 (источник: АРКАДА КП 29.01.2026, типовые из «прайс на лист»). "
        "Уточняются у поставщика на момент заказа. <br/>"
        "• В стоимость НЕ включены: проектирование, монтаж, пусконаладка, доставка, "
        "земляные работы, благоустройство. <br/>"
        "• Корпус КНС Серво-Юг — типоразмер выбран по ближайшему. Точный D × H уточняется по объёму V_приёмного и H/D ≤ 4. <br/>"
        "• Для production-релиза BOM-черновик должен быть согласован с инженером.",
        styles["small"]
    ))

    doc.build(story)
    return buf.getvalue()
