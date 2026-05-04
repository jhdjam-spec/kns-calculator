"""Pydantic-модели входов и выходов калькулятора.

Соответствуют 01_spec/inputs.md (L0/L1) и ALGORITHM_SPEC.md §3 (выход).
"""

from typing import Literal

from pydantic import BaseModel, Field

WastewaterType = Literal["domestic", "drainage", "industrial", "clean_water"]
QUnit = Literal["m3h", "ls", "m3sut"]
PriceSegment = Literal["budget", "mid", "premium"]
PipeMaterial = Literal[
    "pe100_sdr17", "steel_seamless_new", "steel_welded_new",
    "cast_iron_new", "pvc", "pp", "concrete", "korsis_pe_corrugated",
]
ReliabilityCategory = Literal["I", "II", "III"]


# ----------------------- Inputs -----------------------

class L0Input(BaseModel):
    """L0-вход: только Q обязателен. Остальные поля опциональны — при отсутствии калькулятор подставит безопасные дефолты и вернёт их в `assumptions`.

    Дефолты:
      - dH_m: 5.0 м (типичный перепад внутри площадки малой КНС)
      - L_m: 50.0 м (типичная длина внутриплощадочной напорной трассы)
      - wastewater_type: "domestic" (наиболее частый сценарий менеджера ОП)
    """

    Q_m3h: float = Field(..., gt=0, le=10000, description="Расход в м³/ч (единственное обязательное)")
    dH_m: float | None = Field(None, ge=-50, le=200, description="Геометрический перепад точек, м (default 5.0)")
    L_m: float | None = Field(None, ge=0, le=5000, description="Длина напорной трассы, м (default 50.0; 0 = только внутри)")
    wastewater_type: WastewaterType | None = Field(None, description="Тип стоков (default 'domestic')")


class L1Input(BaseModel):
    """Опциональные поля уточнения. None = взять default из coefficients."""

    pipe_material: PipeMaterial | None = None
    pipe_D_mm: float | None = Field(None, gt=0, le=2000)
    n_bends: int | None = Field(None, ge=0, le=50)
    n_valves: int | None = Field(None, ge=0, le=20)
    redundancy: Literal["1+0", "1+1", "2+1", "3+1", "N+0"] | None = None
    Ex_required: bool = False
    reliability_category: ReliabilityCategory | None = None
    liquid_temp_c: float | None = Field(None, ge=0, le=100)
    corpus_material: Literal["pe", "glass"] | None = Field(
        None,
        description="Материал корпуса КНС: pe (ПЭ Серво-Юг, default) или glass (стеклопластик)",
    )


class SelectionRequest(BaseModel):
    """Полный запрос на подбор: L0 обязательный, L1 опциональный."""

    L0: L0Input
    L1: L1Input | None = None


# ----------------------- Computed -----------------------

class ComputedHydraulics(BaseModel):
    """Промежуточные параметры гидравлического расчёта."""

    D_mm: float = Field(..., description="Подобранный диаметр напорного трубопровода")
    v_ms: float = Field(..., description="Фактическая скорость потока")
    Re: float = Field(..., description="Число Рейнольдса")
    friction_factor: float = Field(..., description="λ — коэффициент трения по Дарси-Альтшулю")
    H_tr_m: float = Field(..., description="Потери на трение по длине")
    sum_zeta: float = Field(..., description="Сумма коэффициентов местных сопротивлений")
    H_m_m: float = Field(..., description="Потери на местных сопротивлениях")
    H_full_m: float = Field(..., description="Полный напор насоса (с safety factor)")
    safety_factor: float = Field(..., description="Применённый запас")


# ----------------------- Pump record (subset для выдачи) -----------------------

class PumpEnvelope(BaseModel):
    Q_min_m3h: float
    Q_max_m3h: float
    H_min_m: float
    H_max_m: float
    Q_BEP_m3h: float | None = None
    H_BEP_m: float | None = None
    eta_BEP_pct: float | None = None
    NPSHr_at_BEP_m: float | None = None


class PriceBreakdown(BaseModel):
    """Разбивка ориентировочной цены КНС-комплекта по позициям BOM, ₽."""

    pump_rub: int = 0
    atm_rub: int = 0
    valve_rub: int = 0
    check_valve_rub: int = 0
    rails_rub: int = 0
    cabinet_rub: int = 0
    floats_rub: int = 0
    chain_rub: int = 0
    corpus_rub: int = 0
    total_rub: int = 0


class PumpResult(BaseModel):
    """Один кандидат в выдаче."""

    id: str
    brand: str
    model: str
    type: str
    impeller: str | None = None
    free_passage_mm: float
    envelope: PumpEnvelope
    P_kW: float
    discharge_DN_mm: float | None = None
    price_segment: PriceSegment
    available_ru_status: str
    score: float = Field(..., description="Composite score 0..1")
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    duty_point: dict[str, float] | None = None
    aor_zone: Literal["POR", "AOR", "outside"] | None = None
    notes: list[str] = Field(default_factory=list)

    # Ориентировочная цена комплекта КНС (насос + обвязка + ШУ + корпус), ₽
    price_estimate_rub: int = Field(0, description="Сумма по 9 позициям BOM. 0 = не удалось оценить.")
    price_breakdown: PriceBreakdown = Field(default_factory=PriceBreakdown)
    price_confidence: Literal["low", "medium", "high"] = Field(
        "low",
        description="low — если использованы heuristic-оценки; medium — большинство из БД 2026; high — все из БД",
    )


# ----------------------- Output -----------------------

class SelectionResultsBySegment(BaseModel):
    budget: PumpResult | None = None
    mid: PumpResult | None = None
    premium: PumpResult | None = None


class SelectionResult(BaseModel):
    """Финальный ответ калькулятора."""

    schema_version: str = "1.1"
    input: SelectionRequest
    computed: ComputedHydraulics
    results: SelectionResultsBySegment
    candidates_total: int = Field(..., description="Сколько кандидатов прошло фильтр")
    warnings: list[str] = Field(default_factory=list)
    engineer_handoff_required: bool = False
    trigger_reasons: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(
        default_factory=list,
        description="Дефолты, подставленные при отсутствии данных (например, 'dH_m не указан, использован 5.0 м')",
    )


# ----------------------- Unit conversion -----------------------

def to_m3h(value: float, unit: QUnit) -> float:
    """Перевод любой единицы расхода в м³/ч (внутренний стандарт).

    м³/сут пересчитываем как «средний за сутки» — НЕ применяем K_gen здесь,
    это задача отдельного слоя «Q-from-norms» (вне scope MVP).
    """
    if unit == "m3h":
        return value
    if unit == "ls":
        return value * 3.6
    if unit == "m3sut":
        return value / 24.0
    raise ValueError(f"Unknown Q unit: {unit}")
