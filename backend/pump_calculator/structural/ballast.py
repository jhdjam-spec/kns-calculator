"""Расчёт пригруза корпуса бетоном при высоком УГВ.

Принцип: подъёмная сила Архимеда не должна превышать
собственный вес корпуса + вес содержимого + бетонный пригруз + сила трения,
с коэффициентом запаса ≥1.1 (СП 32.13330.2018 §6.3).

Формула:
    F_подъёма = ρ_воды × g × V_корпуса_подводой
    G_удержания = G_корпуса + G_бетона + G_содержимого + F_трения
    Условие: G_удержания ≥ F_подъёма × K_запаса
"""
from __future__ import annotations

import math

from .models import BallastResult, StructuralScenarioInput

G = 9.80665  # м/с² — стандартное значение, ISO 80000-3 (унифицировано 2026-05-13)

# Удельные веса материалов корпусов, кг/м³ (для расчёта G_корп = ρ × V_материала)
MATERIAL_DENSITIES_KG_M3 = {
    "fiberglass": 1700,
    "hdpe": 950,
    "polypropylene": 910,
    "concrete": 2400,
    "concrete_monolith": 2500,
    "steel": 7850,
    "stainless": 7900,
}

CONCRETE_DENSITY_KG_M3 = 2400  # Бетон класса В20-В25
CONCRETE_DENSITY_UNDERWATER_KG_M3 = 1400  # С учётом сил Архимеда (2400 - 1000)


def calc_ballast_concrete(inputs: StructuralScenarioInput) -> BallastResult:
    """Расчёт пригруза бетоном для корпуса в водонасыщенном грунте."""
    notes: list[str] = []

    # 1. Объём корпуса
    R = inputs.diameter_m / 2
    V_corpus_m3 = math.pi * R**2 * inputs.height_m

    # 2. Глубина погружения в УГВ (если корпус ниже УГВ)
    # Если burial_depth > groundwater_depth → корпус частично/полностью под водой
    submerged_depth = max(0.0, inputs.burial_depth_m - inputs.groundwater_depth_m)
    submerged_depth = min(submerged_depth, inputs.height_m)
    V_submerged_m3 = math.pi * R**2 * submerged_depth

    # 3. Подъёмная сила Архимеда
    F_buoy_kn = 1000.0 * G * V_submerged_m3 / 1000.0  # ρ_воды=1000

    # 4. Собственный вес корпуса (стенки + днище)
    rho_mat = MATERIAL_DENSITIES_KG_M3.get(inputs.material, 1700)
    # Объём материала: цилиндр стенок + днище
    t_m = inputs.wall_thickness_mm / 1000.0
    V_walls_m3 = math.pi * inputs.diameter_m * inputs.height_m * t_m
    V_bottom_m3 = math.pi * R**2 * t_m * 1.5  # Днище толще
    V_material = V_walls_m3 + V_bottom_m3
    G_corpus_kn = rho_mat * G * V_material / 1000.0

    # 5. Вес содержимого (минимально — при пустом корпусе самая опасная)
    fill_h = inputs.height_m * inputs.fill_level_pct / 100.0
    V_contents = math.pi * R**2 * fill_h
    G_contents_kn = inputs.contents_density_kg_m3 * G * V_contents / 1000.0

    # 6. Сила трения грунта по стенкам (СП 22)
    # F_тр = K_a × γ_грунта × h²/2 × π × D × tan(φ)
    # где K_a = tan²(45 - φ/2) — коэф. активного давления
    phi = math.radians(inputs.soil_friction_angle_deg)
    K_a = math.tan(math.radians(45 - inputs.soil_friction_angle_deg / 2)) ** 2
    h_eff = min(inputs.burial_depth_m, inputs.groundwater_depth_m)  # сухая часть
    F_friction_kn = (
        K_a * inputs.soil_density_kg_m3 * G * h_eff**2 / 2.0
        * math.pi * inputs.diameter_m * math.tan(phi)
    ) / 1000.0

    # 7. Расчёт пригруза
    K_safety = 1.1  # СП 32.13330 §6.3
    G_required = F_buoy_kn * K_safety - G_corpus_kn - G_contents_kn - F_friction_kn

    is_required = G_required > 0

    if not is_required:
        notes.append(
            f"Пригруз НЕ требуется: G_удерж={G_corpus_kn + G_contents_kn + F_friction_kn:.1f} кН "
            f"≥ F_подъёма × K = {F_buoy_kn * K_safety:.1f} кН"
        )
        return BallastResult(
            is_required=False,
            archimedes_force_kn=round(F_buoy_kn, 2),
            self_weight_kn=round(G_corpus_kn, 2),
            contents_weight_kn=round(G_contents_kn, 2),
            friction_resistance_kn=round(F_friction_kn, 2),
            safety_factor=K_safety,
            ballast_concrete_volume_m3=0,
            ballast_concrete_thickness_m=0,
            notes=notes,
            references=_refs(),
        )

    # Объём бетона: G_required = V × ρ_бет × g (с поправкой на Архимед, т.к. бетон под водой)
    # Если бетон сам в воде — учитываем его эффективный вес: ρ_эфф = ρ_бет - ρ_воды = 1400
    rho_eff = CONCRETE_DENSITY_UNDERWATER_KG_M3 if submerged_depth > 0 else CONCRETE_DENSITY_KG_M3
    V_concrete_m3 = G_required * 1000.0 / (rho_eff * G)

    # Толщина плиты пригруза = V / S_дна
    S_bottom = math.pi * R**2
    h_concrete = V_concrete_m3 / S_bottom

    notes.extend([
        f"V_корпуса = π·R²·H = {V_corpus_m3:.2f} м³",
        f"V_подводой = {V_submerged_m3:.2f} м³ (заглубление {submerged_depth:.1f} м ниже УГВ)",
        f"F_Архимеда = ρ·g·V = {F_buoy_kn:.1f} кН",
        f"G_корпуса ({inputs.material}) = {G_corpus_kn:.1f} кН",
        f"G_содержимого ({inputs.fill_level_pct}%) = {G_contents_kn:.1f} кН",
        f"F_трения (грунт φ={inputs.soil_friction_angle_deg}°) = {F_friction_kn:.1f} кН",
        f"G_required = F·K - G_сумм = {G_required:.1f} кН (K={K_safety} по СП 32 §6.3)",
        f"V_бетона = G/(ρ_эфф·g) = {V_concrete_m3:.2f} м³ (ρ_эфф={rho_eff})",
        f"h_бетон = V/S = {h_concrete:.2f} м (плита под корпусом D={inputs.diameter_m} м)",
    ])

    return BallastResult(
        is_required=True,
        archimedes_force_kn=round(F_buoy_kn, 2),
        self_weight_kn=round(G_corpus_kn, 2),
        contents_weight_kn=round(G_contents_kn, 2),
        friction_resistance_kn=round(F_friction_kn, 2),
        safety_factor=K_safety,
        ballast_concrete_volume_m3=round(V_concrete_m3, 2),
        ballast_concrete_thickness_m=round(h_concrete, 2),
        notes=notes,
        references=_refs(),
    )


def _refs() -> list[dict]:
    return [
        {
            "regulation_code": "СП 32.13330.2018",
            "section": "§6.3",
            "purpose": "Предотвращение всплытия КНС/НС при УГВ",
            "url": "https://docs.cntd.ru/document/554820821",
        },
        {
            "regulation_code": "СП 22.13330.2016",
            "section": "§5.4",
            "purpose": "Расчётные нагрузки от грунта",
            "url": "https://docs.cntd.ru/document/456054206",
        },
    ]
