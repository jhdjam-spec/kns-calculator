"""Загрузка JSON-датасета из ../02_dataset/.

Override через env var `KNS_DATASET_ROOT` — нужен для serverless-окружений
(Yandex Cloud Functions и др.), где cwd может отличаться от dev-окружения.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_env_root = os.environ.get("KNS_DATASET_ROOT")
if _env_root:
    DATASET_ROOT = Path(_env_root).resolve()
else:
    # 02_dataset/ лежит на 2 уровня выше: backend/pump_calculator/catalog.py → ../../02_dataset/
    DATASET_ROOT = Path(__file__).resolve().parents[2] / "02_dataset"


@lru_cache(maxsize=1)
def load_coefficients() -> dict[str, Any]:
    """Все таблицы коэффициентов (k_э, ζ, K_gen, скорости, AOR/POR и др.)."""
    path = DATASET_ROOT / "theory" / "coefficients.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.exception("coefficients.json corrupt or missing at %s", path)
        # Не маскируем — для коэффициентов лучше упасть громко при старте.
        raise RuntimeError(f"Coefficients dataset unavailable: {e}") from e


@lru_cache(maxsize=1)
def load_pumps() -> list[dict[str, Any]]:
    """БД насосов. При повреждении JSON возвращает [] — endpoint /health
    отдаст pumps_in_db=0, и фронт покажет maintenance message вместо 500.
    """
    path = DATASET_ROOT / "pumps" / "pumps.json"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        pumps = data.get("pumps", [])
        if not isinstance(pumps, list):
            logger.error("pumps.json malformed: 'pumps' is not a list (got %s)", type(pumps).__name__)
            return []
        return pumps
    except FileNotFoundError:
        logger.error("pumps.json not found at %s", path)
        return []
    except json.JSONDecodeError as e:
        logger.exception("pumps.json malformed JSON at %s: %s", path, e)
        return []


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
