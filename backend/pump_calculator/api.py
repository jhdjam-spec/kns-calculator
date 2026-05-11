"""FastAPI app: REST endpoints для калькулятора подбора насосов."""

from __future__ import annotations

import logging
import os
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from pump_calculator import __version__, catalog
from pump_calculator.matching import select_pumps as run_selection
from pump_calculator.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    L0Input,
    SelectionRequest,
    SelectionResult,
)

logger = logging.getLogger(__name__)

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

# CORS: prod — список разрешённых origin'ов через ENV `CORS_ALLOWED_ORIGINS`
# (запятая-разделённый). Dev/MVP по умолчанию ["*"]. См. PRR audit 2026-05-10.
_cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "*").strip()
if _cors_env == "*":
    _cors_origins = ["*"]
else:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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
    """Health check + dataset integrity. 503 если pumps.json не загружен."""
    pumps = catalog.load_pumps()
    coeffs = catalog.load_coefficients()
    if not pumps:
        # safe-empty из catalog.load_pumps() — pumps.json повреждён или отсутствует
        raise HTTPException(503, "pumps dataset unavailable")
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="kns_bom_draft.pdf"'},
    )


@app.post("/handoff/rpz-gost", tags=["handoff"], response_class=Response)
def handoff_rpz_gost(req: SelectionRequest) -> Response:
    """РПЗ по ГОСТ Р 21.101-2020 (13 разделов) — full pipeline endpoint.

    Принимает SelectionRequest (L0+L1), внутри запускает compute_hydraulics
    + select_pumps + build_rpz_gost_pdf и возвращает готовый PDF.

    В отличие от /reports/rpz-gost-pdf (который принимает уже собранный
    RPZGostInput), этот endpoint всё считает сам — удобно для KP-сценария
    «1 клик от опросника до РПЗ».
    """
    from pump_calculator.hydraulics import compute_hydraulics
    from pump_calculator.matching import select_pumps
    from pump_calculator.reports import build_rpz_gost_pdf

    try:
        computed = compute_hydraulics(req.L0, req.L1)
        result = select_pumps(req.L0, req.L1)
        pdf_bytes = build_rpz_gost_pdf(req.L0, req.L1, computed, result)
    except Exception as e:  # pragma: no cover
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(
            status_code=500, detail=f"РПЗ generation failed: {e}"
        ) from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="kns_rpz_gost.pdf"',
        },
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось распарсить DOCX: {e}",
        ) from e

    selection: SelectionResult | None = None
    if parsed.L0 is not None:
        try:
            selection = run_selection(parsed.L0, parsed.L1)
        except Exception as e:  # pragma: no cover
            logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(
            status_code=400,
            detail=f"Некорректный input: {e}",
        ) from e

    try:
        result = calculate_full_storm(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e

    H_design = float(payload.get("H_design_m", 60.0))

    try:
        result = calculate_fire_scenario(inputs, H_design_m=H_design)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e

    try:
        demand = calc_water_demand(inputs)
        station = sizing_water_station(inputs, demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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


@app.get("/climate/cities", tags=["climate"])
def list_climate_cities() -> dict:
    """Список городов из climate_cities_2026.json (для autocomplete во фронте).

    Возвращает {cities: [{city, region, climate_zone, altitude_m, frost_depth_mm, t_min_5pct_c, lat, lon}]}.
    Phase 28 Climate Simulator. Источник СП 131.13330.2020.
    """
    from pump_calculator.climate_simulator import list_cities
    cities = list_cities()
    return {"cities": cities, "count": len(cities)}


@app.get("/climate/{city}", tags=["climate"])
def get_climate_for_city(city: str) -> dict:
    """Полная карточка климата + рекомендации по городу.

    Возвращает {climate: {...}, recommendations: [...]}.
    Если города нет в БД — 404. Phase 28 Climate Simulator.
    """
    from pump_calculator.climate_simulator import (
        _build_recommendations,
        get_city_climate,
    )
    climate = get_city_climate(city)
    if climate is None:
        raise HTTPException(404, f"Город '{city}' не найден в БД climate_cities_2026.json")
    recs = _build_recommendations(climate)
    return {"climate": climate, "recommendations": recs}


@app.post("/structural/ballast", tags=["structural"])
def calc_ballast_endpoint(payload: dict) -> dict:
    """Расчёт пригруза корпуса бетоном при УГВ (СП 32 §6.3)."""
    from pump_calculator.structural import StructuralScenarioInput, calc_ballast_concrete
    try:
        inputs = StructuralScenarioInput(**payload)
    except Exception as e:
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return calc_ballast_concrete(inputs).model_dump()


@app.post("/structural/wall-thickness", tags=["structural"])
def calc_wall_thickness_endpoint(payload: dict) -> dict:
    """Минимальная толщина стенки полимерного корпуса по ISO 9969 SN."""
    from pump_calculator.structural import StructuralScenarioInput, calc_polymer_wall_thickness
    try:
        inputs = StructuralScenarioInput(**payload)
    except Exception as e:
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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


@app.post("/reports/rpz-gost-pdf", tags=["reports"], response_class=Response)
def generate_rpz_gost_endpoint(payload: dict) -> Response:
    """Расчётно-пояснительная записка (РПЗ) по ГОСТ Р 21.101-2020.

    13-разделовая каноническая структура для защиты проекта в
    гос/негосэкспертизе (ст. 49 ГрК РФ).
    Спецификация — по форме 7 ГОСТ 21.110-2013 (8 колонок).
    """
    from pump_calculator.reports import RPZGostInput, generate_rpz_gost_pdf
    try:
        inputs = RPZGostInput(**payload)
    except Exception as e:
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    pdf_bytes = generate_rpz_gost_pdf(inputs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="РПЗ_{inputs.project_code or "kns"}.pdf"'
            ),
        },
    )


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
        logger.exception("unhandled error: %s", e.__class__.__name__)
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
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    return build_complex_bom_summary(complex_obj).model_dump()


@app.post("/bom/export-csv", tags=["bom"], response_class=Response)
def export_bom_csv_endpoint(payload: dict) -> Response:
    """Экспорт BOM в CSV (для импорта в Excel/ГРАНД-Смету)."""
    from pump_calculator.bom import BOMSpecification, export_bom_csv
    try:
        spec = BOMSpecification(**payload)
    except Exception as e:
        logger.exception("unhandled error: %s", e.__class__.__name__)
        raise HTTPException(status_code=400, detail=f"Некорректный input: {e}") from e
    csv_text = export_bom_csv(spec)
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="BOM_{spec.project_code or "kns"}.csv"',
        },
    )


# ──────────────────────────────────────────────────────────────────────────
# P5 mail integration: CRM-light классификатор входящих
# ──────────────────────────────────────────────────────────────────────────


# Список доверенных доменов (часть из 511 в learned_profile.json).
# Только реально проверенные на массиве zakaz@inservo.ru.
# При необходимости можно вынести в JSON-файл и подгружать лениво.
_TRUSTED_DOMAINS: frozenset[str] = frozenset(
    {
        "inservo.ru",
        "servo-yug.ru",
        "servopolimer.ru",
        "mail.ru",
        "yandex.ru",
        "ya.ru",
        "gmail.com",
        "rambler.ru",
        "list.ru",
        "bk.ru",
        "inbox.ru",
        "rosatom.ru",
        "gazprom.ru",
        "rosneft.ru",
        "lukoil.com",
        "tatneft.ru",
        "kaztransgas.kz",
    }
)


@app.post("/etl/classify", response_model=ClassifyResponse, tags=["etl"])
def classify_incoming(req: ClassifyRequest) -> ClassifyResponse:
    """Классификация входящего письма (CRM-light, P5 mail integration).

    Возвращает тип запроса (ОЛ/КП/ТЗ), объект (КНС/ЛОС/ВНС), производителя
    (если упомянут), список извлечённых шифров проектов и флаг доверия
    к домену отправителя.

    Без БД, без auth — чистая функция над текстом. См.
    `pump_calculator.etl.incoming_classifier` для деталей паттернов.
    """
    from pump_calculator.etl.incoming_classifier import (
        classify_subject_marker,
        extract_project_codes,
        is_trusted_sender,
    )

    # 400 если все три поля пустые/только whitespace
    if not (req.subject.strip() or req.body.strip() or req.from_email.strip()):
        raise HTTPException(
            status_code=400,
            detail="Все поля пусты — нечего классифицировать",
        )

    markers = classify_subject_marker(req.subject)

    # Если в subject не нашли — пробуем body (только тип/объект/производитель).
    # Шифры всегда ищем в combined-тексте (subject + body).
    if markers["type"] is None or markers["object"] is None or markers["manufacturer"] is None:
        body_markers = classify_subject_marker(req.body)
        for key in ("type", "object", "manufacturer"):
            if markers[key] is None and body_markers[key] is not None:
                markers[key] = body_markers[key]

    combined_text = f"{req.subject}\n{req.body}".strip()
    project_codes = extract_project_codes(combined_text) if combined_text else []

    trusted = is_trusted_sender(req.from_email, set(_TRUSTED_DOMAINS)) if req.from_email else False

    return ClassifyResponse(
        type=markers["type"],
        object=markers["object"],
        manufacturer=markers["manufacturer"],
        project_codes=project_codes,
        is_trusted_sender=trusted,
    )


# ---------------------- /import/parse — TZ Import (Phase 33) ----------------------


class ImportParseRequest(BaseModel):
    """Запрос на парсинг произвольного ТЗ → pre-fill L0/L1 для Wizard.

    Body может быть plain-текстом из textarea (вставка ТЗ/опросного листа)
    или будущим content-type (DOCX/PDF — пока вне scope MVP).
    """

    text: str = Field("", description="Текст ТЗ или опросного листа")
    format: Literal["plain", "questionnaire"] | None = Field(
        "plain",
        description="Подсказка о формате. Пока ни на что не влияет — задел.",
    )
    original_filename: str | None = Field(
        None,
        description="Оригинальное имя файла (если ТЗ пришло из file-upload). "
        "Используется в имени архивной копии на Я.Диске.",
    )


@app.post("/import/parse", tags=["etl"])
def import_parse_tz(req: ImportParseRequest) -> dict:
    """Извлечь из ТЗ Q/H/город/тип стоков/шифр и сопутствующие L1-параметры.

    Менеджер вставляет ТЗ в /import — backend возвращает поля, которые
    фронт мапит на L0/L1 wizard через URL-параметры (`/project?preset=auto`).

    Без auth, без БД — чистая функция над текстом. Извлекаются:
    - Q (м³/ч), H (м), город, тип стоков
    - шифр проекта (включая список всех найденных)
    - объект (КНС/ЛОС/ВНС), производитель
    - Ex_required, reliability (I/II/III), liquid_temp_c
    - confidence — доля 4 ключевых полей (Q, H, city, wastewater_type)

    После парсинга оригинал ТЗ копируется в архив Серво-Юг на Яндекс.Диск
    (`/inservo_tz_archive/<date>/...`) — graceful если токен не задан.

    См. `pump_calculator.etl.tz_parser` для деталей паттернов.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Поле text пустое — нечего парсить",
        )
    from pump_calculator.etl.dataset_enrichment import (  # noqa: PLC0415
        QUEUE_THRESHOLD,
        enrich_from_parse,
    )
    from pump_calculator.etl.s3_uploader import archive_tz_to_s3  # noqa: PLC0415
    from pump_calculator.etl.tz_parser import parse_tz  # noqa: PLC0415
    from pump_calculator.etl.yadisk_uploader import archive_tz_text  # noqa: PLC0415

    result = parse_tz(req.text)
    response = result.model_dump()

    # ---------- Yandex.Disk mirror (sub a4a5e58e) ------------------------
    # При отсутствии YANDEX_DISK_TOKEN возвращаем archive_path=None +
    # archive_error="...not configured" — non-blocking.
    try:
        yadisk_info = archive_tz_text(
            req.text,
            parsed=response,
            original_filename=req.original_filename,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Yandex.Disk archive crashed (non-fatal): %s", e)
        yadisk_info = {
            "archive_path": None,
            "archive_error": f"unexpected: {type(e).__name__}",
            "archive_size_bytes": 0,
        }

    # Flat keys (legacy, sub a4a5e58e): сохраняем для обратной совместимости фронта.
    response["archive_path"] = yadisk_info.get("archive_path")
    response["archive_error"] = yadisk_info.get("archive_error")
    response["archive_size_bytes"] = yadisk_info.get("archive_size_bytes", 0)

    # Nested form для нового UI / admin-обзора.
    response["yadisk_archive"] = {
        "path": yadisk_info.get("archive_path"),
        "error": yadisk_info.get("archive_error"),
        "size_bytes": yadisk_info.get("archive_size_bytes", 0),
    }

    # ---------- S3 primary archive ---------------------------------------
    # boto3 lazy import; при отсутствии AWS_ACCESS_KEY_ID — no-op.
    try:
        s3_info = archive_tz_to_s3(
            req.text,
            parsed=response,
            original_filename=req.original_filename,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("S3 archive crashed (non-fatal): %s", e)
        s3_info = {
            "bucket": None,
            "key": None,
            "parsed_key": None,
            "upload_id": None,
            "size_bytes": 0,
            "url": None,
            "configured": False,
            "error": f"unexpected: {type(e).__name__}",
        }

    response["s3_archive"] = {
        "bucket": s3_info.get("bucket"),
        "key": s3_info.get("key"),
        "parsed_key": s3_info.get("parsed_key"),
        "upload_id": s3_info.get("upload_id"),
        "size_bytes": s3_info.get("size_bytes", 0),
        "url": s3_info.get("url"),
        "configured": s3_info.get("configured", False),
        "error": s3_info.get("error"),
    }

    # ---------- Dataset enrichment pipeline -----------------------------
    confidence = float(response.get("confidence", 0.0))
    response["dataset_eligible"] = confidence >= QUEUE_THRESHOLD
    try:
        enrichment_info = enrich_from_parse(
            parsed=response,
            raw_text=req.text,
            s3_key=s3_info.get("key"),
            yadisk_path=yadisk_info.get("archive_path"),
            upload_id=s3_info.get("upload_id"),
            original_filename=req.original_filename,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Dataset enrichment crashed (non-fatal): %s", e)
        enrichment_info = {
            "status": "error",
            "confidence": confidence,
            "upload_id": s3_info.get("upload_id"),
            "record_path": None,
            "jsonl_appended": False,
            "error": f"unexpected: {type(e).__name__}",
        }

    response["dataset_enrichment"] = enrichment_info
    return response


# ---------------------- /admin/uploads — review UI (Phase 33+) ------------
# TODO: add JWT auth before public access — currently open for MVP review.


@app.get("/admin/uploads", tags=["admin"])
def admin_list_uploads(
    limit: int = 100,
    source: Literal["s3", "queue", "jsonl"] | None = None,
) -> dict:
    """Список uploaded ТЗ — для будущей review-UI.

    Источники:
    - ``source=s3`` — append-only catalog из S3 (все uploads вне зависимости от confidence)
    - ``source=queue`` — записи на ручном ревью (0.5 ≤ conf < 0.7) из ``_queue/``
    - ``source=jsonl`` — auto-accepted записи из ``etalons_uploaded.jsonl``
    - default (None) — объединение всех трёх с признаком ``source``.

    Returns
    -------
    ``{"items": [...], "count": int, "s3_configured": bool, "limit": int}``
    """
    from pump_calculator.etl.dataset_enrichment import DatasetEnricher  # noqa: PLC0415
    from pump_calculator.etl.s3_uploader import S3Uploader  # noqa: PLC0415

    items: list[dict] = []
    enricher = DatasetEnricher()
    s3 = S3Uploader.from_env()

    if source in (None, "s3"):
        try:
            for entry in s3.read_catalog(limit=limit):
                items.append({"source": "s3", **entry})
        except Exception as e:  # noqa: BLE001
            logger.warning("Cannot read S3 catalog: %s", e)
    if source in (None, "queue"):
        for entry in enricher.read_queue():
            items.append({"source": "queue", **entry})
    if source in (None, "jsonl"):
        for entry in enricher.read_uploaded():
            items.append({"source": "jsonl", **entry})

    # Сортировка по дате (новые сверху) и хвост.
    items.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
    if limit:
        items = items[:limit]

    return {
        "items": items,
        "count": len(items),
        "s3_configured": s3.is_configured,
        "limit": limit,
        "source": source,
    }


@app.get("/admin/uploads/{upload_id}", tags=["admin"])
def admin_get_upload(upload_id: str) -> dict:
    """Детальный просмотр одного upload-а.

    Ищем по ID в (queue, jsonl, S3 catalog) — возвращаем первый найденный
    + (опционально) raw_text из queue. Для S3 catalog — возвращаем
    metadata entry; raw_text загружается отдельно через
    ``/admin/uploads/{id}/raw`` (TODO).
    """
    from pump_calculator.etl.dataset_enrichment import DatasetEnricher  # noqa: PLC0415
    from pump_calculator.etl.s3_uploader import S3Uploader  # noqa: PLC0415

    enricher = DatasetEnricher()
    # 1. Queue
    queue_path = enricher.queue_dir / f"{upload_id}.json"
    if queue_path.exists():
        try:
            import json as _json  # noqa: PLC0415

            data = _json.loads(queue_path.read_text(encoding="utf-8"))
            return {"source": "queue", **data}
        except (OSError, ValueError) as e:
            raise HTTPException(500, f"queue read failed: {e}") from e
    # 2. JSONL
    for entry in enricher.read_uploaded():
        if entry.get("id") == upload_id:
            return {"source": "jsonl", **entry}
    # 3. S3 catalog
    s3 = S3Uploader.from_env()
    if s3.is_configured:
        for entry in s3.read_catalog():
            if entry.get("upload_id") == upload_id:
                return {"source": "s3", **entry}
    raise HTTPException(404, f"upload not found: {upload_id}")


@app.post("/admin/uploads/{upload_id}/approve", tags=["admin"])
def admin_approve_upload(upload_id: str) -> dict:
    """Перенести queued upload → ``etalons_uploaded.jsonl``."""
    from pump_calculator.etl.dataset_enrichment import DatasetEnricher  # noqa: PLC0415

    enricher = DatasetEnricher()
    res = enricher.approve(upload_id)
    if not res.get("ok"):
        raise HTTPException(404, res.get("error") or "approve failed")
    return res


class RejectRequest(BaseModel):
    """Опциональная причина reject — пишется в ``_rejected/<id>.json``."""

    reason: str | None = Field(None, description="Почему отклонили (для аудита)")


@app.post("/admin/uploads/{upload_id}/reject", tags=["admin"])
def admin_reject_upload(upload_id: str, req: RejectRequest | None = None) -> dict:
    """Пометить queued upload как нерелевантный."""
    from pump_calculator.etl.dataset_enrichment import DatasetEnricher  # noqa: PLC0415

    enricher = DatasetEnricher()
    reason = req.reason if req else None
    res = enricher.reject(upload_id, reason=reason)
    if not res.get("ok"):
        raise HTTPException(404, res.get("error") or "reject failed")
    return res


@app.post("/admin/uploads/merge", tags=["admin"])
def admin_merge_uploads() -> dict:
    """Merge ``etalons_uploaded.jsonl`` → ``etalons_from_uploads.json``.

    Manual trigger для ежедневного pipeline. Возвращает
    ``{"merged_count", "skipped_dedup", "output_path"}``.
    """
    from pump_calculator.etl.dataset_enrichment import DatasetEnricher  # noqa: PLC0415

    enricher = DatasetEnricher()
    return enricher.merge_to_etalons()


# ---------------------- Phase 31: TCO / Cost-per-m³ ----------------------


class TCORequest(BaseModel):
    """Запрос на расчёт TCO (Total Cost of Ownership) на N лет.

    Можно передать либо `selection_request` (тогда внутри запустим /select),
    либо уже посчитанный `selection_result` (быстрее, для UI «Стоимость на 10 лет»
    на карточке уже выбранного насоса).
    """

    selection: SelectionResult | None = Field(
        None,
        description="Уже посчитанный SelectionResult. Берём mid-насос по умолчанию.",
    )
    selection_request: SelectionRequest | None = Field(
        None,
        description="L0+L1 — рассчитаем подбор и TCO в одном вызове.",
    )
    segment: Literal["budget", "mid", "premium"] = Field(
        "mid",
        description="Какой ценовой сегмент использовать для TCO.",
    )
    horizon_years: int = Field(10, ge=1, le=30, description="Горизонт TCO, лет")
    tariff_rub_per_kwh: float = Field(
        7.5,
        gt=0,
        le=50,
        description="Тариф электроэнергии в ₽/кВт·ч (default 7.5 — РФ 2026)",
    )
    install_pct: float = Field(0.10, ge=0, le=0.50, description="Доля монтажа от CAPEX")
    transport_pct: float = Field(0.03, ge=0, le=0.30, description="Доля логистики")


@app.post("/tco/calculate", tags=["pricing"])
def tco_calculate(req: TCORequest) -> dict:
    """Расчёт TCO (CAPEX + OPEX за N лет) с разбивкой для Sankey-диаграммы.

    Главный KPI ответа — `cost_per_m3_rub`: «Кубометр стоков стоит X ₽».
    Подходит для обоснования заказчику выбора премиум-насоса
    (КПД +10% → −150 тыс ₽/год за 10 лет).

    Возвращает TCOResult JSON c полями:
        - capex, opex_annual, opex_horizon_rub
        - tco_horizon_rub, flow_horizon_m3, cost_per_m3_rub
        - sankey_nodes[], sankey_links[] (готовые для d3-sankey)
    """
    from pump_calculator.tco import calculate_tco

    # 1. Получить SelectionResult (либо передан, либо считаем)
    if req.selection is not None:
        selection = req.selection
    elif req.selection_request is not None:
        selection = run_selection(req.selection_request.L0, req.selection_request.L1)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'selection' or 'selection_request' must be provided",
        )

    # 2. Взять насос из нужного сегмента
    pump = getattr(selection.results, req.segment, None)
    if pump is None:
        raise HTTPException(
            status_code=422,
            detail=f"No pump available in segment '{req.segment}'. Try another segment.",
        )

    # 3. Определить Q_m3h (из computed.duty_point или из selection_request.L0)
    Q_m3h: float | None = None
    if req.selection_request is not None:
        Q_m3h = req.selection_request.L0.Q_m3h
    elif pump.duty_point and "Q_m3h" in pump.duty_point:
        Q_m3h = pump.duty_point["Q_m3h"]
    else:
        # Fallback: ассампшнс из selection
        for a in selection.assumptions:
            if a.startswith("Q_m3h="):
                try:
                    Q_m3h = float(a.split("=")[1].split()[0])
                except (ValueError, IndexError):
                    pass
                break

    if Q_m3h is None or Q_m3h <= 0:
        raise HTTPException(
            status_code=422,
            detail="Cannot determine Q_m3h for TCO calculation",
        )

    # 4. Определить operating_mode
    operating_mode = None
    if req.selection_request is not None and req.selection_request.L1 is not None:
        operating_mode = req.selection_request.L1.operating_mode

    try:
        result = calculate_tco(
            pump_price_breakdown=pump.price_breakdown,
            P_kW=pump.P_kW,
            Q_m3h=Q_m3h,
            horizon_years=req.horizon_years,
            operating_mode=operating_mode,
            tariff_rub_per_kwh=req.tariff_rub_per_kwh,
            install_pct=req.install_pct,
            transport_pct=req.transport_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        logger.exception("TCO calculation failed: %s", e.__class__.__name__)
        raise HTTPException(status_code=500, detail=f"TCO failed: {e}") from e

    payload = result.model_dump()
    # Метаданные подобранного насоса — для UI
    payload["pump_meta"] = {
        "brand": pump.brand,
        "model": pump.model,
        "P_kW": pump.P_kW,
        "segment": req.segment,
        "price_confidence": pump.price_confidence,
    }
    return payload


# ---------------------- Phase 31: Failure Mode Library ----------------------


@app.get("/failure-modes", tags=["failure_modes"])
def list_failure_modes_endpoint(
    trigger: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> dict:
    """Каталог типовых отказов КНС/НС.

    Источник: 02_dataset/failure_modes/failure_modes_2026.json (26 режимов,
    с симптомами/причинами/стоимостью/downtime + ссылки на СП/ГОСТ).

    Фильтры (комбинируются как AND):
    - trigger: по `trigger_in_calculator` (например `auto_npsh_low`)
    - category: hydraulic / mechanical / electrical / operational / environmental
    - severity: low / medium / high / critical
    """
    from pump_calculator.failure_modes import list_categories, list_failure_modes

    modes = list_failure_modes(trigger=trigger, category=category, severity=severity)
    return {
        "count": len(modes),
        "categories": list_categories(),
        "filter": {"trigger": trigger, "category": category, "severity": severity},
        "modes": modes,
    }


@app.get("/failure-modes/{mode_id}", tags=["failure_modes"])
def get_failure_mode_endpoint(mode_id: str) -> dict:
    """Полная карточка одного режима отказа по id."""
    from pump_calculator.failure_modes import get_failure_mode

    mode = get_failure_mode(mode_id)
    if mode is None:
        raise HTTPException(status_code=404, detail=f"Failure mode not found: {mode_id}")
    return mode


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
