"""Тесты Phase 27 — ЛОС."""
from __future__ import annotations

from pump_calculator.los import (
    LOS_CATALOG,
    POLLUTANT_LIMITS_BY_DISCHARGE,
    LOSScenarioInput,
    calc_purification_efficiency,
    select_los_block,
    typical_influent_for_object,
)


def test_typical_domestic_influent_bod_in_range():
    """Хозбытовые: БПК 200-300 мг/л."""
    inf = typical_influent_for_object("domestic")
    assert 200 <= inf.bod5 <= 300


def test_typical_leachate_higher_bod():
    """Фильтрат ТКО — BOD на порядки выше хозбытового."""
    domestic = typical_influent_for_object("domestic")
    leachate = typical_influent_for_object("leachate_landfill")
    assert leachate.bod5 > domestic.bod5 * 50


def test_pdk_fishery_strictest():
    """Рыбохоз. ПДК — самые строгие по БПК."""
    central = POLLUTANT_LIMITS_BY_DISCHARGE["central_sewerage"]["bod5"]
    fishery = POLLUTANT_LIMITS_BY_DISCHARGE["fishery_water"]["bod5"]
    assert fishery < central


def test_purification_required_high_for_fishery():
    """Хозбытовые → рыбохоз. → требуется очистка БПК ≥99%."""
    domestic = typical_influent_for_object("domestic")
    eff = calc_purification_efficiency(domestic, "fishery_water")
    assert eff["bod5"] >= 99.0


def test_purification_required_low_for_central():
    """Хозбытовые → центр. канализация → очистка минимальная."""
    domestic = typical_influent_for_object("domestic")
    eff = calc_purification_efficiency(domestic, "central_sewerage")
    # 250 → 300 → не требуется очистка по БПК
    assert eff["bod5"] == 0.0


def test_select_los_household_5_persons():
    """5 чел → блок на 1 м³/сут (PEGAS-Б 5 / Топас 5).

    Сброс в irrigation (полив, мягкие ПДК) — типовая бытовая ЛОС
    с био-очисткой 95% покрывает требование.
    """
    inputs = LOSScenarioInput(
        source_type="domestic",
        flow_m3_per_day=1.0,
        discharge_category="irrigation",
        population_equivalent=5,
    )
    result = select_los_block(inputs)
    assert result.selected_block is not None
    assert result.selected_block.capacity_m3_per_day >= 1.0
    assert result.selected_block.capacity_m3_per_day <= 5.0


def test_select_los_50_persons_pegas_or_topas():
    """50 чел → блок на 10 м³/сут (irrigation, био-очистка)."""
    inputs = LOSScenarioInput(
        source_type="domestic",
        flow_m3_per_day=10.0,
        discharge_category="irrigation",
        population_equivalent=50,
    )
    result = select_los_block(inputs)
    assert result.selected_block is not None
    assert result.selected_block.capacity_m3_per_day >= 10.0


def test_select_los_fishery_uses_deep_treatment():
    """Сброс в рыбхоз. водоём → требуется deep_treatment."""
    inputs = LOSScenarioInput(
        source_type="domestic",
        flow_m3_per_day=200.0,
        discharge_category="fishery_water",
        population_equivalent=1000,
    )
    result = select_los_block(inputs)
    assert result.treatment_level == "deep_treatment"
    if result.selected_block:
        assert result.selected_block.technology in ("deep_treatment", "advanced")


def test_select_los_leachate_advanced():
    """Фильтрат ТКО → только advanced."""
    inputs = LOSScenarioInput(
        source_type="leachate_landfill",
        flow_m3_per_day=100.0,
        discharge_category="household_source",
    )
    result = select_los_block(inputs)
    assert result.treatment_level == "advanced"


def test_los_catalog_has_pegas_topas():
    """В каталоге есть PEGAS и ТОПАС."""
    manufacturers = {b.manufacturer for b in LOS_CATALOG}
    assert "PEGAS" in manufacturers
    assert "ТОПАС" in manufacturers


def test_los_references_returned():
    """Каждый расчёт возвращает ссылки на нормативы."""
    inputs = LOSScenarioInput(
        source_type="domestic",
        flow_m3_per_day=1.0,
        discharge_category="central_sewerage",
    )
    result = select_los_block(inputs)
    codes = [r["regulation_code"] for r in result.references]
    assert any("СП 32" in c for c in codes)
    assert any("728" in c for c in codes)
