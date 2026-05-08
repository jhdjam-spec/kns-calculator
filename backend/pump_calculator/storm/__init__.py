"""Phase 18 — Калькулятор ливневых стоков по СП 32.13330.2018 §6.

Метод предельных интенсивностей для расчёта пикового расхода Q_r,
плюс расчёт годовых и суточных объёмов W_д/W_т/W_M.

Калибровочные эталоны:
- ВБД Екатеринбург (Q_r ≈ 540 л/с при F=7.7 га, q20=80)
- РВБ Кубань Краснодар (Q_r ≈ 1168 л/с при F=7.58 га, q20=100)
- Уташ ИБИОКС (Q_r ≈ 974 л/с при F=5 га, асфальт)
- Экотехнопарк Белогорский (Q_r ≈ 44 л/с при F=2.4 га)
"""
from .models import StormInput, StormResult, SurfaceBreakdown
from .peak_flow import calculate_peak_flow, calculate_full_storm
from .annual import calculate_annual_volumes
from .design import calculate_design_volume

__all__ = [
    "StormInput",
    "StormResult",
    "SurfaceBreakdown",
    "calculate_peak_flow",
    "calculate_full_storm",
    "calculate_annual_volumes",
    "calculate_design_volume",
]
