"""Расчёт минимальных размеров стеклопластикового корпуса КНС.

По эмпирическим данным реальных КП (ТКП ПВТ № 3102.4Д-25, эталоны Серво-Юг):

| Q м³/ч  | DN напорный, мм | Корпус Ø × H, мм       |
|---------|------------------|-------------------------|
| < 5     | 50               | Ø1000 × 1500 (приямок) |
| 5–30    | 65–80            | Ø1500–1800 × 2000–3000  |
| 30–100  | 100–150          | Ø2000–2500 × 3000–4500  |
| 100–300 | 150–200          | Ø2500–3000 × 4500–6000  |
| 300–1000| 250–400          | Ø3000–4000 × 6000–8200  |

Высота КНС складывается из:
- depth_inlet_mm — глубина подвода стоков (по проекту)
- height_dry_min_mm — минимальная высота «сухого» отсека для обслуживания (1500 мм)
- pump_height_mm — высота погружного насоса (от 500 для бытовых до 1500 для индустриальных)
- safety_margin_mm — запас (200 мм)

Если depth_inlet_mm не задан — берём типовое значение 2000 мм для КНС бытовой
самотёчной системы.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CorpusType = Literal["pe", "glass"]


@dataclass(frozen=True)
class CorpusSize:
    """Геометрия стеклопластикового / ПЭ корпуса КНС."""

    diameter_mm: float
    height_mm: float
    inlet_DN_mm: float
    outlet_DN_mm: float
    weight_estimate_kg: int  # по аналогии с эталонами ПВТ
    notes: list[str]


# Q-таблица: (Q_max, diameter_mm) — выбираем минимальный диаметр, в который пройдёт Q
_DIAMETER_LADDER_BY_Q: list[tuple[float, float]] = [
    (5, 1000),    # <5 м³/ч — приямок без КНС (бытовой коттедж)
    (15, 1500),   # 5-15 — компактная для одной частной/малой
    (30, 1800),   # 15-30 — типовая бытовая (эталон ПВТ Q=20.6 м³/ч → Ø1800)
    (60, 2000),   # 30-60 — гостиница 50-100 номеров
    (100, 2500),  # 60-100 — крупная гостиница / малый ЖК
    (200, 3000),  # 100-200 — ЖК/ТРЦ
    (500, 3500),  # 200-500 — крупный ТРЦ / промышленность
    (1000, 4000), # 500-1000 — большие площадки
]

# Ладдер DN напорного по Q (м³/ч → мм). Соответствует ALGORITHM_SPEC §4.
_DISCHARGE_DN_LADDER: list[tuple[float, float]] = [
    (5, 50),
    (15, 65),
    (30, 80),
    (60, 100),
    (100, 150),
    (200, 200),
    (500, 250),
    (1000, 350),
]


def select_corpus_diameter_mm(Q_m3h: float) -> float:
    """Подбор минимального диаметра корпуса под расход."""
    for Q_max, dia in _DIAMETER_LADDER_BY_Q:
        if Q_m3h <= Q_max:
            return dia
    return _DIAMETER_LADDER_BY_Q[-1][1]


def select_inlet_dn_mm(Q_m3h: float) -> float:
    """Подбор DN подводящего самотёчного трубопровода (по СП 32 §5.4 v_min=0.7)."""
    # Подвод обычно на 1-2 шага больше напорного из-за самотёка низкой скорости
    discharge_dn = select_discharge_dn_mm(Q_m3h)
    if discharge_dn <= 65:
        return 110.0  # стандарт Корсис OD110/ID94 для бытовой
    if discharge_dn <= 100:
        return 160.0
    if discharge_dn <= 200:
        return 250.0
    return 315.0


def select_discharge_dn_mm(Q_m3h: float) -> float:
    """Подбор DN напорного по таблице."""
    for Q_max, dn in _DISCHARGE_DN_LADDER:
        if Q_m3h <= Q_max:
            return dn
    return _DISCHARGE_DN_LADDER[-1][1]


def estimate_pump_footprint_mm(Q_m3h: float, P_kW: float) -> tuple[float, float]:
    """Габариты одного погружного насоса (длина-высота, мм).

    Эмпирика по KAIQUAN/Wilo/Pedrollo/ANTARUS погружным WQ:
    - до 5 кВт: ~Ø250 × H500 (бытовой)
    - 5-15 кВт: ~Ø350 × H800 (гостиничный)
    - 15-30 кВт: ~Ø450 × H1100 (индустриальный)
    - 30+ кВт: ~Ø600 × H1500 (тяжёлый WQ2290)
    """
    if P_kW <= 5:
        return 250.0, 500.0
    if P_kW <= 15:
        return 350.0, 800.0
    if P_kW <= 30:
        return 450.0, 1100.0
    return 600.0, 1500.0


def estimate_corpus_height_mm(
    Q_m3h: float,
    P_kW: float,
    depth_inlet_mm: float = 2000.0,
    n_pumps: int = 2,
) -> float:
    """Высота корпуса КНС от верха крышки до дна.

    Складывается из:
    - depth_inlet (глубина подвода) + 200 мм проектного превышения подводящей трубы
    - pump_height (высота насоса с автомуфтой)
    - dry_chamber (минимум 1500 мм сухого отсека для обслуживания + лестница)
    - safety 200 мм
    """
    _, pump_h = estimate_pump_footprint_mm(Q_m3h, P_kW)
    safety = 200.0
    # dry_chamber=1500мм условно учтён через safety + min-height clamp ниже
    height = depth_inlet_mm + 200.0 + pump_h + safety
    # Минимум 2000 мм для обслуживания
    return max(2000.0, round(height / 100.0) * 100.0)


def estimate_corpus_weight_kg(diameter_mm: float, height_mm: float) -> int:
    """Эмпирическая оценка веса стеклопластикового корпуса.

    Эталон ПВТ Ø1800×H3000 = 990 кг (без насосов и арматуры) — даёт
    удельный 130 кг/м² бок. поверхности.
    """
    import math
    surface_m2 = math.pi * (diameter_mm / 1000.0) * (height_mm / 1000.0)
    bottom_m2 = math.pi * (diameter_mm / 2000.0) ** 2
    total_m2 = surface_m2 + bottom_m2 + bottom_m2  # стенки + дно + крышка
    return int(round(total_m2 * 130.0))


def compute_corpus_size(
    Q_m3h: float,
    P_kW: float,
    depth_inlet_mm: float | None = None,
    n_pumps: int = 2,
    corpus_type: CorpusType = "pe",
) -> CorpusSize:
    """Главная функция — возвращает размеры корпуса КНС.

    Args:
        Q_m3h: расход
        P_kW: мощность одного насоса (для оценки footprint)
        depth_inlet_mm: глубина подвода (default 2000 мм для бытовой самотёчной)
        n_pumps: количество насосов (для будущей логики увеличения диаметра)
        corpus_type: pe (Серво-Юг) или glass (стеклопластик ПВТ)
    """
    depth = depth_inlet_mm if depth_inlet_mm is not None else 2000.0

    diameter = select_corpus_diameter_mm(Q_m3h)
    height = estimate_corpus_height_mm(Q_m3h, P_kW, depth, n_pumps)

    # 3+ насоса требуют большего диаметра — увеличиваем на 1 шаг лестницы
    if n_pumps >= 3:
        for _q_max, dia in _DIAMETER_LADDER_BY_Q:
            if dia > diameter:
                diameter = dia
                break

    inlet_dn = select_inlet_dn_mm(Q_m3h)
    outlet_dn = select_discharge_dn_mm(Q_m3h)
    weight = estimate_corpus_weight_kg(diameter, height)

    notes: list[str] = []
    if Q_m3h < 5:
        notes.append(
            "Q < 5 м³/ч — для частного коттеджа корпус обычно не нужен, "
            "достаточно готового приямка"
        )
    if depth > 4000:
        notes.append(
            "Глубина подвода >4 м — требуется горизонтальный анкеровка против "
            "выталкивания грунтовыми водами (см. СП 32.13330 §6.3)"
        )
    if n_pumps >= 3:
        notes.append(
            f"{n_pumps} насосов — диаметр увеличен на 1 шаг для размещения "
            "автомуфт и обслуживания"
        )

    return CorpusSize(
        diameter_mm=diameter,
        height_mm=height,
        inlet_DN_mm=inlet_dn,
        outlet_DN_mm=outlet_dn,
        weight_estimate_kg=weight,
        notes=notes,
    )
