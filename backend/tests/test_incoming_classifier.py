"""Тесты P5 mail integration: классификатор входящих запросов.

Покрывает:
- extract_project_codes: цифровые / буквенно-цифровые / проектные шифры
- classify_subject_marker: тип запроса, объект, производитель
- is_trusted_sender: точные домены и поддомены
- Edge cases: пустая строка, мультиязык, мусор
"""

from __future__ import annotations

from pump_calculator.etl.incoming_classifier import (
    classify_subject_marker,
    extract_project_codes,
    is_trusted_sender,
)

# ---------------------------------------------------------------------------
# extract_project_codes
# ---------------------------------------------------------------------------


def test_extract_numeric_code_simple():
    """Чисто цифровой шифр (тендерные номера)."""
    codes = extract_project_codes("Шифр заказа 2799289 — нужно КП")
    assert "2799289" in codes


def test_extract_numeric_code_long():
    """10-значный тендерный код."""
    codes = extract_project_codes("Площадка 5051573421 повторно")
    assert "5051573421" in codes


def test_extract_alphanum_code():
    """Буквенно-цифровой шифр оборудования."""
    codes = extract_project_codes("Прислали ОДВ-150 и NT-304В")
    assert "ОДВ-150" in codes
    assert "NT-304В" in codes


def test_extract_alphanum_solid():
    """БСВП0001809 — без разделителя."""
    codes = extract_project_codes("По шифру БСВП0001809 ждём отгрузку")
    assert "БСВП0001809" in codes


def test_extract_project_code_dashed():
    """Проектный шифр вида 1578-22-НК."""
    codes = extract_project_codes("Проект 1578-22-НК — расчёт КНС-2")
    assert any("1578-22-НК" in c for c in codes)


def test_extract_project_code_complex():
    """Длинный проектный шифр 75-02-21-РД-3-НК1."""
    codes = extract_project_codes("Получен 75-02-21-РД-3-НК1 от заказчика")
    assert any("75-02-21" in c for c in codes)


def test_extract_no_duplicates_overlap():
    """Если проектный шифр поглощает цифровой — дубликата нет."""
    codes = extract_project_codes("РАИ-361-22-Р01")
    # Не должно быть отдельных «361» и «22» как chunks
    assert codes == ["РАИ-361-22-Р01"]


def test_extract_empty_string():
    """Пустая строка → пустой список."""
    assert extract_project_codes("") == []
    assert extract_project_codes(None) == []  # type: ignore[arg-type]


def test_extract_multiple_codes():
    """Несколько шифров в одном тексте."""
    text = "Запрос по 2799289 и шифру БСВП0001809 для ОДВ-150"
    codes = extract_project_codes(text)
    assert "2799289" in codes
    assert "БСВП0001809" in codes
    assert "ОДВ-150" in codes


# ---------------------------------------------------------------------------
# classify_subject_marker
# ---------------------------------------------------------------------------


def test_classify_ol_kns():
    """ОЛ + КНС — самый частый кейс (1213 ОЛ, 40 КНС в learned_profile)."""
    result = classify_subject_marker("ОЛ на КНС-2 для жилого комплекса")
    assert result["type"] == "ОЛ"
    assert result["object"] == "КНС"


def test_classify_kp_los():
    """КП на ЛОС с производителем."""
    result = classify_subject_marker("КП по ЛОС с насосами Grundfos")
    assert result["type"] == "КП"
    assert result["object"] == "ЛОС"
    assert result["manufacturer"] == "GRUNDFOS"


def test_classify_tz_pump():
    """ТЗ + производитель ANTARUS."""
    result = classify_subject_marker("ТЗ — подобрать аналог Antarus")
    assert result["type"] == "ТЗ"
    assert result["manufacturer"] == "ANTARUS"


def test_classify_zayavka():
    """Заявка → ЗАЯВКА."""
    result = classify_subject_marker("Новая заявка с сайта")
    assert result["type"] == "ЗАЯВКА"


def test_classify_empty_returns_nones():
    """Пустой subject → все None."""
    result = classify_subject_marker("")
    assert result == {"type": None, "object": None, "manufacturer": None}


def test_classify_multilang_mixed():
    """Смешанный русско-английский — обработать оба."""
    result = classify_subject_marker("RFQ для KSB pumps на КНС")
    assert result["object"] == "КНС"
    assert result["manufacturer"] == "KSB"


def test_classify_kns_short_token_not_in_word():
    """Короткий токен 'КП' не должен ловиться внутри слова 'СКПР'."""
    result = classify_subject_marker("Документ СКПР — общий")
    assert result["type"] is None


# ---------------------------------------------------------------------------
# is_trusted_sender
# ---------------------------------------------------------------------------


def test_trusted_exact_domain():
    """Прямой домен в списке."""
    trusted = {"inservo.ru", "yandex.ru"}
    assert is_trusted_sender("zakaz@inservo.ru", trusted) is True


def test_trusted_subdomain():
    """Поддомен tracked-домена тоже доверенный."""
    trusted = {"inservo.ru"}
    assert is_trusted_sender("info@krym.inservo.ru", trusted) is True


def test_trusted_with_display_name():
    """Email в формате 'Имя <user@domain>'."""
    trusted = {"mail.ru"}
    assert is_trusted_sender("ООО Ортус <23900@mail.ru>", trusted) is True


def test_trusted_unknown_domain():
    """Незнакомый домен → False."""
    trusted = {"inservo.ru"}
    assert is_trusted_sender("hacker@evil.example.com", trusted) is False


def test_trusted_empty_inputs():
    """Пустые входы не падают."""
    assert is_trusted_sender("", {"inservo.ru"}) is False
    assert is_trusted_sender("user@inservo.ru", set()) is False


def test_trusted_case_insensitive():
    """Сравнение домена case-insensitive."""
    trusted = {"Inservo.RU"}
    assert is_trusted_sender("USER@INSERVO.RU", trusted) is True
