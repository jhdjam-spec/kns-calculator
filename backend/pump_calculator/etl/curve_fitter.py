"""Параболическая регрессия Q-H кривой и поиск Best Efficiency Point.

Модель Q-H у центробежных насосов хорошо приближается параболой:
    H(Q) = a + b·Q + c·Q²

КПД вокруг BEP обычно тоже парабола:
    η(Q) = A·Q² + B·Q + C   (с максимумом в Q_BEP = -B/(2A))

Используем numpy.polyfit (scipy уже подтянут как зависимость).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from pump_calculator.etl.schemas import QHPoint


@dataclass(frozen=True)
class QHCurve:
    """Аппроксимированная Q-H + η кривая.

    Атрибуты:
        H_coeffs: (a, b, c) для H(Q) = a + b·Q + c·Q²
        eta_coeffs: (A, B, C) для η(Q), либо None если не было КПД-точек
        Q_min_m3h, Q_max_m3h: диапазон валидных значений (по которому фитили)
        H_min_m, H_max_m: соответствующие напоры
        Q_BEP_m3h, H_BEP_m, eta_BEP_pct: точка max КПД (если eta доступен)
    """

    H_coeffs: tuple[float, float, float]
    eta_coeffs: tuple[float, float, float] | None
    Q_min_m3h: float
    Q_max_m3h: float
    H_min_m: float
    H_max_m: float
    Q_BEP_m3h: float | None
    H_BEP_m: float | None
    eta_BEP_pct: float | None
    NPSHr_at_BEP_m: float | None

    def H_at(self, Q_m3h: float) -> float:
        """Вычислить напор при заданном расходе."""
        a, b, c = self.H_coeffs
        return a + b * Q_m3h + c * Q_m3h**2

    def eta_at(self, Q_m3h: float) -> float | None:
        """Вычислить КПД (%) при заданном расходе. None если нет данных."""
        if self.eta_coeffs is None:
            return None
        A, B, C = self.eta_coeffs
        return A * Q_m3h**2 + B * Q_m3h + C


def fit_qh_curve(points: Sequence[QHPoint]) -> QHCurve:
    """Аппроксимировать Q-H/η кривую по точкам паспорта.

    Args:
        points: список QHPoint (минимум 3)

    Returns:
        QHCurve с коэффициентами и envelope.

    Особенности:
        - H аппроксимируется параболой (всегда, минимум 3 точки)
        - η — только если есть ≥3 ненулевых eta_pct точек, и их max — внутри диапазона
        - NPSHr_at_BEP — берётся из ближайшей точки к Q_BEP
    """
    if len(points) < 3:
        raise ValueError("Need at least 3 Q-H points for parabolic fit")

    # Сортировка по Q
    sorted_points = sorted(points, key=lambda p: p.Q_m3h)

    Q_arr = np.array([p.Q_m3h for p in sorted_points], dtype=float)
    H_arr = np.array([p.H_m for p in sorted_points], dtype=float)

    # H = c2·Q² + c1·Q + c0 (numpy возвращает старшие коэффициенты первыми)
    coeffs_H = np.polyfit(Q_arr, H_arr, 2)
    # переворачиваем в (a, b, c) для H = a + b·Q + c·Q²
    H_coeffs: tuple[float, float, float] = (
        float(coeffs_H[2]),
        float(coeffs_H[1]),
        float(coeffs_H[0]),
    )

    # КПД: фитим только если есть достаточно ненулевых данных
    eta_pts = [(p.Q_m3h, p.eta_pct) for p in sorted_points if p.eta_pct is not None and p.eta_pct > 0]
    Q_BEP: float | None = None
    H_BEP: float | None = None
    eta_BEP: float | None = None
    eta_coeffs: tuple[float, float, float] | None = None

    if len(eta_pts) >= 3:
        Qe = np.array([p[0] for p in eta_pts], dtype=float)
        Ee = np.array([p[1] for p in eta_pts], dtype=float)
        coeffs_eta = np.polyfit(Qe, Ee, 2)
        # η(Q) = A·Q² + B·Q + C
        A, B, C = float(coeffs_eta[0]), float(coeffs_eta[1]), float(coeffs_eta[2])
        eta_coeffs = (A, B, C)

        # BEP — вершина параболы. Только если A < 0 (парабола вниз)
        if A < 0:
            Q_BEP_calc = -B / (2 * A)
            # Проверка: BEP должен быть внутри диапазона ±10%
            Q_min_data = float(Qe.min())
            Q_max_data = float(Qe.max())
            if Q_min_data * 0.9 <= Q_BEP_calc <= Q_max_data * 1.1:
                Q_BEP = Q_BEP_calc
                eta_BEP_calc = A * Q_BEP**2 + B * Q_BEP + C
                if 0 < eta_BEP_calc <= 100:
                    eta_BEP = eta_BEP_calc
                    H_BEP = H_coeffs[0] + H_coeffs[1] * Q_BEP + H_coeffs[2] * Q_BEP**2

    # NPSHr в BEP — линейная интерполяция между ближайшими точками
    NPSHr_BEP: float | None = None
    if Q_BEP is not None:
        npshr_pts = [(p.Q_m3h, p.NPSHr_m) for p in sorted_points if p.NPSHr_m is not None]
        if len(npshr_pts) >= 2:
            Qn = np.array([p[0] for p in npshr_pts])
            Nn = np.array([p[1] for p in npshr_pts])
            NPSHr_BEP = float(np.interp(Q_BEP, Qn, Nn))

    return QHCurve(
        H_coeffs=H_coeffs,
        eta_coeffs=eta_coeffs,
        Q_min_m3h=float(Q_arr.min()),
        Q_max_m3h=float(Q_arr.max()),
        H_min_m=float(H_arr.min()),
        H_max_m=float(H_arr.max()),
        Q_BEP_m3h=Q_BEP,
        H_BEP_m=H_BEP,
        eta_BEP_pct=eta_BEP,
        NPSHr_at_BEP_m=NPSHr_BEP,
    )
