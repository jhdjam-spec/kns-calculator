"""Tests: DOCX-опросник roundtrip (генерация → ручное заполнение → парсинг → L0Input).

Покрывает:
- Чистая генерация без result (пустой опросник для клиента с нуля)
- Roundtrip с предзаполненным L0 (auto-поля)
- Симуляция клиента: расход в л/с, запятая в числе, русский тип стоков
- Edge cases: пустой Q (missing field), неизвестный тип стоков, невалидное число
"""

from __future__ import annotations

import io

import docx as pydocx
import pytest

from pump_calculator.handoff import (
    generate_questionnaire_docx,
    parse_questionnaire_docx,
)
from pump_calculator.matching import select_pumps
from pump_calculator.schemas import L0Input


def _fill_docx(docx_bytes: bytes, fills: dict[str, str]) -> bytes:
    """Программно заполнить колонку 2 в строках с заданными кодами (имитация клиента)."""
    doc = pydocx.Document(io.BytesIO(docx_bytes))
    for table in doc.tables:
        for row in table.rows:
            if len(row.cells) < 3:
                continue
            code = row.cells[0].text.strip()
            if code in fills:
                cell = row.cells[2]
                # Чистим существующий текст и пишем заново
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.text = ""
                cell.paragraphs[0].add_run(fills[code])
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ------------------------ Базовая генерация ------------------------

def test_generate_empty_questionnaire():
    """Пустой опросник — для клиента, заполняющего с нуля."""
    docx_bytes = generate_questionnaire_docx()
    assert len(docx_bytes) > 5000  # DOCX-файл с таблицами весит > 5KB
    # Проверим что файл валиден — открывается через python-docx
    doc = pydocx.Document(io.BytesIO(docx_bytes))
    assert len(doc.tables) >= 7  # 7 секций по плану


def test_generate_with_prefilled_L0():
    """Если передан result — поля Q, dH, L, тип стоков предзаполняются."""
    L0 = L0Input(Q_m3h=21.2, dH_m=15.0, L_m=120.0, wastewater_type="domestic")
    result = select_pumps(L0, None)
    docx_bytes = generate_questionnaire_docx(result, object_name="Test", city="Sochi")

    parsed = parse_questionnaire_docx(docx_bytes)
    assert parsed.raw_codes["Q_M3H"] == "21.2"
    assert parsed.raw_codes["DH_M"] == "15"
    assert parsed.raw_codes["L_M"] == "120"
    assert "хоз-бытовые" in parsed.raw_codes["WASTEWATER_TYPE"]
    assert parsed.raw_codes["OBJECT_NAME"] == "Test"
    assert parsed.raw_codes["CITY"] == "Sochi"


# ------------------------ Roundtrip с предзаполнением ------------------------

def test_roundtrip_prefilled_L0_recovers_input():
    """Сценарий: менеджер ввёл L0, скачал опросник, клиент ничего не правил, вернул.
    Парсер должен извлечь ровно тот же L0."""
    L0 = L0Input(Q_m3h=21.2, dH_m=15.0, L_m=120.0, wastewater_type="domestic")
    result = select_pumps(L0, None)
    docx_bytes = generate_questionnaire_docx(result)

    parsed = parse_questionnaire_docx(docx_bytes)

    assert parsed.L0 is not None
    assert parsed.L0.Q_m3h == pytest.approx(21.2)
    assert parsed.L0.dH_m == pytest.approx(15.0)
    assert parsed.L0.L_m == pytest.approx(120.0)
    assert parsed.L0.wastewater_type == "domestic"
    assert parsed.missing_fields == []


# ------------------------ Симуляция клиента ------------------------

def test_client_fills_Q_in_ls_unit():
    """Клиент привычно вписал расход в л/с — парсер конвертирует в м³/ч."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_LS": "985",
        "H_M": "3,0",  # запятая вместо точки
        "WASTEWATER_TYPE": "Ливневый",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L0 is not None
    assert parsed.L0.Q_m3h == pytest.approx(985.0 * 3.6)  # 3546.0
    assert parsed.L0.dH_m == pytest.approx(3.0)
    assert parsed.L0.wastewater_type == "drainage"
    assert any("Q_LS" in w for w in parsed.warnings)


def test_client_fills_Q_in_m3sut_unit():
    """Клиент вписал среднесуточный расход в м³/сут."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_M3SUT": "508",  # 508 м³/сут / 24 ≈ 21.17 м³/ч
        "DH_M": "15",
        "L_M": "120",
        "WASTEWATER_TYPE": "хоз-бытовые",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L0 is not None
    assert parsed.L0.Q_m3h == pytest.approx(508.0 / 24, rel=0.01)
    assert any("Q_M3SUT" in w for w in parsed.warnings)


def test_client_fills_with_units_and_garbage():
    """Клиент вписал '21,2 м³/ч' — парсер должен извлечь 21.2."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_M3H": "21,2 м³/ч",
        "DH_M": "около 15 м",
        "L_M": "L = 120 метров",
        "WASTEWATER_TYPE": "хоз. бытовые стоки",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L0 is not None
    assert parsed.L0.Q_m3h == pytest.approx(21.2)
    assert parsed.L0.dH_m == pytest.approx(15.0)
    assert parsed.L0.L_m == pytest.approx(120.0)
    assert parsed.L0.wastewater_type == "domestic"


def test_client_fills_L1_optional_fields():
    """Опциональные L1: материал корпуса, трубы, резервирование, взрывозащита."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_M3H": "21.2",
        "DH_M": "15",
        "L_M": "120",
        "WASTEWATER_TYPE": "domestic",
        "CORPUS_MATERIAL": "стеклопластик",
        "PIPE_MATERIAL": "ПЭ100 SDR17",
        "REDUNDANCY": "2+1",
        "RELIABILITY_CATEGORY": "II",
        "EX_REQUIRED": "нет",
        "LIQUID_TEMP_C": "20",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L1 is not None
    assert parsed.L1.corpus_material == "glass"
    assert parsed.L1.pipe_material == "pe100_sdr17"
    assert parsed.L1.redundancy == "2+1"
    assert parsed.L1.reliability_category == "II"
    assert parsed.L1.Ex_required is False
    assert parsed.L1.liquid_temp_c == pytest.approx(20.0)


# ------------------------ Edge cases ------------------------

def test_missing_Q_returns_None_L0_with_missing_field():
    """Если Q не указан — L0=None и в missing_fields есть Q_M3H."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "DH_M": "15",
        "L_M": "120",
        "WASTEWATER_TYPE": "domestic",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L0 is None
    assert "Q_M3H" in parsed.missing_fields


def test_unknown_wastewater_type_silently_ignored():
    """Если WASTEWATER_TYPE невалиден — поле остаётся None (не ошибка)."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_M3H": "21.2",
        "DH_M": "15",
        "L_M": "120",
        "WASTEWATER_TYPE": "что-то экзотическое",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L0 is not None
    assert parsed.L0.wastewater_type is None
    assert "WASTEWATER_TYPE" in parsed.missing_fields


def test_metadata_extracted():
    docx_bytes = generate_questionnaire_docx(
        object_name="Объект А",
        client_company="ООО Б",
        client_contact="Иванов +7 999 000 11 22",
        city="Сочи",
        kp_number="КП-001",
    )
    parsed = parse_questionnaire_docx(docx_bytes)
    assert parsed.metadata["OBJECT_NAME"] == "Объект А"
    assert parsed.metadata["CLIENT_COMPANY"] == "ООО Б"
    assert parsed.metadata["CITY"] == "Сочи"
    assert parsed.metadata["KP_NUMBER"] == "КП-001"


def test_only_H_provided_uses_H_as_dH():
    """Если клиент знает только полный напор — используем H как ΔH, L=0."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_M3H": "21.2",
        "H_M": "20",
        "WASTEWATER_TYPE": "domestic",
    })
    parsed = parse_questionnaire_docx(filled)

    assert parsed.L0 is not None
    assert parsed.L0.dH_m == pytest.approx(20.0)
    assert parsed.L0.L_m == pytest.approx(0.0)
    assert any("dH=20" in w or "20" in w for w in parsed.warnings)


def test_parsed_L0_is_compatible_with_select():
    """Финальная проверка: распарсенный L0 действительно работает с /select."""
    docx_bytes = generate_questionnaire_docx()
    filled = _fill_docx(docx_bytes, {
        "Q_M3H": "21.2",
        "DH_M": "15",
        "L_M": "120",
        "WASTEWATER_TYPE": "domestic",
    })
    parsed = parse_questionnaire_docx(filled)
    assert parsed.L0 is not None

    result = select_pumps(parsed.L0, parsed.L1)
    # На стандартном объекте 21.2 м³/ч @ H=15 м должны быть кандидаты во всех 3 сегментах
    assert result.results.budget is not None
    assert result.results.mid is not None
    assert result.results.premium is not None
