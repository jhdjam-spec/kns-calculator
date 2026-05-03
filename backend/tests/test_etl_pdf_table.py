"""Тесты `pump_calculator.etl.pdf.table_extractor`.

Все тесты — rule-based (без LLM-вызовов). Реальные таблицы получаем через
`pdfplumber_runner.run_pdfplumber` на фикстуре Pedrollo VX 50 Hz datasheet
(4 страницы, 8 пар single/three-phase моделей = 16 RawPumpDraft).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pump_calculator.etl.pdf.pdfplumber_runner import run_pdfplumber
from pump_calculator.etl.pdf.splitter import split_pdf
from pump_calculator.etl.pdf.table_extractor import (
    RawPumpDraft,
    extract_pumps_from_chunks,
)

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "pedrollo_vx_50hz.pdf"


# ----- Общая фикстура ------------------------------------------------------


@pytest.fixture(scope="module")
def pedrollo_drafts(tmp_path_factory: pytest.TempPathFactory) -> list[RawPumpDraft]:
    """Один прогон pdfplumber + извлечение для всех тестов модуля.

    `scope="module"` — чтобы не дёргать pdfplumber на каждом тесте; pdfplumber
    на 4-страничном Pedrollo VX отрабатывает ~0.5-1 сек, но мы экономим CI-время.
    """
    base = tmp_path_factory.mktemp("pedrollo_table_extract")
    chunks = split_pdf(FIXTURE_PDF, base / "chunks", pages_per_chunk=4)
    chunk_doc = run_pdfplumber(chunks[0], output_dir=base / "plumber")
    return extract_pumps_from_chunks([chunk_doc], brand_hint="Pedrollo", use_llm=False)


# ----- Основные тесты на rule-based извлечение -----------------------------


def test_extract_pedrollo_vx_returns_16_models_rule_based(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """Должно быть ровно 16 моделей: 8 single-phase VXm + 8 three-phase VX."""
    assert len(pedrollo_drafts) == 16, (
        f"ожидаем 16 моделей (8 пар), получили {len(pedrollo_drafts)}: "
        f"{[d.model for d in pedrollo_drafts]}"
    )

    vxm_count = sum(1 for d in pedrollo_drafts if d.model.startswith("VXm "))
    vx_count = sum(1 for d in pedrollo_drafts if d.model.startswith("VX "))
    assert vxm_count == 8
    assert vx_count == 8


def test_extract_pedrollo_vx_models_have_correct_brand(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """brand='Pedrollo' для всех записей."""
    assert all(d.brand == "Pedrollo" for d in pedrollo_drafts)


def test_extract_pedrollo_vx_vxm_is_single_phase(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """Все VXm — single-phase 230 В."""
    vxm = [d for d in pedrollo_drafts if d.model.startswith("VXm ")]
    assert vxm, "нет ни одной VXm-модели"
    for d in vxm:
        assert d.voltage_v == 230, f"{d.model}: voltage_v={d.voltage_v}, ожидаем 230"
        assert d.phase == 1, f"{d.model}: phase={d.phase}, ожидаем 1"


def test_extract_pedrollo_vx_vx_is_three_phase(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """Все VX (без 'm') — three-phase 380/400 В."""
    vx_only = [d for d in pedrollo_drafts if d.model.startswith("VX ")]
    assert vx_only, "нет ни одной VX-модели"
    for d in vx_only:
        assert d.voltage_v == 380, f"{d.model}: voltage_v={d.voltage_v}, ожидаем 380"
        assert d.phase == 3, f"{d.model}: phase={d.phase}, ожидаем 3"


def test_extract_pedrollo_vx_power_kW_correct(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """Контроль номинальной мощности на двух крайних моделях."""
    by_model = {d.model: d for d in pedrollo_drafts}

    # VXm 8/35 → P2 = 0.55 кВт (см. паспорт, столбец POWER (P2) kW)
    assert by_model["VXm 8/35"].P_kW == pytest.approx(0.55)
    # VX 20/50 → P2 = 1.5 кВт
    assert by_model["VX 20/50"].P_kW == pytest.approx(1.5)
    # Заодно проверим, что VXm и VX одного типоразмера имеют одинаковую мощность
    assert by_model["VXm 20/50"].P_kW == pytest.approx(by_model["VX 20/50"].P_kW)


def test_extract_pedrollo_vx_free_passage_correct(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """Серия /35 имеет проход 40 мм, серия /50 — 50 мм."""
    for d in pedrollo_drafts:
        size = d.model.split("/")[-1]  # '35' или '50'
        expected = 40.0 if size == "35" else 50.0
        assert d.free_passage_mm == pytest.approx(expected), (
            f"{d.model}: free_passage_mm={d.free_passage_mm}, ожидаем {expected}"
        )


def test_extract_pedrollo_vx_dn_correct(
    pedrollo_drafts: list[RawPumpDraft],
) -> None:
    """Серия /35 имеет DN=40 (1½\"), серия /50 — DN=50 (2\")."""
    for d in pedrollo_drafts:
        size = d.model.split("/")[-1]
        expected = 40.0 if size == "35" else 50.0
        assert d.discharge_DN_mm == pytest.approx(expected), (
            f"{d.model}: discharge_DN_mm={d.discharge_DN_mm}, ожидаем {expected}"
        )


# ----- Поведение относительно ANTHROPIC_API_KEY ----------------------------


def test_rule_based_works_without_api_key(
    pedrollo_drafts: list[RawPumpDraft],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """use_llm=False работает без ANTHROPIC_API_KEY (полностью offline)."""
    # Гарантируем, что ключа в окружении нет
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=4)
    chunk_doc = run_pdfplumber(chunks[0], output_dir=tmp_path / "plumber")

    drafts = extract_pumps_from_chunks([chunk_doc], brand_hint="Pedrollo", use_llm=False)
    assert len(drafts) == 16
    # И базовый sanity: те же модели, что и в module-фикстуре
    assert {d.model for d in drafts} == {d.model for d in pedrollo_drafts}


def test_llm_mode_raises_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """use_llm=True без ANTHROPIC_API_KEY → понятный RuntimeError, без сетевых вызовов."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    chunks = split_pdf(FIXTURE_PDF, tmp_path / "chunks", pages_per_chunk=4)
    chunk_doc = run_pdfplumber(chunks[0], output_dir=tmp_path / "plumber")

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        extract_pumps_from_chunks([chunk_doc], brand_hint="Pedrollo", use_llm=True)
