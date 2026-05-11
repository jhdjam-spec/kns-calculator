"""Total Cost of Ownership (TCO) калькулятор для КНС.

Считает полную стоимость владения насосной станцией за период (1-15 лет):
    CAPEX (one-time)  — насос, корпус, шкаф, обвязка, монтаж, доставка, пригруз.
    OPEX  (annual×N)  — электричество, ТО, амортизация (замена насоса),
                        промывка корпуса, износ электроники.

Главный продуктовый смысл: «Кубометр стоков стоит X ₽» — позволяет менеджеру
ОП обосновать заказчику выбор премиум-насоса (КПД +10% → −150 тыс ₽/год за
10 лет).

Источники:
    • Тарифы электроэнергии РФ 2026: 7.50 ₽/кВт·ч (среднее, ФСТ).
    • Срок службы насоса: СП 32.13330.2018 п.6.1.7 — 7-10 лет.
    • ТО: 5% от стоимости насоса/год (Wilo Service Bulletin, Grundfos LCC).
    • Промывка корпуса: 30-50 тыс ₽/раз, 1-2 раза/год (Серво-Юг 2025-2026).
    • Износ ШУ/электроники: 2% cabinet_rub/год (МЭК 60721-3-3).
    • Hours/year:
        - continuous   — 8760 ч × 0.95 загрузки = 8322
        - periodic     — 8760 × 0.50 = 4380 ч
        - level_based  — 8760 × 0.30 = 2628 ч (по поплавкам, бытовой)

ВНИМАНИЕ: это **ориентир для менеджера ОП**, а не аудит TCO по ISO 15686.
Точный расчёт делает инженер с учётом графика работы, локального тарифа,
амортизации по конкретной модели.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from pump_calculator.schemas import OperatingMode, PriceBreakdown

# -------- Дефолты тарифов и износа --------

#: Средний тариф РФ на электроэнергию, ₽/кВт·ч, 2026 (ФСТ).
DEFAULT_TARIFF_RUB_PER_KWH: float = 7.50

#: Часы работы в год по режимам.
HOURS_PER_YEAR: dict[str, float] = {
    "continuous": 8322.0,   # 8760 × 0.95
    "periodic": 4380.0,     # 8760 × 0.5
    "level_based": 2628.0,  # 8760 × 0.3 (бытовая КНС по поплавкам)
}

#: Срок службы насоса по СП 32.13330 п.6.1.7, лет.
PUMP_LIFETIME_YEARS: float = 8.0

#: Годовая доля от стоимости насоса на ТО (Wilo LCC, Grundfos Service Manual).
MAINTENANCE_RATE_PUMP: float = 0.05  # 5%/год

#: Промывка корпуса КНС от наслоений и осадка, ₽/раз × 1.5 раза/год.
CLEANING_COST_PER_YEAR_RUB: int = 60_000  # 40 тыс × 1.5

#: Износ электроники ШУ — датчики, контактеры, реле, ЧРП. МЭК 60721-3-3.
ELECTRONICS_WEAR_RATE: float = 0.02  # 2%/год от cabinet_rub

TCOMode = Literal["10y", "5y", "1y", "annual"]


# -------- Pydantic-модели входа/выхода --------


class TCOCapexBreakdown(BaseModel):
    """Разбивка CAPEX, ₽ — берём из PriceBreakdown KNS-комплекта."""

    pump_rub: int = 0
    corpus_rub: int = 0
    cabinet_rub: int = 0
    fittings_rub: int = 0       # atm + valve + check_valve + rails + chain + floats
    install_rub: int = 0        # 10% от total (монтаж + ПНР)
    transport_rub: int = 0      # 3% от total (логистика)
    anti_buoyancy_rub: int = 0  # уже включено в corpus, дублируем для прозрачности
    total_rub: int = 0


class TCOOpexBreakdown(BaseModel):
    """Разбивка OPEX в год, ₽/год."""

    electricity_rub: int = 0
    maintenance_rub: int = 0
    depreciation_rub: int = 0   # амортизация (замена насоса каждые ~8 лет)
    cleaning_rub: int = 0       # промывка корпуса
    electronics_rub: int = 0    # износ ШУ
    total_annual_rub: int = 0


class TCOResult(BaseModel):
    """Результат расчёта TCO.

    `cost_per_m3_rub` — главный KPI для менеджера ОП.
    """

    horizon_years: int = Field(10, description="Горизонт расчёта, лет")
    operating_mode: str = Field("level_based", description="Режим работы насоса")
    hours_per_year: float = Field(2628.0, description="Часы работы в год")
    tariff_rub_per_kwh: float = Field(7.5, description="Тариф электроэнергии, ₽/кВт·ч")

    capex: TCOCapexBreakdown = Field(default_factory=TCOCapexBreakdown)
    opex_annual: TCOOpexBreakdown = Field(default_factory=TCOOpexBreakdown)

    opex_horizon_rub: int = Field(0, description="OPEX суммарно за весь горизонт, ₽")
    tco_horizon_rub: int = Field(0, description="CAPEX + OPEX_horizon, ₽")
    flow_horizon_m3: float = Field(0.0, description="Расход через КНС за горизонт, м³")
    cost_per_m3_rub: float = Field(0.0, description="Стоимость 1 м³ стоков, ₽")

    # Для Sankey: список узлов и связей (frontend читает напрямую)
    sankey_nodes: list[dict] = Field(default_factory=list)
    sankey_links: list[dict] = Field(default_factory=list)


# -------- Вспомогательные --------


def _hours_per_year(mode: OperatingMode | None) -> float:
    """Часы работы в год по режиму. Default = level_based."""
    if mode is None:
        return HOURS_PER_YEAR["level_based"]
    return HOURS_PER_YEAR.get(mode, HOURS_PER_YEAR["level_based"])


def _fittings_total(breakdown: PriceBreakdown) -> int:
    """Сумма обвязки: атм + задвижки + ОК + направляющие + цепь + поплавки."""
    return (
        breakdown.atm_rub
        + breakdown.valve_rub
        + breakdown.check_valve_rub
        + breakdown.rails_rub
        + breakdown.chain_rub
        + breakdown.floats_rub
    )


def _build_sankey(capex: TCOCapexBreakdown, opex_horizon: TCOOpexBreakdown,
                  horizon_years: int) -> tuple[list[dict], list[dict]]:
    """Сборка узлов/связей для Sankey-диаграммы.

    Структура:
        CAPEX → [Насос, Корпус, Шкаф, Обвязка, Монтаж, Транспорт] ─┐
                                                                    ├─→ TCO
        OPEX → [Электр., ТО, Амортизация, Промывка, Электроника]  ─┘
    """
    # opex_horizon уже умножен на N лет
    nodes = [
        {"id": "capex", "name": "CAPEX", "category": "root", "value": capex.total_rub},
        {"id": "opex", "name": f"OPEX {horizon_years}y", "category": "root",
         "value": opex_horizon.total_annual_rub},
        {"id": "pump", "name": "Насосы", "category": "capex", "value": capex.pump_rub},
        {"id": "corpus", "name": "Корпус КНС", "category": "capex", "value": capex.corpus_rub},
        {"id": "cabinet", "name": "Шкаф управления", "category": "capex", "value": capex.cabinet_rub},
        {"id": "fittings", "name": "Обвязка", "category": "capex", "value": capex.fittings_rub},
        {"id": "install", "name": "Монтаж + ПНР", "category": "capex", "value": capex.install_rub},
        {"id": "transport", "name": "Доставка", "category": "capex", "value": capex.transport_rub},
        {"id": "electricity", "name": "Электричество", "category": "opex",
         "value": opex_horizon.electricity_rub},
        {"id": "maintenance", "name": "ТО", "category": "opex",
         "value": opex_horizon.maintenance_rub},
        {"id": "depreciation", "name": "Замена насоса", "category": "opex",
         "value": opex_horizon.depreciation_rub},
        {"id": "cleaning", "name": "Промывка корпуса", "category": "opex",
         "value": opex_horizon.cleaning_rub},
        {"id": "electronics", "name": "Износ электроники", "category": "opex",
         "value": opex_horizon.electronics_rub},
        {"id": "tco", "name": f"TCO {horizon_years}y", "category": "total",
         "value": capex.total_rub + opex_horizon.total_annual_rub},
    ]

    links = [
        # CAPEX → компоненты
        {"source": "pump", "target": "capex", "value": capex.pump_rub},
        {"source": "corpus", "target": "capex", "value": capex.corpus_rub},
        {"source": "cabinet", "target": "capex", "value": capex.cabinet_rub},
        {"source": "fittings", "target": "capex", "value": capex.fittings_rub},
        {"source": "install", "target": "capex", "value": capex.install_rub},
        {"source": "transport", "target": "capex", "value": capex.transport_rub},
        # OPEX → компоненты
        {"source": "electricity", "target": "opex", "value": opex_horizon.electricity_rub},
        {"source": "maintenance", "target": "opex", "value": opex_horizon.maintenance_rub},
        {"source": "depreciation", "target": "opex", "value": opex_horizon.depreciation_rub},
        {"source": "cleaning", "target": "opex", "value": opex_horizon.cleaning_rub},
        {"source": "electronics", "target": "opex", "value": opex_horizon.electronics_rub},
        # CAPEX + OPEX → TCO
        {"source": "capex", "target": "tco", "value": capex.total_rub},
        {"source": "opex", "target": "tco", "value": opex_horizon.total_annual_rub},
    ]
    # Отфильтруем нулевые links (для чистоты диаграммы)
    links = [link for link in links if link["value"] > 0]
    return nodes, links


# -------- Главная функция --------


def calculate_tco(
    pump_price_breakdown: PriceBreakdown,
    P_kW: float,
    Q_m3h: float,
    horizon_years: int = 10,
    operating_mode: OperatingMode | None = None,
    tariff_rub_per_kwh: float = DEFAULT_TARIFF_RUB_PER_KWH,
    install_pct: float = 0.10,
    transport_pct: float = 0.03,
) -> TCOResult:
    """Главная функция: рассчитать TCO на N лет.

    Параметры:
      pump_price_breakdown — PriceBreakdown из pricing.estimate_kns_kit_price.
      P_kW — мощность ОДНОГО рабочего насоса (1 рабочий + 1 резерв = в работе 1).
      Q_m3h — производительность КНС (для расчёта пропущенного объёма).
      horizon_years — горизонт TCO, лет (default 10).
      operating_mode — continuous / periodic / level_based.
      tariff_rub_per_kwh — тариф электроэнергии (default 7.5 ₽/кВт·ч).
      install_pct — доля монтажа от total CAPEX без install/transport (default 10%).
      transport_pct — доля логистики (default 3%).

    Возвращает TCOResult с полной разбивкой + sankey_nodes/links для UI.

    Пример:
      >>> bd = PriceBreakdown(pump_rub=200_000, cabinet_rub=266_000,
      ...                     corpus_rub=350_000, valve_rub=40_000,
      ...                     check_valve_rub=30_000, atm_rub=20_000,
      ...                     floats_rub=20_000, total_rub=926_000)
      >>> result = calculate_tco(bd, P_kW=3.0, Q_m3h=15.0, horizon_years=10)
      >>> result.cost_per_m3_rub > 0
      True
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be > 0")
    if P_kW <= 0:
        raise ValueError("P_kW must be > 0")
    if Q_m3h <= 0:
        raise ValueError("Q_m3h must be > 0")
    if tariff_rub_per_kwh <= 0:
        raise ValueError("tariff_rub_per_kwh must be > 0")

    # ── CAPEX ──
    pump_rub = pump_price_breakdown.pump_rub
    corpus_rub = pump_price_breakdown.corpus_rub
    cabinet_rub = pump_price_breakdown.cabinet_rub
    fittings_rub = _fittings_total(pump_price_breakdown)

    capex_base = pump_rub + corpus_rub + cabinet_rub + fittings_rub
    install_rub = int(round(capex_base * install_pct))
    transport_rub = int(round(capex_base * transport_pct))
    capex_total = capex_base + install_rub + transport_rub

    capex = TCOCapexBreakdown(
        pump_rub=pump_rub,
        corpus_rub=corpus_rub,
        cabinet_rub=cabinet_rub,
        fittings_rub=fittings_rub,
        install_rub=install_rub,
        transport_rub=transport_rub,
        anti_buoyancy_rub=0,  # уже включено в corpus_rub
        total_rub=capex_total,
    )

    # ── OPEX (annual) ──
    hours = _hours_per_year(operating_mode)

    # 1. Электричество. P_kW × hours × tariff. Один рабочий насос
    #    (резерв в покое — потребляет только heating tape, пренебрегаем).
    electricity_annual = int(round(P_kW * hours * tariff_rub_per_kwh))

    # 2. ТО — 5% от стоимости насосов (включая резерв) в год.
    #    Резерв тоже обслуживается (ежегодная прокрутка, ТО-1).
    maintenance_annual = int(round(pump_rub * MAINTENANCE_RATE_PUMP))

    # 3. Амортизация — замена насосов каждые 8 лет.
    #    pump_rub / 8 — линейная амортизация всей группы насосов.
    depreciation_annual = int(round(pump_rub / PUMP_LIFETIME_YEARS))

    # 4. Промывка корпуса — фиксированная сумма в год, только если есть корпус.
    cleaning_annual = CLEANING_COST_PER_YEAR_RUB if corpus_rub > 0 else 0

    # 5. Износ электроники ШУ — 2% от cabinet_rub в год.
    electronics_annual = int(round(cabinet_rub * ELECTRONICS_WEAR_RATE))

    opex_total_annual = (
        electricity_annual + maintenance_annual + depreciation_annual
        + cleaning_annual + electronics_annual
    )

    opex_annual = TCOOpexBreakdown(
        electricity_rub=electricity_annual,
        maintenance_rub=maintenance_annual,
        depreciation_rub=depreciation_annual,
        cleaning_rub=cleaning_annual,
        electronics_rub=electronics_annual,
        total_annual_rub=opex_total_annual,
    )

    # ── OPEX horizon (умножаем на N лет) ──
    opex_horizon = TCOOpexBreakdown(
        electricity_rub=electricity_annual * horizon_years,
        maintenance_rub=maintenance_annual * horizon_years,
        depreciation_rub=depreciation_annual * horizon_years,
        cleaning_rub=cleaning_annual * horizon_years,
        electronics_rub=electronics_annual * horizon_years,
        total_annual_rub=opex_total_annual * horizon_years,
    )

    tco_total = capex_total + opex_horizon.total_annual_rub

    # ── Объём перекачки за горизонт ──
    # Q[м³/ч] × hours/год × N лет — реальная пропускная масса
    flow_horizon_m3 = Q_m3h * hours * horizon_years

    # ── Стоимость 1 м³ ──
    cost_per_m3 = tco_total / flow_horizon_m3 if flow_horizon_m3 > 0 else 0.0

    # ── Sankey nodes/links для frontend ──
    nodes, links = _build_sankey(capex, opex_horizon, horizon_years)

    return TCOResult(
        horizon_years=horizon_years,
        operating_mode=operating_mode or "level_based",
        hours_per_year=hours,
        tariff_rub_per_kwh=tariff_rub_per_kwh,
        capex=capex,
        opex_annual=opex_annual,
        opex_horizon_rub=opex_horizon.total_annual_rub,
        tco_horizon_rub=tco_total,
        flow_horizon_m3=flow_horizon_m3,
        cost_per_m3_rub=round(cost_per_m3, 2),
        sankey_nodes=nodes,
        sankey_links=links,
    )
