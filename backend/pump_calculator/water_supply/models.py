"""Pydantic-модели для калькулятора водопотребления (Phase 23).

Источники: СП 30.13330.2020, СП 31.13330.2021.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Типы зданий по СП 30 прил. А (нормы водопотребления).
BuildingType = Literal[
    "residential_with_baths",       # Жилые с ваннами и душами
    "residential_with_showers",     # Жилые с душами
    "residential_no_baths",         # Жилые без ванн (общежития)
    "hotel_high_class",             # Гостиницы 4-5*
    "hotel_standard",               # Гостиницы 2-3*
    "hostel",                       # Хостел/общежитие
    "office",                       # Офис
    "school",                       # Школа
    "kindergarten",                 # Детский сад
    "hospital",                     # Больница (на койку)
    "polyclinic",                   # Поликлиника (на посещение)
    "shop",                         # Магазин
    "trc",                          # ТРЦ (на 1м² торг.)
    "restaurant",                   # Кафе/ресторан (на блюдо)
    "sports",                       # Спортивный комплекс
    "swimming_pool",                # Бассейн
    "bathhouse",                    # Баня/сауна
    "laundry",                      # Прачечная (на кг белья)
    "carwash",                      # Автомойка
    "industrial_generic",           # Промпредприятие (по технологии)
    "agricultural",                 # Сельхоз (полив, скот)
]

WaterSourceType = Literal[
    "city_network",        # Городская сеть
    "well",                # Скважина
    "open_source",         # Открытый водоём (с водозабором)
    "reservoir_only",      # Только из резервуара (без подвода)
]


class WaterScenarioInput(BaseModel):
    """Входные данные для расчёта водопотребления."""

    building_type: BuildingType = Field(description="Тип здания/объекта")
    population: int = Field(default=0, ge=0, description="Расчётное число пользователей (чел)")
    rooms: int = Field(default=0, ge=0, description="Число номеров (для гостиниц)")
    beds: int = Field(default=0, ge=0, description="Число коек (для больниц)")
    visits_per_day: int = Field(default=0, ge=0, description="Посещений в сутки (поликлиники, бани)")
    area_m2: float = Field(default=0.0, ge=0, description="Площадь (м², для ТРЦ, магазинов)")
    floors: int = Field(default=1, ge=1, description="Этажность (для зонирования)")

    # Дополнительные потребители
    has_hot_water: bool = Field(default=True, description="Горячее водоснабжение")
    has_irrigation: bool = Field(default=False, description="Полив территории")
    irrigation_area_m2: float = Field(default=0.0, ge=0, description="Площадь полива, м²")

    # Источник
    water_source: WaterSourceType = Field(default="city_network", description="Источник водоснабжения")

    # Резерв
    reserve_factor: float = Field(default=0.20, ge=0, le=1, description="Запас на сутки (10-25%)")


class Q_aggregate(BaseModel):
    """Агрегированные расходы для одного типа потребителя."""

    Q_avg_m3_per_day: float = Field(description="Q средний суточный, м³/сут")
    Q_max_day_m3: float = Field(description="Q максимальный суточный (с K_сут_max), м³/сут")
    Q_max_hour_m3h: float = Field(description="Q максимальный часовой, м³/ч")
    Q_max_sec_lps: float = Field(description="Q расчётный секундный, л/с (для трубопроводов)")
    K_sut_max: float = Field(description="Коэф. суточной неравномерности")
    K_hour_max: float = Field(description="Коэф. часовой неравномерности")
    norm_l_per_unit_day: float = Field(description="Норма потребления, л/(ед·сут) — на чел/койку/посещение")
    unit: str = Field(description="Единица — 'чел', 'койка', 'посещение' и т.п.")
    n_units: int = Field(description="Число единиц")


class WaterDemandResult(BaseModel):
    """Результат расчёта водопотребления."""

    cold_water: Q_aggregate
    hot_water: Q_aggregate | None = None
    irrigation: Q_aggregate | None = None
    total_Q_avg_m3_day: float
    total_Q_max_day_m3: float
    total_Q_max_hour_m3h: float
    total_Q_max_sec_lps: float
    references: list[dict]   # RegulationRefDict как dict
    notes: list[str]


class WaterStationSpec(BaseModel):
    """Параметры повысительной насосной станции водоснабжения."""

    operating_pumps: int
    standby_pumps: int
    pump_q_lps: float
    pump_q_m3h: float
    pump_h_m: float
    has_vfd: bool = Field(description="Частотный преобразователь для энергоэкономии")
    has_pressure_tank: bool = Field(description="Гидроаккумулятор для сглаживания пуска")
    reservoir_volume_m3: float | None = Field(description="Объём резервуара (если требуется)")
    notes: list[str]
    reliability_category: int = Field(description="Категория надёжности I/II/III (СП 31 §6.5)")
