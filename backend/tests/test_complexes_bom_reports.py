"""Тесты Phase 28-30 — отчёты, комплексы, BOM."""
from __future__ import annotations

from pump_calculator.bom import (
    BOMItem,
    BOMSpecification,
    build_full_bom,
    export_bom_csv,
    export_bom_markdown,
)
from pump_calculator.complexes import (
    Complex,
    ObjectInComplex,
    Site,
    build_complex_bom_summary,
)
from pump_calculator.reports import (
    CalculationReportInput,
    generate_calculation_report_pdf,
)

# ─── BOM ────────────────────────────────────────────────────────────


def test_bom_item_total_calc():
    """Сумма позиции = qty × price."""
    item = BOMItem(
        section="pumps",
        name="Test pump",
        quantity=2,
        price_rub_2026=50_000,
    )
    assert item.total_rub == 100_000


def test_bom_specification_total():
    """Общая сумма по спецификации."""
    spec = BOMSpecification(
        items=[
            BOMItem(section="pumps", name="P1", quantity=2, price_rub_2026=50_000),
            BOMItem(section="corpus", name="C1", quantity=1, price_rub_2026=300_000),
        ]
    )
    assert spec.total_rub == 400_000


def test_bom_by_section():
    """Группировка по разделам."""
    spec = BOMSpecification(
        items=[
            BOMItem(section="pumps", name="P1", quantity=2, price_rub_2026=50_000),
            BOMItem(section="pumps", name="P2", quantity=1, price_rub_2026=75_000),
            BOMItem(section="corpus", name="C1", quantity=1, price_rub_2026=300_000),
        ]
    )
    by_section = spec.by_section
    assert by_section["pumps"] == 175_000
    assert by_section["corpus"] == 300_000


def test_bom_csv_export():
    """CSV содержит заголовки и итог."""
    spec = BOMSpecification(
        project_code="TEST-1",
        items=[BOMItem(section="pumps", name="P", quantity=1, price_rub_2026=100_000)],
    )
    csv_text = export_bom_csv(spec)
    assert "ИТОГО" in csv_text
    assert "P" in csv_text
    assert "100000" in csv_text


def test_bom_markdown_export():
    """Markdown содержит таблицу и итог."""
    spec = BOMSpecification(
        project_name="ТЕСТ",
        items=[BOMItem(section="corpus", name="Корпус", quantity=1, price_rub_2026=300_000)],
    )
    md = export_bom_markdown(spec)
    assert "ТЕСТ" in md
    assert "ИТОГО" in md
    assert "300" in md


def test_build_full_bom_pump_corpus():
    """build_full_bom собирает позиции."""
    spec = build_full_bom(
        project_code="TEST",
        pump_selection={
            "name": "KAIQUAN 65WQ",
            "article": "KQ-65WQ",
            "manufacturer": "KAIQUAN",
            "quantity": 2,
            "price_rub_2026": 200_000,
        },
        corpus_spec={
            "name": "Стеклопластик BloPlast",
            "article": "BP-1800",
            "manufacturer": "BloPlast",
            "price_rub_2026": 450_000,
            "diameter_mm": 1800,
            "height_mm": 3000,
        },
    )
    assert len(spec.items) == 2
    assert spec.total_rub == 850_000


# ─── Complexes ──────────────────────────────────────────────────────


def test_complex_total_objects():
    """Подсчёт объектов в комплексе."""
    cx = Complex(
        code="KS-14",
        name="КС-14 КазТрансГаз",
        sites=[
            Site(site_id="S1", name="Площадка 1", objects=[
                ObjectInComplex(object_id="K1", object_kind="kns_household"),
                ObjectInComplex(object_id="K2", object_kind="kns_drainage"),
            ]),
            Site(site_id="S2", name="Площадка 2", objects=[
                ObjectInComplex(object_id="V1", object_kind="vns_potable"),
            ]),
        ],
    )
    assert cx.total_objects == 3
    assert len(cx.sites) == 2


def test_complex_summary_consolidated_bom():
    """Сводная BOM объединяет одинаковые позиции."""
    cx = Complex(
        code="TEST",
        name="Тест",
        sites=[Site(site_id="S1", name="S1", objects=[
            ObjectInComplex(
                object_id="O1", object_kind="kns_household",
                bom=[{"name": "Насос KAIQUAN", "article": "KQ-65", "quantity": 2, "price_rub": 100_000}],
                estimated_cost_rub=200_000,
            ),
            ObjectInComplex(
                object_id="O2", object_kind="kns_household",
                bom=[{"name": "Насос KAIQUAN", "article": "KQ-65", "quantity": 2, "price_rub": 100_000}],
                estimated_cost_rub=200_000,
            ),
        ])],
    )
    summary = build_complex_bom_summary(cx)
    # Один и тот же насос в 2 объектах → объединён в одну позицию qty=4
    assert len(summary.bom_consolidated) == 1
    assert summary.bom_consolidated[0]["quantity"] == 4
    assert summary.total_cost_rub == 400_000


def test_complex_cost_breakdown_by_kind():
    """Разбивка стоимости по типам объектов."""
    cx = Complex(
        code="TEST", name="Test",
        sites=[Site(site_id="S1", name="S1", objects=[
            ObjectInComplex(object_id="K1", object_kind="kns_household", estimated_cost_rub=500_000),
            ObjectInComplex(object_id="V1", object_kind="vns_fire", estimated_cost_rub=2_000_000),
        ])],
    )
    summary = build_complex_bom_summary(cx)
    assert summary.cost_breakdown_by_kind["kns_household"] == 500_000
    assert summary.cost_breakdown_by_kind["vns_fire"] == 2_000_000


# ─── Reports (PDF) ──────────────────────────────────────────────────


def test_calculation_report_pdf_generates_bytes():
    """Генерация PDF возвращает bytes (минимальный smoke-тест)."""
    inputs = CalculationReportInput(
        project_name="Тест-проект",
        project_code="TST-001",
        customer="ООО Тестовая",
        inputs_summary={"Q, м³/ч": 50, "H, м": 15},
        hydraulics={"D подобран, мм": 200, "v, м/с": 1.2},
        bom=[
            {"name": "Насос", "article": "P-1", "quantity": 2, "price_rub": 50_000},
            {"name": "Корпус", "article": "C-1", "quantity": 1, "price_rub": 300_000},
        ],
        references=[
            {"regulation_code": "СП 32.13330.2018", "section": "§6", "purpose": "Канализация"},
        ],
    )
    pdf = generate_calculation_report_pdf(inputs)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000   # PDF минимум содержит кое-что
    # PDF должен начинаться с %PDF
    assert pdf[:4] == b"%PDF"
