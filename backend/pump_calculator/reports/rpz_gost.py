"""Расчётно-пояснительная записка (РПЗ) по ГОСТ Р 21.101-2020 + ГОСТ 21.110-2013.

Каноническая структура РПЗ инженера ВК — 13 разделов (по research документации
2026-05-09 и шаблону Серво-Юг):

1. Титульный лист
2. Содержание
3. Введение (исходные данные)
4. Характеристика объекта
5. Расчёт водопотребления (СП 30 А.2)
6. Расчёт расходов сточных вод
7. Гидравлический расчёт сетей
8. Подбор насосного оборудования (Q-H, NPSH, мощность)
9. Расчёт пожарного водоснабжения (СП 8/10.13130)
10. Электротехническая часть (шкаф, кабель, КЗ)
11. Заключение (выводы)
12. Спецификация (BOM по форме 7 ГОСТ 21.110-2013)
13. Список использованных нормативов

Спецификация по форме 7 ГОСТ 21.110-2013 — 8 колонок:
- № п/п
- Наименование
- Тип, марка, обозначение документа
- Код продукции (ОКПД 2)
- Поставщик
- Количество
- Ед. изм.
- Масса, кг
- Примечание
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from pydantic import BaseModel, Field


class RPZSectionData(BaseModel):
    """Данные одной секции РПЗ."""

    title: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    text_blocks: list[str] = Field(default_factory=list)
    formula_refs: list[str] = Field(default_factory=list)


class RPZGostInput(BaseModel):
    """Входные данные для расчётно-пояснительной записки по ГОСТ."""

    # Титул
    project_name: str
    project_code: str = ""
    customer: str = ""
    object_address: str = ""
    designer_organization: str = "INSERVO Studio · Серво-Юг"
    chief_engineer: str = ""
    stage: str = "Р"            # Стадия: П (проект), РД (рабочая), Р (рабочий проект)
    revision: str = "0"         # Изменение

    # Раздел 3-4. Введение и характеристика объекта
    object_description: str = ""
    technical_conditions: str = ""

    # Раздел 5-6. Водопотребление и стоки
    water_demand: dict[str, Any] = Field(default_factory=dict)
    sewage_demand: dict[str, Any] = Field(default_factory=dict)

    # Раздел 7. Гидравлический расчёт
    hydraulics: dict[str, Any] = Field(default_factory=dict)

    # Раздел 8. Насосное оборудование
    pumps: dict[str, Any] = Field(default_factory=dict)

    # Раздел 9. Пожарное водоснабжение
    fire_water: dict[str, Any] = Field(default_factory=dict)

    # Раздел 10. Электротехническая часть
    electrical: dict[str, Any] = Field(default_factory=dict)

    # Раздел 11. Дополнительные расчёты (климат, прочность, ЛОС)
    additional: dict[str, Any] = Field(default_factory=dict)

    # Раздел 12. Спецификация (форма 7 ГОСТ 21.110-2013)
    specification_items: list[dict[str, Any]] = Field(default_factory=list)
    """
    Каждая позиция: {
        'name': str,                # Наименование
        'type': str,                # Тип, марка
        'doc': str,                 # Обозначение документа (ГОСТ/ТУ)
        'okpd': str,                # Код ОКПД 2
        'supplier': str,            # Поставщик
        'quantity': float,
        'units': str,
        'mass_kg': float,
        'note': str,
    }
    """

    # Раздел 13. Нормативы
    references: list[dict[str, str]] = Field(default_factory=list)

    # ──────────────────────────────────────────────────────────────────
    # Раздел 13 Приложения (Phase 28+, P2 расширение 2026-05-11)
    # ──────────────────────────────────────────────────────────────────
    pump_for_chart: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Запись насоса (с envelope, опц. qh_curve) для генерации Q-H графика "
            "в приложении 1. Требуются также duty_Q_m3h и duty_H_m. "
            "Совместимо по полям с CalculationReportInput.pump_for_chart."
        ),
    )
    duty_Q_m3h: float | None = None
    duty_H_m: float | None = None
    encyclopedia_citations: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Цитаты из encyclopedia/*.md в формате {topic, section, text} — "
            "вставляются в приложение 2 как обоснование расчётных подходов."
        ),
    )


def generate_rpz_gost_pdf(inputs: RPZGostInput) -> bytes:
    """Генерация РПЗ по ГОСТ Р 21.101-2020 (13-разделовая структура).

    Использует reportlab. Возвращает bytes готового PDF.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    try:
        from pump_calculator.handoff._pdf_base import get_font_name
        font_name = get_font_name()
    except Exception:
        font_name = "Helvetica"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"РПЗ {inputs.project_code or inputs.project_name}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="GostTitle", fontName=font_name, fontSize=20, alignment=1,
        spaceAfter=18, textColor=colors.HexColor("#1F2937"),
    ))
    styles.add(ParagraphStyle(
        name="GostSubtitle", fontName=font_name, fontSize=14, alignment=1,
        spaceAfter=12, textColor=colors.HexColor("#4B5563"),
    ))
    styles.add(ParagraphStyle(
        name="GostH1", fontName=font_name, fontSize=14, spaceAfter=8, spaceBefore=18,
        textColor=colors.HexColor("#1F2937"),
    ))
    styles.add(ParagraphStyle(
        name="GostH2", fontName=font_name, fontSize=12, spaceAfter=6, spaceBefore=10,
        textColor=colors.HexColor("#374151"),
    ))
    styles.add(ParagraphStyle(
        name="GostBody", fontName=font_name, fontSize=10, spaceAfter=4, leading=13,
    ))
    styles.add(ParagraphStyle(
        name="GostMono", fontName=font_name, fontSize=9, spaceAfter=3, leading=11,
        textColor=colors.HexColor("#6B7280"),
    ))
    styles.add(ParagraphStyle(
        name="GostStamp", fontName=font_name, fontSize=8, alignment=2,
        textColor=colors.HexColor("#9CA3AF"),
    ))

    story = []

    # ════════════════════════════════════════════════════════════════════
    # 1. Титульный лист
    # ════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph(inputs.designer_organization, styles["GostSubtitle"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("РАСЧЁТНО-ПОЯСНИТЕЛЬНАЯ ЗАПИСКА", styles["GostTitle"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(inputs.project_name, styles["GostSubtitle"]))
    if inputs.project_code:
        story.append(Paragraph(
            f"<b>Шифр проекта:</b> {inputs.project_code}", styles["GostBody"]))
    if inputs.customer:
        story.append(Paragraph(
            f"<b>Заказчик:</b> {inputs.customer}", styles["GostBody"]))
    if inputs.object_address:
        story.append(Paragraph(
            f"<b>Адрес объекта:</b> {inputs.object_address}", styles["GostBody"]))
    story.append(Paragraph(
        f"<b>Стадия:</b> {inputs.stage} · <b>Изм.:</b> {inputs.revision}", styles["GostBody"]))
    if inputs.chief_engineer:
        story.append(Spacer(1, 1.5 * cm))
        story.append(Paragraph(
            f"<b>Главный инженер проекта (ГИП):</b> {inputs.chief_engineer}",
            styles["GostBody"]))

    # Подпись внизу страницы
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph(
        "Подготовлено в kns-calculator (бета-версия) · K.M. © 2026 · "
        "https://inservo.ru",
        styles["GostStamp"],
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════
    # 2. Содержание
    # ════════════════════════════════════════════════════════════════════
    story.append(Paragraph("СОДЕРЖАНИЕ", styles["GostH1"]))
    toc_items = [
        ("1.", "Введение и общие положения", "3"),
        ("2.", "Характеристика объекта проектирования", "4"),
        ("3.", "Расчёт водопотребления", "5"),
        ("4.", "Расчёт расходов сточных вод", "6"),
        ("5.", "Гидравлический расчёт сетей", "7"),
        ("6.", "Подбор насосного оборудования", "8"),
        ("7.", "Расчёт пожарного водоснабжения", "10"),
        ("8.", "Электротехническая часть", "11"),
        ("9.", "Дополнительные расчёты", "12"),
        ("10.", "Заключение", "13"),
        ("11.", "Спецификация оборудования (BOM)", "14"),
        ("12.", "Список использованных нормативов", "16"),
        ("13.", "Приложения (Q-H, обоснования)", "17"),
    ]
    rows = [["№", "Раздел", "Стр."]] + [list(item) for item in toc_items]
    t = Table(rows, colWidths=[1.2 * cm, 12.8 * cm, 2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════
    # 3. Введение
    # ════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. ВВЕДЕНИЕ И ОБЩИЕ ПОЛОЖЕНИЯ", styles["GostH1"]))
    story.append(Paragraph(
        "Настоящая расчётно-пояснительная записка (РПЗ) разработана в соответствии "
        "с требованиями ГОСТ Р 21.101-2020 «Система проектной документации для "
        "строительства (СПДС). Основные требования к рабочей документации» и "
        "Постановлением Правительства РФ № 87 от 16.02.2008 «О составе разделов "
        "проектной документации и требованиях к их содержанию».",
        styles["GostBody"],
    ))
    if inputs.object_description:
        story.append(Paragraph(inputs.object_description, styles["GostBody"]))
    story.append(Spacer(1, 0.3 * cm))

    # ════════════════════════════════════════════════════════════════════
    # 4. Характеристика объекта
    # ════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. ХАРАКТЕРИСТИКА ОБЪЕКТА ПРОЕКТИРОВАНИЯ", styles["GostH1"]))
    if inputs.technical_conditions:
        story.append(Paragraph("<b>Технические условия (ТУ):</b>", styles["GostH2"]))
        story.append(Paragraph(inputs.technical_conditions, styles["GostBody"]))
    story.append(Spacer(1, 0.3 * cm))

    # ════════════════════════════════════════════════════════════════════
    # 5-9. Расчёты
    # ════════════════════════════════════════════════════════════════════
    sections = [
        ("3. РАСЧЁТ ВОДОПОТРЕБЛЕНИЯ", inputs.water_demand,
         "Выполнен по СП 30.13330.2020 прил. А.2 (нормы потребления) "
         "и α-методу СП 30.13330.2020 §5.4."),
        ("4. РАСЧЁТ РАСХОДОВ СТОЧНЫХ ВОД", inputs.sewage_demand,
         "Выполнен по СП 32.13330.2018 §6 (метод предельных интенсивностей)."),
        ("5. ГИДРАВЛИЧЕСКИЙ РАСЧЁТ СЕТЕЙ", inputs.hydraulics,
         "Выполнен по ГОСТ Р 56541-2015 + СП 31.13330.2021 §11. "
         "Потери Дарси-Вейсбаха, λ Swamee-Jain, шероховатости по СП 32 §6.5."),
        ("6. ПОДБОР НАСОСНОГО ОБОРУДОВАНИЯ", inputs.pumps,
         "Подбор по ГОСТ 6134-2007 (ISO 9906:2012). "
         "Проверка попадания в зоны AOR/POR (ANSI/HI), NPSH-запас ≥0.5 м."),
        ("7. РАСЧЁТ ПОЖАРНОГО ВОДОСНАБЖЕНИЯ", inputs.fire_water,
         "Выполнен по СП 8.13130.2020 (наружное) + СП 10.13130.2020 (внутреннее) + "
         "ФЗ-123 (категории зданий)."),
        ("8. ЭЛЕКТРОТЕХНИЧЕСКАЯ ЧАСТЬ", inputs.electrical,
         "Выполнен по ПУЭ 7-е изд., ТР ТС 004/2011, ГОСТ IEC 60034-1-2014."),
        ("9. ДОПОЛНИТЕЛЬНЫЕ РАСЧЁТЫ", inputs.additional,
         "Климатические нагрузки СП 131.13330, прочность СП 20.13330, "
         "сейсмика СП 14.13330 (при необходимости)."),
    ]
    for title, data, methodology in sections:
        story.append(Paragraph(title, styles["GostH1"]))
        story.append(Paragraph(f"<i>{methodology}</i>", styles["GostMono"]))
        story.append(Spacer(1, 0.2 * cm))
        if data:
            for k, v in data.items():
                story.append(Paragraph(
                    f"<b>{k}:</b> {v}",
                    styles["GostBody"],
                ))
        else:
            story.append(Paragraph(
                "<i>Данные раздела не предоставлены — требуется заполнение.</i>",
                styles["GostMono"],
            ))
        story.append(Spacer(1, 0.3 * cm))

    # ════════════════════════════════════════════════════════════════════
    # 10. Заключение
    # ════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("10. ЗАКЛЮЧЕНИЕ", styles["GostH1"]))
    story.append(Paragraph(
        "Расчёт выполнен в соответствии с действующими редакциями нормативных "
        "документов на 2026 г. Допустимое отклонение результатов калькулятора "
        "от паспортного расчёта инженера-проектировщика — ±15% (бета-версия).",
        styles["GostBody"],
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "<b>ВНИМАНИЕ:</b> Результаты являются информационным ориентиром для "
        "тендера, ТЭО или коммерческого предложения. Для финального проекта, "
        "защиты в экспертизе (ст. 49 ГрК РФ) и производства работ обязательна "
        "верификация инженером-проектировщиком ВК с правом постановки печати.",
        styles["GostBody"],
    ))

    # ════════════════════════════════════════════════════════════════════
    # 11. Спецификация по форме 7 ГОСТ 21.110-2013
    # ════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph(
        "11. СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ (BOM)",
        styles["GostH1"],
    ))
    story.append(Paragraph(
        "<i>Форма 7 ГОСТ 21.110-2013 «Спецификация оборудования, изделий и материалов».</i>",
        styles["GostMono"],
    ))
    story.append(Spacer(1, 0.2 * cm))

    if inputs.specification_items:
        rows = [[
            "№", "Наименование", "Тип, марка / Док.", "ОКПД 2",
            "Поставщик", "Кол.", "Ед.", "Масса, кг", "Прим.",
        ]]
        total_mass = 0.0
        for i, item in enumerate(inputs.specification_items, start=1):
            qty = item.get("quantity", 1)
            mass = item.get("mass_kg", 0) * qty
            total_mass += mass
            rows.append([
                str(i),
                item.get("name", ""),
                f"{item.get('type', '')}\n{item.get('doc', '')}".strip(),
                item.get("okpd", ""),
                item.get("supplier", ""),
                str(qty),
                item.get("units", "шт"),
                f"{mass:.1f}" if mass else "—",
                item.get("note", ""),
            ])
        rows.append(["", "", "", "", "", "", "ИТОГО, кг", f"{total_mass:.1f}", ""])

        t = Table(rows, colWidths=[
            0.8 * cm, 4 * cm, 3 * cm, 1.8 * cm,
            2.2 * cm, 1 * cm, 1 * cm, 1.5 * cm, 2 * cm,
        ])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (5, 1), (7, -1), "RIGHT"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph(
            "<i>Спецификация не сформирована — заполните раздел в калькуляторе.</i>",
            styles["GostMono"],
        ))

    # ════════════════════════════════════════════════════════════════════
    # 12. Нормативы
    # ════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph(
        "12. СПИСОК ИСПОЛЬЗОВАННЫХ НОРМАТИВНЫХ ДОКУМЕНТОВ",
        styles["GostH1"],
    ))
    if inputs.references:
        for i, ref in enumerate(inputs.references, start=1):
            line = (
                f"{i}. <b>{ref.get('regulation_code', '')}</b> "
                f"{ref.get('section', '')} — {ref.get('purpose', '')}"
            )
            story.append(Paragraph(line, styles["GostBody"]))
    else:
        story.append(Paragraph(
            "<i>Список нормативов не предоставлен.</i>", styles["GostMono"],
        ))

    # ════════════════════════════════════════════════════════════════════
    # 13. Приложения (Phase 28+ / P2 2026-05-11)
    # ════════════════════════════════════════════════════════════════════
    has_chart = (
        inputs.pump_for_chart
        and inputs.duty_Q_m3h is not None
        and inputs.duty_H_m is not None
    )
    has_citations = bool(inputs.encyclopedia_citations)
    if has_chart or has_citations:
        story.append(PageBreak())
        story.append(Paragraph(
            "13. ПРИЛОЖЕНИЯ",
            styles["GostH1"],
        ))
        story.append(Paragraph(
            "<i>Графические материалы, обоснования расчётных подходов и "
            "выписки из нормативов в виде цитат с гиперссылками на источники.</i>",
            styles["GostMono"],
        ))
        story.append(Spacer(1, 0.3 * cm))

    if has_chart:
        story.append(Paragraph(
            "Приложение 1. Q-H характеристика рабочего насоса",
            styles["GostH2"],
        ))
        try:
            from reportlab.platypus import Image as RLImage

            from pump_calculator.reports.qh_chart import render_qh_chart_png
            png = render_qh_chart_png(
                inputs.pump_for_chart,  # type: ignore[arg-type]
                duty_Q_m3h=float(inputs.duty_Q_m3h),  # type: ignore[arg-type]
                duty_H_m=float(inputs.duty_H_m),  # type: ignore[arg-type]
                width_inch=6.0,
                height_inch=4.0,
                dpi=100,
            )
            img = RLImage(BytesIO(png), width=15 * cm, height=10 * cm)
            story.append(img)
            story.append(Paragraph(
                "<i>Зона AOR (Allowable Operating Range) ±15% от Q_BEP — по ANSI/HI 9.6.3-2017. "
                "Зона POR (Preferred Operating Range) ±10% — рекомендуемая по ANSI/HI 14.3.</i>",
                styles["GostMono"],
            ))
            story.append(Spacer(1, 0.3 * cm))
        except Exception:  # pragma: no cover
            story.append(Paragraph(
                "<i>Q-H график недоступен (matplotlib не установлен в lite-deploy).</i>",
                styles["GostMono"],
            ))

    if has_citations:
        story.append(Paragraph(
            "Приложение 2. Обоснование расчётных подходов",
            styles["GostH2"],
        ))
        for cit in inputs.encyclopedia_citations:
            topic = cit.get("topic", "")
            section = cit.get("section", "")
            text = cit.get("text", "")
            header = f"<b>{topic}</b>"
            if section:
                header += f" / {section}"
            story.append(Paragraph(header, styles["GostMono"]))
            story.append(Paragraph(text, styles["GostBody"]))
            story.append(Spacer(1, 0.15 * cm))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "INSERVO Studio · Студия интеграции умных решений Константина Морозова · "
        "https://inservo.ru · K.M. © 2026 · MIT licence",
        styles["GostStamp"],
    ))

    doc.build(story)
    return buffer.getvalue()


# ════════════════════════════════════════════════════════════════════════
# Convenience builder (P2 2026-05-11):
# build_rpz_gost_pdf(L0, L1, computed, result, output_path=None) -> bytes
# ════════════════════════════════════════════════════════════════════════

def build_rpz_gost_pdf(
    L0: Any,
    L1: Any | None,
    computed: Any,
    result: Any,
    output_path: str | None = None,
    *,
    project_name: str = "КНС — подбор оборудования",
    project_code: str = "",
    customer: str = "",
    object_address: str = "",
    chief_engineer: str = "",
    citations_topics: list[tuple[str, str]] | None = None,
) -> bytes:
    """Builder: собрать РПЗ ГОСТ напрямую из доменных объектов калькулятора.

    Args:
        L0, L1: входы (`pump_calculator.schemas.L0Input`, `L1Input | None`)
        computed: `ComputedHydraulics` (результат `hydraulics.compute_hydraulics`)
        result: `SelectionResult` (результат `matching.select_pumps`)
        output_path: если задан — сохранить PDF на диск (для удобства CLI/тестов)
        project_name, project_code, customer, object_address, chief_engineer:
            метаданные титульного листа (по умолчанию — заглушки беты)
        citations_topics: список пар (topic_key, section_anchor) для
            подмешивания цитат из encyclopedia/registry. Default — гидравлика +
            энергоэффективность.

    Returns:
        bytes готового PDF (всегда возвращается; output_path — опциональный sink).
    """
    # 1. Водопотребление / стоки — берём минимум из L0
    sewage_demand = {
        "Q расчётный, м³/ч": L0.Q_m3h,
        "Тип стоков": getattr(L0, "wastewater_type", None) or "domestic",
        "L напорной трассы, м": L0.L_m if L0.L_m is not None else "default 50",
        "Геометрический dH, м": L0.dH_m if L0.dH_m is not None else "default 5",
    }

    # 2. Гидравлический расчёт — раскладываем computed
    hydraulics_data = {
        "D трубы (DN), мм": f"{computed.D_mm:.0f}",
        "v скорость, м/с": f"{computed.v_ms:.2f}",
        "Re число Рейнольдса": f"{computed.Re:.0f}",
        "λ Дарси-Альтшуль": f"{computed.friction_factor:.4f}",
        "H_тр потери по длине, м": f"{computed.H_tr_m:.2f}",
        "Σζ местные сопротивления": f"{computed.sum_zeta:.2f}",
        "H_м потери местные, м": f"{computed.H_m_m:.2f}",
        "H полный (с запасом), м": f"{computed.H_full_m:.2f}",
        "Запас (safety factor)": f"×{computed.safety_factor:.2f}",
    }
    if computed.npsha_m is not None:
        hydraulics_data["NPSHa расчётный, м"] = f"{computed.npsha_m:.2f}"
    if computed.sump_volume_min_m3 is not None:
        hydraulics_data["V_min приёмной камеры, м³"] = (
            f"{computed.sump_volume_min_m3:.2f}"
        )
    hydraulics_data["n_pumps_total"] = computed.n_pumps_total

    # 3. Подбор насосов — 3 сегмента
    segments = result.results
    pumps_data: dict[str, Any] = {}
    spec_items: list[dict[str, Any]] = []
    pump_for_chart: dict[str, Any] | None = None
    for segment_name, label in [
        ("budget", "Эконом"), ("mid", "Стандарт"), ("premium", "Премиум"),
    ]:
        p = getattr(segments, segment_name, None)
        if not p:
            continue
        pumps_data[f"{label} — модель"] = f"{p.brand} {p.model}"
        pumps_data[f"{label} — P, кВт"] = p.P_kW
        pumps_data[f"{label} — AOR/POR"] = p.aor_zone or "n/a"
        pumps_data[f"{label} — цена, ₽"] = f"{p.price_estimate_rub:,}".replace(",", " ")
        # BOM: насос — одна позиция
        spec_items.append({
            "name": "Насос (рабочий + резерв)",
            "type": f"{p.brand} {p.model}",
            "doc": "ГОСТ 6134-2007",
            "okpd": "28.13.14.140",
            "supplier": p.brand,
            "quantity": computed.n_pumps_total,
            "units": "шт",
            "mass_kg": 0,  # неизвестно из PumpResult — заполняется в L1
            "note": f"сегмент {label}, AOR={p.aor_zone or '—'}",
        })
        # Берём первый доступный насос для Q-H графика (предпочтение mid → premium → budget)
        if pump_for_chart is None or segment_name == "mid":
            pump_for_chart = p.model_dump() if hasattr(p, "model_dump") else dict(p)

    # 4. Корпус (если есть в result)
    corpus = getattr(result, "corpus_size", None)
    if corpus is not None:
        spec_items.append({
            "name": "Корпус КНС",
            "type": f"Ø{corpus.diameter_mm:.0f}×{corpus.height_mm:.0f} мм",
            "doc": "ТУ 22.21.21-001-2024",
            "okpd": "22.21.21.000",
            "supplier": "BloPlast / СПД",
            "quantity": 1,
            "units": "шт",
            "mass_kg": corpus.weight_estimate_kg or 0,
            "note": f"DN вход {corpus.inlet_DN_mm}, выход {corpus.outlet_DN_mm}",
        })

    # 5. Нормативы — из result.warnings/trigger_reasons по топикам энциклопедии
    references = [
        {"regulation_code": "СП 32.13330.2018", "section": "§6",
         "purpose": "Канализация наружная — параметры приёмных камер, насосы"},
        {"regulation_code": "СП 31.13330.2021", "section": "§11",
         "purpose": "Водоснабжение — гидравлический расчёт напорных линий"},
        {"regulation_code": "ГОСТ 6134-2007", "section": "общ.",
         "purpose": "Насосы динамические — методика подбора и испытаний (ISO 9906)"},
        {"regulation_code": "ГОСТ Р 21.101-2020", "section": "общ.",
         "purpose": "СПДС — основные требования к рабочей документации"},
        {"regulation_code": "ПУЭ 7-е изд.", "section": "гл.7.3",
         "purpose": "Электрооборудование во взрывоопасных зонах"},
    ]

    # 6. Цитаты из энциклопедии (Phase 28: обоснования)
    citations: list[dict[str, str]] = []
    if citations_topics is None:
        citations_topics = [
            ("hydraulics", "Уравнение неразрывности"),
            ("hydraulics", "Закон Дарси-Вейсбаха"),
        ]
    try:
        from pump_calculator.encyclopedia.registry import build_pdf_citation
        for topic_key, anchor in citations_topics:
            cit = build_pdf_citation(topic_key, anchor, max_chars=500)
            if cit:
                citations.append(cit)
    except Exception:  # pragma: no cover
        pass

    inputs = RPZGostInput(
        project_name=project_name,
        project_code=project_code,
        customer=customer,
        object_address=object_address,
        chief_engineer=chief_engineer,
        object_description=(
            result.summary_text
            or "Канализационная насосная станция (КНС) по результатам подбора."
        ),
        technical_conditions=(
            "ТУ выдаются заказчиком отдельно. "
            "Категория надёжности — по СП 32.13330 §6.2 (мин. 1 раб + 1 рез)."
        ),
        sewage_demand=sewage_demand,
        hydraulics=hydraulics_data,
        pumps=pumps_data,
        electrical={
            "n_pumps_total": computed.n_pumps_total,
            "Ex_required": bool(getattr(L1, "Ex_required", False)) if L1 else False,
        },
        additional={
            "completeness_pct": result.completeness_pct,
            "candidates_total": result.candidates_total,
            "engineer_handoff_required": result.engineer_handoff_required,
        },
        specification_items=spec_items,
        references=references,
        # Приложение 1
        pump_for_chart=pump_for_chart,
        duty_Q_m3h=L0.Q_m3h,
        duty_H_m=computed.H_full_m,
        # Приложение 2
        encyclopedia_citations=citations,
    )

    pdf_bytes = generate_rpz_gost_pdf(inputs)
    if output_path:
        from pathlib import Path
        Path(output_path).write_bytes(pdf_bytes)
    return pdf_bytes
