"""Удаление фосфора (P) из сточных вод — EBPR / FeCl3 / Al2(SO4)3.

Phase 34+ (2026-05-13): закрывает P_removal-пробел PhD-Biology backlog.
Поддерживает EXT-15 phosphorus_removal в matching.py.

Theory (Metcalf & Eddy 5th §8-3 «Phosphorus Removal»):
- Бытовые стоки: P_total = 6-12 мг/л (мочевина + детергенты)
- Промстоки: до 30 мг/л (мясокомбинат, молочные, гальваника, ЦБК)
- ПДК рыбхоз (Приказ Минсельхоза №552, 13.12.2016): 0.05 мг/л
- ПДК водоёмы общего пользования (СанПиН 2.1.5.980-00): 0.2 мг/л
- ПДК для полива (СанПиН СЭ 6.04.001): 1.0 мг/л
- Сброс в гор. канализацию (ПП РФ №728 / №644): 5.0 мг/л

Методы удаления:
  * Биологическое EBPR (Enhanced Biological Phosphorus Removal, PAO bacteria
    Accumulibacter) → 80-85%. Анаэробный селектор (HRT 1-2 ч) → MLSS забирает
    PHA → аэробная фаза → накапливают полифосфаты → удаление с избыточным илом.
  * Химическое FeCl3 (Fe:P молярное 1.5-2.0): 90-98% удаления.
  * Al2(SO4)3 / PAC (Al:P = 1.2-1.5): 85-95% удаления.

Стехиометрия FeCl3 (Metcalf & Eddy §8-3, Table 8-15):
  FePO4 ↓ при pH 5-7
  mol Fe : mol P = 1.5 (с учётом конкурирующих реакций с HCO3⁻)
  M(FeCl3) = 162.2 г/моль
  M(P) = 30.97 г/моль
  → dose FeCl3 (мг/л) = ΔP (мг/л) × 1.5 × 162.2 / 30.97 ≈ ΔP × 7.85
"""
from __future__ import annotations

from typing import Literal

# ПДК фосфора (общего) по приёмнику
P_LIMITS_BY_DISCHARGE: dict[str, float] = {
    "fishery_water": 0.05,        # Приказ Минсельхоза №552
    "general_use": 0.2,            # СанПиН 2.1.5.980-00
    "reuse_irrigation": 1.0,       # СанПиН СЭ 6.04.001
    "municipal_sewage": 5.0,       # ПП РФ №728 / №644 (договор с водоканалом)
}

# Default P_in по типу стоков (Metcalf & Eddy §3-3 + ИТС 10-2015)
P_DEFAULTS_BY_WASTEWATER: dict[str, float] = {
    "domestic": 8.0,
    "industrial": 20.0,
    "drainage": 1.5,
    "clean_water": 0.05,
    "fire_protection": 0.0,
}

# Молярные массы
_M_FE = 55.85
_M_FECL3 = 162.2
_M_AL2SO4_3 = 342.15
_M_AL = 26.98
_M_P = 30.97

PRemovalMethod = Literal["fecl3", "al2so4_3", "ebpr"]


def fecl3_dose_mg_per_mg_p_removed() -> float:
    """Стехиометрия FeCl3 при Fe:P = 1.5 (Metcalf & Eddy §8-3 Table 8-15).

    Returns:
        мг FeCl3 на мг удалённого P. Должно быть ≈ 7.85.
    """
    return 1.5 * _M_FECL3 / _M_P


def al2so4_3_dose_mg_per_mg_p_removed() -> float:
    """Стехиометрия Al2(SO4)3 при Al:P = 1.5 (для устойчивого удаления).

    Returns:
        мг Al2(SO4)3 на мг удалённого P. Должно быть ≈ 8.28.
    """
    # 1 моль Al2(SO4)3 содержит 2 моль Al
    # Al:P = 1.5 → нужно 1.5 моль Al на 1 моль P → 0.75 моль Al2(SO4)3
    return 0.75 * _M_AL2SO4_3 / _M_P


def calculate_p_removal(
    p_in_mgL: float,
    target_p_mgL: float,
    method: PRemovalMethod = "fecl3",
    Q_m3_h: float | None = None,
) -> dict:
    """Расчёт необходимости и дозировки реагента для удаления P.

    Args:
        p_in_mgL: концентрация общего P на входе ЛОС, мг/л.
        target_p_mgL: целевая концентрация P на выходе (по target_discharge), мг/л.
        method: метод удаления — "fecl3" / "al2so4_3" / "ebpr".
        Q_m3_h: расход стоков (опционально), для расчёта годовой нормы реагента.

    Returns:
        dict с полями needed / method / p_in_mgL / p_target_mgL / p_remove_mgL /
        dose_mg_per_L / yearly_dose_kg_per_year (если задан Q_m3_h).

    Пример:
        p_in=8 мг/л, target=0.2 (рыбхоз) → ΔP=7.8, FeCl3=7.8×7.85≈61.2 мг/л.
        При Q=10 м³/ч → 61.2 мг/л × 10 × 24 × 365 = 5.36 т/год.
    """
    if p_in_mgL <= target_p_mgL:
        return {
            "needed": False,
            "method": None,
            "p_in_mgL": p_in_mgL,
            "p_target_mgL": target_p_mgL,
            "p_remove_mgL": 0.0,
            "dose_mg_per_L": 0.0,
            "yearly_dose_kg_per_year": 0.0,
            "reason": "P_in уже ниже целевого — реагент/EBPR не нужен",
        }

    p_remove = p_in_mgL - target_p_mgL

    if method == "fecl3":
        dose_mgL = p_remove * fecl3_dose_mg_per_mg_p_removed()
        method_note = "FeCl3 (Fe:P=1.5), pH 5-7, осадок FePO4↓"
    elif method == "al2so4_3":
        dose_mgL = p_remove * al2so4_3_dose_mg_per_mg_p_removed()
        method_note = "Al2(SO4)3 (Al:P=1.5), pH 5.5-7, осадок AlPO4↓"
    elif method == "ebpr":
        # Биологическое — реагент не нужен, но требуется анаэробный селектор
        # (HRT 1-2 ч) и аэробная фаза с DO≥2 мг/л.
        dose_mgL = 0.0
        method_note = (
            "EBPR (Bio-P), 80-85% удаления, анаэробн. селектор HRT 1-2 ч + "
            "аэроб. фаза DO≥2 мг/л + удаление избыточного ила"
        )
    else:
        raise ValueError(f"Unknown method: {method}. Use fecl3/al2so4_3/ebpr.")

    result: dict = {
        "needed": True,
        "method": method,
        "method_note": method_note,
        "p_in_mgL": p_in_mgL,
        "p_target_mgL": target_p_mgL,
        "p_remove_mgL": round(p_remove, 3),
        "dose_mg_per_L": round(dose_mgL, 2),
    }

    if Q_m3_h is not None and Q_m3_h > 0:
        # Годовая норма: dose (мг/л) × Q (м³/ч) × 24 ч × 365 сут / 1e6 (мг→кг)
        yearly_kg = dose_mgL * Q_m3_h * 24 * 365 / 1_000_000.0
        result["Q_m3_h"] = Q_m3_h
        result["yearly_dose_kg_per_year"] = round(yearly_kg, 2)

    return result


def get_p_limit(target_discharge: str | None) -> float:
    """Возвращает ПДК фосфора по типу приёмника. Default — рыбхоз (самый строгий).

    Args:
        target_discharge: один из P_LIMITS_BY_DISCHARGE или None.

    Returns:
        ПДК P в мг/л.
    """
    if target_discharge is None:
        return P_LIMITS_BY_DISCHARGE["general_use"]
    return P_LIMITS_BY_DISCHARGE.get(target_discharge, 0.2)


def get_p_default(wastewater_type: str | None) -> float:
    """Default P_in по типу стоков (когда оператор не ввёл вручную)."""
    if wastewater_type is None:
        return P_DEFAULTS_BY_WASTEWATER["domestic"]
    return P_DEFAULTS_BY_WASTEWATER.get(wastewater_type, 8.0)
