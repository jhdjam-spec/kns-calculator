"""Тесты TZ Parser — извлечение Q/H/город/тип/шифра из произвольного ТЗ.

Покрывает:
- Типичное ТЗ с Q/H/городом/шифром
- Промышленный объект с Ex / I категория надёжности
- Опросный лист с л/с (конвертация в м³/ч)
- Ливнёвка
- Пустой текст / 400
- Confidence для частичного извлечения
- Naked-формат «88 м³/ч» без маркера Q=
- Шифр проекта вида «1578-22-НК»
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pump_calculator.api import app
from pump_calculator.etl.tz_parser import parse_tz

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests — parse_tz()
# ---------------------------------------------------------------------------


def test_typical_tz_full_extraction():
    """Главный happy-path: КНС, Q=88.6, H=39, Краснодар, бытовые, шифр."""
    text = (
        "Тех.задание на разработку КНС жилого комплекса.\n"
        "Производительность: Q = 88.6 м³/ч, напор 39 м.\n"
        "Город: г. Краснодар. Тип стоков: бытовые.\n"
        "Шифр проекта: 1578-22-НК"
    )
    r = parse_tz(text)
    assert r.Q_m3h == pytest.approx(88.6, abs=0.01)
    assert r.dH_m == pytest.approx(39.0, abs=0.01)
    assert r.city is not None and "краснодар" in r.city.lower()
    assert r.wastewater_type == "domestic"
    assert r.project_code == "1578-22-НК"
    assert r.object_type == "КНС"
    assert r.confidence >= 0.75  # 3-4 из 4 ключевых полей
    assert "Q" in r.fields_found
    assert "H" in r.fields_found


def test_industrial_atex_reliability():
    """Промышленные сточные, ATEX, I категория надёжности."""
    text = (
        "Опросный лист на промышленную КНС.\n"
        "Q=132 м³/ч, H=35 м.\n"
        "г. Москва. Промышленные стоки с нефтепродуктами.\n"
        "Взрывозащищённое исполнение (зона 1, IIB-T3).\n"
        "Категория надёжности: I."
    )
    r = parse_tz(text)
    assert r.Q_m3h == 132.0
    assert r.dH_m == 35.0
    assert r.wastewater_type == "industrial"
    assert r.Ex_required is True
    assert r.reliability == "I"
    assert r.object_type == "КНС"


def test_ls_conversion():
    """Q в л/с → м³/ч (×3.6)."""
    text = "Подобрать насос на расход 25 л/с, напор 18 м, г. Сочи."
    r = parse_tz(text)
    assert r.Q_m3h == pytest.approx(90.0, abs=0.1)  # 25 × 3.6
    assert r.dH_m == 18.0
    assert r.city is not None and "сочи" in r.city.lower()


def test_drainage_stormwater():
    """Ливнёвка — тип drainage."""
    text = (
        "ТЗ: ливневая КНС.\n"
        "Производительность 540 л/с, напор H=22 м.\n"
        "г. Екатеринбург. Поверхностные сточные воды с автодороги."
    )
    r = parse_tz(text)
    assert r.wastewater_type == "drainage"
    assert r.Q_m3h == pytest.approx(540 * 3.6, abs=0.1)
    assert r.dH_m == 22.0
    assert r.object_type == "КНС"


def test_empty_text_zero_confidence():
    """Пустой текст → confidence=0, ничего не извлечено."""
    r = parse_tz("")
    assert r.confidence == 0.0
    assert r.Q_m3h is None
    assert r.dH_m is None
    assert r.fields_found == []


def test_partial_extraction_partial_confidence():
    """Только Q и H без города/типа стоков → confidence=0.5."""
    text = "Q=50 м³/ч, H=15 м. Подобрать насос."
    r = parse_tz(text)
    assert r.Q_m3h == 50.0
    assert r.dH_m == 15.0
    assert r.city is None
    assert r.wastewater_type is None
    assert r.confidence == 0.5  # 2 из 4 ключевых


def test_naked_q_format():
    """Без маркера Q=: «88 м³/ч» прямо в тексте."""
    text = "Насос для КНС 88 м³/ч, напор 25 м."
    r = parse_tz(text)
    assert r.Q_m3h == 88.0
    assert r.dH_m == 25.0


def test_project_code_alphanumeric():
    """Шифр буквенно-цифровой ЖК-Крокус-2024 и тендерный 2799289."""
    text = (
        "Запрос по шифру 2799289. Тех.задание на КНС жилого комплекса.\n"
        "Производительность Q=18 м³/ч, напор 12 м, бытовые стоки, г. Казань."
    )
    r = parse_tz(text)
    # 2799289 — тендерный (>=5 цифр), должен быть найден
    assert "2799289" in r.project_codes
    assert r.Q_m3h == 18.0
    assert r.wastewater_type == "domestic"


def test_manufacturer_extraction():
    """Упомянутый Grundfos должен извлекаться."""
    text = (
        "ТЗ: подобрать аналог Grundfos SEG для КНС.\n"
        "Q = 20 м³/ч, H = 12 м, бытовые стоки, г. Ростов-на-Дону."
    )
    r = parse_tz(text)
    assert r.manufacturer == "GRUNDFOS"
    assert r.Q_m3h == 20.0


def test_liquid_temperature():
    """Температура жидкости извлекается."""
    text = "Q=15 м³/ч, H=10 м. Температура жидкости 65 °C."
    r = parse_tz(text)
    assert r.liquid_temp_c == 65.0


# ---------------------------------------------------------------------------
# Endpoint tests — POST /import/parse
# ---------------------------------------------------------------------------


def test_endpoint_happy_path():
    """POST /import/parse возвращает 200 с заполненными полями."""
    r = client.post(
        "/import/parse",
        json={
            "text": (
                "ТЗ на КНС жилого комплекса. Q=88.6 м³/ч, H=39 м.\n"
                "г. Краснодар, бытовые стоки, шифр 1578-22-НК."
            ),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["Q_m3h"] == pytest.approx(88.6, abs=0.01)
    assert body["dH_m"] == 39.0
    assert body["wastewater_type"] == "domestic"
    assert body["confidence"] >= 0.75


def test_endpoint_empty_text_returns_400():
    """Пустой текст → 400."""
    r = client.post("/import/parse", json={"text": ""})
    assert r.status_code == 400


def test_endpoint_whitespace_returns_400():
    """Только пробелы → 400."""
    r = client.post("/import/parse", json={"text": "   \n\t  "})
    assert r.status_code == 400
