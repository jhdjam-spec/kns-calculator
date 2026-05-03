"""FastAPI app: REST endpoints для калькулятора подбора насосов."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from pump_calculator import __version__, catalog
from pump_calculator.handoff import generate_bom_pdf, generate_questionnaire_pdf
from pump_calculator.matching import select_pumps as run_selection
from pump_calculator.schemas import L0Input, SelectionRequest, SelectionResult

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
    try:
        pdf_bytes = generate_bom_pdf(selection)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="kns_bom_draft.pdf"'},
    )
