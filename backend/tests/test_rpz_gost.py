"""Тесты Phase 28+ — РПЗ по ГОСТ Р 21.101-2020 (13-разделовая структура)."""
from __future__ import annotations

from pump_calculator.reports import RPZGostInput, generate_rpz_gost_pdf


def test_rpz_gost_minimal_pdf_generates():
    """Минимальный РПЗ — только обязательные поля."""
    inputs = RPZGostInput(
        project_name="Тестовый проект КНС",
    )
    pdf = generate_rpz_gost_pdf(inputs)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf[:4] == b"%PDF"


def test_rpz_gost_full_pdf_with_specification():
    """Полный РПЗ со спецификацией по форме 7 ГОСТ 21.110-2013."""
    inputs = RPZGostInput(
        project_name="ЖК-15 этажей, 50 квартир",
        project_code="БМ.12-КД-НК",
        customer="ООО ВБ Инжиниринг",
        object_address="г. Краснодар, ул. Тестовая, д. 1",
        chief_engineer="Иванов И.И.",
        stage="Р",
        revision="1",
        object_description="Канализационная насосная станция бытовых стоков.",
        technical_conditions="ТУ № 42 от 15.04.2026 от МУП Водоканал.",
        water_demand={"Q_сред м³/сут": 37.5, "Q_max_сек л/с": 4.5},
        sewage_demand={"Q_сток м³/сут": 30, "Q_сток_пик л/с": 8},
        hydraulics={"D трубы DN мм": 100, "v м/с": 1.2, "h_потерь м": 4.5},
        pumps={"Модель": "KAIQUAN 65WQS215-7.5", "P кВт": 7.5, "n_pumps": 2},
        fire_water={"Q_наруж л/с": 15, "V_резервуара м³": 200},
        electrical={"Шкаф": "ШУ ОПТИ", "I_кз кА": 12, "Сечение кабеля": "10 мм²"},
        additional={"Заглубление м": 1.4, "Снег район": "II"},
        specification_items=[
            {
                "name": "Насос погружной канализационный",
                "type": "KAIQUAN 65WQS215-7.5",
                "doc": "ГОСТ 6134-2007",
                "okpd": "28.13.14.140",
                "supplier": "ARKADA Сочи",
                "quantity": 2,
                "units": "шт",
                "mass_kg": 65,
                "note": "1 рабочий + 1 резерв",
            },
            {
                "name": "Корпус КНС стеклопластиковый",
                "type": "BloPlast PV-1500/3000",
                "doc": "ТУ 22.21.21-001-2024",
                "okpd": "22.21.21.000",
                "supplier": "BloPlast",
                "quantity": 1,
                "units": "шт",
                "mass_kg": 850,
            },
        ],
        references=[
            {
                "regulation_code": "СП 32.13330.2018",
                "section": "§6",
                "purpose": "Канализация наружная",
            },
            {
                "regulation_code": "ГОСТ Р 21.101-2020",
                "section": "общ.",
                "purpose": "Состав РД (СПДС)",
            },
        ],
    )
    pdf = generate_rpz_gost_pdf(inputs)
    assert isinstance(pdf, bytes)
    # Полный документ — несколько страниц
    assert len(pdf) > 5000
    assert pdf[:4] == b"%PDF"


def test_rpz_gost_no_specification_no_error():
    """Отсутствие спецификации не должно ломать генерацию."""
    inputs = RPZGostInput(project_name="Без BOM", specification_items=[])
    pdf = generate_rpz_gost_pdf(inputs)
    assert pdf[:4] == b"%PDF"


def test_rpz_gost_no_references_no_error():
    """Отсутствие нормативов не должно ломать генерацию."""
    inputs = RPZGostInput(project_name="Без нормативов", references=[])
    pdf = generate_rpz_gost_pdf(inputs)
    assert pdf[:4] == b"%PDF"


def test_rpz_input_default_stage():
    """Стадия по умолчанию = 'Р' (рабочий проект)."""
    inputs = RPZGostInput(project_name="Test")
    assert inputs.stage == "Р"
    assert inputs.revision == "0"
    assert inputs.designer_organization.startswith("INSERVO")
