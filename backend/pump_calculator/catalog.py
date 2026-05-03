"""Загрузка JSON-датасета из ../02_dataset/."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# 02_dataset/ лежит на 2 уровня выше: backend/pump_calculator/catalog.py → ../../02_dataset/
DATASET_ROOT = Path(__file__).resolve().parents[2] / "02_dataset"


@lru_cache(maxsize=1)
def load_coefficients() -> dict[str, Any]:
    """Все таблицы коэффициентов (k_э, ζ, K_gen, скорости, AOR/POR и др.)."""
    path = DATASET_ROOT / "theory" / "coefficients.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_pumps() -> list[dict[str, Any]]:
    """БД насосов envelope-only (14 моделей в seed)."""
    path = DATASET_ROOT / "pumps" / "pumps.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("pumps", [])


@lru_cache(maxsize=1)
def load_producers() -> list[dict[str, Any]]:
    """8 производителей с их сериями."""
    path = DATASET_ROOT / "pumps" / "producers.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_fittings() -> dict[str, Any]:
    """Шаблоны обвязки КНС/СПД с типовыми ценами 2026."""
    path = DATASET_ROOT / "fittings" / "fittings_seed.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_default_pipe_roughness_mm(material: str = "pe100_sdr17") -> float:
    """Эквивалентная шероховатость k_э (мм) по умолчанию."""
    coeffs = load_coefficients()
    return coeffs["pipe_roughness_mm"]["values"][material]["default"]


def get_standard_diameters_mm() -> list[float]:
    """Стандартный ряд диаметров напорных трубопроводов."""
    return load_coefficients()["standard_pipe_diameters_mm"]["values"]


def get_typical_obvyazka_sum_zeta() -> float:
    """Σζ для типовой обвязки КНС (4 отвода + АТМ + задвижка + обратный + выход)."""
    return load_coefficients()["local_resistance_zeta"]["typical_kns_obvyazka_sum_zeta"]["sum_zeta"]


def get_free_passage_required_mm(wastewater_type: str) -> tuple[float, list[str]]:
    """Минимальный свободный проход и допустимые типы колёс по типу стоков."""
    table = load_coefficients()["free_passage_by_wastewater_type_mm"][wastewater_type]
    return table["min"], table["impeller_types"]


def get_aor_por_limits() -> dict[str, tuple[float, float]]:
    """Зоны POR/AOR в долях от Q_BEP."""
    coeffs = load_coefficients()["ansi_hi_963_operating_regions"]
    return {
        "POR": (coeffs["POR"]["Q_min_pct_of_BEP"] / 100, coeffs["POR"]["Q_max_pct_of_BEP"] / 100),
        "AOR": (coeffs["AOR"]["Q_min_pct_of_BEP"] / 100, coeffs["AOR"]["Q_max_pct_of_BEP"] / 100),
    }
