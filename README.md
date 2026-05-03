# kns-calculator

> **Открытый калькулятор первичного подбора насосов для КНС / НС / станций повышения давления (СПД)**

Менеджер отдела продаж вводит **3 числа + 1 кнопку** (расход, перепад точек, длина трассы, тип стоков) — получает топ-3 насоса в трёх ценовых сегментах (Бюджет / Средний / Премиум) и пакет документов для передачи инженеру на полный расчёт.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: WIP](https://img.shields.io/badge/Status-WIP-yellow.svg)](#)

---

## Зачем это нужно

В русскоязычной отрасли подбора КНС и СПД нет открытого калькулятора с двумя режимами (Wizard + Pro) и нейтральной мульти-брендовой базой:
- **Grundfos Product Center** — закрыт (регистрация), привязан к одному вендору
- **Wilo-Select / KSB EasySelect** — то же самое
- **На GitHub** — нет ни одного активного аналога (проверено в `00_research/github_analogs.md`)

Этот проект закрывает пробел: открытый код, открытая методология, открытая база производителей, MIT-лицензия — можно форкать и встраивать.

## Кому полезно

- Менеджерам отдела продаж насосного оборудования (первичная оценка за 30 секунд)
- Инженерам-проектировщикам (готовый PDF-опросник клиенту)
- Дилерам / поставщикам (BOM-черновик для трёх ценовых сценариев)
- Разработчикам, кому нужен датасет насосов и формулы гидравлики в JSON

## Что в репозитории

```
kns-calculator/
├── 00_research/             — Web-research: теория, нормы РФ, конкуренты-калькуляторы,
│                              GitHub-аналоги, MCP/API производителей, UI-референсы
├── 01_spec/                 — Спецификации калькулятора (Inputs, Matching, Hand-off)
├── 02_dataset/              — Машинно-читаемый датасет для движка
│   ├── theory/              — Формулы и коэффициенты (k_э, ζ, K_gen, скорости, нормы расхода)
│   ├── pumps/               — JSON-схема насоса + БД envelope-only по 8 брендам
│   └── fittings/            — Обвязка КНС/СПД с типовыми ценами 2026
├── docs/                    — Архитектура, гайдлайны контрибьюторам
└── ENGINEER_NOTES.md (внутри 02_dataset/) — пометки «работает / не работает / нужна проверка»
```

## Состояние проекта (2026-05-03)

| Этап | Статус |
|---|---|
| Исследование рынка и норм РФ | ✅ |
| Датасет 8 производителей (Grundfos, Wilo, KSB, KAIQUAN, Antarus, LEO, Pedrollo, Aquario/Belamos/Unipump) | ✅ |
| Теория расчётов с инженерными пометками | ✅ |
| JSON-схема насоса + 14 seed-записей | ✅ |
| Тестовый кейс из реального проекта (АртВинд Мысхако, KAIQUAN 50WQ/S 20-22-3) | ✅ |
| Спецификация Inputs (L0/L1/L2 + Zod) | ✅ |
| Спецификация алгоритма матчинга | ✅ |
| Спецификация hand-off пакета (PDF + BOM + JSON для CRM) | ✅ |
| Deep research: нормы РФ + гидравлика + анти-паттерны | ✅ |
| **Backend MVP (Python + FastAPI + fluids)** | ✅ **59/59 тестов** |
| **Frontend MVP (Next.js 14 + Tailwind + Zod)** | ✅ **30/30 тестов** |
| **Калькуляторы ёмкостей (ПП, корпус КНС)** | ✅ модель из ODS Серво-Юг |
| **PDF hand-off (опросник клиенту + BOM-черновик)** | ✅ reportlab, кириллица |
| **ETL: Q-H curve fitter + importer + CLI** | ✅ параболическая регрессия, BEP-detection |
| Парсинг PDF-каталогов производителей (docling) | ⬜ Phase 5.1 |
| Multi-agent оркестрация (LangGraph) | ⬜ Phase 6 |

## Быстрый старт

### Backend (FastAPI на :8000)

```bash
cd backend
pip install -e ".[dev]"
pytest                                              # 27/27 ✅
uvicorn pump_calculator.api:app --reload --port 8000
# Open http://localhost:8000/docs
```

### Frontend (Next.js на :3000)

```bash
cd frontend
npm install
npm test                                            # 30/30 ✅
npm run dev
# Open http://localhost:3000 (подбор насоса)
# Open http://localhost:3000/tanks (калькуляторы ёмкостей)
```

Тестовый кейс (без претензии на «эталон»): вход Q=21.2 м³/ч, ΔH=10 м, L=0, тип=domestic → возвращает **KAIQUAN 50WQ/S 20-22-3** — этот насос фигурирует в реальном проекте АртВинд Мысхако. Это smoke-проверка, что алгоритм даёт разумный результат на типовом случае; не доказательство «правильности» подбора.

```python
from pump_calculator import select_pumps
from pump_calculator.schemas import L0Input

result = select_pumps(L0Input(Q_m3h=21.2, dH_m=10, L_m=0, wastewater_type="domestic"))
print(result.results.budget.brand, result.results.budget.model)
# → KAIQUAN 50WQ/S 20-22-3
```

## Архитектура (high-level)

```
ВХОД (3 поля + 1 радио)              ┌──────────────────────────┐
  Q  — расход                        │  ВЫХОД                   │
  ΔH — перепад точек            ───▶ │  • Бюджет (KAIQUAN/LEO)  │
  L  — длина трассы                  │  • Средний (Antarus/Ped) │
  тип стоков (хоз-быт/др/пром)       │  • Премиум (Wilo/Grundf) │
                                     │  + опросник клиенту PDF  │
                                     │  + BOM-черновик          │
                                     │  + JSON-payload для CRM  │
                                     └──────────────────────────┘
```

Подробнее — в [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Технологии

- **Backend (план):** Python 3.12 + FastAPI + [`CalebBell/fluids`](https://github.com/CalebBell/fluids) для гидравлики
- **Frontend (план):** React/Next.js + Zustand + Zod
- **БД (план):** SQLite/JSON для каталога насосов
- **Парсинг PDF (план):** [`docling-project/docling`](https://github.com/docling-project/docling) + [`dilawar/PlotDigitizer`](https://github.com/dilawar/PlotDigitizer)
- **AI-агенты (план):** Anthropic SDK с prompt caching, мульти-агентная оркестрация

Полное обоснование выбора — [`00_research/github_analogs.md`](00_research/github_analogs.md).

## Использование датасета (предварительно)

Датасет готов к импорту даже без backend:

```python
import json

# Загрузить производителей
producers = json.load(open("02_dataset/pumps/producers.json"))

# Коэффициенты
coeffs = json.load(open("02_dataset/theory/coefficients.json"))

# Насосы (envelope)
pumps = json.load(open("02_dataset/pumps/pumps.json"))

# Простейший фильтр Q-H
def match(Q_user_m3h, H_user_m, type_):
    return [
        p for p in pumps["pumps"]
        if p["envelope"]["Q_min_m3h"] <= Q_user_m3h <= p["envelope"]["Q_max_m3h"]
        and p["envelope"]["H_min_m"]  <= H_user_m  <= p["envelope"]["H_max_m"]
        and type_ in p["wastewater_compat"]
    ]
```

## Нормативная база

Все расчёты опираются на действующие СП РФ:
- **СП 32.13330.2018** «Канализация. Наружные сети и сооружения»
- **СП 31.13330.2012** «Водоснабжение. Наружные сети» (формулы напорных коллекторов)
- **СП 30.13330.2020** «Внутренний водопровод и канализация» (нормы расхода)
- **ГОСТ Р 53682** «Насосы для сточных вод»

Тексты норм **в репозитории не воспроизводятся** — только ссылки на первоисточники. См. [`00_research/norms.md`](00_research/norms.md).

## Известные ограничения

В [`02_dataset/ENGINEER_NOTES.md`](02_dataset/ENGINEER_NOTES.md) собраны:
- 11 решений, которые **не работают** для нашего сегмента (с обоснованием)
- 10 мест, требующих **проверки** (косвенные источники)
- 11 **пробелов** (что нужно собрать в следующих итерациях)
- 10 **проверенных** формул и данных

Это критично для контрибьюторов: прежде чем дополнять датасет — прочитать ENGINEER_NOTES.

## Как помочь

Открыты к контрибьюциям. Особенно нужны:
1. **Парсинг Q-H кривых** из PDF-каталогов производителей (KAIQUAN, Antarus, Wilo, Grundfos, KSB, Pedrollo, LEO)
2. **OCR таблиц 16/17 СП 32** (категории + резервирование) — есть локальный PDF, нужен парсер
3. **Полная А.2 СП 30** (нормы расхода — 50+ строк потребителей)
4. **Корпуса КНС** — модельные ряды российских производителей (Серво-Юг, Блорэй BloPlast, ВК-ТОН)
5. **UI / Frontend** — двухрежимный интерфейс Wizard+Pro

Подробнее — [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).

Можно использовать в коммерческих проектах при условии сохранения копирайта.

## Контакты

Issues и pull requests — через GitHub.

---

**Стартовая дата:** 2026-05-02
**Текущая фаза:** Research → Specification (далее: Implementation)
