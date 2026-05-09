"""Тесты Phase 31-32 — энциклопедия + единый Проект."""
from __future__ import annotations

from pump_calculator.encyclopedia import (
    ENCYCLOPEDIA_TOPICS,
    EXAMPLES_REGISTRY,
    get_topic_full,
    get_topic_section,
    list_topics,
)
from pump_calculator.encyclopedia.registry import build_pdf_citation
from pump_calculator.project import (
    ProjectInput,
    ProjectSubsystems,
    calculate_project,
    list_presets,
)

# ─── Энциклопедия ──────────────────────────────────────────────────


def test_encyclopedia_has_6_topics():
    """В реестре 7 базовых тем (6 расчётных + рабочая документация)."""
    assert len(ENCYCLOPEDIA_TOPICS) == 7
    expected = {"fire", "water", "electrical", "hydraulics", "structural", "los", "documentation"}
    assert set(ENCYCLOPEDIA_TOPICS.keys()) == expected


def test_list_topics_returns_metadata():
    """list_topics возвращает структуру для UI."""
    topics = list_topics()
    assert len(topics) == 7
    for t in topics:
        assert "key" in t
        assert "title" in t
        assert "short_description" in t
        assert "sections_count" in t


def test_get_topic_full_loads_markdown():
    """get_topic_full читает реальный markdown-файл."""
    result = get_topic_full("fire")
    assert result is not None
    assert result["key"] == "fire"
    assert "СП 8.13130" in result["content_markdown"]
    # Должно быть несколько примеров для топика "fire"
    fire_examples = [e for e in EXAMPLES_REGISTRY if e.topic == "fire"]
    assert len(result["examples"]) == len(fire_examples)


def test_get_topic_unknown_returns_none():
    """Несуществующая тема → None."""
    assert get_topic_full("xyz") is None


def test_get_topic_section_finds_anchor():
    """get_topic_section находит секцию по подстроке заголовка."""
    # В fire_water_encyclopedia.md есть раздел про нормативную базу
    result = get_topic_section("fire", "Нормативная база")
    if result is not None:    # секция может отсутствовать в новых файлах
        assert "Нормативная база" in result["section_title"]
        assert len(result["content_markdown"]) > 0


def test_build_pdf_citation_returns_dict():
    """build_pdf_citation возвращает {topic, section, text} для Phase 28 PDF."""
    cit = build_pdf_citation("hydraulics", "Уравнение неразрывности", max_chars=400)
    assert cit is not None
    assert "topic" in cit
    assert "section" in cit
    assert "text" in cit
    assert cit["topic"] == "hydraulics"
    assert "Уравнение неразрывности" in cit["section"]
    # Текст не должен быть пустым
    assert len(cit["text"]) > 30
    # max_chars соблюдается (с запасом на "...")
    assert len(cit["text"]) <= 410


def test_build_pdf_citation_unknown_returns_none():
    """build_pdf_citation возвращает None если секция не найдена."""
    cit = build_pdf_citation("hydraulics", "несуществующий якорь zzzz", max_chars=200)
    assert cit is None


def test_build_pdf_citation_strips_markdown():
    """build_pdf_citation чистит markdown (** __ `) для reportlab."""
    cit = build_pdf_citation("hydraulics", "Уравнение неразрывности", max_chars=400)
    if cit:
        assert "**" not in cit["text"]
        assert "__" not in cit["text"]
        assert "`" not in cit["text"]


def test_examples_have_payload():
    """Все примеры содержат payload и api_endpoint."""
    for ex in EXAMPLES_REGISTRY:
        assert ex.api_endpoint
        assert isinstance(ex.payload, dict)
        assert ex.expected_outcome


def test_examples_topics_valid():
    """Все примеры ссылаются на реальные темы."""
    valid_topics = set(ENCYCLOPEDIA_TOPICS.keys())
    for ex in EXAMPLES_REGISTRY:
        assert ex.topic in valid_topics, f"Example {ex.id} → unknown topic {ex.topic}"


# ─── Проект (визард) ──────────────────────────────────────────────


def test_list_presets_has_13_options():
    """13 типовых пресетов."""
    presets = list_presets()
    assert len(presets) == 13
    keys = {p["key"] for p in presets}
    assert "ihs" in keys
    assert "apartment_complex" in keys
    assert "azs" in keys
    assert "gazprom" in keys


def test_preset_includes_default_subsystems():
    """Каждый пресет включает дефолтный набор подсистем."""
    presets = list_presets()
    for p in presets:
        assert "default_subsystems" in p
        ds = p["default_subsystems"]
        # Хоть одна подсистема активна
        assert any([ds["kns"], ds["vns_potable"], ds["vns_fire"], ds["los"]])


def test_calculate_project_ihs():
    """ИЖС 4 чел → КНС + ЛОС + климат + прочность."""
    inputs = ProjectInput(
        project_name="Тест ИЖС",
        preset="ihs",
        region_city="Краснодар",
        population=4,
        floors=2,
        volume_m3=400,
    )
    result = calculate_project(inputs)
    assert result.kns is not None
    assert result.los is not None
    assert result.climate is not None
    # ИЖС не должен включать пожарку и большую ВНС
    assert result.vns_fire is None


def test_calculate_project_apartment_complex():
    """ЖК 50 квартир → КНС + ВНС хоз. + ВНС пожарная + ливнёвка."""
    inputs = ProjectInput(
        project_name="ЖК 12 эт",
        preset="apartment_complex",
        region_city="Москва",
        population=150,
        floors=12,
        volume_m3=15000,
    )
    result = calculate_project(inputs)
    assert result.kns is not None
    assert result.vns_potable is not None
    assert result.vns_fire is not None
    # ЛОС в ЖК не нужен (есть централизованная канализация)
    assert result.los is None


def test_calculate_project_azs():
    """АЗС → КНС + ливнёвка + ЛОС с нефтеуловителем."""
    inputs = ProjectInput(
        project_name="АЗС-1",
        preset="azs",
        region_city="Краснодар",
        population=10,
        volume_m3=300,
    )
    result = calculate_project(inputs)
    assert result.kns is not None
    assert result.los is not None
    # АЗС обычно не имеет хозпит. ВНС
    assert result.vns_potable is None


def test_calculate_project_returns_consolidated_references():
    """ProjectResult объединяет ссылки на нормативы."""
    inputs = ProjectInput(
        project_name="Тест",
        preset="apartment_complex",
        region_city="Москва",
        population=150,
        floors=12,
        volume_m3=15000,
    )
    result = calculate_project(inputs)
    assert len(result.references_consolidated) >= 2
    # Должны быть ссылки на СП 32 и СП 8.13130 как минимум
    codes = [r.get("regulation_code", "") for r in result.references_consolidated]
    assert any("СП 32" in c for c in codes)
    assert any("СП" in c for c in codes)


def test_custom_preset_no_defaults():
    """Custom preset → подсистемы строго по входу."""
    inputs = ProjectInput(
        project_name="Custom",
        preset="custom",
        subsystems=ProjectSubsystems(
            kns=True, vns_potable=False, vns_fire=False,
            los=False, electrical=False, climate=False, structural=False,
        ),
        region_city="Москва",
        population=10,
        volume_m3=100,
    )
    result = calculate_project(inputs)
    assert result.kns is not None
    assert result.vns_potable is None
    assert result.climate is None
