"""Расчёт аэротенка биологической очистки сточных вод по СП 32.13330.2018.

Главные параметры:

1. Объём аэротенка V_аэр (м³):
   V_аэр = (Q_сут × БПК_вх) / (n × a_i × (1 - s))

   Где:
   - Q_сут — суточный расход стоков, м³/сут
   - БПК_вх — БПК₅ на входе, мг/л
   - n — нагрузка на ил, мг БПК/(г беззольного вещества·сут), от 200 до 600
         (для бытовых стоков — ~300, для промышл. — 200)
   - a_i — концентрация активного ила, г/л (1.5-3.0 для классических)
   - s — зольность ила (0.3 типично)

2. Объёмная нагрузка λ:
   λ = БПК × Q_сут / V (кг БПК/м³·сут)
   Норма 0.3-0.6 для бытовых.

3. Расход воздуха для аэрации:
   Q_воздух = z × БПК × Q_сут / 1000  (м³/ч)
   z = 1.1 для бытовых (поправка на нитрификацию).

4. Возрастные показатели:
   - Возраст ила θ ≥ 5 сут (для нитрификации ≥10 сут)
   - Время аэрации t = V/Q_сут × 24 (часы)

Источники:
- СП 32.13330.2018 §7.4.5 — расчёт аэротенков
- СНиП 2.04.03-85 (отменён, но методика используется)
- ИТС 10-2015 НДТ §6.1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Тип нагрузки на ил для разных стоков
LoadProfile = Literal["domestic_low", "domestic_medium", "industrial_low", "industrial_high"]


# Параметры по типу стоков (нагрузка n, концентрация ила a_i)
LOAD_PROFILES: dict[LoadProfile, dict] = {
    "domestic_low": {
        "n_mg_bod_g_day": 400,
        "a_i_g_l": 2.0,
        "z_air_factor": 1.1,
        "description": "Бытовые стоки, лёгкая нагрузка (квартиры, гостиницы)",
    },
    "domestic_medium": {
        "n_mg_bod_g_day": 300,
        "a_i_g_l": 2.5,
        "z_air_factor": 1.2,
        "description": "Бытовые стоки, средняя нагрузка (микрорайоны, посёлки)",
    },
    "industrial_low": {
        "n_mg_bod_g_day": 250,
        "a_i_g_l": 3.0,
        "z_air_factor": 1.3,
        "description": "Промышленные стоки лёгкого состава (молочные, текстильные)",
    },
    "industrial_high": {
        "n_mg_bod_g_day": 150,
        "a_i_g_l": 3.5,
        "z_air_factor": 1.5,
        "description": "Промышленные стоки тяжёлого состава (нефтехимия, пищёвка)",
    },
}


@dataclass
class AerotankCalcResult:
    """Результат расчёта аэротенка."""

    Q_m3_day: float                # Суточный расход
    BOD_inlet_mg_l: float          # БПК на входе
    profile: LoadProfile           # Профиль нагрузки
    V_aerotank_m3: float           # Объём аэротенка
    n_load: float                  # Нагрузка на ил
    a_i_g_l: float                 # Концентрация ила
    aeration_time_h: float         # Время аэрации
    sludge_age_days: float         # Возраст ила
    air_flow_m3h: float            # Расход воздуха
    BOD_removed_pct: float         # Степень очистки по БПК
    notes: list[str]
    references: list[dict]


def calc_aerotank(
    Q_m3_day: float,
    BOD_inlet_mg_l: float,
    profile: LoadProfile = "domestic_medium",
    BOD_outlet_target_mg_l: float = 15.0,
    sludge_zollnost: float = 0.3,
) -> AerotankCalcResult:
    """Расчёт объёма и параметров аэротенка по СП 32.13330.

    Args:
        Q_m3_day: суточный расход сточных вод, м³/сут.
        BOD_inlet_mg_l: БПК₅ на входе аэротенка, мг/л.
        profile: тип нагрузки (domestic_low/medium, industrial_low/high).
        BOD_outlet_target_mg_l: целевая БПК на выходе (15 мг/л — типовая
                                для рыбохозяйственного сброса).
        sludge_zollnost: зольность ила (s), 0.25-0.35.

    Returns:
        AerotankCalcResult с объёмом, временем аэрации, расходом воздуха.

    Пример:
        Q=10 м³/сут (50 чел), БПК=300, профиль "domestic_medium":
        V_аэр = 10 × 300 / (300 × 2.5 × (1 - 0.3)) ≈ 5.7 м³
        Время аэрации ≈ 13.7 ч
    """
    if profile not in LOAD_PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Valid: {list(LOAD_PROFILES)}")

    spec = LOAD_PROFILES[profile]
    notes: list[str] = []

    n = spec["n_mg_bod_g_day"]
    a_i = spec["a_i_g_l"]
    z = spec["z_air_factor"]

    # V_аэр = Q × БПК / (n × a_i × (1 - s))
    V_aerotank = (Q_m3_day * BOD_inlet_mg_l) / (n * a_i * (1 - sludge_zollnost))

    # Время аэрации (часы)
    t_aeration = V_aerotank / Q_m3_day * 24

    # Возраст ила (упрощённая оценка для классических аэротенков)
    # θ = (V × a_i) / (P_избыт), где P_избыт ≈ 0.4 × БПК × Q (кг/сут)
    P_excess_kg_day = 0.4 * BOD_inlet_mg_l * Q_m3_day / 1000
    sludge_age = (V_aerotank * a_i) / P_excess_kg_day if P_excess_kg_day > 0 else 0

    # Расход воздуха (формула СП 32 §7.4.5)
    # Q_воздух = z × БПК × Q / 1000 (приближённо, м³/ч)
    air_flow = z * BOD_inlet_mg_l * Q_m3_day / 1000 / 24 * 60   # перевод в м³/ч

    # Степень очистки
    bod_removed_pct = (1 - BOD_outlet_target_mg_l / BOD_inlet_mg_l) * 100

    notes.extend([
        f"Q={Q_m3_day} м³/сут, БПК_вх={BOD_inlet_mg_l} мг/л, профиль '{profile}'",
        f"V_аэр = Q × БПК / (n × a_i × (1-s)) = {Q_m3_day} × {BOD_inlet_mg_l} / ({n} × {a_i} × {1-sludge_zollnost:.2f}) = {V_aerotank:.1f} м³",
        f"Время аэрации t = V/Q × 24 = {t_aeration:.1f} ч",
        f"Возраст ила θ ≈ {sludge_age:.1f} сут (норма ≥5 сут, для нитрификации ≥10)",
        f"Расход воздуха ≈ {air_flow:.1f} м³/ч (z={z})",
        f"Степень очистки по БПК: {bod_removed_pct:.1f}% (с {BOD_inlet_mg_l} до {BOD_outlet_target_mg_l} мг/л)",
    ])

    if t_aeration < 4:
        notes.append("⚠ Время аэрации <4 ч — недостаточно для биологической очистки")
    if sludge_age < 5:
        notes.append("⚠ Возраст ила <5 сут — увеличить V или снизить нагрузку")

    references = [
        {
            "regulation_code": "СП 32.13330.2018",
            "section": "§7.4.5",
            "purpose": "Расчёт аэротенков с активным илом",
            "url": "https://docs.cntd.ru/document/554820821",
        },
        {
            "regulation_code": "ИТС 10-2015",
            "section": "§6.1",
            "purpose": "Технология биологической очистки сточных вод (НДТ)",
            "url": "https://www.consultant.ru/document/cons_doc_LAW_193989/",
        },
    ]

    return AerotankCalcResult(
        Q_m3_day=Q_m3_day,
        BOD_inlet_mg_l=BOD_inlet_mg_l,
        profile=profile,
        V_aerotank_m3=round(V_aerotank, 2),
        n_load=n,
        a_i_g_l=a_i,
        aeration_time_h=round(t_aeration, 2),
        sludge_age_days=round(sludge_age, 2),
        air_flow_m3h=round(air_flow, 2),
        BOD_removed_pct=round(bod_removed_pct, 1),
        notes=notes,
        references=references,
    )


def list_load_profiles() -> list[dict]:
    """Каталог 4 профилей нагрузки для UI."""
    return [
        {
            "profile": p,
            "description": data["description"],
            "n_mg_bod_g_day": data["n_mg_bod_g_day"],
            "a_i_g_l": data["a_i_g_l"],
        }
        for p, data in LOAD_PROFILES.items()
    ]
