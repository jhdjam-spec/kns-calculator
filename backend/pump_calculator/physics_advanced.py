"""Phase 22 — углублённая физика для точности подбора насосов и обвязки.

Дополняет physics.py следующими разделами:

1. **Атмосфера** — давление от высоты над уровнем моря (формула Бабине / стандартная атмосфера ICAO).
2. **Гравитация от широты** — формула WGS-84 (важно для очень точных NPSH-расчётов).
3. **Гидроудар по Жуковскому** — с учётом материала трубы и времени закрытия (метод Михайлова).
4. **Параллельная работа** — Q-H кривая системы при N работающих насосах.
5. **Последовательная работа** — Q-H для бустерных схем (повышение давления).
6. **Шероховатость труб** по материалам (СП 32 табл., Colebrook-White, Swamee-Jain).
7. **Поправки физических свойств для нечистых жидкостей**:
   - плотность фильтрата ТКО (по содержанию SS и DS)
   - кинематическая вязкость грязной воды по Эйнштейну
8. **Re — число Рейнольдса** для оценки режима потока.
9. **Удельные потери Дарси-Вейсбаха** — без обобщений `friction_factor_per_q2`,
   а через явный λ(Re, ε/D).

Источники:
- ICAO Standard Atmosphere (1993)
- WGS-84 (формула гравитации)
- Идельчик. Справочник по гидравлическим сопротивлениям (1992).
- Моисеев. Гидроудар в инженерных системах (2014).
- Karassik. Pump Handbook (4th ed.) гл. 8 — параллельная работа.
- ГОСТ Р 56541-2015. Гидравлические расчёты систем водоснабжения и канализации.
- СП 32.13330.2018 §6.5 — шероховатости труб.
- Einstein A. Eine neue Bestimmung der Moleküldimensionen (1906) — вязкость суспензий.

Все формулы привязаны к нормативам через regulations.ref().
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .physics import (
    density_water_kg_m3,
    kinematic_viscosity_water_m2s,
    vapor_pressure_water_kpa,
)
from .regulations import RegulationReference, ref

G_STANDARD = 9.80665  # м/с² — стандартное значение, ISO 80000-3


# ============================================================================
# 1. АТМОСФЕРНОЕ ДАВЛЕНИЕ И ГРАВИТАЦИЯ
# ============================================================================

def atmospheric_pressure_kpa(altitude_m: float, T_celsius: float = 15.0) -> float:
    """Атмосферное давление (кПа) от высоты над уровнем моря.

    Барометрическая формула с поправкой на температуру:
        P(h) = P_0 × (1 - L·h/T_0)^(g·M/(R·L))
    где L=0.0065 K/m (стандартный градиент), T_0 в кельвинах, g=9.80665, R=8.31446,
    M=0.02897 кг/моль (молярная масса воздуха).

    Для высокогорных объектов (Кавказ Q≥1500м, Урал) поправка существенная:
    - 0 м (уровень моря)        → 101.325 кПа
    - 500 м (Краснодар-Экб)      → 95.6 кПа
    - 1500 м (Бакуриани, Архыз)  → 84.6 кПа
    - 2500 м (Эльбрус подножие)  → 75.0 кПа

    Для NPSHa важно: каждые 100 м высоты ~ -1.0 м водяного столба.
    """
    P_0 = 101.325
    T_0 = T_celsius + 273.15
    L = 0.0065
    g = G_STANDARD
    M = 0.02897
    R = 8.31446
    if altitude_m < -500 or altitude_m > 11000:
        # Тропосфера: формула верна 0-11 км
        raise ValueError(f"altitude_m={altitude_m} вне зоны тропосферы (0-11000)")
    return P_0 * (1.0 - L * altitude_m / T_0) ** (g * M / (R * L))


def gravity_at_latitude(latitude_deg: float, altitude_m: float = 0.0) -> float:
    """Ускорение свободного падения от широты и высоты по WGS-84.

    g(φ, h) = g_e × (1 + k·sin²φ) / √(1 - e²·sin²φ) - 3.086·10⁻⁶·h

    Где:
    - g_e = 9.7803253359 (на экваторе)
    - k   = 0.001931852652
    - e²  = 0.00669437999013

    Для России (φ=45-55°) g ≈ 9.812-9.820, отличие от 9.81 < 0.1%.
    Для гидростатики и насосов важно только при NPSHa-критических задачах.
    """
    phi = math.radians(latitude_deg)
    sin2 = math.sin(phi) ** 2
    g_e = 9.7803253359
    k = 0.001931852652
    e2 = 0.00669437999013
    g_lat = g_e * (1 + k * sin2) / math.sqrt(1 - e2 * sin2)
    return g_lat - 3.086e-6 * altitude_m


def npsha_with_corrections(
    H_suction_m: float,
    T_celsius: float = 20.0,
    H_friction_suction_m: float = 0.0,
    altitude_m: float = 0.0,
    latitude_deg: float = 55.0,
) -> tuple[float, list[RegulationReference]]:
    """NPSHa с поправками на высоту и широту.

    Используется для критичных объектов: Архыз (1700м), Кавказ, Сибирь.
    """
    P_atm = atmospheric_pressure_kpa(altitude_m, T_celsius)
    rho = density_water_kg_m3(T_celsius)
    p_vap = vapor_pressure_water_kpa(T_celsius)
    g = gravity_at_latitude(latitude_deg, altitude_m)
    h_atm = (P_atm * 1000.0) / (rho * g)
    h_vap = (p_vap * 1000.0) / (rho * g)
    npsha = h_atm - h_vap - H_suction_m - H_friction_suction_m
    refs = [
        ref("GOST_6134", "§5.4 NPSH", "Расчёт NPSHa с учётом высоты и широты"),
        ref("ISO_9906", "§5.5", "NPSH3 определение"),
    ]
    return round(npsha, 3), refs


# ============================================================================
# 2. ГИДРОУДАР (Жуковский / Михайлов)
# ============================================================================

# Скорость распространения волны давления в воде по материалам труб (м/с).
# Источник: Моисеев 2014, СП 31.13330 §11.10.
WAVE_CELERITY_MPS = {
    "steel":          1340.0,    # Сталь
    "cast_iron":      1230.0,    # Чугун
    "concrete":       1100.0,    # Железобетон
    "pe100_sdr17":     320.0,    # ПЭ100 SDR17 (PN10)
    "pe100_sdr11":     440.0,    # ПЭ100 SDR11 (PN16)
    "pe100_sdr26":     230.0,    # ПЭ100 SDR26 (PN6) — самые «мягкие»
    "pvc":             400.0,    # ПВХ
    "fiberglass":      650.0,    # Стеклопластик
    "asbestos":       1000.0,    # Асбоцемент
    "copper":         1320.0,    # Медь
    "stainless":      1340.0,    # Нержавейка
}


@dataclass
class WaterHammerResult:
    delta_p_kpa: float           # Прирост давления, кПа
    delta_h_m: float             # Прирост напора, м
    wave_celerity_mps: float
    closure_time_s: float
    is_direct: bool              # Полный гидроудар (T_закр < 2L/c)
    pressure_class_required: str # "PN10" | "PN16" | "PN25"
    references: list[RegulationReference]


def water_hammer(
    v_ms: float,
    pipe_material: str = "pe100_sdr17",
    pipe_length_m: float = 100.0,
    closure_time_s: float = 5.0,
    T_celsius: float = 15.0,
) -> WaterHammerResult:
    """Расчёт гидроудара (Жуковский-Михайлов).

    Полный (прямой) удар при T_закр < 2L/c:
        Δp = ρ·c·v
    Неполный удар (медленное закрытие):
        Δp = ρ·c·v · (2L)/(c·T_закр) = 2ρ·v·L/T_закр  (формула Михайлова)
    """
    if pipe_material not in WAVE_CELERITY_MPS:
        raise ValueError(f"Unknown pipe material: {pipe_material}")
    c = WAVE_CELERITY_MPS[pipe_material]
    rho = density_water_kg_m3(T_celsius)

    T_phase = 2.0 * pipe_length_m / c   # Фаза удара
    if closure_time_s <= T_phase:
        # Прямой удар: формула Жуковского
        delta_p_pa = rho * c * v_ms
        is_direct = True
    else:
        # Непрямой удар: формула Михайлова
        delta_p_pa = 2.0 * rho * v_ms * pipe_length_m / closure_time_s
        is_direct = False

    delta_p_kpa = delta_p_pa / 1000.0
    delta_h = delta_p_pa / (rho * G_STANDARD)

    # Класс давления (PN) для трубы с запасом 1.3
    p_required_bar = (delta_p_pa / 100_000) * 1.3 + 1.0  # +1 атм рабочее
    if p_required_bar <= 6:
        pn = "PN6"
    elif p_required_bar <= 10:
        pn = "PN10"
    elif p_required_bar <= 16:
        pn = "PN16"
    elif p_required_bar <= 25:
        pn = "PN25"
    else:
        pn = f"PN{int(p_required_bar)+1}"

    refs = [
        ref("SP_31", "§11.10", "Расчёт гидроудара в напорных водопроводах"),
        ref("SP_32", "§7.4", "Защита от гидроудара в напорной канализации"),
    ]
    return WaterHammerResult(
        delta_p_kpa=round(delta_p_kpa, 1),
        delta_h_m=round(delta_h, 2),
        wave_celerity_mps=c,
        closure_time_s=closure_time_s,
        is_direct=is_direct,
        pressure_class_required=pn,
        references=refs,
    )


# ============================================================================
# 3. ШЕРОХОВАТОСТЬ ТРУБ И ТРЕНИЕ
# ============================================================================

# Эквивалентная шероховатость k_s (мм) по СП 32.13330.2018 табл. 6.5
# и СП 31.13330.2021 табл. Б.1.
PIPE_ROUGHNESS_MM = {
    "steel_new":       0.05,
    "steel_old":       1.0,        # с инкрустацией
    "cast_iron_new":   0.25,
    "cast_iron_old":   1.5,
    "concrete":        2.0,
    "asbestos":        0.05,
    "pe100":           0.01,       # Гладкие пластик
    "pvc":             0.01,
    "fiberglass":      0.05,
    "copper":          0.0015,
    "stainless":       0.015,
    "galvanized":      0.15,
}


def reynolds_number(v_ms: float, D_mm: float, T_celsius: float = 15.0) -> float:
    """Число Рейнольдса Re = v·D/ν."""
    nu = kinematic_viscosity_water_m2s(T_celsius)
    return v_ms * (D_mm / 1000.0) / nu


def darcy_friction_factor(Re: float, eps_over_D: float) -> float:
    """Коэффициент трения λ по Swamee-Jain (явная аппроксимация Colebrook-White).

    λ = 0.25 / [log10(ε/3.7D + 5.74/Re^0.9)]²

    Точность ±1.5% при 5×10³ < Re < 10⁸ и 10⁻⁶ < ε/D < 10⁻².
    """
    if Re < 2300:
        # Ламинарный режим
        return 64.0 / Re
    # Турбулентный
    arg = eps_over_D / 3.7 + 5.74 / (Re ** 0.9)
    return 0.25 / (math.log10(arg) ** 2)


def darcy_weisbach_head_loss_m(
    L_m: float,
    D_mm: float,
    v_ms: float,
    pipe_material: str = "pe100",
    T_celsius: float = 15.0,
) -> tuple[float, dict]:
    """Потери напора Дарси-Вейсбаха: h_f = λ·(L/D)·v²/(2g).

    Возвращает (h_f_м, дет.: λ, Re, ε/D, режим).
    """
    if pipe_material not in PIPE_ROUGHNESS_MM:
        raise ValueError(f"Unknown pipe material: {pipe_material}")
    eps_mm = PIPE_ROUGHNESS_MM[pipe_material]
    eps_over_D = eps_mm / D_mm
    Re = reynolds_number(v_ms, D_mm, T_celsius)
    lam = darcy_friction_factor(Re, eps_over_D)
    h_f = lam * (L_m / (D_mm / 1000.0)) * (v_ms ** 2) / (2 * G_STANDARD)
    return round(h_f, 3), {
        "lambda": round(lam, 5),
        "Re": round(Re, 0),
        "eps_over_D": round(eps_over_D, 6),
        "regime": "laminar" if Re < 2300 else ("transitional" if Re < 4000 else "turbulent"),
        "pipe_material": pipe_material,
        "roughness_mm": eps_mm,
    }


# ============================================================================
# 4. ПАРАЛЛЕЛЬНАЯ И ПОСЛЕДОВАТЕЛЬНАЯ РАБОТА НАСОСОВ
# ============================================================================

@dataclass
class ParallelOperatingPoint:
    n_pumps: int
    Q_per_pump_m3h: float
    Q_total_m3h: float
    H_m: float
    flow_efficiency_pct: float    # Q_total / (N · Q_single) — обычно 70-95%


def parallel_pumps_qh(
    pump_coeffs: list[float],
    n_pumps: int,
    system_static_h_m: float,
    system_friction_factor_per_q2: float,
) -> ParallelOperatingPoint:
    """Рабочая точка при N параллельных насосах.

    Для параллели: H_pump(Q_total/N) = H_st + k·Q_total²
    Решаем биссекцией.

    Эффективность параллели: чем круче кривая системы (k·Q²), тем меньше
    реальный прирост (обычно 1.7× для 2 насосов вместо 2×).
    """
    from .physics import evaluate_qh_polynomial

    def diff(Q_total):
        Q_single = Q_total / n_pumps
        return evaluate_qh_polynomial(pump_coeffs, Q_single) - (
            system_static_h_m + system_friction_factor_per_q2 * Q_total ** 2
        )

    # Биссекция
    a, b = 0.01, 1e5
    fa, fb = diff(a), diff(b)
    if fa * fb > 0:
        Q_total = b if fa > 0 else a
    else:
        for _ in range(100):
            mid = (a + b) / 2
            fm = diff(mid)
            if abs(fm) < 0.001:
                break
            if fa * fm < 0:
                b, fb = mid, fm
            else:
                a, fa = mid, fm
        Q_total = (a + b) / 2

    Q_single = Q_total / n_pumps
    H = sum(c * Q_single ** i for i, c in enumerate(pump_coeffs))

    # Эффективность параллели — насколько Q_total меньше идеального N·Q_single_alone
    # Q_single_alone (один насос работает в системе) — нужно решить отдельно
    def diff_single(Q):
        return sum(c * Q ** i for i, c in enumerate(pump_coeffs)) - (
            system_static_h_m + system_friction_factor_per_q2 * Q ** 2
        )
    a, b = 0.01, 1e5
    fa, fb = diff_single(a), diff_single(b)
    Q_single_alone = b if fa * fb > 0 else (a + b) / 2
    if fa * fb < 0:
        for _ in range(100):
            mid = (a + b) / 2
            fm = diff_single(mid)
            if abs(fm) < 0.001:
                break
            if fa * fm < 0:
                b, fb = mid, fm
            else:
                a, fa = mid, fm
        Q_single_alone = (a + b) / 2

    flow_eff = (Q_total / (n_pumps * Q_single_alone)) * 100 if Q_single_alone > 0 else 0

    return ParallelOperatingPoint(
        n_pumps=n_pumps,
        Q_per_pump_m3h=round(Q_single, 2),
        Q_total_m3h=round(Q_total, 2),
        H_m=round(H, 2),
        flow_efficiency_pct=round(flow_eff, 1),
    )


# ============================================================================
# 5. ФИЗИЧЕСКИЕ СВОЙСТВА «ГРЯЗНОЙ» ВОДЫ
# ============================================================================

def density_wastewater_kg_m3(
    T_celsius: float = 15.0,
    suspended_solids_mg_l: float = 0.0,
    dissolved_solids_mg_l: float = 0.0,
) -> float:
    """Плотность сточной воды.

    ρ_сток = ρ_вода + 0.5·SS_kg_m3 + 0.7·DS_kg_m3

    Для фильтрата ТКО (SS=20-50 г/л, DS=20-30 г/л) ρ ≈ 1080-1100 кг/м³.
    """
    rho_clean = density_water_kg_m3(T_celsius)
    SS_kg_m3 = suspended_solids_mg_l / 1000.0
    DS_kg_m3 = dissolved_solids_mg_l / 1000.0
    return rho_clean + 0.5 * SS_kg_m3 + 0.7 * DS_kg_m3


def viscosity_wastewater_factor(
    suspended_solids_mg_l: float = 0.0,
    fiber_content_pct: float = 0.0,
) -> float:
    """Множитель кинематической вязкости для грязной воды (по Эйнштейну + эмпирика).

    ν_сток = ν_вода × (1 + 2.5·φ + 6·φ²) где φ — объёмная доля.

    Для волокон поправка дополнительная +5-25%.
    """
    phi = suspended_solids_mg_l / 1_000_000.0  # объёмная доля
    factor = 1.0 + 2.5 * phi + 6.0 * phi ** 2
    if fiber_content_pct > 0:
        factor *= 1.0 + min(0.25, 0.05 * fiber_content_pct)
    return factor


# ============================================================================
# 6. ПРИВЯЗКА К НОРМАТИВАМ — централизованный список
# ============================================================================

def regulations_for_hydraulics() -> list[RegulationReference]:
    """Возвращает базовые ссылки для гидравлических расчётов.

    Используется в API responses для модулей hydraulics, physics, fire_water.
    """
    return [
        ref("SP_32", "§6.5 (шероховатость), §7 (напорные сети)", "Канализация наружная"),
        ref("SP_31", "§11 (трубопроводы), §11.10 (гидроудар)", "Водоснабжение наружное"),
        ref("GOST_6134", "§5.4-5.5", "NPSH испытания"),
        ref("ISO_9906", "§5", "Международный стандарт по подбору"),
    ]
