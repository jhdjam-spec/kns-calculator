"""Генератор PDF опросного листа клиенту.

Структура — по 01_spec/handoff.md::artifact_1 и эталону `характеристики_КНС.png`.
10 секций, ~50 полей с авто-заполнением из L0/L1.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from pump_calculator.handoff._pdf_base import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    get_styles,
    register_cyrillic_fonts,
)
from pump_calculator.schemas import SelectionResult

# Маппинг типов стоков для отображения
WASTEWATER_LABELS = {
    "domestic": "хоз-бытовые",
    "drainage": "дренажные / ливнёвка",
    "industrial": "производственные",
}


def _empty_field_table(rows: list[tuple[str, str]], col_widths: tuple[float, float] = (6 * cm, 11 * cm)) -> Table:
    """Таблица 'label | пустое поле для заполнения' — для опросника."""
    register_cyrillic_fonts()
    data = [[label, value if value else "_________________________________"] for label, value in rows]
    table = Table(data, colWidths=col_widths)
    table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (1, 0), (1, -1), 0.3, colors.HexColor("#d1d5db")),
            # Жирная label-колонка
            ("FONTNAME", (0, 0), (0, -1), DEFAULT_BOLD),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ])
    )
    return table


def generate_questionnaire_pdf(
    result: SelectionResult,
    *,
    object_name: str = "",
    client_company: str = "",
    client_contact: str = "",
    city: str = "",
    kp_number: str = "",
) -> bytes:
    """Сгенерировать PDF опросного листа клиенту.

    Поля шапки (object_name, client_company, ...) — опциональные, если переданы из CRM
    то предзаполняются. Иначе остаются пустыми для ручного заполнения клиентом.
    """
    register_cyrillic_fonts()
    styles = get_styles()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Опросный лист клиенту — kns-calculator",
        author="kns-calculator",
    )

    story = []

    # ---------- Шапка ----------
    story.append(Paragraph("Опросный лист на КНС / НС / СПД", styles["title"]))
    story.append(Paragraph(
        f"Сформирован {datetime.now().strftime('%d.%m.%Y %H:%M')} · "
        f"kns-calculator (open-source, github.com/jhdjam-spec/kns-calculator)",
        styles["small"]
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ---------- Секция 1. Объект ----------
    story.append(Paragraph("1. Объект и заказчик", styles["h2"]))
    story.append(_empty_field_table([
        ("Название объекта", object_name),
        ("Заказчик (компания)", client_company),
        ("Контактное лицо, телефон", client_contact),
        ("Город / регион", city),
        ("№ КП / запроса", kp_number),
        ("Дата заполнения", datetime.now().strftime("%d.%m.%Y")),
    ]))
    story.append(Spacer(1, 0.3 * cm))

    # ---------- Секция 2. Параметры стоков ----------
    L0 = result.input.L0
    story.append(Paragraph("2. Параметры стоков", styles["h2"]))
    story.append(_empty_field_table([
        ("Тип стоков (auto)", WASTEWATER_LABELS.get(L0.wastewater_type, L0.wastewater_type)),
        ("Залповый объём, м³", ""),
        ("Температура жидкости, °C", "15 (default; уточнить если горячие)"),
        ("Плотность стоков, кг/м³", ""),
        ("Абразивность, мг/л", ""),
        ("pH", "6–9 (для domestic; для industrial — обязательно)"),
        ("Включения (волокна, твёрдые)", ""),
    ]))

    # ---------- Секция 3. Расход ----------
    story.append(Paragraph("3. Расход и режим работы", styles["h2"]))
    story.append(_empty_field_table([
        ("Q расчётный, м³/ч (auto)", f"{L0.Q_m3h:g}"),
        ("Q среднесуточный, м³/сут", ""),
        ("Q пиковый часовой, м³/ч", ""),
        ("Коэффициент неравномерности K_gen.max", "auto, см. СП 32 табл. 1"),
        ("Часов работы в сутки", "24 (default)"),
    ]))

    # ---------- Секция 4. Геометрия трассы ----------
    story.append(Paragraph("4. Геометрия трассы", styles["h2"]))
    story.append(_empty_field_table([
        ("Перепад точек ΔH, м (auto)", f"{L0.dH_m:g}"),
        ("Длина напорной трассы L, м (auto)", f"{L0.L_m:g}"),
        ("Глубина заложения подводящего, м", ""),
        ("Глубина заложения напорного, м", ""),
        ("Перепад от рельефа, м", ""),
        ("Направление подвода (часов)", ""),
    ]))

    # ---------- Секция 5. Подводящий трубопровод ----------
    story.append(Paragraph("5. Подводящий трубопровод (самотёчный)", styles["h2"]))
    story.append(_empty_field_table([
        ("Диаметр D, мм", ""),
        ("Материал", "ПЭ100 SDR17 / Корсис / другое"),
        ("Кол-во вводов в КНС", "1 (default)"),
        ("Скорость в трубе, м/с", "auto"),
    ]))

    # ---------- Секция 6. Напорный трубопровод ----------
    story.append(Paragraph("6. Напорный трубопровод", styles["h2"]))
    story.append(_empty_field_table([
        ("Диаметр D, мм (auto)", f"{result.computed.D_mm:g}"),
        ("Материал", "ПЭ100 SDR17 (default)"),
        ("PN-класс (давление)", f"PN10 (default; для L>500 м проверить гидроудар: ΔH ≈ {result.computed.v_ms * 320 / 9.81:.0f} м)"),
        ("Кол-во отводов 90°", "4 (default)"),
        ("Кол-во задвижек/обр.клапанов", "2 (default)"),
        ("Перепад между точками, м (auto)", f"{L0.dH_m:g}"),
    ]))

    # ---------- Секция 7. Корпус КНС ----------
    story.append(Paragraph("7. Корпус КНС", styles["h2"]))
    story.append(_empty_field_table([
        ("Тип корпуса", "ПЭ / стеклопластик / бетон"),
        ("Диаметр D_корп, мм", ""),
        ("Высота H_корп, мм", ""),
        ("Объём приёмного резервуара, м³", "по формуле V = Q / (4·z), см. СП 32"),
        ("УГВ относительно дна, м", "(если выше дна — нужна якорная плита SF≥1.25)"),
        ("Тип грунта", "песок / суглинок / глина / скала"),
    ]))

    # ---------- Секция 8. Резервирование ----------
    story.append(Paragraph("8. Резервирование и категория", styles["h2"]))
    story.append(_empty_field_table([
        ("Категория надёжности (СП 32 табл. 16)", "I / II (default) / III"),
        ("Схема насосов (рабочих + резервных)", "1+1 (default) / 2+1 / 3+1 / N+0"),
        ("На складе", "0 / 1"),
        ("На складе — срок", "(для I категории — 24-72 ч)"),
    ]))

    # ---------- Секция 9. Электрика и автоматика ----------
    story.append(Paragraph("9. Электроснабжение и автоматика", styles["h2"]))
    story.append(_empty_field_table([
        ("Категория электроснабжения", "I / II / III"),
        ("Наличие АВР", "обязателен для P>50 кВт суммарно"),
        ("Метод пуска", "DOL (≤7.5 кВт) / Soft-Start (≤22) / ЧРП (>75)"),
        ("Защита двигателя (PTC, phase monitor)", "PTC обязателен при P>5.5 кВт"),
        ("Тип управления", "поплавки (default) / гидростат / радар"),
        ("Диспетчеризация", "GSM / ModBus / Ethernet / нет"),
    ]))

    # ---------- Секция 10. Особые требования ----------
    story.append(Paragraph("10. Особые требования", styles["h2"]))
    story.append(_empty_field_table([
        ("Взрывозащита (ATEX/Ex)", "да / нет"),
        ("Степень защиты IP", "IP68 (default) / IP69"),
        ("Пожаротушение", "да / нет"),
        ("Питьевая вода", "да / нет (требует сертификации)"),
        ("Прочие требования", ""),
    ]))

    # ---------- Подпись клиента ----------
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Подпись клиента / уполномоченного лица:", styles["label"]))
    story.append(Spacer(1, 0.5 * cm))
    sig_data = [
        ["Фамилия И.О.", "_________________________________", "Дата", "____________"],
        ["Должность", "_________________________________", "Подпись", "____________"],
    ]
    sig_table = Table(sig_data, colWidths=(3 * cm, 8 * cm, 1.5 * cm, 4 * cm))
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), DEFAULT_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    # ---------- Footer ----------
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Этот опросный лист сгенерирован автоматически на основе первичных данных, "
        "введённых менеджером в kns-calculator. После заполнения клиентом — передаётся "
        "инженеру-проектировщику для уточнённого расчёта.",
        styles["small"]
    ))

    doc.build(story)
    return buf.getvalue()
