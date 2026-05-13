"""Денитрификация: NO3 → N2 в анаэробной зоне аэротенка.

Phase 34+ (2026-05-13): закрывает denitrification-пробел PhD-Biology backlog.
Поддерживает EXT-16 denitrification в matching.py (срабатывает ПОСЛЕ EXT-9
nitrification — нельзя денитрифицировать без преобразования NH4 → NO3 на
первом этапе).

Theory (Henze IWA 2008 «Biological Wastewater Treatment» §3.5 + Metcalf & Eddy 5th §8-7):
- Гетеротрофные денитрификаторы (Pseudomonas, Achromobacter и др.) восстанавливают
  NO3⁻ → NO2⁻ → NO → N2O → N2↑ в отсутствие O2.
- ПДК NO3 (по N):
    * рыбхоз (Приказ Минсельхоза №552): 40 мг/л
    * общего пользования (СанПиН 2.1.5.980-00): 45 мг/л
    * полив (СанПиН СЭ 6.04.001): 50 мг/л
    * городская канализация (ПП РФ №728 / №644): 80 мг/л
- C:N ratio для гетеротрофной денитрификации: BOD5/NO3-N ≥ 4-5 (Metcalf §8-7).
  При меньшем C:N — дозировать внешний углерод (метанол / ацетат / глицерин).
- Recycle ratio R = (NO3_in - NO3_out) / NO3_out, типично 100-400%.
  Рециркуляция нитратов из аэробной зоны в аноксическую (pre-DN, Ludzack-Ettinger).
- T-коррекция Arrhenius θ_DN = 1.07 (медленнее нитрификации; θ_NH = 1.103).

Доза метанола (Metcalf & Eddy §8-7 eq. 8-21):
  CH3OH : NO3-N = 2.47 г CH3OH / г NO3-N
  (с учётом эндогенного расходования и стехиометрии C5H7NO2)

Объём аноксической зоны (Ludzack-Ettinger 1962, MLE):
  V_anoxic / V_aerobic ≈ 0.25-0.5 (HRT 1-3 ч)
"""
from __future__ import annotations

# ПДК NO3 (как мг N/л) по приёмнику
NO3_LIMITS_BY_DISCHARGE: dict[str, float] = {
    "fishery_water": 40.0,        # Приказ Минсельхоза №552
    "general_use": 45.0,           # СанПиН 2.1.5.980-00
    "reuse_irrigation": 50.0,      # СанПиН СЭ 6.04.001
    "municipal_sewage": 80.0,      # ПП РФ №728 / №644
}

# Стехиометрия (Metcalf & Eddy §8-7 Table 8-21)
_CH3OH_PER_NO3_N = 2.47
_THETA_DN = 1.07  # Arrhenius T-correction для денитрификации (медленнее нитри)
_MAX_RECYCLE_PCT = 400.0  # практический предел рециркуляции (Henze §3.5)
_MIN_CN_RATIO = 4.0  # порог дозировки внешнего C-источника


def calculate_denitrification(
    no3_in_mgL: float,
    target: str,
    bod5_in_mgL: float,
    T_c: float = 20.0,
    no3_target_override: float | None = None,
) -> dict:
    """Расчёт денитрификации и потребности в метаноле.

    Args:
        no3_in_mgL: концентрация NO3-N на входе аноксической зоны, мг/л.
            При полной нитрификации NH4_in (= no3_in после аэробной зоны).
        target: target_discharge ("fishery_water" / "general_use" / ...).
        bod5_in_mgL: БПК5 на входе ЛОС, мг/л (как источник углерода).
        T_c: температура жидкости, °C (default 20).
        no3_target_override: явный целевой NO3 на выходе, перекрывает таблицу.

    Returns:
        dict с полями needed / no3_in_mgL / no3_target_mgL / cn_ratio /
        methanol_needed / methanol_dose_mgL / recycle_ratio_pct /
        T_correction / V_anoxic_to_aerobic_ratio.

    Пример:
        NH4 после нитрификации 100 мг/л, target=рыбхоз (40), BOD5=500, T=20.
        cn_ratio = 500/100 = 5 ≥ 4 → метанол не нужен.
        recycle = (100-40)/40 = 150%.
    """
    no3_limit = (
        no3_target_override
        if no3_target_override is not None
        else NO3_LIMITS_BY_DISCHARGE.get(target, 45.0)
    )

    if no3_in_mgL <= no3_limit:
        return {
            "needed": False,
            "no3_in_mgL": no3_in_mgL,
            "no3_target_mgL": no3_limit,
            "reason": "NO3_in уже ниже ПДК — денитрификация не нужна",
        }

    no3_remove = no3_in_mgL - no3_limit

    cn_ratio = bod5_in_mgL / no3_in_mgL if no3_in_mgL > 0 else 0.0
    methanol_needed = cn_ratio < _MIN_CN_RATIO
    methanol_dose_mgL = no3_remove * _CH3OH_PER_NO3_N if methanol_needed else 0.0

    # Рециркуляция нитратов (MLE pre-denitrification)
    recycle_ratio = (no3_in_mgL - no3_limit) / no3_limit if no3_limit > 0 else 0.0
    recycle_pct = min(recycle_ratio * 100, _MAX_RECYCLE_PCT)

    # Arrhenius T-correction (k_DN при T = k_DN(20) × θ^(T-20))
    T_correction = _THETA_DN ** (T_c - 20.0)

    # Объёмное соотношение аноксической/аэробной зоны (MLE)
    # При нагрузке NO3-N 5 кг/кгMLSS·сут и MLSS 3.5 г/л → V_an/V_aer ≈ 0.3
    v_ratio = 0.3 if no3_remove < 30 else 0.5

    return {
        "needed": True,
        "no3_in_mgL": no3_in_mgL,
        "no3_target_mgL": no3_limit,
        "no3_remove_mgL": round(no3_remove, 2),
        "cn_ratio": round(cn_ratio, 2),
        "methanol_needed": methanol_needed,
        "methanol_dose_mgL": round(methanol_dose_mgL, 2),
        "recycle_ratio_pct": round(recycle_pct, 1),
        "T_correction": round(T_correction, 3),
        "T_c": T_c,
        "V_anoxic_to_aerobic_ratio": v_ratio,
        "target": target,
    }


def get_no3_limit(target_discharge: str | None) -> float:
    """ПДК NO3-N по типу приёмника. Default — общего пользования."""
    if target_discharge is None:
        return NO3_LIMITS_BY_DISCHARGE["general_use"]
    return NO3_LIMITS_BY_DISCHARGE.get(target_discharge, 45.0)
