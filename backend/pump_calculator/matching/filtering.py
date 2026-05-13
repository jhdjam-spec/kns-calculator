"""Фильтры жёсткого отсева (Шаги 3-5) — wastewater_type, Q-H envelope, AOR, IP, Ex.

Соответствует matching.md §3-5. Не содержит scoring-логики — это делает
`matching.scoring`. Возвращают подмножество исходного списка `pumps`.
"""

from __future__ import annotations

import re
from typing import Any

from pump_calculator import catalog
from pump_calculator.hydraulics import aor_zone

# ----------------------- Шаг 3: жёсткий фильтр -----------------------

def filter_by_wastewater_type(
    pumps: list[dict[str, Any]], wastewater_type: str
) -> list[dict[str, Any]]:
    """Шаг 3: фильтр по свободному проходу и совместимости с типом стоков."""
    free_passage_min, allowed_impellers = catalog.get_free_passage_required_mm(wastewater_type)
    out = []
    for p in pumps:
        if p.get("_engineer_flag") == "not_recommended":
            continue
        if wastewater_type not in p.get("wastewater_compat", []):
            continue
        # NB: free_passage_mm может быть null у насосов чистой воды (booster_station,
        # CWP, жокей-насосы) — там свободный проход неприменим. Трактуем null как 0
        # (для wastewater_compat=[clean_water]/fire_protection это не блокирует, т.к.
        # для них free_passage_required=0).
        fp = p.get("free_passage_mm") or 0
        if fp < free_passage_min:
            continue
        if p.get("impeller") and p["impeller"] not in allowed_impellers:
            continue
        out.append(p)
    return out


# ----------------------- Шаг 4: Q-H envelope -----------------------

def filter_by_envelope(
    pumps: list[dict[str, Any]], Q_m3h: float, H_full_m: float
) -> list[dict[str, Any]]:
    """Шаг 4: Q ∈ [Q_min·0.85, Q_max·1.15], H_full ∈ [H_min, H_max·1.05].

    Reality: для бытовой канализации Q_клиент часто **меньше** минимума насосной
    серии (нет канализационных <5 м³/ч). Инженер ставит ближайший доступный
    канализационный с большим запасом по Q — это нормально, важнее DN ≥65 и
    free_passage. Поэтому **нижняя граница Q ослаблена до 0.05·Q_min**: насос
    «больше нужного» допускается, выше — отсекаем (overflow точно).
    """
    out = []
    for p in pumps:
        e = p["envelope"]
        # Q: насос может быть до 20× больше нужного по Q (Q_клиент ≥ 5% Q_min).
        # Это инженерная практика для бытовой канализации.
        if Q_m3h > e["Q_max_m3h"] * 1.15:
            continue
        if Q_m3h < e["Q_min_m3h"] * 0.05:
            continue
        # H: верхняя граница строгая (H_full > H_max → не дотянет).
        # Нижняя граница ослаблена для канализационных (см. КП Серво-Юг 2026:
        # H_full=1.92м, ставят KAIQUAN с H_min=6м — насос «слишком сильный»
        # допустим, только КПД ниже).
        if H_full_m > e["H_max_m"] * 1.05:
            continue
        # NB: ceiling H_max не вводим — КП Серво-Юг 2026 показывает что для
        # Q=0.5 H_full=4 ставят KAIQUAN с H_max=25 (6× запас). Защита от
        # экстремальных ЦНС (H до 1422 м) для бытовых запросов работает
        # через filter_by_wastewater_type — ЦНС имеют compat=[clean_water],
        # для domestic/drainage они уже отсеяны.
        out.append(p)
    return out


# Иерархия защиты IP — ключ для сравнения "не ниже". Используется в filter_by_ip_motor.
_IP_RANK: dict[str, int] = {"IP54": 1, "IP55": 2, "IP58": 3, "IP68": 4}


def filter_by_ip_motor(
    pumps: list[dict[str, Any]], required_ip: str | None
) -> list[dict[str, Any]]:
    """Фильтр по IP-рейтингу двигателя (L1.ip_motor).

    Если required_ip=None — фильтр не применяется (backward compat).
    Иначе оставляем только насосы с pump.power.ip_rating >= required_ip.

    NB: Если у насоса ip_rating не задан — пропускаем (НЕ отсекаем),
    чтобы не «обрубать» БД с неполной паспортизацией. Это
    консервативное поведение для текущего состояния каталога (~70% насосов
    без IP-поля), но в будущем может стать строгим (deprecation warning
    в notes).
    """
    if not required_ip or required_ip not in _IP_RANK:
        return pumps
    threshold = _IP_RANK[required_ip]
    out = []
    for p in pumps:
        pump_ip = (p.get("power") or {}).get("ip_rating")
        if not pump_ip:
            # Поле не задано — оставляем (консервативно, чтобы не вырезать пол-БД).
            out.append(p)
            continue
        if pump_ip not in _IP_RANK:
            # Странный формат IP — оставляем
            out.append(p)
            continue
        if _IP_RANK[pump_ip] >= threshold:
            out.append(p)
    return out


def filter_by_ex(
    pumps: list[dict[str, Any]],
    ex_required: bool,
    ex_zone: str | None = None,
) -> list[dict[str, Any]]:
    """Шаг 5б: фильтр по ATEX-маркировке для взрывоопасных зон.

    v0.3 (2026-05-13) — добавлено по PhD-Electrical audit P0-1
    + Sc.D. cross-domain (filter_by_ex отсутствовал, что = риск ст. 217.2 УК РФ).

    Источник: IEC 60079-0:2017 «Электроустановки во взрывоопасных зонах».
    ТР ТС 012/2011 «О безопасности оборудования для работы во взрывоопасных средах».

    Логика:
      - Если ex_required=False и ex_zone in (None, "none") — фильтр не применяется
        (выдаём все насосы, включая неEx — это обычные объекты).
      - Если ex_required=True ИЛИ ex_zone in {Zone_0, Zone_1, Zone_2, Zone_20/21/22}:
        оставляем только насосы с power.ex_rating НЕ null И НЕ "none",
        ИЛИ с явным is_ex=True, ИЛИ с "Ex"/"ATEX" в model/id (паттерн ETL).

    NB: При недостатке Ex-моделей в каталоге (≤80% БД без ex_rating) функция
    может вернуть пустой список — в pipeline это даёт пустой выход + триггер
    auto_no_match → handoff инженеру (это safe behavior, ст.217.2 УК РФ
    лучше handoff, чем wrong спецификация).
    """
    if not ex_required and (not ex_zone or ex_zone == "none"):
        return pumps
    out = []
    for p in pumps:
        power = p.get("power") or {}
        ex_rating = power.get("ex_rating")
        is_ex_flag = power.get("is_ex") or p.get("is_ex")
        model_str = str(p.get("model", "")).lower()
        id_str = str(p.get("id", "")).lower()
        # 1) Прямой флаг is_ex=True
        if is_ex_flag is True:
            out.append(p)
            continue
        # 2) ex_rating задан и не пустой
        if ex_rating and str(ex_rating).lower() not in ("none", "null", ""):
            out.append(p)
            continue
        # 3) Паттерн "Ex" в id/model (например kaiquan-50wqe-15-15-ex)
        # NB: проверяем границы слова, чтобы не путать "exempt"/"extra"
        if re.search(r"(?:^|[-_\s/])ex(?:$|[-_\s/0-9])", id_str) or \
           re.search(r"(?:^|[-_\s/])ex(?:$|[-_\s/0-9])", model_str):
            out.append(p)
            continue
        if "atex" in id_str or "atex" in model_str:
            out.append(p)
            continue
    return out


def filter_by_aor(pumps: list[dict[str, Any]], Q_m3h: float) -> list[dict[str, Any]]:
    """Шаг 5а: отсечь кандидатов вне AOR (40-150% Q_BEP).

    **Important:** AOR (ANSI/HI 9.6.3) применим к **continuous duty** —
    непрерывной работе. Канализационные погружные (submersible_sewage)
    работают в **on/off cycling** режиме (поплавковое управление, циклы
    1-5 минут), и формально могут быть «outside AOR» по моментальной точке,
    но это нормальная практика для бытовой канализации с малым притоком.

    Реальный кейс: КП Серво-Юг 2026 для Q=0.5 м³/ч ставит KAIQUAN с Q_BEP=18 —
    Q/Q_BEP = 2.8% (outside по HI), но насос пускается раз в 30 минут и
    работает в свою BEP-точку короткое время.

    Для booster_station (СПД) AOR-фильтр сохраняем — там continuous duty.
    """
    out = []
    for p in pumps:
        Q_BEP = p["envelope"].get("Q_BEP_m3h")
        if not Q_BEP:
            out.append(p)
            continue
        # Submersible sewage с pulsed duty — AOR не применяем
        if p.get("type") == "submersible_sewage":
            out.append(p)
            continue
        # Booster / clean water — continuous duty, AOR обязателен
        zone = aor_zone(Q_m3h, Q_BEP)
        if zone == "outside":
            continue
        out.append(p)
    return out
