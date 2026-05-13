"""Объём аэротенка по MLSS + SRT (Metcalf & Eddy 5th §8-4).

Phase 34+ (2026-05-13): закрывает MLSS-calculator пробел PhD-Biology backlog.
Дополняет существующий aerotank.py (расчёт по СП 32 nag на ил n × a_i × (1-s))
второй методикой Metcalf & Eddy на основе кинетики Monod / SRT-уравнения.

Theory (Metcalf & Eddy 5th §8-4 «Activated Sludge Process Design», eq. 8-22):

  V = Q · SRT · Y · (S0 - S) / (X · (1 + Kd · SRT))

Где:
  Q       — расход стоков (м³/сут)
  SRT     — sludge retention time / возраст ила (сут):
              5-8 для удаления BOD (БПК)
              10-15 для нитрификации (при T=15°C)
              15-25 для нитри+денитрификации
  Y       — выход биомассы от субстрата (г VSS / г BOD), 0.4-0.6 (Metcalf §8-2)
  S0      — BOD на входе (мг/л)
  S       — BOD на выходе (мг/л), целевая 10-15
  X       — MLSS, mixed liquor suspended solids (г/л):
              2-3 — обычные аэротенки
              3-4 — с нитрификацией
              4-6 — MBR (мембранный биореактор)
  Kd      — endogenous decay coefficient (1/сут), 0.04-0.08 (default 0.05)

Дополнительно (Metcalf & Eddy eq. 8-25):
  F:M ratio (food to microorganism) = Q · S0 / (V · X)
    0.2-0.5 — обычные
    0.05-0.15 — extended aeration (увеличенный SRT)

Время аэрации:
  HRT = V / Q × 24 (часы)
    4-8 ч — типичный
    18-24 ч — extended aeration

Источники:
- Metcalf & Eddy 5th ed. (2014) §8-4 — design equations
- Henze IWA 2008 §3.2 — Activated Sludge Model
- СП 32.13330.2018 §7.4 — частично перекрывается с aerotank.py
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AerotankSizingResult:
    """Результат расчёта объёма аэротенка по Metcalf & Eddy MLSS-методу."""

    V_m3: float                    # объём аэротенка (без запаса), м³
    V_with_safety_20pct_m3: float  # объём с запасом 20%
    Q_m3_day: float                # расход стоков, м³/сут
    srt_days: float                # SRT (возраст ила)
    mlss_g_L: float                # концентрация MLSS
    Y: float                       # выход биомассы
    Kd: float                      # endogenous decay
    bod_in_mgL: float              # BOD на входе
    bod_out_mgL: float             # BOD на выходе (целевой)
    bod_remove_mgL: float          # ΔBOD
    HRT_hours: float               # время аэрации (часы)
    f_to_m_ratio: float            # F:M ratio
    notes: list[str]


def calculate_aerotank_volume(
    Q_m3_day: float,
    bod_in_mgL: float,
    bod_out_target: float = 15.0,
    srt_days: float = 10.0,
    mlss_g_L: float = 3.5,
    Y: float = 0.5,
    Kd: float = 0.05,
) -> dict:
    """Расчёт объёма аэротенка по уравнению Metcalf & Eddy (8-22).

    Args:
        Q_m3_day: расход стоков, м³/сут.
        bod_in_mgL: БПК5 на входе, мг/л.
        bod_out_target: БПК5 на выходе, мг/л (default 15 — типовая рыбхоз).
        srt_days: SRT / возраст ила, сут (5-25, default 10 для нитрификации).
        mlss_g_L: MLSS, г/л (2-6, default 3.5).
        Y: выход биомассы г VSS / г BOD (0.4-0.6, default 0.5).
        Kd: endogenous decay, 1/сут (0.04-0.08, default 0.05).

    Returns:
        dict с V_m3 / V_with_safety_20pct_m3 / HRT_hours / F:M ratio / notes.

    Пример:
        Q=1000 м³/сут, BOD_in=250, BOD_out=15, SRT=10 сут, MLSS=3.5 г/л:
        ΔBOD=235 → V = 1000·10·0.5·235 / (3500·(1+0.05·10)) ≈ 224 м³
        HRT = 224/1000·24 ≈ 5.4 ч (норма 4-8 ч ✓).
    """
    notes: list[str] = []

    bod_remove = bod_in_mgL - bod_out_target
    if bod_remove <= 0:
        return {
            "V_m3": 0.0,
            "V_with_safety_20pct_m3": 0.0,
            "Q_m3_day": Q_m3_day,
            "srt_days": srt_days,
            "mlss_g_L": mlss_g_L,
            "bod_in_mgL": bod_in_mgL,
            "bod_out_mgL": bod_out_target,
            "bod_remove_mgL": 0.0,
            "HRT_hours": 0.0,
            "f_to_m_ratio": 0.0,
            "notes": [
                f"BOD_in={bod_in_mgL} мг/л уже ≤ цели {bod_out_target} — "
                "аэротенк не требуется (только доочистка)."
            ],
            "reason": "BOD already below target",
        }

    # Metcalf & Eddy eq. 8-22:
    # V = Q · SRT · Y · ΔBOD / (MLSS_mgL · (1 + Kd · SRT))
    # MLSS в г/л → переводим в мг/л через × 1000.
    denom = mlss_g_L * 1000.0 * (1.0 + Kd * srt_days)
    V_m3 = (Q_m3_day * srt_days * Y * bod_remove) / denom

    V_safety = V_m3 * 1.2

    # HRT — гидравлическое время удерживания (часы)
    HRT_h = (V_m3 / Q_m3_day) * 24.0 if Q_m3_day > 0 else 0.0

    # F:M ratio = Q · BOD_in / (V · MLSS_mgL)
    f_to_m = (Q_m3_day * bod_in_mgL) / (V_m3 * mlss_g_L * 1000.0) if V_m3 > 0 else 0.0

    notes.extend([
        f"Q={Q_m3_day} м³/сут, ΔBOD={bod_remove:.0f} мг/л, SRT={srt_days} сут, "
        f"MLSS={mlss_g_L} г/л, Y={Y}, Kd={Kd}",
        f"V = Q·SRT·Y·ΔBOD / (MLSS·(1+Kd·SRT)) = {V_m3:.1f} м³",
        f"HRT (время аэрации) = V/Q·24 = {HRT_h:.1f} ч",
        f"F:M ratio = Q·BOD/(V·MLSS) = {f_to_m:.3f} 1/сут",
    ])

    # Sanity checks
    if HRT_h < 4.0:
        notes.append(
            f"⚠ HRT={HRT_h:.1f} ч < 4 ч — слишком быстро. Снизьте MLSS или "
            "увеличьте SRT (стандарт 4-8 ч)."
        )
    if HRT_h > 24.0:
        notes.append(
            f"⚠ HRT={HRT_h:.1f} ч > 24 ч — extended aeration. Проверьте "
            "стоимость аэрации (cost ↑ × 1.5-2)."
        )
    if f_to_m < 0.05:
        notes.append(
            f"⚠ F:M={f_to_m:.3f} < 0.05 — недостаток субстрата, ил голодает."
        )
    if f_to_m > 0.5:
        notes.append(
            f"⚠ F:M={f_to_m:.3f} > 0.5 — перегрузка, неполное окисление BOD."
        )
    if srt_days < 10 and bod_out_target < 20:
        notes.append(
            "ℹ Для нитрификации (NH4 → NO3) рекомендуется SRT ≥ 10 сут."
        )

    return {
        "V_m3": round(V_m3, 2),
        "V_with_safety_20pct_m3": round(V_safety, 2),
        "Q_m3_day": Q_m3_day,
        "srt_days": srt_days,
        "mlss_g_L": mlss_g_L,
        "Y": Y,
        "Kd": Kd,
        "bod_in_mgL": bod_in_mgL,
        "bod_out_mgL": bod_out_target,
        "bod_remove_mgL": round(bod_remove, 2),
        "HRT_hours": round(HRT_h, 2),
        "f_to_m_ratio": round(f_to_m, 4),
        "notes": notes,
        "references": [
            {
                "regulation_code": "Metcalf & Eddy 5th ed.",
                "section": "§8-4 eq. 8-22",
                "purpose": "Design equation for activated sludge volume (SRT-based)",
            },
            {
                "regulation_code": "Henze IWA 2008",
                "section": "§3.2",
                "purpose": "Activated Sludge Model №1-3 (ASM kinetics)",
            },
            {
                "regulation_code": "СП 32.13330.2018",
                "section": "§7.4",
                "purpose": "Параллельный метод расчёта по нагрузке n × a_i",
                "url": "https://docs.cntd.ru/document/554820821",
            },
        ],
    }
