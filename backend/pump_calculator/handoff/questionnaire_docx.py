"""DOCX-генератор опросного листа клиенту.

В отличие от PDF (handoff/questionnaire_pdf.py), DOCX гарантированно парсится
обратно — клиент возвращает заполненный файл, парсер извлекает значения и
запускает /select.

Для надёжного парсинга у каждого поля есть стабильный machine-readable код
в первой колонке (например `Q_M3H`, `WASTEWATER_TYPE`). Парсер ищет по коду,
не по русской метке — это устойчиво к косметическим правкам текста и
разному написанию ("м³/ч" vs "м3/ч" vs "куб.м/час").

Эталон формы (изучен как образец, см. 01_research/quiz_format_samples/):
"Опросный лист КНС-2 ливневая канализация" от Серво-Юг — структура секций
"Расход / Тип стока / Кол-во насосов / Вход / Выход / Комплектация".
"""

from __future__ import annotations

import io
from datetime import datetime

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.shared import Cm, Pt, RGBColor

from pump_calculator.schemas import SelectionResult

WASTEWATER_LABELS = {
    "domestic": "хоз-бытовые",
    "drainage": "ливнёвка / дренажные",
    "industrial": "производственные",
    "clean_water": "чистая вода (СПД)",
}


def _add_section_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x37, 0x41, 0x51)


def _add_field_table(
    doc: Document,
    rows: list[tuple[str, str, str]],
) -> None:
    """Таблица 3 колонки: КОД | Метка | Значение.

    Параметр `rows` — список троек (code, label, prefilled_value).
    Если prefilled_value пустое — клиент сам заполняет.
    """
    table = doc.add_table(rows=len(rows), cols=3)
    table.autofit = False
    # Ширина колонок: код узкий, метка средняя, значение широкое
    widths = (Cm(3.2), Cm(7.5), Cm(6.0))

    for i, (code, label, value) in enumerate(rows):
        cells = table.rows[i].cells
        cells[0].text = ""
        cells[1].text = ""
        cells[2].text = ""

        # 0: код (моноширинный, серый)
        run0 = cells[0].paragraphs[0].add_run(code)
        run0.font.name = "Consolas"
        run0.font.size = Pt(8)
        run0.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)

        # 1: метка
        run1 = cells[1].paragraphs[0].add_run(label)
        run1.font.size = Pt(9)

        # 2: значение
        run2 = cells[2].paragraphs[0].add_run(value if value else "")
        run2.font.size = Pt(9)
        run2.bold = True

        for c, w in zip(cells, widths, strict=False):
            c.width = w
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Лёгкая сетка для визуального удобства
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{border_name}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:color"), "D1D5DB")
        tblBorders.append(b)
    tblPr.append(tblBorders)


def generate_questionnaire_docx(
    result: SelectionResult | None = None,
    *,
    object_name: str = "",
    client_company: str = "",
    client_contact: str = "",
    city: str = "",
    kp_number: str = "",
) -> bytes:
    """Сгенерировать DOCX опросного листа клиенту.

    Если передан `result` — поля из L0/L1 предзаполняются (auto). Иначе
    форма пустая, клиент заполняет с нуля.

    Format: stable machine-readable codes в первой колонке таблицы +
    русские метки + значения. Парсер `quiz_extractor.parse_questionnaire_docx`
    читает обратно по кодам.
    """
    doc = Document()

    # Поля страницы
    section = doc.sections[0]
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    # ---------- Шапка ----------
    title = doc.add_paragraph()
    title_run = title.add_run("Опросный лист на КНС / НС / СПД")
    title_run.bold = True
    title_run.font.size = Pt(16)
    title_run.font.color.rgb = RGBColor(0x1f, 0x29, 0x37)

    sub = doc.add_paragraph()
    sub_run = sub.add_run(
        f"Сформирован {datetime.now().strftime('%d.%m.%Y %H:%M')} · "
        f"kns-calculator (open-source, github.com/jhdjam-spec/kns-calculator)"
    )
    sub_run.font.size = Pt(8)
    sub_run.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)

    instr = doc.add_paragraph()
    instr_run = instr.add_run(
        "Заполните значения в правой колонке. Не удаляйте коды в левой колонке "
        "(они нужны для автоматического распознавания). После заполнения отправьте "
        "файл менеджеру — калькулятор автоматически извлечёт параметры и сделает подбор."
    )
    instr_run.font.size = Pt(8)
    instr_run.italic = True
    instr_run.font.color.rgb = RGBColor(0x4b, 0x55, 0x63)

    # ---------- 1. Объект и заказчик ----------
    _add_section_heading(doc, "1. Объект и заказчик")
    _add_field_table(doc, [
        ("OBJECT_NAME", "Название объекта", object_name),
        ("CLIENT_COMPANY", "Заказчик (компания)", client_company),
        ("CLIENT_CONTACT", "Контактное лицо, телефон", client_contact),
        ("CITY", "Город / регион", city),
        ("KP_NUMBER", "№ КП / запроса", kp_number),
        ("FILL_DATE", "Дата заполнения", datetime.now().strftime("%d.%m.%Y")),
    ])

    # ---------- 2. Расход ----------
    L0 = result.input.L0 if result else None
    _add_section_heading(doc, "2. Расход (заполните одно из двух)")
    _add_field_table(doc, [
        ("Q_M3H", "Расход Q, м³/ч",
         f"{L0.Q_m3h:g}" if L0 else ""),
        ("Q_LS", "Расход Q, л/с (alt. ввод)", ""),
        ("Q_M3SUT", "Расход среднесуточный, м³/сут (alt.)", ""),
    ])

    # ---------- 3. Напор и геометрия ----------
    _add_section_heading(doc, "3. Напор и геометрия трассы")
    _add_field_table(doc, [
        ("DH_M", "Геом. перепад точек ΔH, м",
         f"{L0.dH_m:g}" if (L0 and L0.dH_m is not None) else ""),
        ("L_M", "Длина напорной трассы L, м",
         f"{L0.L_m:g}" if (L0 and L0.L_m is not None) else ""),
        ("H_M", "Полный напор H, м (если ΔH+L неизвестны)", ""),
        ("PIPE_DEPTH_INPUT_M", "Глубина заложения подводящей, м", ""),
        ("PIPE_DEPTH_OUTPUT_M", "Глубина заложения напорной, м", ""),
    ])

    # ---------- 4. Тип стоков ----------
    _add_section_heading(doc, "4. Тип стоков")
    wastewater = ""
    if L0 and L0.wastewater_type:
        wastewater = WASTEWATER_LABELS.get(L0.wastewater_type, L0.wastewater_type)
    _add_field_table(doc, [
        ("WASTEWATER_TYPE",
         "Тип (domestic / drainage / industrial / clean_water)",
         wastewater),
        ("LIQUID_TEMP_C", "Температура жидкости, °C", ""),
        ("PH", "pH (для industrial)", ""),
        ("INCLUSIONS", "Особые включения (волокна, абразив)", ""),
    ])

    # ---------- 5. Корпус и трубопровод ----------
    L1 = result.input.L1 if (result and result.input.L1) else None
    _add_section_heading(doc, "5. Корпус и трубопровод")
    corpus = L1.corpus_material if L1 and L1.corpus_material else ""
    pipe_mat = L1.pipe_material if L1 and L1.pipe_material else ""
    _add_field_table(doc, [
        ("CORPUS_MATERIAL", "Материал корпуса (pe / glass)", corpus),
        ("CORPUS_D_MM", "Диаметр корпуса D, мм (если задан)", ""),
        ("CORPUS_H_MM", "Высота корпуса H, мм", ""),
        ("PIPE_MATERIAL",
         "Материал напорной трубы (pe100_sdr17 / steel_welded_new / pvc / pp)",
         pipe_mat),
        ("PIPE_D_MM", "Диаметр напорной трубы D, мм (если задан)", ""),
    ])

    # ---------- 6. Резервирование и автоматика ----------
    _add_section_heading(doc, "6. Резервирование и автоматика")
    redundancy = L1.redundancy if L1 and L1.redundancy else ""
    ex_required = ""
    if L1:
        ex_required = "да" if L1.Ex_required else "нет"
    _add_field_table(doc, [
        ("REDUNDANCY",
         "Схема насосов (1+0 / 1+1 / 2+1 / 3+1 / N+0)",
         redundancy),
        ("RELIABILITY_CATEGORY",
         "Категория надёжности (I / II / III)",
         L1.reliability_category if (L1 and L1.reliability_category) else ""),
        ("EX_REQUIRED", "Взрывозащита (да / нет)", ex_required),
        ("DISPATCHING", "Диспетчеризация (GSM / Modbus / Ethernet / нет)", ""),
        ("CONTROL_TYPE",
         "Тип управления (поплавки / гидростат / радар)",
         ""),
    ])

    # ---------- 7. Прочее ----------
    _add_section_heading(doc, "7. Прочие требования")
    _add_field_table(doc, [
        ("INSTALL_UNDER_ROAD", "Установка под проезжей частью (да / нет)", ""),
        ("FIRE_PROTECTION", "Пожаротушение (да / нет)", ""),
        ("DRINKING_WATER", "Питьевая вода (да / нет)", ""),
        ("OTHER_REQUIREMENTS", "Прочие требования", ""),
    ])

    # ---------- Footer ----------
    doc.add_paragraph()
    foot = doc.add_paragraph()
    foot_run = foot.add_run(
        "Подпись клиента: _______________________________ "
        "Должность: ___________________ Дата: _______________"
    )
    foot_run.font.size = Pt(9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
