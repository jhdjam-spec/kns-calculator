"""Тесты реестра нормативов (Phase 22)."""
from __future__ import annotations

import pytest

from pump_calculator.regulations import (
    ALL_REGULATIONS,
    FZ_123,
    GOST_6134,
    PUE_7,
    SP_8_13130,
    SP_10_13130,
    SP_30,
    SP_32,
    SP_32_2012,
    SP_131,
    Regulation,
    RegulationReference,
    get_regulation,
    list_regulations_by_category,
    ref,
)


def test_all_regulations_have_required_fields():
    """У каждого норматива есть код, название, редакция, дата ввода, URL."""
    for key, reg in ALL_REGULATIONS.items():
        assert isinstance(reg, Regulation), key
        assert reg.code, f"Empty code for {key}"
        assert reg.title, f"Empty title for {key}"
        assert reg.edition, f"Empty edition for {key}"
        assert reg.in_force_from, f"Empty in_force_from for {key}"
        # URL может быть пустым — но если есть, должен начинаться с http
        if reg.url_official:
            assert reg.url_official.startswith("http"), key


def test_sp_32_supersedes_sp_32_2012():
    """СП 32.13330.2018 заменяет СП 32.13330.2012."""
    assert SP_32_2012.superseded_by == SP_32.code
    assert SP_32.superseded_by is None


def test_sp_8_13130_has_izm_1():
    """СП 8.13130 имеет Изм.№1 от 01.03.2024."""
    assert "Изм.№1" in SP_8_13130.edition
    assert "2024" in SP_8_13130.edition


def test_sp_32_has_izm_4():
    """СП 32 имеет Изм.№4 от 17.01.2025."""
    assert "Изм.№4" in SP_32.edition
    assert "2025" in SP_32.edition


def test_categories_consistent():
    """Категории нормативов соответствуют ожидаемым."""
    assert SP_32.category == "sewerage"
    assert SP_30.category == "water_supply"
    assert SP_8_13130.category == "fire_safety"
    assert SP_131.category == "climate"
    assert PUE_7.category == "electrical"
    assert FZ_123.category == "fire_safety"


def test_get_regulation_by_key_and_code():
    """Поиск работает по ключу (SP_32) и по коду (СП 32.13330.2018)."""
    r1 = get_regulation("SP_32")
    r2 = get_regulation("СП 32.13330.2018")
    assert r1 is r2 is SP_32


def test_get_regulation_unknown():
    """Несуществующий норматив → None."""
    assert get_regulation("XYZ-999") is None


def test_list_by_category():
    """Фильтр по категориям возвращает только нужные."""
    fire = list_regulations_by_category("fire_safety")
    codes = {r.code for r in fire}
    assert SP_8_13130.code in codes
    assert SP_10_13130.code in codes
    assert FZ_123.code in codes
    assert SP_32.code not in codes


def test_ref_constructor():
    """ref() создаёт корректный RegulationReference."""
    r = ref("SP_8_13130", "§6.3 табл. 1", "Расход на наружное пожаротушение")
    assert isinstance(r, RegulationReference)
    assert r.regulation_code == SP_8_13130.code
    assert r.section == "§6.3 табл. 1"
    assert r.purpose == "Расход на наружное пожаротушение"
    assert r.url == SP_8_13130.url_official


def test_ref_unknown_raises():
    """ref() с неизвестным ключом → KeyError."""
    with pytest.raises(KeyError):
        ref("XYZ_999", "§1", "test")


def test_at_least_25_regulations():
    """В реестре должно быть достаточно нормативов для покрытия задач."""
    assert len(ALL_REGULATIONS) >= 25


def test_iso_9906_and_gost_6134_coexist():
    """ISO 9906 и ГОСТ 6134 — оба должны быть."""
    assert get_regulation("ISO_9906") is not None
    assert GOST_6134.code.startswith("ГОСТ 6134")
