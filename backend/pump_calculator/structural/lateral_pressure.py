"""Боковое давление грунта на стенку корпуса КНС.

По СП 22.13330.2016 §5.6 «Расчёт оснований по деформациям и устойчивости»:

  • Активное (рабочее):    σ_a = γ·z·K_a + γ_w·z_w
  • Пассивное (отпор):     σ_p = γ·z·K_p
  • В покое (at-rest):     σ_0 = γ·z·K_0

Где:
  γ   — удельный вес грунта (кН/м³)
  z   — глубина точки от поверхности грунта (м)
  K_a — коэффициент активного давления = tan²(45° − φ/2)
  K_p — коэффициент пассивного давления = tan²(45° + φ/2)
  K_0 — коэффициент покоя = 1 − sin(φ)  (Jaky 1944)
  γ_w — удельный вес воды (9.80665 кН/м³, ISO 80000-3)
  z_w — высота столба грунтовых вод над точкой (м)

Когда что применять (СП 22 §5.6.2-5.6.5):
  K_a — стенка может смещаться от грунта (отдельно стоящий корпус
        без жёсткого пригруза); консервативно для проверки прочности.
  K_0 — стенка зафиксирована (ж/б обойма, плита-пригруз, шпунт);
        промежуточное значение.
  K_p — проверка «откол грунта» когда выкопана соседняя траншея
        и стенка КНС не может больше опираться на пассивный отпор.

Источники:
  • СП 22.13330.2016 §5.6 — cntd.ru/document/456054206
  • Цытович «Механика грунтов» (1983), §5.4
  • Coulomb 1776 / Jaky 1944
  • ISO 80000-3 (g = 9.80665 м/с² → γ_w = 9.80665 кН/м³)
"""
from __future__ import annotations

from dataclasses import dataclass

from .ground_context import GroundContext

# ISO 80000-3: standard gravitational acceleration g₀ = 9.80665 м/с².
# Унифицировано во всём проекте 2026-05-13 (Sc.D. audit P1-1).
GRAVITY: float = 9.80665
GAMMA_WATER_KN_M3: float = 9.80665  # γ_w для пресной воды

# Допустимые напряжения долговременной прочности ПЭ100 (ISO 9080:2012 +
# ГОСТ 18599-2001) — для боковой нагрузки на стенку корпуса.
PE100_SDR17_ADMISSIBLE_KPA: float = 50.0
PE100_SDR11_ADMISSIBLE_KPA: float = 80.0

# Коэффициент трения грунт-стенка ПЭ (δ ≈ 0.4·φ для бетон/полимер;
# Sc.D. audit cross-domain P0 — нужно использовать в EXT-11).
WALL_FRICTION_RATIO: float = 0.4


@dataclass
class LateralPressure:
    """Боковое давление грунта на стенку корпуса КНС на глубине z.

    Все компоненты — в кПа.
    """
    z_m: float                            # глубина точки от поверхности
    active_kPa: float                     # σ_a = γ·z·K_a (грунт)
    passive_kPa: float                    # σ_p = γ·z·K_p (отпор)
    at_rest_kPa: float                    # σ_0 = γ·z·K_0
    water_component_kPa: float            # σ_w = γ_w·z_w (гидростатика УГВ)
    total_active_with_water_kPa: float    # σ_a + σ_w — для проверки прочности


def calculate_pressure(ctx: GroundContext, z_m: float) -> LateralPressure:
    """Рассчитать боковое давление грунта на глубине z.

    Args:
      ctx: GroundContext (тип грунта + УГВ + глубина корпуса).
      z_m: Глубина точки от поверхности земли (м). Обычно z = install_depth
        для проверки нагрузки на дно стенки.

    Returns:
      LateralPressure с компонентами σ_a, σ_p, σ_0, σ_w и суммой.
    """
    if z_m < 0:
        z_m = 0.0

    gamma = ctx.gamma_kN_m3
    sigma_a = gamma * z_m * ctx.K_a
    sigma_p = gamma * z_m * ctx.K_p
    sigma_0 = gamma * z_m * ctx.K_0

    # Гидростатика грунтовых вод (СП 22 §5.6.5):
    # на глубине z считается столб воды от точки z вверх до УГВ.
    #   - bottom-of-corpus уровень = install_depth_m
    #   - УГВ относительно поверхности = -groundwater_level_m (вглубь)
    #     gwl=-3 → УГВ на 3 м ниже земли
    #   - На глубине z воды есть, если z > -groundwater_level_m
    #     (т.е. z глубже отметки УГВ).
    gwl_depth_from_surface = -ctx.groundwater_level_m  # м, положит. вниз
    z_w = max(0.0, z_m - gwl_depth_from_surface)
    sigma_w = GAMMA_WATER_KN_M3 * z_w

    return LateralPressure(
        z_m=z_m,
        active_kPa=sigma_a,
        passive_kPa=sigma_p,
        at_rest_kPa=sigma_0,
        water_component_kPa=sigma_w,
        total_active_with_water_kPa=sigma_a + sigma_w,
    )


def check_corpus_strength(
    ctx: GroundContext,
    z_max_m: float | None = None,
    sigma_allowable_kPa: float = PE100_SDR17_ADMISSIBLE_KPA,
    safety_factor_required: float = 1.2,
) -> dict:
    """Проверить ПЭ-корпус на боковую нагрузку грунта + УГВ.

    Args:
      ctx: GroundContext.
      z_max_m: Глубина проверки (м). По умолчанию = ctx.install_depth_m
        (низ корпуса = максимальное давление).
      sigma_allowable_kPa: Допустимое напряжение долговременной прочности
        материала (по умолчанию ПЭ100 SDR17 — 50 кПа по ISO 9080).
      safety_factor_required: Требуемый коэффициент запаса (СП 22 §5.4 +
        СП 31 для I категории = 1.2).

    Returns:
      dict с результатом проверки и breakdown давлений.
    """
    if z_max_m is None:
        z_max_m = ctx.install_depth_m

    p = calculate_pressure(ctx, z_max_m)
    sigma_total = p.total_active_with_water_kPa
    sf = sigma_allowable_kPa / sigma_total if sigma_total > 0 else float("inf")

    # Рекомендуемое усиление если SF < 1.2
    recommendation: str
    if sf >= safety_factor_required:
        recommendation = "PE100 SDR17 OK"
    elif sigma_total <= PE100_SDR11_ADMISSIBLE_KPA / safety_factor_required:
        recommendation = "Upgrade to PE100 SDR11 (σ_доп=80 кПа)"
    else:
        recommendation = "Ribs / RC jacket required (σ_x > 80 кПа)"

    return {
        "depth_m": z_max_m,
        "soil_label": ctx.label,
        "sigma_total_kPa": round(sigma_total, 2),
        "sigma_allowable_kPa": sigma_allowable_kPa,
        "safety_factor": round(sf, 3) if sf != float("inf") else None,
        "safety_factor_required": safety_factor_required,
        "passes": sf >= safety_factor_required,
        "needs_reinforcement": sf < safety_factor_required,
        "recommendation": recommendation,
        "pressure_breakdown": {
            "soil_active_kPa": round(p.active_kPa, 2),
            "soil_at_rest_kPa": round(p.at_rest_kPa, 2),
            "passive_resistance_kPa": round(p.passive_kPa, 2),
            "water_kPa": round(p.water_component_kPa, 2),
        },
        "ground_context": {
            "soil_type": ctx.soil_type,
            "gamma_kN_m3": ctx.gamma_kN_m3,
            "phi_deg": ctx.phi_deg,
            "K_a": round(ctx.K_a, 3),
            "K_p": round(ctx.K_p, 3),
            "K_0": round(ctx.K_0, 3),
            "groundwater_level_m": ctx.groundwater_level_m,
            "gwl_above_bottom_m": round(ctx.gwl_above_bottom_m, 2),
        },
    }


def wall_friction_force_kN(
    ctx: GroundContext,
    wall_area_m2: float,
    z_avg_m: float | None = None,
) -> float:
    """Сила трения грунта по стенке корпуса (для EXT-11 anti-buoyancy).

    Sc.D. cross-domain P0: «нужна F_трения = 0.4 × σ_a × A_wall»
    (механика грунтов: δ = 0.4·φ для контакта грунт-полимер).

    Args:
      ctx: GroundContext.
      wall_area_m2: Площадь стенки корпуса в контакте с грунтом (м²).
      z_avg_m: Средняя глубина по высоте стенки (м). По умолчанию
        половина install_depth (треугольное распределение давления).

    Returns:
      Сила трения F (кН), направленная вверх при подъёме корпуса
      (т.е. добавляется к удерживающим силам в anti-buoyancy).
    """
    if z_avg_m is None:
        z_avg_m = ctx.install_depth_m / 2.0
    sigma_a_avg = ctx.gamma_kN_m3 * z_avg_m * ctx.K_a  # кПа
    F = WALL_FRICTION_RATIO * sigma_a_avg * wall_area_m2  # кН/м² × м² = кН
    return F


__all__ = [
    "GRAVITY",
    "GAMMA_WATER_KN_M3",
    "PE100_SDR11_ADMISSIBLE_KPA",
    "PE100_SDR17_ADMISSIBLE_KPA",
    "WALL_FRICTION_RATIO",
    "LateralPressure",
    "calculate_pressure",
    "check_corpus_strength",
    "wall_friction_force_kN",
]
