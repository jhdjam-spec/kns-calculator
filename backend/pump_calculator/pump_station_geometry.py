"""Phase 8.5 — формулы §15 из R4 textbooks (СП 32 + HI 9.6.x + HI 9.8).

Реализовано:
- §15.1 V_min — нижний контроль объёма приёмного резервуара (cycling-protection)
- §15.5 S/D = 1 + 2.3·Fr — минимальное погружение всасывающего раструба (HI 9.8)
- §15.6 Specific Speed Ns — фактор для composite_score (KSB Lexicon, Lobanoff & Ross)
- §15.7 NPSH margin — формула вместо плоского «0.5-1.5 м запас» (HI 9.6.1-2024)
- §15.9 v_min — жёсткий минимум скорости 1.0 м/с в напорной канализации (СП 32 §5.4)

Полное описание формул и источников: `02_dataset/theory/formulas.md` §15.
"""

from __future__ import annotations

from math import pi, sqrt

G = 9.80665  # м/с² — стандартное значение, ISO 80000-3 (унифицировано 2026-05-13)


def calc_v_min_pool_m3(Q_per_pump_m3h: float, t_min_run_min: float = 5.0) -> float:
    """§15.1 — минимальный полезный объём приёмного резервуара.

    Защита от cycling-смерти: насос не должен запускаться чаще, чем требуется
    его паспортное z (СП 32 §8.2.15). Эквивалентная формулировка — между
    пусками насос должен проработать не менее 5 минут (АВОК ст. 8095, Flotenk).

        V_min = Q_1н × t_min / 60      [м³]

    Args:
        Q_per_pump_m3h: производительность одного насоса, м³/ч
        t_min_run_min: минимальное время работы между пусками, мин (default 5)

    Returns:
        V_min, м³. Калькулятор должен использовать V = max(V_СП32, V_min).
    """
    if Q_per_pump_m3h <= 0:
        return 0.0
    return round(Q_per_pump_m3h * t_min_run_min / 60.0, 2)


def calc_min_submergence_m(
    Q_per_pump_m3h: float,
    suction_DN_mm: float,
) -> dict[str, float]:
    """§15.5 — минимальное погружение всасывающего раструба (HI 9.8-2024).

    Если уровень воды над раструбом меньше S_min → воздухозабор → кавитация
    → удар по подшипникам. Формула:

        S_min / D = 1 + 2.3 × Fr      где Fr = v / √(g·D)

    Args:
        Q_per_pump_m3h: подача насоса, м³/ч
        suction_DN_mm: диаметр всасывающего раструба, мм

    Returns:
        dict с ключами:
          - 'v_ms': скорость в раструбе, м/с
          - 'Fr': число Фруда
          - 'S_over_D': безразмерное отношение S_min/D
          - 'S_min_m': минимальное погружение, м

    Источник: Hydraulic Institute ANSI/HI 9.8-2024 «Pump Intake Design».
    """
    if Q_per_pump_m3h <= 0 or suction_DN_mm <= 0:
        return {"v_ms": 0.0, "Fr": 0.0, "S_over_D": 0.0, "S_min_m": 0.0}

    D_m = suction_DN_mm / 1000.0
    A_m2 = pi * (D_m / 2.0) ** 2
    Q_m3s = Q_per_pump_m3h / 3600.0
    v_ms = Q_m3s / A_m2
    Fr = v_ms / sqrt(G * D_m)
    S_over_D = 1.0 + 2.3 * Fr
    S_min_m = S_over_D * D_m

    return {
        "v_ms": round(v_ms, 3),
        "Fr": round(Fr, 3),
        "S_over_D": round(S_over_D, 3),
        "S_min_m": round(S_min_m, 3),
    }


def calc_specific_speed_ns(
    rpm: float,
    Q_m3h: float,
    H_m: float,
) -> float:
    """§15.6 — Specific Speed Ns в SI-системе.

        Ns = n × √Q / H^0.75       (n: об/мин, Q: м³/с, H: м)

    Допустимые диапазоны для канализационных насосов:
      - Ns < 15  — радиальное колесо: высокий H, низкий КПД (≤55%)
      - 15-80    — vortex/single-channel/multi-channel (рабочий диапазон)
      - Ns > 80  — осевое: малый H, риск кавитации

    Returns:
        Ns в SI. 0 если данных недостаточно.

    Источник: KSB Centrifugal Pump Lexicon, Lobanoff & Ross гл.2.
    """
    if rpm <= 0 or Q_m3h <= 0 or H_m <= 0:
        return 0.0
    Q_m3s = Q_m3h / 3600.0
    Ns = rpm * sqrt(Q_m3s) / (H_m**0.75)
    return round(Ns, 1)


def score_ns_compatibility(Ns: float) -> float:
    """§15.6 — penalty по Specific Speed для composite_score.

    1.0 — оптимально (Ns в рабочем диапазоне 15-80)
    0.7 — на границе (10-15 или 80-100)
    0.4 — за границей (<10 или >100)
    1.0 — Ns=0 (нет данных, не штрафуем)

    Returns:
        float в [0.0, 1.0].
    """
    if Ns <= 0:
        return 1.0  # нет данных — не штрафуем
    if 15.0 <= Ns <= 80.0:
        return 1.0
    if 10.0 <= Ns < 15.0 or 80.0 < Ns <= 100.0:
        return 0.7
    return 0.4


def calc_npsh_margin_m(NPSHR_m: float) -> float:
    """§15.7 — требуемый запас NPSH по HI 9.6.1-2024.

        margin = max(1.0 м, 0.1 × NPSHR)

    Для NPSHR ≤ 10 м даёт фиксированный 1 м.
    Для NPSHR > 10 м — пропорциональный 10%.

    Args:
        NPSHR_m: паспортный NPSHR насоса, м

    Returns:
        Минимальный margin, м.

    Источник: Hydraulic Institute ANSI/HI 9.6.1-2024.
    """
    if NPSHR_m <= 0:
        return 1.0  # консервативный default
    return round(max(1.0, 0.1 * NPSHR_m), 2)


# §15.9 — минимальные скорости по типу стоков
V_MIN_BY_WASTEWATER = {
    "domestic": 1.0,    # бытовые — заиливание, СП 32 §5.4
    "industrial": 1.0,  # промышленные с волокнами
    "drainage": 0.7,    # дождевые — без волокон, можно меньше
    "clean_water": 0.6,  # чистая (СПД)
}


def get_v_min_for_wastewater(wastewater_type: str | None) -> float:
    """§15.9 — минимальная скорость в напорном трубопроводе по типу стоков.

    Это **жёсткий фильтр**, не рекомендация: меньшая скорость →
    заиливание гарантировано (для domestic/industrial).
    """
    if not wastewater_type:
        return 1.0  # консервативный default — бытовые
    return V_MIN_BY_WASTEWATER.get(wastewater_type, 1.0)
