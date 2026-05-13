"""GroundContext — единый объект для soil + groundwater + temperature.

Sc.D. audit 2026-05-13 (reference_kns_scd_hydraulics_mechanics_2026-05-13.md):
«N×M связность soil/gwl/T между 5 модулями — нужен единый объект GroundContext».

Используется:
  • EXT-1 (lateral_pressure) — σ_x = γ·z·K_a + γ_w·z_w
  • EXT-11 (anti-buoyancy) — F_трения по стенке, K_a, γ_w·z_w
  • R_заземления (ПУЭ 1.7) — удельное сопротивление грунта
  • bearing wear / vibration (косвенно через soil_seismic)

Источники:
  • СП 22.13330.2016 «Основания зданий и сооружений», таблица А.1
    (cntd: https://docs.cntd.ru/document/456054206)
  • coefficients.json → soil_parameters_sp22 (single source of truth для γ/φ/K_a)
  • IEC 60079-10-1 / IEC 60079-10-2 — Ex-зоны (не входит, но согласуется
    с L1.ex_zone_class / ex_temp_class)

Принципы:
  • frozen dataclass — immutable, безопасно передавать по слоям.
  • Backward compat: L1.soil_type=None → "sand_medium" (старый K_a=0.33).
  • Все γ, φ, K_a, K_p, K_0, resistivity — производные от soil_type
    и читаются из coefficients.json (если не загружен — fallback к
    встроенному словарю — soil_parameters_sp22 table А.1).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

SoilType = Literal[
    "sand_dense", "sand_medium", "sand_loose", "sand_water_saturated",
    "loam", "clay_hard", "clay_plastic", "clay_soft", "peat",
]

# ────────────────────────────────────────────────────────────────────────
# Параметры грунтов (СП 22.13330.2016 табл. А.1)
# Дублируем coefficients.json `soil_parameters_sp22` для standalone-режима
# (если файл не доступен — структура должна работать всё равно).
# ────────────────────────────────────────────────────────────────────────
_SOIL_FALLBACK: dict[str, dict[str, float | str]] = {
    "sand_dense":           {"gamma": 18.0, "phi": 38, "c_kPa": 1,  "K_a": 0.24, "label": "Песок плотный"},
    "sand_medium":          {"gamma": 18.0, "phi": 30, "c_kPa": 0,  "K_a": 0.33, "label": "Песок ср. плотности (default)"},
    "sand_loose":           {"gamma": 16.0, "phi": 25, "c_kPa": 0,  "K_a": 0.41, "label": "Песок рыхлый"},
    "sand_water_saturated": {"gamma":  8.0, "phi": 28, "c_kPa": 0,  "K_a": 0.36, "label": "Песок водонасыщенный"},
    "loam":                 {"gamma": 19.0, "phi": 22, "c_kPa": 15, "K_a": 0.45, "label": "Суглинок"},
    "clay_hard":            {"gamma": 19.0, "phi": 22, "c_kPa": 60, "K_a": 0.45, "label": "Глина твёрдая"},
    "clay_plastic":         {"gamma": 18.0, "phi": 15, "c_kPa": 30, "K_a": 0.59, "label": "Глина пластичная"},
    "clay_soft":            {"gamma": 18.0, "phi": 12, "c_kPa": 15, "K_a": 0.65, "label": "Глина мягкопластичная"},
    "peat":                 {"gamma": 11.0, "phi": 10, "c_kPa": 5,  "K_a": 0.70, "label": "Торф"},
}

# Удельное электрическое сопротивление грунта (Ом·м), ПУЭ 1.7.103, Табл. 1.7.4.
# Используется для расчёта R_заземления (ЭО.1 заземлитель). Source:
# ПУЭ 7-е изд. §1.7 + ГОСТ 12.1.030-81.
_RESISTIVITY_OHM_M: dict[str, float] = {
    "sand_dense":            500.0,  # 100–1000, типовое для сухого песка
    "sand_medium":           300.0,  # 100–500
    "sand_loose":            400.0,
    "sand_water_saturated":   80.0,  # водонасыщенный — резко падает
    "loam":                   60.0,  # 30–100
    "clay_hard":              40.0,
    "clay_plastic":           30.0,
    "clay_soft":              20.0,  # 10–50
    "peat":                   25.0,  # 10–50
}


@lru_cache(maxsize=1)
def _load_soil_table() -> dict[str, dict[str, Any]]:
    """Загрузить soil_parameters_sp22 из coefficients.json (single source).

    Если файл не найден — fallback к встроенному словарю.
    Кеш — потому что таблица не меняется.
    """
    # backend/pump_calculator/structural/ground_context.py
    #  → backend/pump_calculator/structural
    #  → backend/pump_calculator
    #  → backend
    #  → kns-calculator-repo
    repo_root = Path(__file__).resolve().parents[3]
    coef_path = repo_root / "02_dataset" / "theory" / "coefficients.json"
    if not coef_path.exists():
        return _SOIL_FALLBACK  # type: ignore[return-value]
    try:
        data = json.loads(coef_path.read_text(encoding="utf-8"))
        soil = data.get("soil_parameters_sp22", {}).get("values", {})
        if not soil:
            return _SOIL_FALLBACK  # type: ignore[return-value]
        # Нормализуем ключи к ожидаемой схеме (gamma/phi/K_a).
        out: dict[str, dict[str, Any]] = {}
        for key, row in soil.items():
            out[key] = {
                "gamma": float(row.get("gamma_kN_m3", _SOIL_FALLBACK[key]["gamma"])),  # type: ignore[index]
                "phi": float(row.get("phi_deg", _SOIL_FALLBACK[key]["phi"])),  # type: ignore[index]
                "c_kPa": float(row.get("c_kPa", _SOIL_FALLBACK[key].get("c_kPa", 0))),  # type: ignore[arg-type]
                "K_a": float(row.get("K_a", _SOIL_FALLBACK[key]["K_a"])),  # type: ignore[index]
                "label": str(row.get("label", _SOIL_FALLBACK[key]["label"])),  # type: ignore[index]
            }
        return out
    except (json.JSONDecodeError, OSError, KeyError, ValueError):
        return _SOIL_FALLBACK  # type: ignore[return-value]


@dataclass(frozen=True)
class GroundContext:
    """Единый объект для soil + groundwater + temperature.

    Используется EXT-1 (lateral pressure), EXT-11 (anti-buoyancy),
    R_заземления (resistivity), bearing wear (vibration).

    Attributes:
      soil_type: Тип грунта по СП 22.13330.2016 таб. А.1
        (default sand_medium = старый K_a=0.33).
      groundwater_level_m: Отметка УГВ относительно земли, м.
        Отрицательная = ниже земли (default -5.0 — далёкий УГВ).
        Положительная = выше земли (площадка затоплена).
      liquid_temp_c: Температура жидкости/воздуха в корпусе (°C).
      install_depth_m: Глубина установки корпуса (низ дна от земли), м.
    """
    soil_type: SoilType = "sand_medium"
    groundwater_level_m: float = -5.0  # отрицательное = ниже земли
    liquid_temp_c: float = 20.0
    install_depth_m: float = 3.0

    # ── geo-mechanical properties ──────────────────────────────────────

    @property
    def gamma_kN_m3(self) -> float:
        """Удельный вес грунта γ (кН/м³) по СП 22.13330.2016 Табл. А.1.

        Для sand_water_saturated — эффективный (γ' = γ - γ_w = 8 кН/м³).
        """
        return float(_load_soil_table()[self.soil_type]["gamma"])

    @property
    def phi_deg(self) -> float:
        """Угол внутреннего трения φ (град) по СП 22.13330 А.1."""
        return float(_load_soil_table()[self.soil_type]["phi"])

    @property
    def cohesion_kPa(self) -> float:
        """Удельное сцепление c (кПа) по СП 22 А.1.

        Для глин — значим (15-60 кПа). Для песков ≈ 0.
        """
        return float(_load_soil_table()[self.soil_type]["c_kPa"])

    @property
    def label(self) -> str:
        """Человеко-читаемая метка типа грунта."""
        return str(_load_soil_table()[self.soil_type]["label"])

    @property
    def K_a(self) -> float:
        """Активное давление по Кулону: K_a = tan²(45° - φ/2).

        Минимально опасный коэффициент — для расчёта прочности корпуса
        используется в формуле σ_a = γ·z·K_a.
        """
        phi_rad = math.radians(self.phi_deg)
        return math.tan(math.pi / 4 - phi_rad / 2) ** 2

    @property
    def K_p(self) -> float:
        """Пассивное давление: K_p = tan²(45° + φ/2).

        Максимальный коэффициент — отпор грунта при попытке выпучить
        стенку. Используется для проверки «откол грунта» при откопе
        траншеи (когда соседняя стенка снята).
        """
        phi_rad = math.radians(self.phi_deg)
        return math.tan(math.pi / 4 + phi_rad / 2) ** 2

    @property
    def K_0(self) -> float:
        """Покой (at-rest): K_0 = 1 − sin(φ) (формула Jaky 1944).

        Применяется когда корпус не может смещаться (жёсткое крепление,
        пригруз, ж/б обойма). Между K_a и K_p.
        """
        return 1 - math.sin(math.radians(self.phi_deg))

    # ── groundwater geometry ───────────────────────────────────────────

    @property
    def gwl_above_bottom_m(self) -> float:
        """Высота столба грунтовых вод над дном корпуса (м).

        Положительная — УГВ выше дна (нужна гидростатика σ_w = γ_w·z_w).
        0 — УГВ ниже или на уровне дна.

        z_w = install_depth + gwl  (gwl отрицателен, если ниже земли).
        Пример: install_depth=5 м, gwl=-3 м (3 м ниже земли) →
        z_w = 5 - 3 = 2 м (УГВ на 2 м выше дна корпуса).
        """
        return max(0.0, self.install_depth_m + self.groundwater_level_m)

    @property
    def is_submerged(self) -> bool:
        """Корпус частично/полностью под УГВ → нужен пригруз и σ_w."""
        return self.gwl_above_bottom_m > 0.0

    # ── electrical / thermal ───────────────────────────────────────────

    @property
    def resistivity_ohm_m(self) -> float:
        """Удельное сопротивление грунта для R_заземления (Ом·м).

        Источник: ПУЭ 7-е изд. §1.7.103, ГОСТ 12.1.030-81.
        Песок: 100-500, глина: 20-100, торф: 10-50.
        """
        return _RESISTIVITY_OHM_M.get(self.soil_type, 300.0)

    # ── factory ────────────────────────────────────────────────────────

    @classmethod
    def from_l1(cls, l1: Any) -> GroundContext:
        """Построить из L1Input объекта.

        Все поля опциональные — если None, берём дефолты.
        Backward compat: L1=None → дефолт sand_medium / gwl=-5 / T=20 / 3 м.
        """
        if l1 is None:
            return cls()

        soil = getattr(l1, "soil_type", None) or "sand_medium"
        gwl = getattr(l1, "groundwater_level_m", None)
        if gwl is None:
            gwl = -5.0
        temp = getattr(l1, "liquid_temp_c", None)
        if temp is None:
            temp = 20.0
        depth_mm = getattr(l1, "install_depth_inlet_mm", None)
        depth_m = (depth_mm / 1000.0) if depth_mm else 3.0

        return cls(
            soil_type=soil,
            groundwater_level_m=float(gwl),
            liquid_temp_c=float(temp),
            install_depth_m=float(depth_m),
        )


__all__ = ["GroundContext", "SoilType"]
