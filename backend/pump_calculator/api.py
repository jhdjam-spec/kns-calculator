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
