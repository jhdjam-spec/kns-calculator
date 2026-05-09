"""Генерация PDF-расчётной записки.

Использует reportlab (уже в зависимостях через handoff/_pdf_base).
Структура — 5 секций по образцу docx-шаблона из reference_kns_calculation_template_docx.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from pydantic import BaseModel, Field


class CalculationReportInput(BaseModel):
    """Входные данные для расчётной записки."""

    project_name: str = Field(description="Название проекта")
    project_code: str = Field(default="", description="Шифр проекта")
    customer: str = Field(default="", description="Заказчик")
    object_address: str = Field(default="", description="Адрес объекта")

    # Исходные данные
    inputs_summary: dict[str, Any] = Field(default_factory=dict, description="Опросный лист")

    # Результаты по этапам
    hydraulics: dict[str, Any] = Field(default_factory=dict)
    electrical: dict[str, Any] = Field(default_factory=dict)
    fire_water: dict[str, Any] = Field(default_factory=dict)
    water_supply: dict[str, Any] = Field(default_factory=dict)
    climate: dict[str, Any] = Field(default_factory=dict)
    structural: dict[str, Any] = Field(default_factory=dict)
    los: dict[str, Any] = Field(default_factory=dict)

    # Спецификация
    bom: list[dict] = Field(default_factory=list)

    # Ссылки на нормативы
    references: list[dict] = Field(default_factory=list)

    # Q-H график рабочего насоса (опционально, Phase 28)
    pump_for_chart: dict | None = Field(
        default=None,
        description=(
            "Запись насоса из pumps.json (с envelope, опц. qh_curve) для "
            "генерации Q-H графика в секции 3. Требуется duty_Q_m3h и duty_H_m."
        ),
    )
    duty_Q_m3h: float | None = None
    duty_H_m: float | None = None

    # Цитаты из энциклопедии (Phase 28: обоснования)
    encyclopedia_citations: list[dict] = Field(
        default_factory=list,
        description=(
            "Список словарей {topic, section, text} из encyclopedia/*.md "
            "для вставки в секцию 'Методика' с прямыми цитатами."
        ),
    )


def generate_calculation_report_pdf(inputs: CalculationReportInput) -> bytes:
    """Генерирует PDF-расчётную записку.

    Возвращает bytes (для отдачи через FastAPI Response).
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

    # Регистрация русского шрифта (используем тот же что в handoff)
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
        title=f"Расчётная записка — {inputs.project_name}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="RuTitle",
        fontName=font_name,
        fontSize=18,
        spaceAfter=12,
        alignment=1,  # center
        textColor=colors.HexColor("#1F2937"),
    ))
    styles.add(ParagraphStyle(
        name="RuH1",
        fontName=font_name,
        fontSize=14,
        spaceAfter=8,
        spaceBefore=16,
        textColor=colors.HexColor("#1F2937"),
    ))
    styles.add(ParagraphStyle(
        name="RuH2",
        fontName=font_name,
        fontSize=12,
        spaceAfter=6,
        spaceBefore=10,
        textColor=colors.HexColor("#374151"),
    ))
    styles.add(ParagraphStyle(
        name="RuBody",
        fontName=font_name,
        fontSize=10,
        spaceAfter=4,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        name="RuMono",
        fontName=font_name,
        fontSize=9,
        spaceAfter=3,
        leading=11,
    ))

    story = []

    # ─── Титул ─────────────────────────────────────────────────────────
    story.append(Paragraph("РАСЧЁТНАЯ ЗАПИСКА", styles["RuTitle"]))
    story.append(Paragraph(inputs.project_name, styles["RuH1"]))
    if inputs.project_code:
        story.append(Paragraph(f"Шифр: {inputs.project_code}", styles["RuBody"]))
    if inputs.customer:
        story.append(Paragraph(f"Заказчик: {inputs.customer}", styles["RuBody"]))
    if inputs.object_address:
        story.append(Paragraph(f"Адрес: {inputs.object_address}", styles["RuBody"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Подготовлено: kns-calculator (бета-версия) · INSERVO Studio · K.M. © 2026",
        styles["RuMono"],
    ))
    story.append(PageBreak())

    # ─── 1. Опросный лист ──────────────────────────────────────────────
    story.append(Paragraph("1. ОПРОСНЫЙ ЛИСТ (ИСХОДНЫЕ ДАННЫЕ)", styles["RuH1"]))
    if inputs.inputs_summary:
        rows = [["Параметр", "Значение"]]
        for k, v in inputs.inputs_summary.items():
            rows.append([str(k), str(v)])
        t = Table(rows, colWidths=[8 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # ─── 2. Методика ───────────────────────────────────────────────────
    story.append(Paragraph("2. МЕТОДИКА РАСЧЁТА", styles["RuH1"]))
    story.append(Paragraph(
        "Расчёт выполнен на основании следующих нормативных документов:", styles["RuBody"]))
    if inputs.references:
        for ref in inputs.references:
            url = ref.get("url") or ref.get("url_official") or ""
            if url:
                line = (
                    f'— <a href="{url}" color="blue">'
                    f'{ref.get("regulation_code", "")} {ref.get("section", "")}'
                    f'</a>: {ref.get("purpose", "")}'
                )
            else:
                line = f"— {ref.get('regulation_code', '')} {ref.get('section', '')}: {ref.get('purpose', '')}"
            story.append(Paragraph(line, styles["RuMono"]))
    story.append(Spacer(1, 0.3 * cm))

    # Цитаты из энциклопедии (Phase 28: обоснования)
    if inputs.encyclopedia_citations:
        story.append(Paragraph("Обоснование расчётных подходов:", styles["RuH2"]))
        for cit in inputs.encyclopedia_citations:
            topic = cit.get("topic", "")
            section = cit.get("section", "")
            text = cit.get("text", "")
            header = f"<b>{topic}</b>"
            if section:
                header += f" / {section}"
            story.append(Paragraph(header, styles["RuMono"]))
            story.append(Paragraph(text, styles["RuBody"]))
            story.append(Spacer(1, 0.15 * cm))
        story.append(Spacer(1, 0.3 * cm))

    # ─── 3. Результаты ─────────────────────────────────────────────────
    story.append(Paragraph("3. РЕЗУЛЬТАТЫ РАСЧЁТА", styles["RuH1"]))

    sections = [
        ("3.1. Гидравлика", inputs.hydraulics),
        ("3.2. Электрика", inputs.electrical),
        ("3.3. Пожарное водоснабжение", inputs.fire_water),
        ("3.4. Хозпитьевое водопотребление", inputs.water_supply),
        ("3.5. Климатические нагрузки", inputs.climate),
        ("3.6. Прочностные расчёты", inputs.structural),
        ("3.7. Локальные очистные сооружения", inputs.los),
    ]
    for title, data in sections:
        if not data:
            continue
        story.append(Paragraph(title, styles["RuH2"]))
        for k, v in data.items():
            line = f"<b>{k}:</b> {v}"
            story.append(Paragraph(line, styles["RuBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Q-H график рабочего насоса (Phase 28)
    if inputs.pump_for_chart and inputs.duty_Q_m3h is not None and inputs.duty_H_m is not None:
        try:
            from reportlab.platypus import Image as RLImage

            from pump_calculator.reports.qh_chart import render_qh_chart_png
            png = render_qh_chart_png(
                inputs.pump_for_chart,
                duty_Q_m3h=inputs.duty_Q_m3h,
                duty_H_m=inputs.duty_H_m,
                width_inch=6.0,
                height_inch=4.0,
                dpi=100,
            )
            story.append(Paragraph("3.8. Q-H характеристика рабочего насоса", styles["RuH2"]))
            # NB: используем глобальный BytesIO (импортирован в шапке модуля).
            img = RLImage(BytesIO(png), width=15 * cm, height=10 * cm)
            story.append(img)
            story.append(Spacer(1, 0.3 * cm))
        except Exception:  # pragma: no cover
            # Если matplotlib недоступен (lite-deploy) — пропускаем
            pass

    # ─── 4. Спецификация ───────────────────────────────────────────────
    if inputs.bom:
        story.append(PageBreak())
        story.append(Paragraph("4. СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ (BOM)", styles["RuH1"]))
        rows = [["№", "Наименование", "Артикул", "Кол-во", "Цена ₽", "Сумма ₽"]]
        total = 0.0
        for i, item in enumerate(inputs.bom, start=1):
            qty = item.get("quantity", 1)
            price = item.get("price_rub", 0)
            sum_ = qty * price
            total += sum_
            rows.append([
                str(i),
                item.get("name", ""),
                item.get("article", ""),
                str(qty),
                f"{price:,.0f}".replace(",", " "),
                f"{sum_:,.0f}".replace(",", " "),
            ])
        rows.append(["", "", "", "ИТОГО", "", f"{total:,.0f}".replace(",", " ")])
        t = Table(rows, colWidths=[1 * cm, 6 * cm, 3 * cm, 2 * cm, 2.5 * cm, 2.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(t)

    # ─── 5. Выводы ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("5. ВЫВОДЫ И РЕКОМЕНДАЦИИ", styles["RuH1"]))
    story.append(Paragraph(
        "Расчёт выполнен с использованием актуальных редакций нормативных документов "
        "(СП 32.13330.2018+Изм.№4, СП 8.13130.2020+Изм.№1, СП 30.13330.2020, СП 31.13330.2021, "
        "СП 131.13330.2020, СП 20.13330.2016, ПУЭ 7-е, ТР ТС 010/012/020). "
        "Допустимое отклонение результатов по сравнению с реальной проектной документацией — ±15% "
        "(оценочная погрешность калькулятора в режиме «бета-версия»).",
        styles["RuBody"],
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "<b>ВНИМАНИЕ:</b> Результаты являются информационными. Перед применением в проекте "
        "обязательна верификация инженером-проектировщиком ВК. "
        "Калькулятор не заменяет ГИП и не является основанием для производства работ.",
        styles["RuBody"],
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "INSERVO Studio · Студия интеграции умных решений Константина Морозова · "
        "https://inservo.ru · K.M. © 2026",
        styles["RuMono"],
    ))

    doc.build(story)
    return buffer.getvalue()
