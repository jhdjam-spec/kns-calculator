# ALGORITHM_SPEC — Калькулятор КНС/НС/СПД

**Версия:** 1.0 | **Дата:** 2026-05-03
**Назначение:** единый документ для разработчика, объединяющий вход / алгоритм / выход / hand-off / зависимости / антипаттерны.

---

## 0. Резюме за 60 секунд

```
ВХОД (4 поля)                           ВЫХОД
                                        ┌──────────────────────────┐
Q   расход (м³/ч / л/с / м³/сут)        │ Топ-1 в каждом сегменте: │
ΔH  перепад точек (м)             ───▶  │   Бюджет  (KAIQUAN/LEO)  │
L   длина напорной трассы (м)           │   Средний (Antarus/Ped)  │
type стоков (хоз-быт/дренаж/пром)       │   Премиум (Wilo/Grundf)  │
                                        │ + опросник клиенту PDF   │
                                        │ + BOM-черновик           │
                                        │ + JSON-payload для CRM   │
                                        │ + флаг engineer_handoff  │
                                        └──────────────────────────┘
```

**Эталон верификации:** KAIQUAN 50WQ/S 20-22-3 (проект АртВинд Мысхако, Q=21.2, dH=10, L=0, domestic). Алгоритм возвращает его в сегменте `budget` с composite_score ≈ 0.624. ✅ ПРОЙДЕНО.

---

## 1. Вход (Inputs Schema)

Полная спецификация — [`01_spec/inputs.md`](01_spec/inputs.md).

### L0 — Express (4 поля, для менеджера)
| Поле | Тип | Диапазон | Дефолт |
|---|---|---|---|
| `Q` | number + unit (л/с / м³/ч / м³/сут) | 0.5–10000 м³/ч экв. | unit=`m³/ч` |
| `dH` | number, м | -50…+200 | — |
| `L` | number, м | 0–5000 | — |
| `wastewater_type` | radio | domestic / drainage / industrial | — |

Внутреннее хранение Q — всегда **м³/ч** (`toM3h()`). Для `м³/сут` автоматически применяется K_gen.max.

### L1 — Уточнить (опционально, +6 полей)
`pipe_material`, `pipe_D_mm` (auto если пусто), `n_bends` (default 4), `n_valves` (default 2), `redundancy` (default 1+1 для II категории), `Ex_required` (default false).

### L2 — Pro (полный опросник для инженера, 30+ полей)
По эталону `характеристики_КНС.png`: размеры корпуса, глубина подвода, T жидкости, плотность, абразив, категория надёжности, и т.д.

---

## 2. Алгоритм первичного подбора (7 шагов)

Полная спецификация — [`01_spec/matching.md`](01_spec/matching.md).

### Шаг 1. Авто-подбор диаметра напорного D
```python
v_target = 1.2  # м/с (СП 32, 1.0–1.5)
Q_si = Q_m3h / 3600  # перевод в м³/с
D_calc = math.sqrt(4 * Q_si / (math.pi * v_target))  # м
D_mm = round_up_to_standard(D_calc * 1000, [50,63,75,90,110,...,400,...,630])
v_actual = 4 * Q_si / (math.pi * (D_mm/1000)**2)
# Контроль: 0.7 ≤ v_actual ≤ pressure_pipe_max_plastic (4 м/с для ПЭ)
```

### Шаг 2. Расчёт полного напора H_full
```python
import fluids  # CalebBell/fluids MIT

k_e_mm = COEFFS["pipe_roughness_mm"]["pe100_sdr17"]["default"]  # 0.007 mm
Re = fluids.core.Reynolds(V=v_actual, D=D_mm/1000, nu=1.01e-6)
fd = fluids.friction_factor(Re=Re, eD=k_e_mm/1000 / (D_mm/1000))
H_tr = fd * (L / (D_mm/1000)) * (v_actual**2) / (2 * 9.81)

# Местные потери через Σζ Идельчика (v0.2)
sum_zeta = COEFFS["local_resistance_zeta"]["typical_kns_obvyazka_sum_zeta"]["sum_zeta"]  # 10.79
H_m = sum_zeta * (v_actual**2) / (2 * 9.81)

safety = 0.10 if L > 0 else 0.05
H_full = (dH + H_tr + H_m) * (1 + safety)
```

### Шаг 3. Жёсткий фильтр по типу стоков
```python
free_passage_required = COEFFS["free_passage_by_wastewater_type_mm"][wastewater_type]["min"]
allowed_impellers = COEFFS["free_passage_by_wastewater_type_mm"][wastewater_type]["impeller_types"]

candidates = [
    p for p in PUMPS_DB
    if p["free_passage_mm"] >= free_passage_required
    and p["impeller"] in allowed_impellers
    and wastewater_type in p["wastewater_compat"]
    and p.get("_engineer_flag") != "not_recommended"
]
```

### Шаг 4. Q-H envelope matching
```python
candidates = [
    p for p in candidates
    if p["envelope"]["Q_min_m3h"] * 0.85 <= Q_m3h <= p["envelope"]["Q_max_m3h"] * 1.15
    and p["envelope"]["H_min_m"] <= H_full <= p["envelope"]["H_max_m"] * 1.05
]
```

### Шаг 5. AOR/POR проверка (v0.2 ANSI/HI 9.6.3)
```python
# Только для насосов с Q_BEP в envelope
for p in candidates:
    if p["envelope"]["Q_BEP_m3h"]:
        ratio = Q_m3h / p["envelope"]["Q_BEP_m3h"]
        if not (0.40 <= ratio <= 1.50):  # вне AOR — исключаем
            candidates.remove(p)
        elif not (0.70 <= ratio <= 1.20):  # в AOR но вне POR — penalty
            p["_aor_penalty"] = 0.7
```

### Шаг 6. Composite score
```python
def score(pump, Q, H_full):
    # BEP proximity (40%)
    Q_BEP = pump["envelope"].get("Q_BEP_m3h") or (pump["envelope"]["Q_min_m3h"] + pump["envelope"]["Q_max_m3h"]) / 2
    bep_prox = max(0, 1 - abs(Q - Q_BEP) / Q_BEP)

    # КПД в рабочей точке (25%)
    eta = pump["envelope"].get("eta_BEP_pct", 30) / 100  # fallback 0.30 (не 0.50!)

    # H margin quality (20%) — идеал H_max/H_full в [1.05, 1.15]
    ratio = pump["envelope"]["H_max_m"] / H_full
    if 1.05 <= ratio <= 1.15:
        h_quality = 1.0
    elif ratio < 1.0:
        h_quality = 0  # не покрывает
    elif 1.0 <= ratio < 1.05 or 1.15 < ratio <= 1.30:
        h_quality = 0.7
    else:
        h_quality = 0.4  # избыточный запас

    # Доступность РФ (10%)
    avail_map = {"official": 1.0, "parallel_import": 0.6, "stock_only": 0.4, "discontinued": 0.0}
    ru = avail_map.get(pump["available_ru"]["status"], 0.5)

    # Гарантия (5%)
    warranty = min(pump.get("warranty_months", 12) / 24, 1.0)

    score = 0.40*bep_prox + 0.25*eta + 0.20*h_quality + 0.10*ru + 0.05*warranty
    score *= pump.get("_aor_penalty", 1.0)
    return score
```

### Шаг 7. Топ-1 в каждом сегменте + триггеры hand-off
```python
results = {}
for segment in ["budget", "mid", "premium"]:
    seg_candidates = [p for p in candidates if p["price_segment"] == segment]
    if seg_candidates:
        results[segment] = max(seg_candidates, key=lambda p: score(p, Q_m3h, H_full))
    else:
        results[segment] = None  # warning «нет варианта в этом сегменте»

# 10 триггеров hand-off (TRIG-1..10 + новые из v0.2)
triggers = []
if Q_m3h > 500 or H_full > 80: triggers.append("auto_q_high")
if wastewater_type == "industrial": triggers.append("auto_industrial")
if L > 500: triggers.append("auto_l_long_zhukovsky")  # NEW v0.2
if liquid_temp_c and liquid_temp_c > 40: triggers.append("auto_npsh_hot")  # NEW v0.2
if reliability_category == "I": triggers.append("auto_category_I")
if sum(1 for v in results.values() if v) < 2: triggers.append("auto_no_match")
if pump_type == "booster_station" and Q_m3h > 50: triggers.append("auto_spd_complex")
if ground_water_above_floor: triggers.append("auto_anchoring_required")  # NEW v0.2
if Ex_required: triggers.append("auto_ex")
if pump_depth_m > 4: triggers.append("auto_corpus_deep")
```

---

## 3. Выход (JSON-схема)

```json
{
  "schema_version": "1.0",
  "calc_id": "uuid",
  "timestamp": "2026-05-03T00:15:00+03:00",
  "input": {
    "L0": {"Q_m3h": 21.2, "dH_m": 10, "L_m": 0, "wastewater_type": "domestic"},
    "L1": null
  },
  "computed": {
    "D_mm": 90,
    "v_ms": 0.926,
    "Re": 8.2e4,
    "lambda": 0.025,
    "H_tr_m": 0.0,
    "H_m_m": 0.47,
    "H_full_m": 12.6,
    "sum_zeta": 10.79
  },
  "results": {
    "budget":  {"id": "kaiquan-50wqs202-3", "score": 0.624, "duty_point": {"Q":21.2, "H":17.4, "eta":0.464}},
    "mid":     null,
    "premium": null
  },
  "warnings": ["mid: нет насосов в сегменте", "premium: нет насосов в сегменте"],
  "engineer_handoff_required": false,
  "trigger_reasons": [],
  "artifacts": {
    "questionnaire_pdf_url": null,
    "draft_bom_pdf_url": null,
    "crm_payload_json_url": null
  }
}
```

---

## 4. Hand-off Package

Полная спецификация — [`01_spec/handoff.md`](01_spec/handoff.md).

3 артефакта формируются ВСЕГДА (даже если `engineer_handoff_required=false` — менеджер может отправить вручную):

1. **PDF опросник клиенту** — ~50 полей в 10 секциях (по эталону `характеристики_КНС.png`), auto-fill из L0/L1
2. **BOM-черновик** — 9+ позиций × 3 ценовых сегмента (насос + АТМ + задвижка + обр.клапан + направляющие + цепь + поплавки + ШУ + корпус)
3. **JSON-payload для CRM** — структура `calc_id, manager, client, inputs_L0/L1, computed, primary_selection, artifacts, status`

**SLA:** менеджер сделал L0 → автоотправка → инженер должен ответить за 24-72 ч → менеджер видит статус.

---

## 5. Dataset (Single Source of Truth)

Все коэффициенты, формулы и БД — в [`02_dataset/`](02_dataset/).

### Структура
```
02_dataset/
├── README.md
├── ENGINEER_NOTES.md          ← 23 NOT_OK + закрытые GAP + 11 пробелов
├── theory/
│   ├── formulas.md            ← 14 разделов с метками ✅⚠️❌
│   ├── coefficients.json      ← 27 топ-секций (k_э, ζ, K_gen, скорости, гидроудар, AOR/POR, и т.д.)
│   ├── reliability_categories.md
│   └── dependencies_map.md    ← 37 DEP связей + 13 слоёв + граф
├── pumps/
│   ├── schema.json            ← JSON-schema записи насоса
│   ├── pumps.json             ← 14 насосов envelope-only
│   ├── producers.json         ← 8 брендов (KAIQUAN, Antarus, LEO, Aquario/Belamos/Unipump, Grundfos, Wilo, KSB, Pedrollo)
│   └── seed_kaiquan_50WQS202.json  ← эталон верификации
└── fittings/
    └── fittings_seed.json     ← обвязка КНС/СПД с типовыми ценами 2026
```

### Ключевые таблицы coefficients.json
- `pipe_roughness_mm` — k_э для 11 типов труб
- `local_resistance_zeta` — точные значения Идельчика (отвод 90° R/D=1.5 = 0.21)
- `K_gen_max` / `K_gen_min` — таблица СП 32 §5.1
- `velocity_limits_ms` — СП 32 §5.4 (v_max metal=8, plastic=4)
- `wave_speed_ms_by_pipe_material` — для гидроудара
- `pn_by_sdr_pe100` — PN = 160/(SDR-1) бар
- `redundancy_table_sp32_t17` — реконструированная таблица 17
- `hi_976_viscosity_correction` — для промстоков
- `ansi_hi_963_operating_regions` — POR/AOR
- `motor_starting_method_by_power` — DOL/SS/VFD выбор
- `motor_protection_required` — PTC/PT100/phase_monitor

---

## 6. Зависимости и анти-паттерны

Полная карта — [`02_dataset/theory/dependencies_map.md`](02_dataset/theory/dependencies_map.md).

**13 слоёв, 37 DEP связей.** Каждая связь снабжена антипаттерном и проверкой.

### 23 решения, КОТОРЫЕ НЕ РАБОТАЮТ

Все в [`02_dataset/ENGINEER_NOTES.md`](02_dataset/ENGINEER_NOTES.md). Топ-10 для memorize:

1. ❌ Aquario/Belamos/Unipump для промышленных КНС
2. ❌ Cutter (измельчитель) для гостиниц/ТРЦ
3. ❌ Чугун для напорной канализации (default)
4. ❌ NPSH-расчёт пропускают для T>40°C даже у погружных
5. ❌ Запас по напору 5%
6. ❌ Подбор по нижнему пределу диапазона производителя
7. ❌ «Q одного × N = Q общий» (реально 1.6× для 2 насосов)
8. ❌ ПЭ100 SDR17 PN10 для L>500 м без расчёта гидроудара
9. ❌ Прямой пуск (DOL) >7.5 кВт
10. ❌ ПЭ-корпус с УГВ выше дна без anchoring SF≥1.25

---

## 7. Стек реализации

| Слой | Технология | Лицензия | Откуда |
|---|---|---|---|
| Гидравлика (формулы) | [`CalebBell/fluids`](https://github.com/CalebBell/fluids) | MIT | `pip install fluids` |
| Backend API | FastAPI | MIT | — |
| Валидация | Pydantic | MIT | — |
| БД | SQLite + JSON catalog | — | свой |
| Frontend | React/Next.js + Zustand + Zod | MIT | — |
| PDF generator | reportlab / weasyprint | LGPL/MPL | для опросника |
| ETL парсер каталогов | [`docling-project/docling`](https://github.com/docling-project/docling) + [`dilawar/PlotDigitizer`](https://github.com/dilawar/PlotDigitizer) | MIT | для Q-H кривых |
| Multi-agent (опц.) | Anthropic SDK + LangGraph | MIT | для Coordinator |
| Grundfos integration | apiexplorer.grundfos.com | API | live-данные |

---

## 8. Roadmap

| Фаза | Что | Статус |
|---|---|---|
| 0. Research | Web + локальный аудит + datasets | ✅ |
| 1. Specification | Inputs / Matching / Hand-off / Dependencies / NOT_OK | ✅ |
| 2. Backend MVP | FastAPI + fluids + JSON-БД | ⬜ |
| 3. Frontend MVP | React Wizard L0 (4 поля) | ⬜ |
| 4. PDF Generator | hand-off артефакты | ⬜ |
| 5. ETL парсер | docling+PlotDigitizer для PDF-каталогов | ⬜ |
| 6. Multi-agent | Coordinator → Hydro/Catalog/Engineer/Docs (LangGraph) | ⬜ |
| 7. UI Pro mode | Полный опросник L2 для инженеров | ⬜ |
| 8. CRM integration | Bitrix/amoCRM/собственный | ⬜ |

---

## 9. Открытые вопросы (для следующих итераций)

1. ⚠️ **Точные Q-H кривые** для всех насосов в БД (сейчас envelope-only)
2. ⚠️ **Полная А.2 СП 30** (50+ строк потребителей)
3. ⚠️ **Дословные тела таблиц 16, 17, А.2** — OCR локального PDF
4. ⚠️ **Корпуса КНС Серво-Юг** — модельный ряд D × H + актуальные цены
5. ⚠️ **Цены 2026 на обвязку** у 3-5 разных поставщиков (сейчас только АРКАДА)
6. ⚠️ **Доступность Grundfos/Wilo/KSB на 2026** — статус параллельного импорта
7. ⚠️ **Целевая CRM** — Bitrix/amoCRM/Inservo registry
8. ⚠️ **Локализация** ru/uz (для персоны сварщика)

Все детали — в `ENGINEER_NOTES.md::GAP`.

---

**Эта спецификация — единый source of truth для разработчика. Все вопросы → README.md → ARCHITECTURE.md → этот файл → детальные spec в `01_spec/`.**
