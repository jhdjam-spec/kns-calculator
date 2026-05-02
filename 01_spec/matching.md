# Matching Algorithm — первичный подбор насоса по 3+1 показателям

> **Версия:** v1.0 (2026-05-02). Заменяет v0.1.
> **Назначение:** алгоритм первичного (envelope-only) подбора насосов КНС/НС по входу L0 (Q, dH, L, wastewater_type) с возвратом топ-1 в каждом из 3 ценовых сегментов + флаг hand-off к инженеру.
> **Источники:** `01_spec/inputs.md`, `02_dataset/theory/dependencies_map.md`, `02_dataset/theory/formulas.md`, `02_dataset/theory/coefficients.json`, `02_dataset/pumps/pumps.json`, `02_dataset/pumps/seed_kaiquan_50WQS202.json`, `00_research/github_analogs.md`.
> **Гидравлический бэкенд:** `CalebBell/fluids` (MIT) — `friction.friction_factor()`, `Reynolds()`.

---

## Шаг 1. Авто-подбор диаметра напорного трубопровода D

**Цель:** найти минимальный стандартный диаметр D, при котором фактическая скорость v_actual попадает в рекомендуемый диапазон [1.0, 1.5] м/с (СП 32.13330.2018 разд. 5.4 + `velocity_limits_ms` из `coefficients.json`).

### Формула

```
v_target  = 1.2 м/с                          # центр диапазона 1.0–1.5
Q_m3s     = Q_m3h / 3600
D_calc    = sqrt(4 · Q_m3s / (π · v_target)) [м]
D_calc_mm = D_calc · 1000
```

### Округление вверх

```
std_D = coefficients.standard_pipe_diameters_mm
      = [50, 63, 75, 90, 110, 125, 140, 160, 180, 200, 225, 250, 280, 315, 355, 400, 450, 500, 560, 630]
D_mm  = min{ d ∈ std_D : d ≥ D_calc_mm }
```

### Контроль фактической скорости

```
v_actual = 4 · Q_m3s / (π · (D_mm/1000)²)
```

| Условие | Действие |
|---|---|
| `v_actual < 0.7` | warning «риск заиливания», понизить D на одну ступень и пересчитать |
| `v_actual > 2.5` | warning «риск гидроудара», повысить D на одну ступень |
| `0.7 ≤ v_actual ≤ 2.5` | OK (запасной диапазон) |
| `1.0 ≤ v_actual ≤ 1.5` | оптимум, в `computed.v_optimal=true` |

### Граничные случаи

- **L = 0** (короткая внутренняя обвязка) — D всё равно подбираем, потому что v влияет на ζ-сумму внутри корпуса КНС.
- **L > 1000 м** — переключить `v_target = 1.0 м/с` (длинные трассы → меньше потери трения, больше D).

---

## Шаг 2. Расчёт полного напора H_full

### 2.1 Шероховатость и режим течения

```python
import fluids

k_e_mm = coefficients.pipe_roughness_mm[pipe_material].default   # default pe100_sdr17 = 0.007 мм
nu     = 1.01e-6                                                 # м²/с (вода 20 °C)
Re     = fluids.Reynolds(V=v_actual, D=D_mm/1000, nu=nu)
lam    = fluids.friction_factor(Re=Re, eD=(k_e_mm/1000)/(D_mm/1000))   # Альтшуль/Colebrook через fluids
```

Если `fluids` недоступен — fallback на ручную Альтшуль:

```
λ = 0.11 · ((k_э/D) + (68/Re))^0.25
```

### 2.2 Потери на трение по длине (Дарси-Вейсбах)

```
H_тр = λ · (L / D_m) · v_actual² / (2g)         [м];  g = 9.81
```

### 2.3 Местные потери

| Случай | Формула |
|---|---|
| `L = 0` (внутренняя обвязка КНС) | `H_м = 2.0` (фикс — 4 отвода + АТМ + задвижка + обр. клапан внутри корпуса) |
| `L > 0` (default L0 без уточнения) | `H_м = 0.15 · H_тр` (typical 4 отвода + 2 арматуры) |
| `L > 0` + L1 заполнен | `H_м = Σζᵢ · v² / (2g)` через `local_resistance_zeta` |

### 2.4 Полный напор с запасом

```
H_full = (dH + H_тр + H_м) × (1 + safety)
safety = 0.05  если L = 0
       = 0.10  default (5 ≤ L ≤ 1000)
       = 0.20  если L > 1000 или dH < 0
```

### 2.5 Контроль

- `H_full ≤ 0` → ошибка «нет напора, насос не нужен», hand-off.
- `H_full > 80 м` → TRIG-1 (engineer hand-off).

---

## Шаг 3. Жёсткий фильтр по типу стоков (free passage)

Из `coefficients.json::free_passage_by_wastewater_type_mm`:

| wastewater_type | min free_passage, мм | impeller_types |
|---|---|---|
| `domestic`   | ≥ 50 | vortex, single-channel, multi-channel |
| `drainage`   | ≥ 10 | open, channel |
| `industrial` | ≥ 80 | vortex, cutter |

**Жёсткое отсечение** — насос исключается из кандидатов, если:

1. `pump.free_passage_mm < required_free_passage` ИЛИ
2. `pump.impeller ∉ allowed_impeller_types` ИЛИ
3. `wastewater_type ∉ pump.wastewater_compat` ИЛИ
4. `pump._engineer_flag == 'not_recommended'` ИЛИ
5. `pump.type ∉ {'submersible_sewage'}` (КНС-ветка; СПД — отдельная).

Дополнительно для `L1.Ex_required = true` → исключить все насосы где `power.ex_rating == null`.

---

## Шаг 4. Q-H envelope matching

Для каждого `pump` после Шага 3 — проверка:

```
Q_min_ok = Q_m3h ≥ pump.envelope.Q_min_m3h × 0.85
Q_max_ok = Q_m3h ≤ pump.envelope.Q_max_m3h × 1.15
H_min_ok = H_full ≥ pump.envelope.H_min_m
H_max_ok = H_full ≤ pump.envelope.H_max_m × 1.05
```

Все 4 условия должны выполняться (AND). Допуск ±15 % по Q и +5 % по H_max — компромисс между «не пропустить хорошего кандидата на границе» и «не предложить заведомо перегруженный насос».

---

## Шаг 5. Composite score (ранжирование кандидатов)

### Формула

```
score = 0.40 · BEP_proximity
      + 0.25 · eta_at_op
      + 0.20 · H_margin_quality
      + 0.10 · ru_availability
      + 0.05 · warranty
```

Сумма весов = 1.0. Score ∈ [0, 1].

### 5.1 BEP_proximity (вес 0.40)

```
if pump.envelope.Q_BEP_m3h is not None:
    BEP_proximity = max(0, 1 − |Q_m3h − Q_BEP| / Q_BEP)
else:
    Q_BEP_proxy   = (pump.envelope.Q_min_m3h + pump.envelope.Q_max_m3h) / 2
    BEP_proximity = max(0, 1 − |Q_m3h − Q_BEP_proxy| / Q_BEP_proxy) × 0.85   # штраф за прокси
```

### 5.2 eta_at_op (вес 0.25)

```
if pump.envelope.eta_BEP_pct is not None:
    eta_at_op = pump.envelope.eta_BEP_pct / 100        # упрощение для envelope-only
else:
    eta_at_op = 0.5                                    # penalty
```

> **Уточнение для v1.1:** интерполяция по `qh_curve` (точное η в Q_user) вместо η_BEP. См. DEP-14.

### 5.3 H_margin_quality (вес 0.20)

```
ratio = pump.envelope.H_max_m / H_full

if   1.05 ≤ ratio ≤ 1.15:   h_margin = 1.0
elif ratio < 1.0:           h_margin = 0.0     # насос не покрывает H_full
elif ratio < 1.05:          h_margin = 0.7
elif ratio ≤ 1.20:          h_margin = 0.85
else:                       h_margin = max(0, 1 − (ratio − 1.20) × 2)
```

> **Альтернатива при наличии `qh_curve`:** считать `ratio = H_pump_at_Q / H_full` интерполяцией. Точнее, потому что `H_max_m` — это «закрытая задвижка» (Q = 0), а в рабочей точке напор насоса меньше.

### 5.4 ru_availability (вес 0.10)

```
status = pump.available_ru.status
ru_avail = {
    'official':         1.0,
    'parallel_import':  0.6,
    'stock_only':       0.4,
}.get(status, 0.3)
```

### 5.5 warranty (вес 0.05)

```
warranty_score = min(1.0, max(0.0, pump.warranty_months / 24))
# если warranty_months отсутствует → default 12 → 0.5
```

### 5.6 Финальный score

```
score = 0.40·BEP_proximity + 0.25·eta_at_op + 0.20·h_margin + 0.10·ru_avail + 0.05·warranty_score
```

---

## Шаг 6. Топ-1 в каждом ценовом сегменте

Сегмент берётся из `pump.price_segment ∈ {'budget', 'mid', 'premium'}`. Группируем кандидатов по сегменту, в каждом сортируем по убыванию score, берём верхний (плюс top-3 для drill-down).

```python
segments = ['budget', 'mid', 'premium']
results, top3 = {}, {}
for seg in segments:
    seg_candidates = sorted([c for c in candidates if c.pump.price_segment == seg],
                            key=lambda x: x.score, reverse=True)
    results[seg] = seg_candidates[0] if seg_candidates else None
    top3[seg]    = seg_candidates[:3]
    if not seg_candidates:
        warnings.append(f"Нет кандидата в сегменте '{seg}' — попробуйте L1/L2 или поднимите бюджет")
```

Если `results['budget'] is None and results['mid'] is None and results['premium'] is None` → engineer_handoff_required = true (TRIG-6).

---

## Шаг 7. Триггеры hand-off инженеру

Из `dependencies_map.md` (Слой 10). Любое выполненное условие → `engineer_handoff_required = true`, добавить ID в `trigger_reasons`.

| ID | Условие | Источник |
|---|---|---|
| **TRIG-1** | `Q_m3h > 500` ИЛИ `H_full > 80` | Выход за бюджетные серии, нужны крупные/сухие установки |
| **TRIG-2** | `wastewater_type == 'industrial'` | pH, абразив, Ex — нужны L2-поля |
| **TRIG-3** | `L > 500` | Гидроудар, выбор PN-класса трубы (DEP-19) |
| **TRIG-4** | `liquid_temp_c > 30` (только из L2) | NPSHa-расчёт обязателен (DEP-11) |
| **TRIG-5** | `reliability_category == 'I'` (L2) | Сложная схема резервирования + АВР |
| **TRIG-6** | `len(candidates) < 2` после Шагов 3–4 | Нет покрытия в БД |
| **TRIG-7** | `pump.type == 'booster_station'` И `Q_m3h > 50` | Сложный СПД с ЧРП и баками |
| **TRIG-8** | `groundwater_high == true` (L2: УГВ выше дна корпуса) | Якорение, расчёт всплытия |
| **TRIG-9** | `H_corp_mm > 4000` (L2: глубина корпуса > 4 м) | Гофр-конструкция, спец. монтаж |
| **TRIG-10** | `Ex_required == true` (L1) | Полный пакет Ex-сертификации |

`engineer_handoff_required` — флаг, **не блокирующий выдачу результатов**: топ-3 всё равно показываются, но с предупреждением «требуется проверка инженером». Менеджер ОП видит red badge и кнопку «передать инженеру».

---

## Верификация — тест Мысхако (АртВинд)

### Вход

```json
{"Q": 21.2, "dH": 10, "L": 0, "wastewater_type": "domestic"}
```

### Ожидаемый результат

`results.budget` = **KAIQUAN 50WQ/S 20-22-3** (`id: kaiquan-50wqs202-3`).

### Прогон расчёта (ручная сверка)

| Шаг | Вычисление | Значение |
|---|---|---|
| 1 | `D_calc = √(4·(21.2/3600)/(π·1.2)) · 1000` | 79.0 мм |
| 1 | `D_mm` (округление вверх в std-ряду) | **90 мм** |
| 1 | `v_actual = 4·(21.2/3600)/(π·0.090²)` | 0.926 м/с (диапазон 0.7–2.5 ✓, чуть ниже оптимума) |
| 2 | `H_тр = 0` (L = 0) | 0 |
| 2 | `H_м = 2.0` (фикс для L = 0) | 2.0 м |
| 2 | `H_full = (10 + 0 + 2.0) × 1.05` (safety 5 % при L = 0) | **12.6 м** |
| 3 | filter: free_passage 50 ≥ 50, vortex ∈ allowed, domestic ∈ compat ✓ | passed |
| 4 | Q ∈ [5·0.85, 30·1.15] = [4.25, 34.5] → 21.2 ✓; H_full = 12.6 ∈ [8, 26.25] ✓ | passed |
| 5.1 | `BEP_proximity = 1 − |21.2 − 22.9|/22.9` | **0.926** |
| 5.2 | `eta_at_op = 46.4/100` | **0.464** |
| 5.3 | `ratio = 25/12.6 = 1.98` → штраф большой запас | **h_margin ≈ 0.0** (по формуле 1−(1.98−1.20)·2 = −0.56 → clamp 0) |
| 5.4 | status = official | **ru_avail = 1.0** |
| 5.5 | warranty 18 мес → 18/24 | **0.75** |
| **score** | `0.40·0.926 + 0.25·0.464 + 0.20·0 + 0.10·1.0 + 0.05·0.75` | **≈ 0.624** |

### Анализ результата

KAIQUAN 50WQ/S 20-22-3 проходит фильтры и попадает в `budget`. Конкурентов в `budget` с Q ≈ 21 м³/ч и H ≈ 13 м у нас в БД нет:

- KAIQUAN 65WQS215-18.5: Q_min = 30, не подходит на 21.2 м³/ч (даже с допуском −15 % это 25.5).
- KAIQUAN WQ 2290-21-36-80: Q_min = 1500, не подходит.
- LEO XKS 50: free_passage = 35 мм < 50 → отсекается на Шаге 3.

KAIQUAN 50WQ/S — единственный в `budget` сегменте, выводится как топ-1. **Тест проходит.**

> **Замечание о h_margin = 0:** формула штрафует «избыточный запас» (1.98 vs идеал 1.10). В реальности `H_max = 25 м` — это свободный сброс (Q = 0); в рабочей точке Q = 21.2 → H_pump ≈ 17.85 м (интерполяция qh_curve), что даёт более честный ratio = 17.85/12.6 = 1.42. Это всё ещё выше идеала, но не катастрофа. **Решение для v1.1:** если у насоса есть `qh_curve` — использовать H_pump_at_Q вместо H_max. Это поднимет h_margin до ~0.6 и итоговый score до ~0.75.

### Если бы алгоритм НЕ вернул KAIQUAN 50WQ/S — что пересмотреть

1. Снизить вес `H_margin_quality` с 0.20 до 0.10 (envelope-only данные не позволяют точно судить о запасе).
2. Поднять вес `BEP_proximity` с 0.40 до 0.50 — это самое надёжное на envelope-данных.
3. Расширить допуск Q до ±20 % (если граничные модели не проходят).
4. Проверить, не отрезается ли насос в Шаге 4 из-за `H_full < pump.H_min_m`.

---

## JSON-структура ответа

```json
{
  "input": {
    "Q_m3h": 21.2,
    "dH_m": 10,
    "L_m": 0,
    "wastewater_type": "domestic",
    "level": "L0"
  },
  "computed": {
    "D_mm": 90,
    "v_actual_ms": 0.926,
    "v_in_recommended_range": false,
    "v_in_acceptable_range": true,
    "Re": null,
    "lambda": null,
    "H_tr_m": 0.0,
    "H_m_m": 2.0,
    "safety_factor": 0.05,
    "H_full_m": 12.6,
    "free_passage_required_mm": 50,
    "allowed_impeller_types": ["vortex", "single-channel", "multi-channel"]
  },
  "results": {
    "budget": {
      "pump_id": "kaiquan-50wqs202-3",
      "brand": "KAIQUAN",
      "model": "50WQ/S 20-22-3",
      "score": 0.624,
      "score_breakdown": {
        "BEP_proximity": 0.926,
        "eta_at_op": 0.464,
        "H_margin_quality": 0.0,
        "ru_availability": 1.0,
        "warranty": 0.75
      },
      "envelope": {"Q_min_m3h": 5, "Q_max_m3h": 30, "H_min_m": 8, "H_max_m": 25, "Q_BEP_m3h": 22.9, "eta_BEP_pct": 46.4},
      "power_kW": 3.0,
      "free_passage_mm": 50,
      "available_ru": {"status": "official", "distributor": "АСО"}
    },
    "mid": null,
    "premium": null,
    "_alternatives": {
      "budget_top3": [],
      "mid_top3": [],
      "premium_top3": []
    }
  },
  "warnings": [
    "v_actual = 0.926 м/с — ниже рекомендуемого 1.0 м/с, но в допустимом диапазоне",
    "Нет кандидата в сегменте 'mid'",
    "Нет кандидата в сегменте 'premium'"
  ],
  "engineer_handoff_required": false,
  "trigger_reasons": []
}
```

---

## Псевдокод Python (production-ready)

```python
"""
matching.py — первичный подбор насоса L0.
Зависимости: pip install fluids
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass, field
from typing import Literal, Optional

try:
    import fluids
    HAS_FLUIDS = True
except ImportError:
    HAS_FLUIDS = False

WastewaterType = Literal["domestic", "drainage", "industrial"]
Segment        = Literal["budget", "mid", "premium"]
G              = 9.81
NU_WATER_20C   = 1.01e-6  # м²/с

# ---------- ВХОД / ВЫХОД ----------

@dataclass
class L0Input:
    Q_m3h: float
    dH_m: float
    L_m: float
    wastewater_type: WastewaterType

@dataclass
class Computed:
    D_mm: int
    v_actual_ms: float
    Re: Optional[float]
    lam: Optional[float]
    H_tr_m: float
    H_m_m: float
    safety_factor: float
    H_full_m: float
    free_passage_required_mm: int
    allowed_impeller_types: list[str]

@dataclass
class ScoreBreakdown:
    BEP_proximity: float
    eta_at_op: float
    H_margin_quality: float
    ru_availability: float
    warranty: float

@dataclass
class Candidate:
    pump_id: str
    pump: dict
    score: float
    breakdown: ScoreBreakdown

@dataclass
class MatchResult:
    input: L0Input
    computed: Computed
    results: dict[str, Optional[Candidate]]   # 'budget'|'mid'|'premium' -> Candidate|None
    top3: dict[str, list[Candidate]]
    warnings: list[str] = field(default_factory=list)
    engineer_handoff_required: bool = False
    trigger_reasons: list[str] = field(default_factory=list)


# ---------- ШАГ 1: ДИАМЕТР ----------

STD_D_MM = [50, 63, 75, 90, 110, 125, 140, 160, 180, 200,
            225, 250, 280, 315, 355, 400, 450, 500, 560, 630]

def auto_diameter(Q_m3h: float, L_m: float) -> tuple[int, float]:
    """Возвращает (D_mm, v_actual_ms)."""
    v_target = 1.0 if L_m > 1000 else 1.2
    Q_m3s = Q_m3h / 3600.0
    D_calc_mm = math.sqrt(4 * Q_m3s / (math.pi * v_target)) * 1000
    D_mm = next((d for d in STD_D_MM if d >= D_calc_mm), STD_D_MM[-1])
    v_actual = 4 * Q_m3s / (math.pi * (D_mm / 1000) ** 2)
    return D_mm, v_actual


# ---------- ШАГ 2: H_full ----------

def friction_factor(Re: float, k_e_mm: float, D_mm: float) -> float:
    if HAS_FLUIDS and Re > 0:
        return fluids.friction_factor(Re=Re, eD=(k_e_mm / 1000) / (D_mm / 1000))
    # Fallback Альтшуль
    if Re < 1e-6:
        return 0.04
    return 0.11 * (((k_e_mm / D_mm) + 68 / Re) ** 0.25)

def head_full(
    Q_m3h: float, dH_m: float, L_m: float,
    D_mm: int, v_ms: float, k_e_mm: float = 0.007
) -> tuple[float, float, float, float, float, float]:
    """Возвращает (Re, lam, H_tr_m, H_m_m, safety, H_full_m)."""
    if L_m == 0:
        Re, lam = 0.0, 0.0
        H_tr = 0.0
        H_m  = 2.0
        safety = 0.05
    else:
        Re = (v_ms * (D_mm / 1000)) / NU_WATER_20C
        lam = friction_factor(Re, k_e_mm, D_mm)
        H_tr = lam * (L_m / (D_mm / 1000)) * (v_ms ** 2) / (2 * G)
        H_m  = 0.15 * H_tr
        safety = 0.20 if (L_m > 1000 or dH_m < 0) else 0.10
    H_full = (dH_m + H_tr + H_m) * (1 + safety)
    return Re, lam, H_tr, H_m, safety, H_full


# ---------- ШАГ 3: ФИЛЬТР ПО ТИПУ СТОКОВ ----------

FREE_PASSAGE = {
    "domestic":   {"min_mm": 50, "impellers": {"vortex", "single-channel", "multi-channel"}},
    "drainage":   {"min_mm": 10, "impellers": {"open", "channel"}},
    "industrial": {"min_mm": 80, "impellers": {"vortex", "cutter"}},
}

def passes_hard_filter(pump: dict, ww: WastewaterType, ex_required: bool = False) -> bool:
    rule = FREE_PASSAGE[ww]
    if pump.get("free_passage_mm", 0) < rule["min_mm"]:                  return False
    if pump.get("impeller") not in rule["impellers"]:                    return False
    if ww not in pump.get("wastewater_compat", []):                      return False
    if pump.get("_engineer_flag") == "not_recommended":                  return False
    if ex_required and not pump.get("power", {}).get("ex_rating"):       return False
    if pump.get("type") not in {"submersible_sewage"}:                   return False  # КНС-ветка
    return True


# ---------- ШАГ 4: Q-H ENVELOPE ----------

def envelope_match(pump: dict, Q_m3h: float, H_full: float) -> bool:
    env = pump["envelope"]
    return (
        Q_m3h >= env["Q_min_m3h"] * 0.85 and
        Q_m3h <= env["Q_max_m3h"] * 1.15 and
        H_full >= env["H_min_m"]            and
        H_full <= env["H_max_m"] * 1.05
    )


# ---------- ШАГ 5: COMPOSITE SCORE ----------

W_BEP, W_ETA, W_H, W_RU, W_WAR = 0.40, 0.25, 0.20, 0.10, 0.05

def score_pump(pump: dict, Q_m3h: float, H_full: float) -> tuple[float, ScoreBreakdown]:
    env = pump["envelope"]

    # 5.1 BEP_proximity
    Q_BEP = env.get("Q_BEP_m3h")
    if Q_BEP:
        bep = max(0.0, 1.0 - abs(Q_m3h - Q_BEP) / Q_BEP)
    else:
        proxy = (env["Q_min_m3h"] + env["Q_max_m3h"]) / 2
        bep = max(0.0, 1.0 - abs(Q_m3h - proxy) / proxy) * 0.85   # штраф за прокси

    # 5.2 eta
    eta_pct = env.get("eta_BEP_pct")
    eta = (eta_pct / 100.0) if eta_pct else 0.5

    # 5.3 H_margin
    ratio = env["H_max_m"] / max(H_full, 0.01)
    if   1.05 <= ratio <= 1.15: h_m = 1.0
    elif ratio < 1.0:           h_m = 0.0
    elif ratio < 1.05:          h_m = 0.7
    elif ratio <= 1.20:         h_m = 0.85
    else:                       h_m = max(0.0, 1.0 - (ratio - 1.20) * 2)

    # 5.4 ru_availability
    status = pump.get("available_ru", {}).get("status", "unknown")
    ru = {"official": 1.0, "parallel_import": 0.6, "stock_only": 0.4}.get(status, 0.3)

    # 5.5 warranty
    war = min(1.0, max(0.0, pump.get("warranty_months", 12) / 24.0))

    score = W_BEP * bep + W_ETA * eta + W_H * h_m + W_RU * ru + W_WAR * war
    return score, ScoreBreakdown(bep, eta, h_m, ru, war)


# ---------- ШАГ 7: ТРИГГЕРЫ HAND-OFF ----------

def collect_triggers(inp: L0Input, H_full: float, n_candidates: int,
                     ex_required: bool = False, l2: dict | None = None) -> list[str]:
    t = []
    if inp.Q_m3h > 500 or H_full > 80:                t.append("TRIG-1")
    if inp.wastewater_type == "industrial":            t.append("TRIG-2")
    if inp.L_m > 500:                                  t.append("TRIG-3")
    if l2 and l2.get("liquid_temp_c", 15) > 30:        t.append("TRIG-4")
    if l2 and l2.get("reliability_category") == "I":   t.append("TRIG-5")
    if n_candidates < 2:                               t.append("TRIG-6")
    # TRIG-7 — ветка booster_station, обрабатывается в отдельном пайплайне
    if l2 and l2.get("groundwater_high"):              t.append("TRIG-8")
    if l2 and (l2.get("H_corp_mm") or 0) > 4000:       t.append("TRIG-9")
    if ex_required:                                    t.append("TRIG-10")
    return t


# ---------- ОРКЕСТРАТОР ----------

def match(inp: L0Input, pumps_db: list[dict],
          ex_required: bool = False, l2: dict | None = None) -> MatchResult:
    warnings: list[str] = []

    # Шаг 1
    D_mm, v_actual = auto_diameter(inp.Q_m3h, inp.L_m)
    if v_actual < 0.7:  warnings.append(f"v={v_actual:.2f} м/с — риск заиливания")
    if v_actual > 2.5:  warnings.append(f"v={v_actual:.2f} м/с — риск гидроудара")

    # Шаг 2
    Re, lam, H_tr, H_m, safety, H_full = head_full(inp.Q_m3h, inp.dH_m, inp.L_m, D_mm, v_actual)

    # Шаг 3 + Шаг 4
    survivors = [p for p in pumps_db
                 if passes_hard_filter(p, inp.wastewater_type, ex_required)
                 and envelope_match(p, inp.Q_m3h, H_full)]

    # Шаг 5
    scored = [Candidate(p["id"], p, *score_pump(p, inp.Q_m3h, H_full)) for p in survivors]

    # Шаг 6
    results: dict[str, Optional[Candidate]] = {"budget": None, "mid": None, "premium": None}
    top3:    dict[str, list[Candidate]]      = {"budget": [], "mid": [], "premium": []}
    for seg in ("budget", "mid", "premium"):
        seg_c = sorted([c for c in scored if c.pump["price_segment"] == seg],
                       key=lambda x: x.score, reverse=True)
        if seg_c:
            results[seg] = seg_c[0]
            top3[seg] = seg_c[:3]
        else:
            warnings.append(f"Нет кандидата в сегменте '{seg}'")

    # Шаг 7
    triggers = collect_triggers(inp, H_full, len(scored), ex_required, l2)

    rule = FREE_PASSAGE[inp.wastewater_type]
    computed = Computed(
        D_mm=D_mm, v_actual_ms=round(v_actual, 3),
        Re=Re or None, lam=lam or None,
        H_tr_m=round(H_tr, 3), H_m_m=round(H_m, 3),
        safety_factor=safety, H_full_m=round(H_full, 2),
        free_passage_required_mm=rule["min_mm"],
        allowed_impeller_types=sorted(rule["impellers"]),
    )

    return MatchResult(
        input=inp, computed=computed,
        results=results, top3=top3,
        warnings=warnings,
        engineer_handoff_required=bool(triggers),
        trigger_reasons=triggers,
    )


# ---------- USAGE ----------

if __name__ == "__main__":
    with open("02_dataset/pumps/pumps.json", "r", encoding="utf-8") as f:
        db = json.load(f)["pumps"]
    res = match(L0Input(Q_m3h=21.2, dH_m=10, L_m=0, wastewater_type="domestic"), db)
    print(json.dumps({
        "computed": res.computed.__dict__,
        "results": {k: (v.pump_id if v else None) for k, v in res.results.items()},
        "warnings": res.warnings,
        "engineer_handoff_required": res.engineer_handoff_required,
        "trigger_reasons": res.trigger_reasons,
    }, indent=2, ensure_ascii=False))
```

---

## Граничные случаи

| # | Случай | Поведение алгоритма |
|---|---|---|
| 1 | `L = 0` | `H_тр = 0`, `H_м = 2.0` фикс, safety = 0.05 |
| 2 | `dH < 0` | warning «КНС выше точки сброса», safety = 0.20 |
| 3 | `dH = 0` И `L = 0` | `H_full = 2.0 × 1.05 = 2.1` м — большинство канализационных насосов попадает ниже H_min, → TRIG-6 |
| 4 | `Q < 1.5 м³/ч` | hint «возможно нужен СПД/сололифт, не КНС»; всё равно ищем кандидатов |
| 5 | `Q > 500` ИЛИ `H_full > 80` | TRIG-1, hand-off |
| 6 | `wastewater_type = industrial` | TRIG-2 (всегда), но кандидатов всё равно ищем |
| 7 | После Шага 3 пусто | warnings + TRIG-6 |
| 8 | После Шага 4 пусто во всех сегментах | warnings + TRIG-6 |
| 9 | `v_actual < 0.7` | warning, повторный пересчёт с D_mm на ступень ниже (если возможно) |
| 10 | `v_actual > 2.5` | warning, повторный пересчёт с D_mm на ступень выше |
| 11 | `pump.envelope.Q_BEP_m3h is None` | прокси = центр диапазона × штраф 0.85 в BEP_proximity |
| 12 | `pump.envelope.eta_BEP_pct is None` | eta_at_op = 0.5 (penalty) |
| 13 | `pump.warranty_months` отсутствует | default 12 → warranty_score = 0.5 |

---

## Open questions / спорные моменты

1. **H_margin_quality на envelope-only данных штрафует слишком сильно.** Идеал ratio = 1.10 относится к H_pump_at_Q, а не к H_max_m («закрытая задвижка»). При envelope-only `H_max_m / H_full` всегда даёт 1.5–2.5 — почти все насосы получают 0. **Решение v1:** оставить как есть, но при наличии `qh_curve` (как у KAIQUAN seed) использовать H_pump_at_Q. **Решение v1.1:** снизить вес до 0.10, поднять BEP до 0.50.

2. **eta_at_op = 0.5 как penalty при отсутствии данных** — это слишком мягко: насос без паспортного КПД получает score сравнимый с честными 50 % КПД-моделями. Альтернатива: penalty 0.3, чтобы стимулировать заполнение `eta_BEP_pct` в БД.

3. **Допуск ±15 % по Q** — слишком широкий или нет? KAIQUAN seed: Q_BEP = 22.9, Q_max = 30, +15 % = 34.5 — попадает Q = 34. На паспортной кривой Q = 30 → H = 12, η = 38 %, что уже хуже BEP. **Решение для v1.1:** двухуровневый допуск — ±10 % «зелёная зона» (без штрафа в BEP_proximity), ±15 % «жёлтая» (штраф −0.15).

4. **Параллельная работа насосов (DEP-15)** в L0 не учитывается. При 1+1 — считаем по одному рабочему (правильно). Но при 2+1 («оба рабочие в параллель») реальный Q ≈ 1.6 × Q_одного, не 2 × Q. В v1 предполагаем 1 рабочий + резерв. **v1.1:** добавить характеристику параллельной работы.

5. **price_segment как enum в pumps.json** — жёстко привязан. Реальная цена меняется (курс юаня, пошлины). KAIQUAN 2025 vs 2026 может перейти из budget в mid. **Решение v1.2:** добавить `price_rub_2026` и динамически вычислять сегмент по порогам {≤500к: budget, 500к–1.5М: mid, >1.5М: premium}.

6. **Шаг 3 жёстко исключает booster_station для КНС-ветки.** Если пользователь ввёл L0 с СПД-задачей (Q = 15, dH = 60, type = domestic, но это водоснабжение коттеджа) — алгоритм не догадается. **Решение:** в L0 добавить radio «КНС / СПД водоснабжения» (5-е поле) ИЛИ автодетекция: dH > 30 + Q < 30 → подсказка «возможно вам нужен СПД, переключите тип».

7. **TRIG-6 (n_candidates < 2)** срабатывает уже на этапе Шага 4, но это не значит, что результат пуст — это значит «всего 1 насос в БД подошёл». Возможно стоит сделать `< 1` для пустоты и оставить `< 2` только как warning без hand-off.

8. **Ru_availability `parallel_import = 0.6`** — статичное значение. Реально статус подразумевает срок поставки 4–12 недель и риск исключения из перечня (как с Grundfos в апр 2025). Для срочных проектов «1.5 месяца ждать» = «нет в наличии», и penalty должен быть жёстче (0.3 или 0.0). **Решение:** разрешить override через UI «срочно: только in_stock» → исключать parallel_import.

9. **`fluids.friction_factor`** возвращает λ для разных режимов автоматически (Clamond / Colebrook / Альтшуль). Хорошо, но нужно убедиться что для Re ≈ 100 000 и k/D = 7e-5 значение совпадает с Альтшулем (нашим reference). **Action item:** в тестах запинить cross-check между формулами.

10. **`liquid_temp_c`, `groundwater_high`, `H_corp_mm`** в TRIG-4/8/9 берутся из L2 — в L0 их нет. Если пользователь не открывал L2, эти триггеры не срабатывают. Это OK для L0, но в результирующей карточке нужно показывать «триггеры активные на L0» отдельно от «триггеры, требующие L2-уточнения».
