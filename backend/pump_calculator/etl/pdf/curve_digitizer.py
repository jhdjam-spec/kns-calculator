"""Графическая оцифровка Q-H кривых (для каталогов без числовых таблиц).

⚠️ Phase 6.3: STUB. Pedrollo VX имеет Q-H в табличной форме (см.
:mod:`pump_calculator.etl.pdf.qh_extractor`), поэтому графический парсинг
для него не нужен.

Этот модуль будет реализован в Phase 6.6+ для каталогов KAIQUAN/KSB,
где Q-H представлены только графически. План:
    - ``pdf2image``: PDF page → PNG
    - ``pillow`` color masking: разделение multi-curve по цветам
    - ``subprocess`` ``plotdigitizer``: оцифровка одной кривой за вызов
    - калибровка осей по подписям из docling
"""

from __future__ import annotations

from pathlib import Path


def digitize_curve_image(
    image_path: Path,
    x_axis_range: tuple[float, float],
    y_axis_range: tuple[float, float],
) -> list[tuple[float, float]]:
    """STUB: оцифровать одну кривую с известными осями. Реализация в Phase 6.6.

    Args:
        image_path: PNG с одной (уже цветово-выделенной) кривой.
        x_axis_range: (x_min, x_max) в реальных единицах (например Q м³/ч).
        y_axis_range: (y_min, y_max) в реальных единицах (например H м).

    Returns:
        Список (x, y) точек кривой в реальных единицах.

    Raises:
        NotImplementedError: всегда. Реализация запланирована на Phase 6.6.
    """
    raise NotImplementedError(
        "curve_digitizer будет реализован в Phase 6.6 для каталогов "
        "без числовых Q-H таблиц (KAIQUAN, KSB Amarex KRT). Pedrollo VX "
        "имеет Q-H в табличной форме, см. qh_extractor.py."
    )
