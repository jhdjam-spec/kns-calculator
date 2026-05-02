# GitHub-аналоги калькулятора подбора насосов (КНС / НС / СПД)

## Дата: 2026-05-02
## Использовано запросов: 13 / 18

---

## Сводная таблица топ-N

| # | Repo | Звёзды | Stack | Лицензия | Релевантность | Что взять |
|---|------|--------|-------|----------|---------------|-----------|
| 1 | [CalebBell/fluids](https://github.com/CalebBell/fluids) | 431 | Python 3.9+ | MIT | ⭐⭐⭐⭐⭐ | Целиком как hydraulics-engine: friction, fittings, NPSH, piping, pumps |
| 2 | [OpenWaterAnalytics/EPyT](https://github.com/OpenWaterAnalytics/EPyT) | 72 | Python + EPANET | EUPL-1.2 | ⭐⭐⭐⭐ | Pump curves, energy, lift station controls. Лицензия — копилефт, осторожно |
| 3 | [dmgsantos/WaterPy](https://github.com/dmgsantos/WaterPy) | 15 | Python | не указана | ⭐⭐⭐⭐ | `EQ_pumpstation_npshr()`, `EQ_pumpstation_p()`, friction loss — формулы для КНС |
| 4 | [ddjokic/Pump-Calculation](https://github.com/ddjokic/Pump-Calculation) | 5 | Python | есть LICENSE | ⭐⭐⭐⭐ | Парабольная регрессия Q-H по 3+ точкам, NPSHa, viscosity correction (HI standards) |
| 5 | [ddjokic/HydraulicCalcsToolbox](https://github.com/ddjokic/HydraulicCalcsToolbox) | 1 | Python | GPL-2.0 | ⭐⭐⭐ | Network solver, Darcy-Weisbach, balancing — только идеи (GPL заразен) |
| 6 | [amirsadafi/Pump_Sizing_Selection](https://github.com/amirsadafi/Pump_Sizing_Selection) | 1 | Jupyter | MIT | ⭐⭐⭐ | Дерево решений типа насоса по flow/pressure — идея для Wizard |
| 7 | [fpoposki/Mechanical-Engineering-Based-Code-Python](https://github.com/fpoposki/Mechanical-Engineering-Based-Code-Python) | — | Python (numpy/scipy/matplotlib) | — | ⭐⭐⭐ | Q-H curve + similarity laws (пересчёт RPM) |
| 8 | [USEPA/epanet-solver](https://github.com/USEPA/epanet-solver) | — | C / C-API | MIT | ⭐⭐⭐ | Источник истины для гидравлики; через EPyT |
| 9 | [oopnet/oopnet](https://github.com/oopnet/oopnet) | — | Python | — | ⭐⭐ | OO-обёртка над EPANET с Pythonic API |
| 10 | [dilawar/PlotDigitizer](https://github.com/dilawar/PlotDigitizer) | — | Python | — | ⭐⭐⭐ | Оцифровка Q-H кривых из PDF/png в CSV (батч-режим) |
| 11 | [pliolios/curvedigitizer](https://github.com/pliolios/curvedigitizer) | — | Python | — | ⭐⭐ | Альтернатива plot digitizer |
| 12 | [docling-project/docling](https://github.com/docling-project/docling) | — | Python | MIT | ⭐⭐⭐ | Парсинг PDF (layout, таблицы) — для каталогов KAIQUAN/Pedrollo |
| 13 | [eduardo-jh/hydrx](https://github.com/eduardo-jh/hydrx) | — | Python | — | ⭐⭐ | Hydraulics+hydrology library, маленькая |
| 14 | [EdM44/hydraulics](https://github.com/EdM44/hydraulics) | — | R | — | ⭐⭐ | Pump-vs-system curve matching, Hardy-Cross — только формулы |

---

## 1. Прямые аналоги (калькуляторы насосов)

### CalebBell/fluids — главный кандидат на базу
- URL: https://github.com/CalebBell/fluids
- 431⭐ / 86 forks / последний релиз v1.3.0 — окт 2025 / **MIT**
- Stack: Python 3.9+, PyPy, Numba-acceleration, ~4 MB RAM, грузится за 20 мс
- Что делает: библиотека ChEDL с модулями `pumps`, `friction`, `fittings`, `piping`, `compressible`, `two_phase`, `control_valves`, `flow_meters`, `open_flow`, `atmosphere`. Покрывает **>90% инженерных формул**, нужных для КНС.
- Что взять: **целиком в зависимости** (`pip install fluids`). Использовать как backend-движок гидравлики. На фронте — только UI и логика подбора.
- UX: библиотека, без UI.
- Релевантность: ⭐⭐⭐⭐⭐

### OpenWaterAnalytics/EPyT
- URL: https://github.com/OpenWaterAnalytics/EPyT
- 72⭐ / 35 forks / 18 релизов / последний релиз фев 2026 / **EUPL-1.2** (копилефт-light, совместим с MIT при оговорках)
- Stack: Python + EPANET C-engine, Jupyter notebooks с примерами
- Что делает: Pythonic-обёртка над EPANET 2.2 — pump curves, эффективность, energy patterns, valve controls (PRV/PCV/FCV), правила управления.
- Что взять: код моделирования pump curve как функции `(Q, H, η)`, схема описания насосной станции, методология симуляции работы КНС с уровнями в резервуарах.
- **Важно:** EUPL — копилефт. Если линковать целиком, ваш продукт может попасть под её условия. Лучше брать идеи и переписывать.
- Релевантность: ⭐⭐⭐⭐

### dmgsantos/WaterPy
- URL: https://github.com/dmgsantos/WaterPy
- 15⭐ / 3 forks / Python / лицензия не указана (риск!)
- 11 модулей: Bioreactor, Equipment (`EQ_pumpstation_npshr`, `EQ_pumpstation_p`), Hydrology, PorousMediaFlow, UniformPressurizedFlow, и т.д.
- Что взять: **формулы NPSHr и мощности насосной станции** напрямую. Без лицензии — только как референс, не копировать.
- Релевантность: ⭐⭐⭐⭐

### ddjokic/Pump-Calculation
- URL: https://github.com/ddjokic/Pump-Calculation
- 5⭐ / 5 forks / Python / есть LICENSE (надо проверить тип)
- Что делает: shaft power (η=0.6 по умолчанию), NPSHa и cavitation analysis, парабольная аппроксимация Q-H по 3+ точкам, **viscosity correction по Hydraulic Institute standards** (это редкая фича!).
- Что взять: алгоритм viscosity correction (для перекачки сточных вод важно), парабольный фит Q-H (точно нужен для импорта данных каталогов).
- Релевантность: ⭐⭐⭐⭐

### amirsadafi/Pump_Sizing_Selection
- URL: https://github.com/amirsadafi/Pump_Sizing_Selection
- 1⭐ / Jupyter / **MIT**
- CLI / notebook, дерево решений: flow rate (GPM) → pressure → particulates → self-priming → тип насоса.
- Что взять: **только структуру decision-tree** для Wizard-режима. Реализация очень простая, но как UX-схема — годится.
- Релевантность: ⭐⭐⭐ (как UX-эскиз Wizard'а)

### RoshniGN/SelectorPro
- URL: https://github.com/RoshniGN/SelectorPro
- 0⭐ / 1 commit / без README / **мёртвый**
- Релевантность: ⭐ — пропустить.

---

## 2. Гидравлические библиотеки (формулы)

Помимо `fluids`:

### ddjokic/HydraulicCalcsToolbox
- URL: https://github.com/ddjokic/HydraulicCalcsToolbox
- 1⭐ / Python / **GPL-2.0** ⚠️ (заразный копилефт — нельзя в коммерческий продукт без открытия исходников)
- Darcy-Weisbach, network solver, орифисы, балансировка.
- Что взять: **только идеи и формулы**, переписывать с нуля.
- Помечен «work in progress, experimental».
- Релевантность: ⭐⭐⭐ для теории, ⭐ для прямой интеграции.

### DrTol/pressure_loss_calculator-Python
- URL: https://github.com/DrTol/pressure_loss_calculator-Python
- Friction loss по Darcy-Weisbach, Clamond-алгоритм для friction factor.
- Что взять: эталонная реализация Clamond — но в `fluids` уже есть.
- Релевантность: ⭐⭐

### USEPA/epanet-solver
- URL: https://github.com/USEPA/epanet-solver / **MIT** / C
- Эталонный движок водных сетей. Через EPyT/oopnet — Python-доступ.
- Релевантность: ⭐⭐⭐ как «истина в последней инстанции».

### eduardo-jh/hydrx, EdM44/hydraulics (R)
- Маленькие библиотеки. R-пакет содержит Hardy-Cross и matching pump curve to system curve.
- Релевантность: ⭐⭐ — формулы для подсмотреть.

---

## 3. Парсеры PDF / Q-H кривых

**Готового парсера PDF-каталогов насосов на GitHub НЕ СУЩЕСТВУЕТ.** Есть только общие инструменты:

### docling-project/docling
- URL: https://github.com/docling-project/docling
- **MIT**, активный, понимает page layout, reading order, таблицы.
- Что взять: **парсер PDF-каталогов KAIQUAN / Wilo / Grundfos / Pedrollo / Antarus** для извлечения таблиц с моделями, габаритами, мощностями.
- Релевантность: ⭐⭐⭐⭐ для пайплайна импорта каталогов.

### dilawar/PlotDigitizer и pliolios/curvedigitizer
- Оцифровка Q-H кривых со сканов / скриншотов в CSV.
- `PlotDigitizer` — батч-режим (ценно при массовой оцифровке каталога), `curvedigitizer` — простой.
- Что взять: для **полу-автоматического сбора Q-H кривых из PDF-каталогов**. Один раз отработать пайплайн → накопить датасет.
- Релевантность: ⭐⭐⭐

### pdfplumber, py-pdf-parser, pdfminer.six
- Стандартный набор для табличных данных из PDF. Если каталог имеет машинно-читаемые таблицы — берём pdfplumber. Если только картинки — нужен docling + plot digitizer.

---

## 4. Архитектура двухрежимных (Wizard + Pro) калькуляторов

**Прямого open-source аналога с двумя режимами для насосов НЕ НАШЁЛ.** Все найденные «engineering calculators» в React — простые scientific/арифметические.

### Что есть как идейный референс:
- amirsadafi/Pump_Sizing_Selection — линейный wizard (flowchart)
- una/custom-calculator — multi-variable engineering calculator (структура полей)

### Вывод: придётся проектировать UX с нуля
Из соседних доменов (HVAC, котлы, OBC) тоже **готового двухрежимного open-source калькулятора не нашлось**. Это пробел рынка — и одновременно ваше конкурентное преимущество.

Подсказки для архитектуры:
- Wizard = stepper (formik/react-hook-form + zod, multi-step form)
- Pro = inspector-вью с раскрытыми группами (как Blender / Figma side-panel)
- Между режимами — единая схема параметров (Single Source Of Truth, например JSON-Schema, в Pro показываем все поля, в Wizard — фильтрованный субсет)

---

## 5. БД насосов (датасеты)

**Открытых датасетов промышленных насосов (КНС / СПД) на GitHub нет.**

Что есть:
- **FZJ-IEK3-VSA/hplib** (https://github.com/FZJ-IEK3-VSA/hplib) — это **тепловые насосы** (Heat Pumps) из Keymark базы EU. Не наш домен, но архитектура CSV (`hplib_database.csv`) — хороший шаблон схемы.
- **smart-data-models/dataModel.WaterDistributionManagementEPANET** — модель данных насоса в EPANET-формате. Подсмотреть структуру JSON-описания насоса.
- **modelica-3rdparty/WasteWater** — Modelica-модели очистных, не насосов как таковых.

### Вывод: БД насосов придётся **строить с нуля**
Источник — PDF-каталоги производителей (KAIQUAN, Wilo, Grundfos, Pedrollo, Antarus), парсинг через docling + plot digitizer для Q-H. Это самостоятельный подпроект.

---

## 6. Мёртвые / нерелевантные (одной строкой)

- `RoshniGN/SelectorPro` — 0⭐, 1 коммит, README ошибка — мёртв
- `tormec/SimpleCentrifugalPump` — параметрический CFD импеллера, не подбор
- `arda-guler/ChatGPT-Does-Engineering` — учебный одноразовый скрипт
- `sommaa/pump_modeling`, `shreeshkarjagi/Fluid-Flow-Simulation-...` — OpenFOAM CFD, не наша задача
- `20jeka08/PyPump` — **репозиторий disabled GitHub Staff** (нарушение TOS), недоступен
- `dbdespot/pysewer` — генератор канализационных сетей (полезно для вышестоящего ТЗ, но не для подбора насоса)
- `mathworks/Simscape-Triplex-Pump` — predictive maintenance, не подбор
- `githubwateruse/RTC_WDNs` — RL-планирование расписания насосов, исследовательский
- `ClarkLabUCB/NewEraPumps_Python3`, `gunakkoc/HiPeristaltic` — лабораторные перистальтические/шприцевые, не наш профиль
- `openenergymonitor/tools`, `jlfwong/hvac-sim-app` — heat pumps, другой домен
- `samadritakarmakar/LiquiNet` — FEM-решатель сетей, более тяжёлый чем EPANET, исследовательский
- `pav2000/ControlHP`, `vad7/ControlHeatPump` — контроллеры тепловых насосов на МК, не наша тема
- `Soljourner/claude-engineering-skills` — это **набор Claude-skills**, не пайплайн калькулятора. Может пригодиться как inspiration для архитектуры агентов.

---

## 7. РЕКОМЕНДАЦИИ ДЛЯ КАЛЬКУЛЯТОРА КНС

### Брать целиком (как зависимости в backend)
1. **`CalebBell/fluids`** (MIT) — основной hydraulics-engine. Покрывает friction, fittings, NPSH, piping, two-phase, pumps. Это ядро всех гидравлических расчётов.
2. **`pdfplumber` / `docling`** (MIT) — пайплайн импорта PDF-каталогов производителей.
3. **`dilawar/PlotDigitizer`** — однократный инструмент инженера для оцифровки Q-H графиков.

### Брать как референс (формулы, идеи, переписать)
4. **`ddjokic/Pump-Calculation`** — алгоритм viscosity correction (для сточных вод важно), парабольная регрессия Q-H по 3 точкам.
5. **`dmgsantos/WaterPy`** — конкретные формулы NPSHr и power для pumping station (без лицензии — только идеи).
6. **`amirsadafi/Pump_Sizing_Selection`** — структура decision-tree для Wizard-режима.
7. **`OpenWaterAnalytics/EPyT`** — методология описания pump curve и моделирования работы КНС (учитывая EUPL — переписать под себя).

### Опционально, если делаем «гидравлический симулятор сети»
8. **`USEPA/epanet-solver`** + **`oopnet/oopnet`** — для «расширенного режима» с моделированием работы насоса в сети, графиком включений, объёмом резервуара.

### Писать с нуля (рынок пуст)
- **БД насосов** (КНС/СПД, ru/uz сегмент): KAIQUAN, Antarus, Pedrollo, Wilo, Grundfos. Источник — PDF-каталоги. Схема — JSON-Schema или PostgreSQL JSONB.
- **Двухрежимный UX** Wizard + Pro: open-source аналогов не нашлось, проектируем сами на основе принципа Single Source Of Truth для параметров.
- **Бизнес-логика подбора** для российских/узбекских реалий: ГОСТ Р, СП 32.13330, СНиП — формулы похожи на западные, но коэффициенты и подход другой.
- **i18n ru/uz** + **UX для сварщика** (см. `user_persona_welder.md`) — нет аналогов.

### Архитектурный вывод
Готов **движок гидравлики** (`fluids`, ~80% формул бесплатно). Готовы **парсеры PDF** (отдельные кубики). **Нет ничего готового** для:
- БД насосов отечественного / узбекского сегмента
- Двухрежимного UI Wizard/Pro
- Алгоритма ранжирования подходящих моделей под входные условия
- UX-логики, считывающей реалии стройплощадки (вода, грязь, перчатки)

Это и есть фронт работ для проекта `Калькулятор КНС`.
