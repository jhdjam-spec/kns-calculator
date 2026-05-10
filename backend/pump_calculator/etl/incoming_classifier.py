"""P5 Mail Integration — классификатор входящих запросов (CRM-light).

Назначение
==========
Утилита для будущего CRM-light внутри kns-calculator: «новый запрос →
определить тип (ОЛ/КП/ТЗ/проект) → создать карточку в очереди инженера».

Источник паттернов: `02_dataset/_inbox/mail_ru_imap/learned_profile.json`
(8 330 писем zakaz@inservo.ru, период 2019-2026, ru-locale).

Что классифицирует
==================
1. **Шифры проектов** — `extract_project_codes(text)`:
   - Цифровые: `5051573`, `2799289`, `16243555`
   - Буквенно-цифровые: `БСВП0001809`, `NT-304В`, `ОДВ-150`, `EN-20`
   - Проектные: `1578-22-НК`, `75-02-21-РД-3-НК1`, `РАИ-361-22-Р01`

2. **Subject markers** — `classify_subject_marker(subject)`:
   - Тип запроса: ОЛ (опросный лист), КП (коммерческое предложение),
     ТЗ (техзадание), ЗАЯВКА, ЗАПРОС
   - Объект: КНС, ЛОС, ВНС, ВЗиС, пожарка, водоснабжение
   - Производитель: SCHWARTZ, GRUNDFOS, KSB, WILO, ANTARUS, СМЗ, KAIQUAN, CNP

3. **Доверенные отправители** — `is_trusted_sender(email, domains)`:
   проверка домена против списка из learned_profile (511 доменов).

Изоляция
========
Модуль НЕ дёргает matching.py / pricing.py / matching pipeline.
Это standalone-утилита для будущего CRM. Интеграция — отдельная фаза.
"""

from __future__ import annotations

import re
from typing import Final

# ---------------------------------------------------------------------------
# Регексы шифров (порядок важен: от более специфичных к общим)
# ---------------------------------------------------------------------------

# Проектные шифры: «1578-22-НК», «75-02-21-РД-3-НК1», «РАИ-361-22-Р01»
# Структура: цифры/буквы → разделитель → цифры → опц. блоки с РД/НК/НВК и т.п.
_RE_PROJECT_CODE: Final[re.Pattern[str]] = re.compile(
    r"\b[А-ЯA-Z\d]{2,5}[-./]\d{2,4}([-./][А-ЯA-Z\d]{1,5}){1,5}\b"
)

# Буквенно-цифровые: «БСВП0001809», «NT-304В», «ОДВ-150», «EN-20», «АХ-ОД-1к-20»
_RE_ALPHANUM_CODE: Final[re.Pattern[str]] = re.compile(
    r"\b[А-ЯA-Z]{2,6}[-]?\d{2,10}[А-Я]?\b"
)

# Чисто цифровые шифры (тендерные/контрактные номера): 7-10 знаков
# 5+ цифр (5051xxxxxx, 2799289, 16243555, 53741469)
_RE_NUMERIC_CODE: Final[re.Pattern[str]] = re.compile(r"\b\d{5,10}\b")

# ---------------------------------------------------------------------------
# Словари маркеров (по убыванию частоты в learned_profile.json)
# ---------------------------------------------------------------------------

REQUEST_TYPE_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    "ОЛ": ("ОЛ", "опросный", "опросн.", "опросник"),
    "КП": ("КП", "коммерческое", "коммерческое предложение"),
    "ТЗ": ("ТЗ", "техзадание", "техническое задание"),
    "ЗАЯВКА": ("заявка", "новая заявка"),
    "ЗАПРОС": ("запрос", "новый запрос"),
    "ТЕНДЕР": ("тендер", "закупка"),
}

OBJECT_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    "КНС": ("КНС", "канализационная насосная"),
    "ЛОС": ("ЛОС", "очистные", "локальные очистные"),
    "ВНС": ("ВНС", "водопроводная насосная"),
    "ВЗиС": ("ВЗиС", "водозаборные"),
    "ПОЖАРКА": ("пожар", "пожарная", "пожаротушения"),
    "ВОДОСНАБЖЕНИЕ": ("водоснабжение", "водоотведение"),
    "ЁМКОСТИ": ("емкост", "ёмкост", "резервуар"),
    "СЕПТИК": ("септик",),
}

MANUFACTURER_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    "GRUNDFOS": ("grundfos", "грундфос"),
    "KSB": ("ksb",),
    "WILO": ("wilo", "вило"),
    "PEDROLLO": ("pedrollo", "педролло"),
    "SCHWARTZ": ("schwartz", "шварц"),
    "ANTARUS": ("antarus", "антарус"),
    "KAIQUAN": ("kaiquan", "кайкван"),
    "CNP": ("cnp",),
    "СМЗ": ("смз", "иртыш"),
    "ГНОМ": ("гном",),
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_project_codes(text: str) -> list[str]:
    """Извлечь все возможные шифры проектов из текста.

    Возвращает список уникальных кодов в порядке появления, с приоритетом
    более специфичных паттернов (проектный → буквенно-цифровой → цифровой).
    Пересекающиеся совпадения не дублируются.
    """
    if not text:
        return []

    found: list[str] = []
    seen: set[str] = set()
    consumed_spans: list[tuple[int, int]] = []

    def _add_matches(pattern: re.Pattern[str]) -> None:
        for m in pattern.finditer(text):
            span = m.span()
            # Skip if overlaps with a span already consumed by more specific pattern
            if any(s <= span[0] < e or s < span[1] <= e for s, e in consumed_spans):
                continue
            code = m.group(0)
            if code not in seen:
                seen.add(code)
                found.append(code)
                consumed_spans.append(span)

    # Порядок: специфичный → общий
    _add_matches(_RE_PROJECT_CODE)
    _add_matches(_RE_ALPHANUM_CODE)
    _add_matches(_RE_NUMERIC_CODE)
    return found


def classify_subject_marker(subject: str) -> dict[str, str | None]:
    """Классифицировать subject письма по типу запроса, объекту и производителю.

    Returns
    -------
    dict с ключами:
        type         — ОЛ | КП | ТЗ | ЗАЯВКА | ЗАПРОС | ТЕНДЕР | None
        object       — КНС | ЛОС | ВНС | ... | None
        manufacturer — GRUNDFOS | KSB | ... | None
    """
    result: dict[str, str | None] = {"type": None, "object": None, "manufacturer": None}
    if not subject:
        return result

    lower = subject.lower()
    upper = subject.upper()

    # Type: ОЛ, КП, ТЗ имеют ASCII-представление токенов (часто в верхнем регистре)
    for key, markers in REQUEST_TYPE_MARKERS.items():
        for marker in markers:
            # Короткие аббревиатуры (≤3 симв) ищем как токены, иначе substring
            if len(marker) <= 3:
                # Граница слова \b плохо работает с кириллицей в re; используем токен по разделителям
                if re.search(rf"(?<![А-ЯA-Zа-яa-z]){re.escape(marker)}(?![А-ЯA-Zа-яa-z])", upper):
                    result["type"] = key
                    break
            elif marker.lower() in lower:
                result["type"] = key
                break
        if result["type"]:
            break

    # Object
    for key, markers in OBJECT_MARKERS.items():
        for marker in markers:
            if marker.lower() in lower:
                result["object"] = key
                break
        if result["object"]:
            break

    # Manufacturer
    for key, markers in MANUFACTURER_MARKERS.items():
        for marker in markers:
            if marker.lower() in lower:
                result["manufacturer"] = key
                break
        if result["manufacturer"]:
            break

    return result


def is_trusted_sender(email: str, trusted_domains: set[str]) -> bool:
    """Проверить, принадлежит ли email доверенному домену.

    Email может быть в формате `user@domain.tld` или `Имя <user@domain.tld>`.
    Домен сравнивается case-insensitive. Поддомены тоже считаются доверенными,
    если их корневой домен в списке (например, krym.inservo.ru при inservo.ru).
    """
    if not email or not trusted_domains:
        return False

    # Достаём адрес из <…>
    m = re.search(r"<([^>]+)>", email)
    addr = m.group(1) if m else email

    if "@" not in addr:
        return False
    domain = addr.rsplit("@", 1)[1].strip().lower()
    domains_lower = {d.lower() for d in trusted_domains}

    if domain in domains_lower:
        return True
    # Поддомен: проверить, не оканчивается ли на «.<trusted>»
    return any(domain.endswith("." + d) for d in domains_lower)
