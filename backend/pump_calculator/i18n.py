"""Минимальная i18n для error messages kns-calculator API.

Sc.D. Cross-Domain audit 2026-05-13: «EN-локализация = 0% (весь schemas/error
message на русском)». Этот модуль закрывает finding, давая dict-based
translation для пары ru/en (расширяемо до uk/kk/be по необходимости).

Дизайн
------
- 2 языка: ``ru`` (default) и ``en``.
- Источник lang: HTTP ``Accept-Language`` header или ENV ``DEFAULT_LANG``.
- Pure-Python, без зависимостей (gettext/babel — overkill для 50 ключей).
- Fallback: если ключа нет в выбранном lang → fallback на ``ru``;
  если и там нет → возвращается сам ключ (видимый «marker» для разработчика).
- Format-string подстановки через ``str.format``; если плейсхолдер не передан,
  возвращаем raw-сообщение (без KeyError → fail-safe для production).

Использование
-------------
.. code-block:: python

    from pump_calculator.i18n import t, detect_lang

    lang = detect_lang(request.headers.get("Accept-Language"))
    raise HTTPException(400, t("missing_q", lang))
    raise HTTPException(413, t("body_too_large", lang, max_mb=10))

FastAPI dependency (см. ``api.get_lang``) делает это эргономично:

.. code-block:: python

    @app.post("/select")
    def select(req: SelectionRequest, lang: Lang = Depends(get_lang)):
        if req.L0.Q_m3h <= 0:
            raise HTTPException(400, t("invalid_q", lang))

Backlog
-------
- ``uk`` / ``kk`` / ``be`` для постсоветских рынков (Q4 2026).
- Перевод ``Field(description=...)`` в Pydantic schemas (для OpenAPI на en).
- Серверные warnings/triggers в matching.py — пока чисто-русские.
"""

from __future__ import annotations

import os
from typing import Final, Literal

Lang = Literal["ru", "en"]
"""Поддерживаемые языки. Расширяется в ``MESSAGES`` ниже."""

DEFAULT_LANG: Final[Lang] = "ru"
"""Дефолтный язык. Меняется через ENV ``DEFAULT_LANG``."""


# ──────────────────────────────────────────────────────────────────────────
# Translation table.
#
# Naming convention:
#   <area>_<short_key>     e.g. "missing_q", "auth_required", "tco_q_unknown"
#
# Placeholders в значениях используют ``str.format`` синтаксис, например
# "{pump_id}", "{max_mb}". См. использование в api.py.
# ──────────────────────────────────────────────────────────────────────────

MESSAGES: dict[Lang, dict[str, str]] = {
    "ru": {
        # — Общие/валидация L0/L1 —
        "missing_q": "Не задано Q (расход)",
        "invalid_q": "Q должно быть > 0 и < 10000 м³/ч",
        "missing_dh": "Не задан перепад dH",
        "invalid_dh": "dH должен быть в диапазоне [-50, 200] м",
        "invalid_l": "L должно быть в диапазоне [0, 5000] м",
        "all_fields_empty": "Все поля пусты — нечего классифицировать",
        "text_empty": "Поле text пустое — нечего парсить",
        # — Auth / admin —
        "missing_admin_pass": "Admin auth не настроен (ADMIN_PASS env)",
        "bad_credentials": "Неверные учётные данные",
        "auth_required": "Требуется аутентификация",
        # — Rate-limit / body-size —
        "rate_limit_exceeded": "Превышен лимит запросов. Повторите через минуту.",
        "rate_limit_with_detail": "Превышен лимит запросов: {detail}",
        "body_too_large": "Тело запроса слишком большое (макс. {max_mb} МБ)",
        # — Files / uploads —
        "file_empty": "Файл пустой",
        "file_too_large": "Файл слишком большой ({size} байт). Максимум {max_size} байт ({max_mb} MB).",
        "only_docx_supported": (
            "Поддерживается только DOCX. Для PDF/XLSX/scan см. roadmap Phase 12.2-12.3."
        ),
        "docx_parse_failed": "Не удалось распарсить DOCX: {error}",
        # — Selection / pumps —
        "selection_failed": "Ошибка подбора: {error}",
        "pump_not_found": "Насос '{pump_id}' не найден",
        "no_pump_in_segment": (
            "В сегменте '{segment}' нет подобранного насоса. Попробуйте другой сегмент."
        ),
        "must_provide_selection": (
            "Необходимо передать 'selection' или 'selection_request'"
        ),
        "cannot_determine_q": "Не удаётся определить Q_m3h для TCO-расчёта",
        # — Reports / handoff —
        "pdf_failed": "Ошибка генерации PDF: {error}",
        "docx_failed": "Ошибка генерации DOCX: {error}",
        "rpz_failed": "Ошибка генерации РПЗ: {error}",
        # — Domain calculations —
        "storm_failed": "Ошибка расчёта ливневых стоков: {error}",
        "fire_water_failed": "Ошибка пожарного расчёта: {error}",
        "water_failed": "Ошибка расчёта водоснабжения: {error}",
        "tco_failed": "Ошибка TCO: {error}",
        # — Lookups / catalogs —
        "topic_not_found": "Тема не найдена: {topic_key}",
        "section_not_found": "Раздел не найден: topic={topic_key}, anchor={anchor}",
        "failure_mode_not_found": "Режим отказа не найден: {mode_id}",
        "regulation_not_found": "Норматив не найден: {code}",
        # — Health —
        "service_unavailable": "Сервис недоступен (БД насосов не загружена)",
    },
    "en": {
        # — General / L0/L1 validation —
        "missing_q": "Q (flow rate) is required",
        "invalid_q": "Q must be > 0 and < 10000 m³/h",
        "missing_dh": "dH (head difference) is required",
        "invalid_dh": "dH must be in range [-50, 200] m",
        "invalid_l": "L must be in range [0, 5000] m",
        "all_fields_empty": "All fields are empty — nothing to classify",
        "text_empty": "Field 'text' is empty — nothing to parse",
        # — Auth / admin —
        "missing_admin_pass": "Admin auth not configured (set ADMIN_PASS env)",
        "bad_credentials": "Bad credentials",
        "auth_required": "Authentication required",
        # — Rate-limit / body-size —
        "rate_limit_exceeded": "Rate limit exceeded. Try again in a minute.",
        "rate_limit_with_detail": "Rate limit exceeded: {detail}",
        "body_too_large": "Request body too large (max {max_mb} MB)",
        # — Files / uploads —
        "file_empty": "File is empty",
        "file_too_large": "File too large ({size} bytes). Max {max_size} bytes ({max_mb} MB).",
        "only_docx_supported": (
            "Only DOCX is supported. For PDF/XLSX/scan see Phase 12.2-12.3 roadmap."
        ),
        "docx_parse_failed": "DOCX parsing failed: {error}",
        # — Selection / pumps —
        "selection_failed": "Selection failed: {error}",
        "pump_not_found": "Pump '{pump_id}' not found",
        "no_pump_in_segment": (
            "No pump available in segment '{segment}'. Try another segment."
        ),
        "must_provide_selection": (
            "Either 'selection' or 'selection_request' must be provided"
        ),
        "cannot_determine_q": "Cannot determine Q_m3h for TCO calculation",
        # — Reports / handoff —
        "pdf_failed": "PDF generation failed: {error}",
        "docx_failed": "DOCX generation failed: {error}",
        "rpz_failed": "RPZ generation failed: {error}",
        # — Domain calculations —
        "storm_failed": "Storm calculation failed: {error}",
        "fire_water_failed": "Fire water calculation failed: {error}",
        "water_failed": "Water calculation failed: {error}",
        "tco_failed": "TCO failed: {error}",
        # — Lookups / catalogs —
        "topic_not_found": "Topic not found: {topic_key}",
        "section_not_found": "Section not found: topic={topic_key}, anchor={anchor}",
        "failure_mode_not_found": "Failure mode not found: {mode_id}",
        "regulation_not_found": "Regulation not found: {code}",
        # — Health —
        "service_unavailable": "Service unavailable (pump catalog not loaded)",
    },
}


def t(key: str, lang: Lang | str | None = None, **kwargs: object) -> str:
    """Translate ``key`` to ``lang`` and apply ``kwargs`` via ``str.format``.

    Parameters
    ----------
    key
        Ключ из ``MESSAGES[lang]``. Если ключа нет — возвращаем ``key`` как
        marker для отладки (вместо raise — фронт всё ещё получает осмысленный
        текст).
    lang
        Один из ``"ru"`` / ``"en"``. Если ``None`` или неизвестное значение —
        берётся ``DEFAULT_LANG`` (ENV-настраиваемый).
    kwargs
        Плейсхолдеры для ``str.format``. Если плейсхолдер не передан, raw
        сообщение возвращается без подстановки (KeyError swallowed).
    """
    resolved_lang: Lang = _coerce_lang(lang)
    table = MESSAGES.get(resolved_lang) or MESSAGES[DEFAULT_LANG]
    msg = table.get(key)
    if msg is None:
        # Fallback на DEFAULT_LANG (ru) — потом на сам ключ.
        msg = MESSAGES[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            # Не падаем в production из-за неполных kwargs.
            return msg
    return msg


def detect_lang(accept_language: str | None) -> Lang:
    """Парсинг HTTP ``Accept-Language`` header (упрощённо, без q-весов).

    Логика:
    1. Если header пустой → ENV ``DEFAULT_LANG`` или ``"ru"``.
    2. Берётся первая lang-tag (до запятой/точки-с-запятой) и обрезается до
       primary subtag (например ``en-US`` → ``en``, ``ru-RU`` → ``ru``).
    3. Если primary subtag известен → используем; иначе ``DEFAULT_LANG``.

    Полноценный q-weighted RFC 4647 lookup (Babel/Negotiator) — overkill
    для двух языков. При расширении до 5+ — заменить на ``Babel``.
    """
    env_default = _env_default_lang()
    if not accept_language:
        return env_default
    first_tag = accept_language.split(",")[0].split(";")[0].strip().lower()
    if not first_tag:
        return env_default
    primary = first_tag.split("-")[0]
    if primary in MESSAGES:
        return primary  # type: ignore[return-value]
    return env_default


# ──────────────────────────────────────────────────────────────────────────
# Internals
# ──────────────────────────────────────────────────────────────────────────


def _coerce_lang(lang: Lang | str | None) -> Lang:
    """Cast incoming ``lang`` to known ``Lang``; fallback to default."""
    if lang and lang in MESSAGES:
        return lang  # type: ignore[return-value]
    return _env_default_lang()


def _env_default_lang() -> Lang:
    """Read ``DEFAULT_LANG`` from ENV; fall back to module ``DEFAULT_LANG``."""
    raw = os.environ.get("DEFAULT_LANG", "").strip().lower()
    if raw in MESSAGES:
        return raw  # type: ignore[return-value]
    return DEFAULT_LANG


__all__ = ["DEFAULT_LANG", "Lang", "MESSAGES", "detect_lang", "t"]
