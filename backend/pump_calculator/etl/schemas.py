"""Pydantic-модели для входных raw-данных ETL.

`RawPumpRecord` — то что человек/парсер заполняет.
После импорта (importer.py) превращается в запись pumps.json формата.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QHPoint(BaseModel):
    """Одна точка Q-H кривой из паспорта."""

    Q_m3h: float = Field(..., ge=0, description="Расход, м³/ч")
    H_m: float = Field(..., ge=0, description="Напор, м")
    eta_pct: float | None = Field(None, ge=0, le=100, description="КПД в этой точке, %")
    P_kW: float | None = Field(None, ge=0, description="Мощность на валу, кВт")
    NPSHr_m: float | None = Field(None, ge=0, description="NPSH required, м")


class RawPumpRecord(BaseModel):
    """Сырая запись насоса до конвертации в формат pumps.json.

    Поля расположены так, как удобно человеку при ручном вводе из паспорта.
    Поля envelope (Q_min, Q_max, H_min, H_max, Q_BEP, eta_BEP) ВЫЧИСЛЯЮТСЯ
    автоматически из qh_curve в curve_fitter.
    """

    # ----- Идентификация -----
    brand: str
    model: str
    type: Literal[
        "submersible_sewage",
        "submersible_drainage",
        "submersible_cutter",
        "submersible_vortex",
        "dry_pit_sewage",
        "multistage_vertical",
        "booster_station",
    ]
    impeller: Literal[
        "vortex", "single-channel", "multi-channel",
        "open", "semi-open", "cutter", "closed",
    ] | None = None
    free_passage_mm: float = Field(..., ge=0, le=200)

    # ----- Q-H паспорт -----
    qh_curve: list[QHPoint] = Field(
        ..., min_length=3,
        description="Минимум 3 точки. Рекомендуется 5: shutoff, 25%, 50%, BEP, 125%.",
    )

    # ----- Силовые параметры -----
    P_kW: float = Field(..., gt=0, description="Номинальная мощность двигателя")
    voltage_v: int = Field(380, description="Напряжение")
    phase: int = Field(3, description="Фаз")
    ip_rating: str = "IP68"
    ex_rating: str | None = None

    # ----- Подключение -----
    discharge_DN_mm: float | None = None

    # ----- Совместимость -----
    wastewater_compat: list[Literal["domestic", "drainage", "industrial", "clean_water"]]

    # ----- Бизнес-метаданные -----
    price_segment: Literal["budget", "mid", "premium"]
    available_ru_status: Literal["official", "parallel_import", "stock_only", "discontinued"] = "official"
    distributor: str | None = None
    lead_time_ru: str | None = None
    warranty_months: int = Field(12, ge=0, le=120)

    # ----- Источник -----
    datasheet_url: str | None = None
    image_url: str | None = None
    notes: str | None = None
    source: str = Field(..., description="Откуда: 'manual', 'docling-pdf-2026-05', 'wilo-select-scrape', ...")
