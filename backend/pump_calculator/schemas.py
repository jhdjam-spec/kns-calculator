"""Pydantic-модели входов и выходов калькулятора.

Соответствуют 01_spec/inputs.md (L0/L1) и ALGORITHM_SPEC.md §3 (выход).
"""

from typing import Literal

from pydantic import BaseModel, Field

WastewaterType = Literal["domestic", "drainage", "industrial", "clean_water", "fire_protection"]
QUnit = Literal["m3h", "ls", "m3sut"]
PriceSegment = Literal["budget", "mid", "premium"]
PipeMaterial = Literal[
    "pe100_sdr17", "steel_seamless_new", "steel_welded_new",
    "cast_iron_new", "pvc", "pp", "concrete", "korsis_pe_corrugated",
]
ReliabilityCategory = Literal["I", "II", "III"]
OperatingMode = Literal["continuous", "periodic", "level_based"]


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

    # Режим работы и приток — влияют на расчёт sump_volume, cycles_per_hour
    operating_mode: OperatingMode | None = Field(
        None,
        description=(
            "Алгоритм работы: continuous (24/7 равномерный приток), "
            "periodic (циклы вкл/выкл по таймеру), level_based (по поплавкам, default)"
        ),
    )
    inflow_per_hour_m3: float | None = Field(
        None,
        ge=0,
        le=10000,
        description=(
            "Фактический приток стоков в час, м³/ч. Если задан и меньше Q насоса — "
            "запускаем расчёт цикла вкл/выкл (sump_volume по СП 32 §6.2 — V_min = Q_p · 5 мин)"
        ),
    )

    # Кол-во насосов — переопределяет дефолт redundancy
    pumps_total_override: int | None = Field(
        None,
        ge=2,  # СП 32.13330 п.6.2: минимум 1 раб + 1 рез
        le=10,
        description=(
            "Точное количество насосов в станции (рабочие + резерв). "
            "Если задано — переопределяет redundancy. По СП 32.13330 п.6.2 "
            "минимум 1 раб + 1 рез (=2). Pydantic отбивает значения <2."
        ),
    )

    # ──────────────────────────────────────────────────────────────────
    # 2026-05-09: 8 новых полей из анализа 109 полей по 54 ОЛ (Agent B)
    # ──────────────────────────────────────────────────────────────────
    # Геометрия подвода
    inlet_pipe_diam_mm: float | None = Field(
        None, gt=0, le=2000,
        description="Диаметр подводящей трубы (в КНС), мм. Влияет на подбор корпуса по DN.",
    )
    install_depth_inlet_mm: float | None = Field(
        None, ge=0, le=20000,
        description="Глубина лотка подвода относительно поверхности, мм. Влияет на высоту корпуса.",
    )
    # Уровневое управление и защита
    level_sensor_type: Literal["floats", "ultrasonic", "capacitive", "pneumatic"] | None = Field(
        None,
        description="Тип датчиков уровня: поплавки/УЗД/ёмкостные/пневматические.",
    )
    dry_run_protection: bool = Field(
        True,
        description="Защита от сухого хода (default True по СП 32 §6.2).",
    )
    # Электрика и автоматика
    ip_motor: Literal["IP54", "IP55", "IP58", "IP68"] | None = Field(
        None,
        description="IP-рейтинг двигателя. IP68 — погружные стандарт, IP55 — наземные.",
    )
    modbus_rtu_required: bool = Field(
        False,
        description="Требуется Modbus RTU для интеграции в SCADA (CIM 200, и т.п.).",
    )
    above_ground_pavilion: bool = Field(
        False,
        description="Наземный павильон над КНС (для доступа в холодных регионах).",
    )
    # Грунт и УГВ
    groundwater_level_m: float | None = Field(
        None, ge=-50, le=10,
        description=(
            "Отметка УГВ относительно земли, м (отрицательные — ниже земли). "
            "Если ниже отметки дна корпуса — нужен anti-buoyancy расчёт."
        ),
    )
    # Барометрия — для NPSHa в горных регионах
    altitude_m: float | None = Field(
        None, ge=-500, le=4500,
        description=(
            "Высота над уровнем моря, м. Используется для коррекции "
            "атмосферного давления при расчёте NPSHa (P_atm падает с высотой). "
            "Default: 0 (уровень моря, P_atm=101.325 кПа). "
            "Для Архыза (1700 м) → P_atm≈83 кПа, NPSHa ниже на ~1.8 м."
        ),
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

    # Sump / cycles — рассчитываются если задан inflow_per_hour_m3 (СП 32 §6.2)
    sump_volume_min_m3: float | None = Field(
        None,
        description=(
            "Минимальный полезный объём приёмной камеры КНС, м³. "
            "По СП 32.13330 §6.2: V_min = Q_pump · 5 мин, "
            "чтобы цикл вкл/выкл был не чаще 6 раз в час (защита двигателя)"
        ),
    )
    cycles_per_hour_estimate: float | None = Field(
        None,
        description=(
            "Циклы вкл/выкл за час при заданном inflow и V_min. "
            "При inflow ≥ Q_pump → 0 (continuous duty, насос не выключается)"
        ),
    )
    operating_mode_effective: str | None = Field(
        None,
        description="Фактический режим: continuous / periodic / level_based — определяется из inflow vs Q_pump",
    )
    n_pumps_total: int = Field(
        2,
        description="Итоговое количество насосов в станции (рабочие + резерв). По умолчанию 2 (1+1) по СП 32 §6.2",
    )
    # 2026-05-10: NPSHa с поправкой на высоту над уровнем моря (L1.altitude_m).
    # Если altitude_m=None — используется уровень моря (P_atm=101.325 кПа).
    # NPSHa = (P_atm − P_vap) / (ρ·g) − H_suction − h_friction_suction.
    # Для подбора по умолчанию принимаем H_suction=0 (затопленный погружной насос),
    # h_friction_suction=0. Реальный объект может иметь H_suction>0 — тогда NPSHa
    # ниже расчётного. Используется как первичная оценка для триггера
    # auto_npsha_low (NPSHa < 5 м в горах).
    npsha_m: float | None = Field(
        None,
        description=(
            "NPSHa (доступный кавитационный запас), м. Учитывает атмосферное "
            "давление от высоты над уровнем моря (L1.altitude_m). None если "
            "поле не задано — расчёт пропускается. Принят H_suction=0 "
            "(затопленный погружной насос). Подробнее: physics_advanced.npsha_with_corrections."
        ),
    )


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
    # Phase 9: диапазон цены — учитывает полноту входных данных
    # При неполном вводе диапазон шире (±20-30%), при полном — узкий (±5-10%)
    total_low_rub: int = Field(0, description="Нижняя граница диапазона цены, ₽")
    total_high_rub: int = Field(0, description="Верхняя граница диапазона цены, ₽")
    # 2026-05-09: НДС и дилерская скидка
    vat_rate: float = Field(0.22, description="Ставка НДС (с 2026 = 22%)")
    vat_included: bool = Field(True, description="True = total_rub уже включает НДС")
    is_dealer_price: bool = Field(False, description="True = применена дилерская скидка -25%")
    total_dealer_rub: int = Field(0, description="Цена со скидкой -25% (если is_dealer)")


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


class InputSuggestion(BaseModel):
    """«Возможно вы имели в виду» — мягкое предложение исправить параметр.

    2 уровня объяснения для разных аудиторий:
    - reason_engineer: 👷 инженерный (формулы, СП-цитаты, термины)
    - reason_manager: 💼 менеджерский ОП (что произойдёт, цена, срок)

    Frontend показывает табы или toggle между уровнями. Поле reason
    оставлено как fallback (= reason_engineer).
    """

    field: str = Field(..., description="Имя поля: Q_m3h, dH_m, L_m, pipe_material, и др.")
    current_value: str = Field(..., description="Текущее значение (как ввёл пользователь)")
    suggested_value: str = Field(..., description="Предлагаемое значение")
    reason: str = Field(..., description="Fallback (= reason_engineer для backward compat)")
    reason_engineer: str = Field(
        default="",
        description="👷 Инженерный: формулы, СП-цитаты, физика/гидравлика/материаловедение",
    )
    reason_manager: str = Field(
        default="",
        description="💼 Менеджерский ОП: что произойдёт, сколько денег, какой срок",
    )
    severity: Literal["info", "warning", "critical"] = "warning"


class SelectionResult(BaseModel):
    """Финальный ответ калькулятора."""

    schema_version: str = "1.2"
    input: SelectionRequest
    computed: ComputedHydraulics
    results: SelectionResultsBySegment
    candidates_total: int = Field(..., description="Сколько кандидатов прошло фильтр")
    warnings: list[str] = Field(default_factory=list)
    engineer_handoff_required: bool = False
    trigger_reasons: list[str] = Field(default_factory=list)
    suggestions: list[InputSuggestion] = Field(
        default_factory=list,
        description=(
            "«Возможно вы имели в виду...» — конкретные предложения исправить "
            "входные параметры. Frontend может показать модалку 'Применить?' "
            "до повторного запроса. См. backend/pump_calculator/matching.py:build_suggestions."
        ),
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Дефолты, подставленные при отсутствии данных (например, 'dH_m не указан, использован 5.0 м')",
    )
    # Phase 9: полнота ввода и человекочитаемый прогноз
    completeness_pct: int = Field(
        100,
        ge=0,
        le=100,
        description="Процент заполнения входных данных (0-100). 100 — все поля L0+L1 заданы.",
    )
    summary_text: str = Field(
        "",
        description="Человекочитаемая сводка: 'Для гостиницы 50 номеров — ориентир 800k-1.2M ₽ в эконом-сегменте...'",
    )
    # Phase 13: размеры корпуса КНС (опционально, если нужен корпус)
    corpus_size: "CorpusSize | None" = Field(
        None,
        description=(
            "Минимальные размеры стеклопластикового корпуса КНС: "
            "diameter_mm × height_mm + DN входа/выхода. None если корпус не нужен "
            "(малые бытовые с готовым приямком, СПД-блоки)"
        ),
    )
    # 2026-05-09: альтернативные кандидаты по брендам (P2.3)
    alternatives: list["PumpResult"] = Field(
        default_factory=list,
        description=(
            "До 6 альтернативных кандидатов с разными брендами от topbudget/mid/premium, "
            "чтобы менеджер видел не только Antarus, но и Pedrollo/KSB/CNP/ИЛТ и т.д. "
            "Сортировка по убыванию score."
        ),
    )


# ----------------------- Corpus (Phase 13) -----------------------

class CorpusSize(BaseModel):
    """Размеры стеклопластикового / ПЭ корпуса КНС."""

    diameter_mm: float = Field(..., description="Внутренний диаметр корпуса, мм")
    height_mm: float = Field(..., description="Полная высота корпуса от дна до крышки, мм")
    inlet_DN_mm: float = Field(..., description="DN подводящего самотёчного трубопровода")
    outlet_DN_mm: float = Field(..., description="DN напорного выходного трубопровода")
    weight_estimate_kg: float | None = Field(
        default=None,
        description=(
            "Ориентировочный вес корпуса без насосов и арматуры (кг). "
            "Считается по геометрии стенок (π·D·H + 2·π·D²/4) и плотности материала: "
            "ПЭ100 SDR17 (δ=D/17, ρ=950 кг/м³) или стеклопластик (130 кг/м²). "
            "None если данных недостаточно (Q<5 без корпуса, нет sample_pump)."
        ),
    )
    reinforcement_kg: float | None = Field(
        default=None,
        description=(
            "Дополнительный вес усиления стенок (кг) при auto_lateral_earth_pressure "
            "(install_depth_inlet_mm > 4000 мм). Считается по СП 22.13330 + Кулону: "
            "σ_x = γ·z·K_a (γ=18 кН/м³, K_a=0.33 для песка φ=30°). "
            "z=4-5 м — рёбра жёсткости ПЭ (~5% от веса корпуса); "
            "z=5-7 м — частичная ж/б обойма (площадь стенок · 100 кг/м²); "
            "z>7 м — полная ж/б обойма (площадь стенок · 250 кг/м²). "
            "None если усиление не требуется (depth ≤ 4000 мм или вес корпуса не оценён)."
        ),
    )
    notes: list[str] = Field(default_factory=list)


# Forward-ref резолв для SelectionResult.corpus_size
SelectionResult.model_rebuild()


# ----------------------- CRM-light: классификация входящих писем -----------------------


class ClassifyRequest(BaseModel):
    """Запрос на классификацию входящего письма (CRM-light, P5 mail integration).

    Принимает три текстовых поля; все опциональны (для гибкости UI), но при
    полностью пустом теле возвращается 400. Subject + body конкатенируются
    для извлечения шифров; subject отдельно идёт в marker-классификатор.
    """

    subject: str = Field("", description="Тема письма")
    body: str = Field("", description="Тело письма (plain text или HTML без тегов)")
    from_email: str = Field(
        "",
        description="Адрес отправителя (формат `user@domain` или `Имя <user@domain>`)",
    )


class ClassifyResponse(BaseModel):
    """Ответ /etl/classify: тип запроса, объект, производитель, шифры, флаг доверия."""

    type: str | None = Field(None, description="ОЛ | КП | ТЗ | ЗАЯВКА | ЗАПРОС | ТЕНДЕР | null")
    object: str | None = Field(None, description="КНС | ЛОС | ВНС | ВЗиС | ПОЖАРКА | ... | null")
    manufacturer: str | None = Field(
        None,
        description="GRUNDFOS | KSB | WILO | PEDROLLO | SCHWARTZ | ANTARUS | KAIQUAN | CNP | СМЗ | ГНОМ | null",
    )
    project_codes: list[str] = Field(
        default_factory=list,
        description="Извлечённые шифры (проектные/буквенно-цифровые/тендерные)",
    )
    is_trusted_sender: bool = Field(
        False,
        description="True если домен отправителя в списке доверенных (inservo.ru, mail.ru, yandex.ru и др.)",
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
