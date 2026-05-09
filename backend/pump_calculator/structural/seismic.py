"""Сейсмический расчёт корпуса КНС/НС по СП 14.13330.2018.

Учитывает:
- Интенсивность площадки (балл по ОСР-2015 — карта А, B или С)
- Категорию грунта (I-IV) — корректирующий коэффициент K_грунт
- Массу корпуса с содержимым
- Высоту корпуса (для определения момента)

Формула горизонтальной сейсмической силы:
    F_сейсм = K₀ × K_ψ × K_грунт × m × g

Где:
- K₀ — коэф. интенсивности (1 балл = 0.025)
- K_ψ — коэф. ответственности (1.0 для обычных, 1.5 для I категории)
- K_грунт — коэф. по категории грунта (I=0.8, II=1.0, III=1.4, IV=1.7)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SoilSeismicCategory = Literal["I", "II", "III", "IV"]


# Категории грунтов по СП 14.13330.2018 табл. 5.1 — корректирующий коэффициент
SOIL_SEISMIC_FACTORS: dict[SoilSeismicCategory, dict] = {
    "I": {
        "factor": 0.8,
        "description": "Скальные грунты, крупнообломочные плотные",
        "examples": "Граниты, базальты, плотные конгломераты",
    },
    "II": {
        "factor": 1.0,
        "description": "Скальные выветрелые, крупнообломочные средней плотности, пески плотные",
        "examples": "Песок плотный гравелистый, плотные суглинки",
    },
    "III": {
        "factor": 1.4,
        "description": "Пески рыхлые, глинистые мягкопластичные, супеси",
        "examples": "Песок пылеватый, супесь текучая, глина мягкопластичная",
    },
    "IV": {
        "factor": 1.7,
        "description": "Заторфованные, илистые, лёссовые, водонасыщенные",
        "examples": "Торф, ил, лёсс, грунты при УГВ выше дна корпуса",
    },
}


# Базовый коэффициент интенсивности по СП 14.13330 §5.5
SEISMIC_INTENSITY_K0: dict[int, float] = {
    6: 0.025,
    7: 0.05,
    8: 0.10,
    9: 0.20,
    10: 0.40,
}


@dataclass
class SeismicResult:
    """Результат сейсмического расчёта корпуса."""

    intensity_balls: int
    soil_category: str
    soil_factor: float
    K0: float
    K_psi: float
    K_total: float
    F_horizontal_kn: float
    M_overturning_kn_m: float
    is_calculation_required: bool
    notes: list[str]
    references: list[dict]


def calc_seismic_force_on_corpus(
    intensity_balls: int,
    soil_category: SoilSeismicCategory,
    corpus_mass_kg: float,
    corpus_height_m: float = 3.0,
    is_special_responsibility: bool = False,
) -> SeismicResult:
    """Сейсмический расчёт корпуса по СП 14.13330."""
    notes: list[str] = []
    g = 9.81

    if intensity_balls < 7:
        notes.append(
            f"Интенсивность {intensity_balls} баллов < 7 — расчёт не обязателен по СП 14 §5.1"
        )
        return SeismicResult(
            intensity_balls=intensity_balls,
            soil_category=soil_category,
            soil_factor=SOIL_SEISMIC_FACTORS[soil_category]["factor"],
            K0=SEISMIC_INTENSITY_K0.get(intensity_balls, 0.0),
            K_psi=1.0,
            K_total=0.0,
            F_horizontal_kn=0.0,
            M_overturning_kn_m=0.0,
            is_calculation_required=False,
            notes=notes,
            references=_refs(),
        )

    if soil_category not in SOIL_SEISMIC_FACTORS:
        raise ValueError(f"Unknown soil category: {soil_category}. Valid: I-IV")

    if intensity_balls not in SEISMIC_INTENSITY_K0:
        raise ValueError(f"intensity_balls должно быть 6-10, получено {intensity_balls}")

    K0 = SEISMIC_INTENSITY_K0[intensity_balls]
    soil = SOIL_SEISMIC_FACTORS[soil_category]
    K_grunt = soil["factor"]
    K_psi = 1.5 if is_special_responsibility else 1.0
    K_total = K0 * K_psi * K_grunt

    F_kn = K_total * corpus_mass_kg * g / 1000
    M_kn_m = F_kn * corpus_height_m / 2

    notes.extend([
        f"Интенсивность {intensity_balls} баллов → K₀ = {K0}",
        f"Грунт {soil_category} ({soil['description']}) → K_грунт = {K_grunt}",
        f"K_ответственности = {K_psi} ({'особый' if is_special_responsibility else 'обычный'} объект)",
        f"K_сум = K₀ × K_ψ × K_грунт = {K0} × {K_psi} × {K_grunt} = {K_total:.4f}",
        f"F_горизонт. = K_сум × m × g = {K_total:.4f} × {corpus_mass_kg} × 9.81 = {F_kn:.2f} кН",
        f"Момент опрокидывания M = F × H/2 = {F_kn:.2f} × {corpus_height_m / 2:.2f} = {M_kn_m:.2f} кН·м",
    ])

    if intensity_balls >= 9:
        notes.append("⚠ Интенсивность ≥9 баллов — требуется усиление анкеровки и проверка на раскачивание")
    if soil_category == "IV":
        notes.append(
            "⚠ Грунт IV категории (водонасыщенный/лёсс/торф) — сейсмическое воздействие "
            "удваивается. Проверить разжижение по СП 14 §5.1.7"
        )

    return SeismicResult(
        intensity_balls=intensity_balls,
        soil_category=soil_category,
        soil_factor=K_grunt,
        K0=K0,
        K_psi=K_psi,
        K_total=round(K_total, 4),
        F_horizontal_kn=round(F_kn, 2),
        M_overturning_kn_m=round(M_kn_m, 2),
        is_calculation_required=True,
        notes=notes,
        references=_refs(),
    )


def _refs() -> list[dict]:
    return [
        {
            "regulation_code": "СП 14.13330.2018",
            "section": "§5",
            "purpose": "Расчёт зданий и сооружений в сейсмических районах",
            "url": "https://docs.cntd.ru/document/551989895",
        },
        {
            "regulation_code": "СП 14.13330.2018 + ОСР-2015",
            "section": "карты А, B, C",
            "purpose": "Карты сейсмического районирования территории РФ",
            "url": "https://docs.cntd.ru/document/551989895",
        },
    ]


def list_soil_categories() -> list[dict]:
    """Каталог 4 категорий грунта для UI."""
    return [
        {
            "category": cat,
            "factor": data["factor"],
            "description": data["description"],
            "examples": data["examples"],
        }
        for cat, data in SOIL_SEISMIC_FACTORS.items()
    ]
