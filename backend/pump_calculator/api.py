"""FastAPI app: REST endpoints для калькулятора подбора насосов."""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from pump_calculator import __version__, catalog
from pump_calculator.matching import select_pumps as run_selection
from pump_calculator.schemas import L0Input, SelectionRequest, SelectionResult

# pump_calculator.handoff (reportlab + python-docx + lxml) импортируется лениво
# внутри handoff-эндпоинтов — это уменьшает cold-start lambda на ~50 МБ.

app = FastAPI(
    title="kns-calculator API",
    description=(
        "Открытый калькулятор первичного подбора насосов для КНС / НС / СПД. "
        "Менеджер вводит 4 поля (Q, dH, L, тип стоков) — получает топ-3 насоса в трёх ценовых сегментах. "
        "MIT, see https://github.com/jhdjam-spec/kns-calculator"
    ),
    version=__version__,
)

# Permissive CORS for the open-source MVP. Tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "kns-calculator",
        "version": __version__,
        "docs": "/docs",
        "repo": "https://github.com/jhdjam-spec/kns-calculator",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Простой health check + проверка что dataset подгружается."""
    pumps = catalog.load_pumps()
    coeffs = catalog.load_coefficients()
    return {
        "status": "ok",
        "version": __version__,
        "pumps_in_db": len(pumps),
        "coefficients_loaded": len(coeffs),
    }


@app.post("/select", response_model=SelectionResult, tags=["selection"])
def select(req: SelectionRequest) -> SelectionResult:
    """Главный endpoint: 7-шаговый алгоритм подбора насоса.

    Принимает L0 (4 поля обязательно) + L1 (опционально).
    Возвращает топ-1 в каждом из {budget, mid, premium} + флаги hand-off.
    """
    try:
        return run_selection(req.L0, req.L1)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Selection failed: {e}") from e


@app.post("/select/quick", response_model=SelectionResult, tags=["selection"])
def select_quick(L0: L0Input) -> SelectionResult:
    """Упрощённый endpoint: только L0, без L1. Для быстрых L0-вызовов с фронта."""
    return run_selection(L0, None)


@app.get("/pumps", tags=["catalog"])
def list_pumps() -> dict:
    """Полный каталог насосов в БД."""
    pumps = catalog.load_pumps()
    return {"total": len(pumps), "pumps": pumps}


@app.get("/pumps/{pump_id}", tags=["catalog"])
def get_pump(pump_id: str) -> dict:
    pumps = catalog.load_pumps()
    for p in pumps:
        if p["id"] == pump_id:
            return p
    raise HTTPException(status_code=404, detail=f"Pump '{pump_id}' not found")


@app.get("/producers", tags=["catalog"])
def list_producers() -> list:
    return catalog.load_producers()


@app.get("/coefficients", tags=["catalog"])
def list_coefficients() -> dict:
    """Все коэффициенты, формулы и таблицы из 02_dataset/theory/coefficients.json."""
    return catalog.load_coefficients()


# ---------------------- Phase 4 hand-off PDF ----------------------


class QuestionnaireRequest(BaseModel):
    """Запрос на генерацию PDF опросного листа клиенту."""

    selection: SelectionResult
    object_name: str = Field("", description="Название объекта (опционально)")
    client_company: str = Field("", description="Заказчик (компания)")
    client_contact: str = Field("", description="Контакт")
    city: str = Field("", description="Город / регион")
    kp_number: str = Field("", description="№ КП / запроса")


@app.post("/handoff/questionnaire", tags=["handoff"], response_class=Response)
def handoff_questionnaire(req: QuestionnaireRequest) -> Response:
    """Генерация PDF опросного листа клиенту (Артефакт 1)."""
    from pump_calculator.handoff import generate_questionnaire_pdf

    try:
        pdf_bytes = generate_questionnaire_pdf(
            req.selection,
            object_name=req.object_name,
            client_company=req.client_company,
            client_contact=req.client_contact,
            city=req.city,
            kp_number=req.kp_number,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="kns_questionnaire.pdf"'},
    )


@app.post("/handoff/bom", tags=["handoff"], response_class=Response)
def handoff_bom(selection: SelectionResult) -> Response:
    """Генерация PDF BOM-черновика (Артефакт 2). 3 ценовых сегмента."""
    from pump_calculator.handoff import generate_bom_pdf

    try:
        pdf_bytes = generate_bom_pdf(selection)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="kns_bom_draft.pdf"'},
    )


# ---------------------- Phase 12: DOCX опросник + парсер ----------------------


@app.post("/handoff/questionnaire-docx", tags=["handoff"], response_class=Response)
def handoff_questionnaire_docx(req: QuestionnaireRequest) -> Response:
    """Генерация DOCX опросного листа клиенту (для редактирования и парсинга обратно).

    DOCX формат предпочтительнее PDF для случаев, когда клиент будет заполнять
    форму на компьютере и возвращать заполненный файл — мы автоматически
    извлечём параметры через POST /select/from-file.
    """
    from pump_calculator.handoff import generate_questionnaire_docx

    try:
        docx_bytes = generate_questionnaire_docx(
            req.selection,
            object_name=req.object_name,
            client_company=req.client_company,
            client_contact=req.client_contact,
            city=req.city,
            kp_number=req.kp_number,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {e}") from e

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="kns_questionnaire.docx"'},
    )


@app.post("/handoff/empty-questionnaire-docx", tags=["handoff"], response_class=Response)
def handoff_empty_questionnaire_docx() -> Response:
    """Пустой DOCX опросник — для клиента, который заполняет с нуля без предзаполнения."""
    from pump_calculator.handoff import generate_questionnaire_docx

    try:
        docx_bytes = generate_questionnaire_docx()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {e}") from e

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="kns_questionnaire_empty.docx"'},
    )


class FromFileResponse(BaseModel):
    """Ответ /select/from-file: что извлекли + результат подбора (если хватило данных)."""

    extracted_codes: dict[str, str] = Field(
        default_factory=dict,
        description="Все извлечённые из опросника коды и значения (для отладки)",
    )
    L0: L0Input | None = None
    L1_provided: bool = Field(False, description="Извлечены ли опциональные L1-поля")
    metadata: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    selection: SelectionResult | None = Field(
        None,
        description="Результат подбора. None если Q не извлечён (требуется ручной ввод).",
    )


@app.post("/select/from-file", response_model=FromFileResponse, tags=["selection"])
async def select_from_file(file: UploadFile = File(...)) -> FromFileResponse:  # noqa: B008  (идиома FastAPI)
    """Принять заполненный DOCX-опросник, извлечь параметры и сделать подбор.

    Поддерживаемые форматы:
    - DOCX (нашего шаблона, сгенерированного через /handoff/questionnaire-docx)

    Возвращает ExtractedQuiz + SelectionResult в одном payload. Если Q не
    извлечён, вернётся `selection=null` и `missing_fields=["Q_M3H"]` —
    фронт должен показать форму для ручного ввода недостающих полей.
    """
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Поддерживается только DOCX. Для PDF/XLSX/scan см. roadmap Phase 12.2-12.3.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Файл пустой")

    from pump_calculator.handoff import parse_questionnaire_docx

    try:
        parsed = parse_questionnaire_docx(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось распарсить DOCX: {e}",
        ) from e

    selection: SelectionResult | None = None
    if parsed.L0 is not None:
        try:
            selection = run_selection(parsed.L0, parsed.L1)
        except Exception as e:  # pragma: no cover
            raise HTTPException(
                status_code=500, detail=f"Selection failed: {e}",
            ) from e

    return FromFileResponse(
        extracted_codes=parsed.raw_codes,
        L0=parsed.L0,
        L1_provided=parsed.L1 is not None,
        metadata=parsed.metadata,
        missing_fields=parsed.missing_fields,
        warnings=parsed.warnings,
        selection=selection,
    )


# ──────────────────────────────────────────────────────────────────────────
# Phase 19: Storm calculator endpoints
# ──────────────────────────────────────────────────────────────────────────


@app.post("/storm/calc", tags=["storm"])
def calculate_storm(payload: dict) -> dict:
    """Полный расчёт ливневой канализации по СП 32.

    Принимает StormInput (см. pump_calculator.storm.models) и возвращает
    StormResult с пиковым расходом, годовыми объёмами, рекомендациями по ЛОС.

    Используется как Минимальным режимом (frontend/storm/minimal), так и
    Классическим (Phase 20).
    """
    from pump_calculator.storm import calculate_full_storm
    from pump_calculator.storm.models import StormInput

    try:
        inputs = StormInput(**payload)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Некорректный input: {e}",
        ) from e

    try:
        result = calculate_full_storm(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"Storm calculation failed: {e}",
        ) from e

    # Подпись авторства INSERVO в каждом ответе (Слой 2 ADR-002)
    response = result.model_dump()
    response["_signature"] = {
        "studio": "INSERVO Studio · Студия интеграции умных решений Константина Морозова",
        "author": "Konstantin Morozov",
        "url": "https://inservo.ru",
        "license": "MIT",
        "watermark": "K.M. © 2026",
    }
    return response


@app.get("/storm/cities", tags=["storm"])
def list_storm_cities() -> dict:
    """Список 36 городов из climate БД для UI-автокомплита."""
    from pump_calculator.storm.regions import list_cities

    return {"cities": list_cities()}


@app.get("/storm/presets", tags=["storm"])
def list_storm_presets() -> dict:
    """Не реализовано — пресеты типов объектов хранятся на frontend
    (frontend/src/data/objectTypePresets.json). Этот эндпоинт зарезервирован
    под backend-валидацию пресетов в Phase 20.
    """
    return {
        "note": "Presets are stored on frontend. See frontend/src/data/objectTypePresets.json",
        "phase": "Phase 19 MVP",
    }


# ──────────────────────────────────────────────────────────────────────────
# Phase 22: Fire water (СП 8.13130 / СП 10.13130)
# ──────────────────────────────────────────────────────────────────────────


@app.post("/fire-water/sprinklers", tags=["fire_water"])
def calc_sprinklers_endpoint(payload: dict) -> dict:
    """Расчёт автоматических спринклерных установок по СП 485.1311500.2020.

    Требует:
    - group: одна из ["1", "2", "3", "4.1", "4.2", "5", "6", "7"]
    - coverage_area_m2 (опционально): реальная площадь защищаемого помещения
    """
    from pump_calculator.fire_water import calc_sprinkler_demand
    try:
        result = calc_sprinkler_demand(
            group=payload["group"],
            coverage_area_m2=payload.get("coverage_area_m2"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "group": result.group,
        "group_title": result.group_title,
        "q_total_lps": result.q_total_lps,
        "q_total_m3h": result.q_total_m3h,
        "area_m2": result.area_m2,
        "duration_min": result.duration_min,
        "n_sprinklers_min": result.n_sprinklers_min,
        "min_pressure_m": result.min_pressure_m,
        "water_volume_m3": result.water_volume_m3,
        "notes": result.notes,
        "references": result.references,
    }


@app.get("/fire-water/sprinkler-groups", tags=["fire_water"])
def list_sprinkler_groups_endpoint() -> dict:
    """Каталог 8 групп помещений по СП 485 для UI."""
    from pump_calculator.fire_water import list_sprinkler_groups
    return {"groups": list_sprinkler_groups()}


@app.post("/fire-water/calc", tags=["fire_water"])
def calculate_fire_water(payload: dict) -> dict:
    """Расчёт противопожарного водоснабжения по СП 8.13130 + СП 10.13130.

    Принимает FireScenarioInput (см. pump_calculator.fire_water.models),
    возвращает FireResult с расходами, резервуаром, насосной и ссылками
    на нормативы.
    """
    from pump_calculator.fire_water import (
        FireScenarioInput,
        calculate_fire_scenario,
    )

    try:
        inputs = FireScenarioInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e

    H_design = float(payload.get("H_design_m", 60.0))

    try:
        result = calculate_fire_scenario(inputs, H_design_m=H_design)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"Fire water calculation failed: {e}",
        ) from e

    response = result.model_dump()
    # Конвертируем dataclass-ссылки в dict
    response["references"] = [
        {
            "code": r.regulation_code,
            "section": r.section,
            "purpose": r.purpose,
            "url": r.url,
        }
        for r in result.references
    ]
    response["_signature"] = {
        "studio": "INSERVO Studio · Студия интеграции умных решений Константина Морозова",
        "watermark": "K.M. © 2026",
    }
    return response


# ──────────────────────────────────────────────────────────────────────────
# Phase 23: Water supply (СП 30 / СП 31)
# ──────────────────────────────────────────────────────────────────────────


@app.post("/water/demand", tags=["water_supply"])
def calculate_water_demand_endpoint(payload: dict) -> dict:
    """Расчёт водопотребления по СП 30.13330.2020 + СП 31.13330.2021.

    Принимает WaterScenarioInput, возвращает WaterDemandResult с раздельными
    расходами ХВС/ГВС/полива и суммарными показателями.
    """
    from pump_calculator.water_supply import (
        WaterScenarioInput,
        calc_water_demand,
        sizing_water_station,
    )

    try:
        inputs = WaterScenarioInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e

    try:
        demand = calc_water_demand(inputs)
        station = sizing_water_station(inputs, demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"Water calculation failed: {e}",
        ) from e

    response = {
        "demand": demand.model_dump(),
        "station": station.model_dump(),
        "_signature": {
            "studio": "INSERVO Studio",
            "watermark": "K.M. © 2026",
        },
    }
    return response


@app.get("/water/norms", tags=["water_supply"])
def list_water_norms() -> dict:
    """Список норм потребления по типам зданий (СП 30 прил. А)."""
    from pump_calculator.water_supply.demand import NORMS_LITERS_PER_DAY

    return {
        "count": len(NORMS_LITERS_PER_DAY),
        "norms": NORMS_LITERS_PER_DAY,
        "source": "СП 30.13330.2020 прил. А.2 + прил. Б",
    }


# ──────────────────────────────────────────────────────────────────────────
# Регистр нормативов (для UI-энциклопедии)
# ──────────────────────────────────────────────────────────────────────────


@app.get("/regulations", tags=["regulations"])
def list_regulations(category: str | None = None) -> dict:
    """Список действующих нормативов (СП/ГОСТ/ТР ТС/ФЗ), на которых
    базируется калькулятор.

    Используется UI-энциклопедией для отображения «нормативной карты».
    """
    from pump_calculator.regulations import (
        ALL_REGULATIONS,
        list_regulations_by_category,
    )

    if category:
        regs = list_regulations_by_category(category)
    else:
        regs = list(ALL_REGULATIONS.values())

    return {
        "count": len(regs),
        "category_filter": category,
        "regulations": [
            {
                "code": r.code,
                "title": r.title,
                "edition": r.edition,
                "in_force_from": r.in_force_from,
                "superseded_by": r.superseded_by,
                "url_official": r.url_official,
                "scope": r.scope,
                "category": r.category,
            }
            for r in regs
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# Phase 21+22: Physics advanced (NPSH, hydroshock, Darcy)
# ──────────────────────────────────────────────────────────────────────────


@app.post("/physics/npsh", tags=["physics"])
def calc_npsh_endpoint(payload: dict) -> dict:
    """NPSHa с поправкой на высоту над уровнем моря и широту.

    Используется для критичных объектов: горные регионы (Архыз, Кавказ),
    нестандартные температуры жидкости.
    """
    from pump_calculator.physics_advanced import npsha_with_corrections
    try:
        npsha, refs = npsha_with_corrections(
            H_suction_m=payload["H_suction_m"],
            T_celsius=payload.get("T_celsius", 20.0),
            H_friction_suction_m=payload.get("H_friction_suction_m", 0.0),
            altitude_m=payload.get("altitude_m", 0.0),
            latitude_deg=payload.get("latitude_deg", 55.0),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "npsha_m": npsha,
        "encyclopedia_topic": "hydraulics",
        "encyclopedia_anchor": "NPSH",
        "references": [
            {
                "regulation_code": r.regulation_code,
                "section": r.section,
                "purpose": r.purpose,
                "url": r.url,
            }
            for r in refs
        ],
    }


@app.post("/physics/water-hammer", tags=["physics"])
def calc_water_hammer_endpoint(payload: dict) -> dict:
    """Гидроудар по Жуковскому-Михайлову с учётом материала трубы."""
    from pump_calculator.physics_advanced import water_hammer
    try:
        result = water_hammer(
            v_ms=payload["v_ms"],
            pipe_material=payload.get("pipe_material", "pe100_sdr17"),
            pipe_length_m=payload.get("pipe_length_m", 100.0),
            closure_time_s=payload.get("closure_time_s", 5.0),
            T_celsius=payload.get("T_celsius", 15.0),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "delta_p_kpa": result.delta_p_kpa,
        "delta_h_m": result.delta_h_m,
        "wave_celerity_mps": result.wave_celerity_mps,
        "is_direct": result.is_direct,
        "pressure_class_required": result.pressure_class_required,
        "encyclopedia_topic": "hydraulics",
        "encyclopedia_anchor": "Гидроудар",
        "references": [
            {
                "regulation_code": r.regulation_code,
                "section": r.section,
                "purpose": r.purpose,
                "url": r.url,
            }
            for r in result.references
        ],
    }


@app.post("/physics/darcy-weisbach", tags=["physics"])
def calc_darcy_weisbach_endpoint(payload: dict) -> dict:
    """Потери напора Дарси-Вейсбаха с λ Swamee-Jain."""
    from pump_calculator.physics_advanced import darcy_weisbach_head_loss_m
    try:
        h_f, details = darcy_weisbach_head_loss_m(
            L_m=payload["L_m"],
            D_mm=payload["D_mm"],
            v_ms=payload["v_ms"],
            pipe_material=payload.get("pipe_material", "pe100"),
            T_celsius=payload.get("T_celsius", 15.0),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"h_f_m": h_f, **details}


# ──────────────────────────────────────────────────────────────────────────
# Phase 31: Encyclopedia (drawer + /teach)
# ──────────────────────────────────────────────────────────────────────────


@app.get("/encyclopedia/topics", tags=["encyclopedia"])
def list_encyclopedia_topics() -> dict:
    """Список всех тем энциклопедии для главной /teach."""
    from pump_calculator.encyclopedia import list_topics
    return {"topics": list_topics()}


@app.get("/encyclopedia/topic/{topic_key}", tags=["encyclopedia"])
def get_encyclopedia_topic(topic_key: str) -> dict:
    """Полная статья по теме (markdown + интерактивные примеры)."""
    from pump_calculator.encyclopedia import get_topic_full
    result = get_topic_full(topic_key)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Topic not found: {topic_key}")
    return result


@app.get("/encyclopedia/section/{topic_key}", tags=["encyclopedia"])
def get_encyclopedia_section(topic_key: str, anchor: str) -> dict:
    """Фрагмент статьи по якорю заголовка (для drill-down drawer)."""
    from pump_calculator.encyclopedia import get_topic_section
    result = get_topic_section(topic_key, anchor)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section not found: topic={topic_key}, anchor={anchor}",
        )
    return result


@app.get("/encyclopedia/examples", tags=["encyclopedia"])
def list_encyclopedia_examples() -> dict:
    """Эталонные примеры для запуска из энциклопедии."""
    from pump_calculator.encyclopedia import EXAMPLES_REGISTRY
    return {
        "examples": [
            {
                "id": e.id,
                "title": e.title,
                "topic": e.topic,
                "description": e.description,
                "api_endpoint": e.api_endpoint,
                "payload": e.payload,
                "expected_outcome": e.expected_outcome,
            }
            for e in EXAMPLES_REGISTRY
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# Phase 32: Project (главный flow — единый визард)
# ──────────────────────────────────────────────────────────────────────────


@app.get("/project/presets", tags=["project"])
def list_project_presets() -> dict:
    """13 типовых пресетов проекта (ИЖС, ЖК, АЗС, ТРЦ и т.п.)."""
    from pump_calculator.project import list_presets
    return {"presets": list_presets()}


@app.post("/project/calculate", tags=["project"])
def calculate_project_endpoint(payload: dict) -> dict:
    """Главный оркестратор: запускает все подсистемы по проекту.

    Возвращает ProjectResult со всеми расчётами + сводную BOM + ссылки на нормативы.
    Это сердце калькулятора — пользователь вводит 5-7 полей раз и получает
    готовое решение проектировщика.
    """
    from pump_calculator.project import ProjectInput, calculate_project
    try:
        inputs = ProjectInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return calculate_project(inputs).model_dump()


# ──────────────────────────────────────────────────────────────────────────
# Phase 25-30: Climate, Structural, LOS, Reports, Complexes, BOM
# ──────────────────────────────────────────────────────────────────────────


@app.post("/climate/burial-depth", tags=["climate"])
def calc_burial_depth_endpoint(payload: dict) -> dict:
    """Глубина заложения трубопровода по СП 32 + СП 131."""
    from pump_calculator.climate import calc_pipe_burial_depth
    try:
        result = calc_pipe_burial_depth(
            region_city=payload["region_city"],
            soil_type=payload.get("soil_type", "clay_loam"),
            pipe_dn_mm=payload.get("pipe_dn_mm", 200),
            has_groundwater=payload.get("has_groundwater", False),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result.model_dump()


@app.post("/climate/loads", tags=["climate"])
def calc_climate_loads_endpoint(payload: dict) -> dict:
    """Снеговая, ветровая и сейсмическая нагрузки по СП 20 + СП 14."""
    from pump_calculator.climate.loads import (
        calc_seismic_load,
        calc_snow_load_pavilion,
        calc_wind_load_pavilion,
    )
    city = payload.get("region_city", "Москва")
    area = payload.get("pavilion_area_m2", 0.0)
    height = payload.get("pavilion_height_m", 3.0)
    facade = payload.get("pavilion_facade_area_m2", height * 4)

    s, s_total, s_region, s_notes = calc_snow_load_pavilion(city, area)
    w, w_total, w_region, w_notes = calc_wind_load_pavilion(city, height, facade)
    K, F_seism, seism_notes = calc_seismic_load(
        payload.get("seismic_intensity_balls", 6),
        payload.get("object_mass_kg", 5000),
    )
    return {
        "snow": {"load_kn_m2": s, "total_kn": s_total, "region": s_region, "notes": s_notes},
        "wind": {"load_pa": w, "total_kn": w_total, "region": w_region, "notes": w_notes},
        "seismic": {"K": K, "F_kn": F_seism, "notes": seism_notes},
    }


@app.post("/structural/ballast", tags=["structural"])
def calc_ballast_endpoint(payload: dict) -> dict:
    """Расчёт пригруза корпуса бетоном при УГВ (СП 32 §6.3)."""
    from pump_calculator.structural import StructuralScenarioInput, calc_ballast_concrete
    try:
        inputs = StructuralScenarioInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return calc_ballast_concrete(inputs).model_dump()


@app.post("/structural/wall-thickness", tags=["structural"])
def calc_wall_thickness_endpoint(payload: dict) -> dict:
    """Минимальная толщина стенки полимерного корпуса по ISO 9969 SN."""
    from pump_calculator.structural import StructuralScenarioInput, calc_polymer_wall_thickness
    try:
        inputs = StructuralScenarioInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return calc_polymer_wall_thickness(inputs).model_dump()


@app.post("/structural/ladder", tags=["structural"])
def calc_ladder_endpoint(payload: dict) -> dict:
    """Расчёт лестницы внутри корпуса (СП 12-104)."""
    from pump_calculator.structural import calc_ladder_geometry
    return calc_ladder_geometry(
        height_m=payload["height_m"],
        pit_diameter_m=payload["pit_diameter_m"],
        is_corrosive_environment=payload.get("is_corrosive_environment", True),
    ).model_dump()


@app.post("/los/select", tags=["los"])
def calc_los_select_endpoint(payload: dict) -> dict:
    """Подбор ЛОС-блока по типу стоков и точке сброса."""
    from pump_calculator.los import LOSScenarioInput, select_los_block
    try:
        inputs = LOSScenarioInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return select_los_block(inputs).model_dump()


@app.get("/los/catalog", tags=["los"])
def list_los_catalog() -> dict:
    """Каталог ЛОС-блоков (PEGAS, ТОПАС, БиоПроект, КИТ, ГЕОН и др.)."""
    from pump_calculator.los import LOS_CATALOG
    return {
        "count": len(LOS_CATALOG),
        "blocks": [b.model_dump() for b in LOS_CATALOG],
    }


@app.post("/reports/calculation-pdf", tags=["reports"], response_class=Response)
def calc_report_pdf_endpoint(payload: dict) -> Response:
    """Генерация PDF расчётной записки на основе результатов всех модулей."""
    from pump_calculator.reports import (
        CalculationReportInput,
        generate_calculation_report_pdf,
    )
    try:
        inputs = CalculationReportInput(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    pdf_bytes = generate_calculation_report_pdf(inputs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Расчётная_записка_{inputs.project_code or "kns"}.pdf"',
        },
    )


@app.post("/complex/summary", tags=["complexes"])
def calc_complex_summary_endpoint(payload: dict) -> dict:
    """Сводная BOM по многообъектному комплексу (РЭУ → площадка → объект)."""
    from pump_calculator.complexes import Complex, build_complex_bom_summary
    try:
        complex_obj = Complex(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return build_complex_bom_summary(complex_obj).model_dump()


@app.post("/bom/export-csv", tags=["bom"], response_class=Response)
def export_bom_csv_endpoint(payload: dict) -> Response:
    """Экспорт BOM в CSV (для импорта в Excel/ГРАНД-Смету)."""
    from pump_calculator.bom import BOMSpecification, export_bom_csv
    try:
        spec = BOMSpecification(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    csv_text = export_bom_csv(spec)
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="BOM_{spec.project_code or "kns"}.csv"',
        },
    )


@app.get("/regulations/{code}", tags=["regulations"])
def get_regulation_by_code(code: str) -> dict:
    """Получить норматив по коду (например 'SP_32' или 'СП 32.13330.2018')."""
    from pump_calculator.regulations import get_regulation

    reg = get_regulation(code)
    if reg is None:
        raise HTTPException(status_code=404, detail=f"Regulation not found: {code}")
    return {
        "code": reg.code,
        "title": reg.title,
        "edition": reg.edition,
        "in_force_from": reg.in_force_from,
        "superseded_by": reg.superseded_by,
        "url_official": reg.url_official,
        "scope": reg.scope,
        "category": reg.category,
    }
