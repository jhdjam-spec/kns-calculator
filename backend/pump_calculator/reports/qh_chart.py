"""Q-H график для PDF расчётной записки (Phase 28 заготовка).

Генерирует PNG-байты с кривой Q-H насоса, рабочей точкой системы и
зоной AOR/POR. Используется в `calculation_report.py` через
`reportlab.platypus.Image(io.BytesIO(png_bytes))`.

Не вызывается из API — только из PDF-генератора. Чтобы избежать
накладных matplotlib при cold-start, импорт matplotlib делается лениво
внутри функции (Phase 28: PDF-генератор уже lazy-imported в api.py).
"""
from __future__ import annotations

import io
from typing import Any


def render_qh_chart_png(
    pump: dict[str, Any],
    duty_Q_m3h: float,
    duty_H_m: float,
    width_inch: float = 6.0,
    height_inch: float = 4.0,
    dpi: int = 100,
) -> bytes:
    """Генерирует PNG-картинку Q-H графика для одного насоса.

    Args:
        pump: запись из pumps.json с envelope.{Q_min,Q_max,H_min,H_max,Q_BEP,H_BEP}
              опционально qh_curve [(Q,H), ...] для точной кривой
        duty_Q_m3h: рабочая точка системы (Q клиента)
        duty_H_m: H_full системы
        width_inch / height_inch: размеры картинки в дюймах (для reportlab Image)
        dpi: разрешение

    Returns:
        PNG-байты, готовые для вставки в reportlab Image(io.BytesIO(...))
    """
    import matplotlib
    matplotlib.use("Agg")  # без X-сервера — для serverless
    import matplotlib.pyplot as plt

    env = pump.get("envelope", {})
    Q_min = env.get("Q_min_m3h", 0)
    Q_max = env.get("Q_max_m3h", duty_Q_m3h * 2)
    H_min = env.get("H_min_m", 0)
    H_max = env.get("H_max_m", duty_H_m * 1.5)
    Q_BEP = env.get("Q_BEP_m3h") or (Q_min + Q_max) / 2
    H_BEP = env.get("H_BEP_m") or (H_min + H_max) / 2

    qh_curve = pump.get("qh_curve") or []

    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=dpi)

    # 1. Кривая Q-H (или envelope если кривой нет)
    if qh_curve and len(qh_curve) >= 3:
        Qs = [pt.get("Q_m3h", pt[0] if isinstance(pt, list) else 0) for pt in qh_curve]
        Hs = [pt.get("H_m", pt[1] if isinstance(pt, list) else 0) for pt in qh_curve]
        ax.plot(Qs, Hs, "b-", linewidth=2, label=f"{pump.get('brand','')} {pump.get('model','')}")
    else:
        # Парабольная аппроксимация Q-H через 3 точки: (Q_min, H_max), (Q_BEP, H_BEP), (Q_max, H_min)
        import numpy as np
        Qs = np.linspace(Q_min, Q_max, 30)
        # H = a*Q^2 + b*Q + c
        # Решаем систему через 3 точки
        try:
            A = np.array([
                [Q_min**2, Q_min, 1],
                [Q_BEP**2, Q_BEP, 1],
                [Q_max**2, Q_max, 1],
            ])
            B = np.array([H_max, H_BEP, H_min])
            a, b, c = np.linalg.solve(A, B)
            Hs = a * Qs**2 + b * Qs + c
            ax.plot(Qs, Hs, "b-", linewidth=2,
                    label=f"{pump.get('brand','')} {pump.get('model','')}")
        except Exception:
            # Fallback: просто envelope rectangle
            ax.fill_between([Q_min, Q_max], [H_min, H_min], [H_max, H_max],
                            alpha=0.3, color="lightblue", label="envelope")

    # 2. AOR/POR зоны (по HI 9.6.1-2024: AOR = ±15% от Q_BEP, POR = ±10%)
    ax.axvspan(Q_BEP * 0.85, Q_BEP * 1.15, alpha=0.15, color="green", label="AOR ±15%")
    ax.axvspan(Q_BEP * 0.90, Q_BEP * 1.10, alpha=0.20, color="darkgreen", label="POR ±10%")

    # 3. BEP точка
    ax.plot(Q_BEP, H_BEP, "g*", markersize=15, label=f"BEP ({Q_BEP:.0f}, {H_BEP:.0f})")

    # 4. Рабочая точка системы
    ax.plot(duty_Q_m3h, duty_H_m, "r^", markersize=12,
            label=f"Duty ({duty_Q_m3h:.1f}, {duty_H_m:.1f})")

    # Оформление
    ax.set_xlabel("Подача Q, м³/ч", fontsize=10)
    ax.set_ylabel("Напор H, м", fontsize=10)
    ax.set_title(f"Q-H характеристика: {pump.get('brand','')} {pump.get('model','')}",
                 fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    # Сохраняем в bytes
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
