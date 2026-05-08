"""БД 36 городов РФ с климатологическими параметрами для расчёта ливневок.

Источники: СП 131.13330.2020 (h_warm, h_cold, T_min_5%); СП 32.13330.2018 прил. А
(q20, n, mr — Курганов А.М. «Расчёт дождевого стока»); СП 33-101-2003 (Cv, Cs);
СП 20.13330.2016 (snow/wind зоны); СП 14.13330.2018 ОСР-2015 (сейсмика).

Данные собраны через multi-agent research 2026-05-08, raw JSON:
02_dataset/storm_research_raw/02_climate_db_36_cities.json
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Путь к JSON БД (на 1 уровень выше backend/)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DB_PATH = _REPO_ROOT / "02_dataset" / "storm_research_raw" / "02_climate_db_36_cities.json"


@lru_cache(maxsize=1)
def _load_db() -> dict:
    """Загрузить БД городов (закешировано)."""
    with open(_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_city(name: str) -> dict | None:
    """Получить параметры города по имени (case-insensitive)."""
    db = _load_db()
    name_norm = name.strip().lower()
    for city in db["cities"]:
        if city["name"].lower() == name_norm:
            return city
    return None


def list_cities() -> list[str]:
    """Список доступных городов."""
    db = _load_db()
    return [c["name"] for c in db["cities"]]


def get_q20(city: str) -> float | None:
    """q20, л/с·га для города."""
    c = get_city(city)
    return c["q20_l_s_ha"] if c else None


def get_n(city: str) -> float | None:
    """Показатель степени n из формулы A."""
    c = get_city(city)
    return c["n"] if c else None


def get_mr(city: str) -> int | None:
    """Среднее число дождей в год."""
    c = get_city(city)
    return c["mr"] if c else None


def get_climate_params(city: str) -> dict | None:
    """Все параметры одной выборкой."""
    return get_city(city)


def get_gamma(city: str, default: float = 1.54) -> float:
    """γ показатель степени по табл. Б.4 СП 32 §6.2.4 (Phase 18.2).

    Юг ЕТР, Кавказ, Крым, Дальний Восток (приморский климат): γ=1.82
    Центр ЕТР, Поволжье, Урал, Сибирь, Северо-Запад: γ=1.54
    """
    c = get_city(city)
    if c is None:
        return default
    return c.get("gamma", default)
