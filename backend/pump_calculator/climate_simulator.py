"""Climate Simulator — выбор города даёт altitude/frost/climate + рекомендации.

Phase 28: построен поверх dataset 02_dataset/regulations/climate_cities_2026.json
(70 городов, источник СП 131.13330.2020 табл. 3.1, 5.1 + СП 20 + СП 14).

Функции:
- list_cities() — все города с краткой сводкой
- get_city_climate(city) — полная карточка по городу
- apply_climate_to_l1(l1, city) — автозаполнение L1.altitude_m + рекомендации

Триггеры (см. recommendations):
- frost_depth > 1500 мм → utility_insulation_required (СП 41 утепление трасс)
- t_min_5pct < -30 °C → cabinet_uhl1_required (ХЛ1 + atex_consider)
- heating_period > 200 дней → heating_cable_required (для подводящих линий)
- altitude > 1000 м → npsha_low_warning (P_atm падает с высотой)
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import structlog

from pump_calculator.catalog import DATASET_ROOT
from pump_calculator.schemas import L1Input

logger = structlog.get_logger(__name__)

CLIMATE_DATASET_PATH = DATASET_ROOT / "regulations" / "climate_cities_2026.json"


@lru_cache(maxsize=1)
def _load_climate_dataset() -> dict[str, Any]:
    """Загружает climate_cities_2026.json (lazy, кэш)."""
    try:
        with open(CLIMATE_DATASET_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("climate_cities_2026.json not found at %s", CLIMATE_DATASET_PATH)
        return {"cities": []}
    except json.JSONDecodeError as e:
        logger.exception("climate_cities_2026.json malformed: %s", e)
        return {"cities": []}


@lru_cache(maxsize=1)
def _city_index() -> dict[str, dict[str, Any]]:
    """Индекс {city_lower: record} для быстрого lookup."""
    data = _load_climate_dataset()
    return {c["city"].lower(): c for c in data.get("cities", [])}


def list_cities() -> list[dict[str, Any]]:
    """Список всех городов с краткой сводкой (для autocomplete).

    Возвращает [{city, region, climate_zone, altitude_m, frost_depth_mm}, ...].
    """
    data = _load_climate_dataset()
    return [
        {
            "city": c["city"],
            "region": c["region"],
            "climate_zone": c["climate_zone"],
            "altitude_m": c["altitude_m"],
            "frost_depth_mm": c["frost_depth_mm"],
            "t_min_5pct_c": c["t_min_5pct_c"],
            "lat": c.get("lat"),
            "lon": c.get("lon"),
        }
        for c in data.get("cities", [])
    ]


def get_city_climate(city: str) -> dict[str, Any] | None:
    """Полная карточка климата для города.

    Точное совпадение → запись. Иначе — поиск по подстроке (двусторонний).
    Возвращает None если город не найден.
    """
    if not city:
        return None
    idx = _city_index()
    key = city.strip().lower()
    if key in idx:
        return dict(idx[key])
    # Двусторонний substring match (Москва ↔ Москва область)
    for k, rec in idx.items():
        if key in k or k in key:
            return dict(rec)
    return None


def _build_recommendations(climate: dict[str, Any]) -> list[dict[str, Any]]:
    """Строит рекомендации по климату с trigger-кодами для wizard.

    Каждая рекомендация: {trigger, severity, title, detail, source}.
    """
    recs: list[dict[str, Any]] = []
    frost = climate.get("frost_depth_mm", 0)
    t_min = climate.get("t_min_5pct_c", 0)
    heating_days = climate.get("heating_period_days", 0)
    altitude = climate.get("altitude_m", 0)
    city = climate.get("city", "")

    # Утепление трасс (СП 41 / СП 32 §6.5) — суровые зимы
    if frost > 1500:
        recs.append({
            "trigger": "auto_pipe_insulation_required",
            "severity": "warning",
            "title": "Утепление подводящих/напорных трасс обязательно",
            "detail": (
                f"В {city} промерзание {frost} мм > 1500 мм — без утепления труба "
                f"замерзнёт уже в первую зиму. Минвата δ≥50 мм или ЭППС."
            ),
            "source": "СП 41-103-2000, СП 32.13330.2018 §6.5",
        })

    # ХЛ1 шкаф для экстремального холода
    if t_min < -30:
        recs.append({
            "trigger": "cabinet_uhl1_required",
            "severity": "warning",
            "title": "Шкаф управления исполнение ХЛ1 (−60 °C)",
            "detail": (
                f"t_min_5% = {t_min} °C ниже −30 °C — стандартный УХЛ4 не выдержит. "
                f"Нужен ХЛ1 + ATEX-проверка, +20–30% к цене ШУ."
            ),
            "source": "ГОСТ 15150-69, ТР ТС 010/2011",
        })

    # Греющий кабель — длинная зима
    if heating_days > 200:
        recs.append({
            "trigger": "heating_cable_required",
            "severity": "info",
            "title": "Греющий кабель на подводящих линиях",
            "detail": (
                f"Отопительный период {heating_days} дней (>200) — на участках, "
                f"которые невозможно закопать ниже промерзания, требуется "
                f"саморегулирующийся кабель 30–40 Вт/м + теплоизоляция."
            ),
            "source": "СП 41-103-2000, ПУЭ §7.4",
        })

    # NPSHa в горах
    if altitude > 1000:
        npsha_drop = round(altitude * 0.00012 * 10.33, 2)  # ~0.12 кПа/м
        recs.append({
            "trigger": "auto_npsha_low",
            "severity": "warning",
            "title": "Снижение NPSHa из-за высоты",
            "detail": (
                f"Высота {altitude} м над уровнем моря — P_atm ниже на ~{npsha_drop:.1f} м H₂O. "
                f"NPSHa может оказаться < 5 м у горячих стоков; уменьшите H_suction."
            ),
            "source": "Базовая гидравлика + СП 32.13330 §6.4",
        })

    # Снеговая нагрузка V+ — нужен прочный павильон
    snow_district = climate.get("snow_district", "")
    if snow_district in ("V", "VI", "VII", "VIII"):
        recs.append({
            "trigger": "auto_snow_load_high",
            "severity": "info",
            "title": f"Снеговой район {snow_district} — усиленный павильон",
            "detail": (
                "Снеговая нагрузка S₀ ≥ 3.2 кПа — для павильона над КНС нужен "
                "расчёт прочности по СП 20 §10 и угол ската ≥ 30° для самосброса."
            ),
            "source": "СП 20.13330.2016 + Изм.№4 2024, табл. 10.1",
        })

    return recs


def apply_climate_to_l1(l1: L1Input | None, city: str) -> tuple[L1Input, list[dict[str, Any]]]:
    """Автозаполнение L1 + рекомендации по городу.

    Поведение:
    - Если l1 is None → создаём пустой L1Input.
    - Если l1.altitude_m уже задан вручную → НЕ перезаписываем.
    - Возвращает (обновлённый L1, рекомендации).
    """
    if l1 is None:
        l1 = L1Input()

    climate = get_city_climate(city)
    if climate is None:
        return l1, [{
            "trigger": "city_not_found",
            "severity": "info",
            "title": f"Город '{city}' не найден в БД",
            "detail": "Использованы значения по умолчанию. Заполните altitude_m вручную для горных регионов.",
            "source": "climate_cities_2026.json",
        }]

    # Автозаполнение altitude_m (только если не задан)
    if l1.altitude_m is None:
        l1 = l1.model_copy(update={"altitude_m": float(climate["altitude_m"])})

    recs = _build_recommendations(climate)
    return l1, recs
