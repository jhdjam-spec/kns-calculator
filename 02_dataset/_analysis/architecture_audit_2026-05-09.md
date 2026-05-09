# Аудит целостности kns-calculator

Дата: 2026-05-09
Аудитор: Claude (Opus 4.7) автономный архитектурный анализ
Объём: backend/pump_calculator/* (91 .py), frontend/src/* (~70 .tsx), api/index.py, vercel.json
Метод: read-only Glob/Grep/Read; никаких прогонов кода и изменений

---

## 1. Резюме (TL;DR)

**Главные находки (в порядке убывания критичности).**

1. **Регистр нормативов (`regulations.py`) фактически НЕ используется большинством модулей.** Из 17+ расчётных модулей `ref()` вызывают только `physics_advanced.py` и `fire_water/scenario.py`. Остальные (climate, los, structural, water_supply, storm, sprinklers, ladder, ballast и т.д.) **дублируют коды и URL норм как сырые dict'ы**. Нарушает заявленный принцип «обновил норматив — обновился весь код». Это самая массовая системная проблема (≥30 hardcoded ссылок).

2. **Visionный «3-режимный» UX сильно неполон.**
   - **Минимальный** существует только для ливнёвки (`/storm/minimal`). Для КНС/ВНС/ЛОС — нет.
   - **Классический** = Hero-форма + 4-шаговый wizard `/project`, но wizard принимает 11 полей вместо 60.
   - **Продвинутый** = checkbox «Расширенные параметры» в Hero/CalculatorPanel открывает только `dH/L/corpus_material`. До 150+ полей с переопределением коэффициентов — **близко к нулю**.

3. **`/project/calculate` — оркестратор, который ломает логику для половины пресетов.**
   - В `_calc_kns_subsystem` Q всегда вычисляется как `population × 0.25 / 24 × 2.5` и `wastewater_type` всегда `"domestic"` — для АЗС, ТРЦ, гостиниц, складов, промышленности это даст бессмысленные числа.
   - В `_calc_water_subsystem` для `preset="hospital"` building_type становится `"hospital"` (unit=койка), но `inputs.beds=0` (поле в `ProjectInput` отсутствует) → backend падает с ValueError.
   - Подсистема `electrical=True` в пресете → но в orchestrator **нет функции** `_calc_electrical_subsystem`. Чекбокс работает, но возвращается всегда `None`.
   - Подсистема `storm` в orchestrator явно пропущена комментарием `# storm — пока пропускаем`.
   - Поле `area_m2` в `ProjectInput` есть, в UI заполняется, но никаким `_calc_*_subsystem` не используется.

4. **Вся выходная BOM Проекта — заглушка с магическими ценами.** `frontend/src/components/project/ProjectStepResults.tsx:42-141` функция `buildBomFromProject` использует hardcoded цены 50 000, 300 000, 75 000, 120 000, 400 000, 100 000 ₽ независимо от подобранного насоса/корпуса. `pricing.py` и `pricing_glass.py` (вся логика BOM с диапазонами low/high и confidence) **выкидывается** в pipeline Проекта — её результаты до UI не доходят.

5. **Vercel-деплой работает только как статический фронт без backend.**
   - `vercel.json` НЕ содержит rewrites `/api/*` → `api/index.py`.
   - `next.config.mjs` отключает rewrites при `process.env.VERCEL`.
   - `api/index.py` существует, но мёртвый код.
   - `frontend/src/components/storm/minimal/StormMinimalForm.tsx:86` зовёт `/api/storm/calc` (без префикса `backend`) — ошибка пути даже в dev.

**Менее критичные, но требующие внимания:**

6. Технические утечки в UI: `02_dataset/tanks/tank_calculator_models.json` отображается на `/tanks` (`HorizontalTankForm.tsx:195`) — пользователь видит внутренний путь.
7. Оставшиеся осиротевшие компоненты: `HandoffPanel.tsx`, `QuizUploader.tsx`, `WizardL0.tsx`, `ResultsCards.tsx` — не импортируются в production-роутах, остались с Phase 4–6.
8. Преамбула CalculatorPanel показывает `Q расчётный` через `result.computed?.H_full_m` (опечатка переменной — выводится H в графе Q).
9. Двойной learning-источник: `regulations.py` (registry) и `encyclopedia/registry.py` (`RegulationFull`) дублируют названия норм. Третий источник — hardcoded строки в каждом модуле.
10. Имена `physics.py` и `physics_advanced.py` пересекаются по NPSH/density/viscosity. Переезд в namespace `physics/` (как `climate/`, `electrical/`) уменьшит путаницу.

**Главная рекомендация: переход с «много карточек = много фич» к «единый pipeline → корректные модули».** Сейчас в репозитории много готовых модулей (electrical, complexes, los aerotank, structural seismic, sprinklers и т.д.), которые покрыты тестами, **но не подключены ни к UI, ни к Project orchestrator'у**. Закрыть эти провалы важнее, чем добавлять новые расчёты.

---

## 2. Архитектура backend

### 2.1 Граф зависимостей модулей

Строгая нижняя граница (Layer 0):
- `schemas.py` — Pydantic-модели L0/L1 + результат
- `catalog.py` — загрузка JSON-датасета (pumps, fittings, coefficients)
- `regulations.py` — реестр норм + `ref()` хелпер
- `physics.py`, `physics_advanced.py` — физика (плотность, NPSH, гидроудар, Дарси)
- `phase15.py` — формулы §15 (V_min, Specific Speed, S/D, NPSH margin, v_min)
- `corpus_sizing.py` — геометрия корпуса
- `pricing_glass.py` — расчёт стоимости стеклопластикового корпуса

Среднее (Layer 1, расчётные подсистемы):
- `hydraulics.py` (использует catalog, schemas)
- `pricing.py` (использует catalog, pricing_glass, schemas)
- `forecast.py` (использует schemas, чистые функции)
- `matching.py` (Layer 1 главный — использует hydraulics, pricing, phase15, forecast, schemas)
- `storm/*` (peak_flow, design, annual, surfaces, regions; нет внешних зависимостей кроме models)
- `fire_water/*` (external, internal, sprinklers, scenario, reservoir, pump_station; **scenario.py** правильно использует `ref()`)
- `water_supply/*` (demand, alpha_coefficients, station)
- `electrical/*` (motor, cable, protection, control_panel, short_circuit) — **standalone**
- `climate/*` (frost, loads) — **standalone**
- `structural/*` (ballast, ladder, wall_thickness, seismic) — **standalone**
- `los/*` (selection, aerotank, composition)
- `bom/builder.py`, `bom/export.py`
- `complexes/summary.py`
- `reports/calculation_report.py`
- `encyclopedia/registry.py`

Высокий уровень (Layer 2):
- `project/orchestrator.py` — связывает большинство Layer 1 модулей через одну входную модель `ProjectInput`
- `api.py` — FastAPI-роутер с lazy-импортами

ETL и handoff — отдельные стеки:
- `handoff/*` — DOCX/PDF + парсер опросника, lazy-импорт reportlab/python-docx/lxml
- `etl/*` — обработка PDF паспортов насосов (curve_fitter, importer, pipeline, pdf-parsers)

**Циклов и обратных зависимостей нет — это здорово.** Но есть много случаев, когда Layer 1 сам перепрашивает данные из Layer 0 (orchestrator вызывает `select_pumps`, который сам вызывает `compute_hydraulics`, который сам вызывает `catalog.load_coefficients`) — в общем-то, нормально.

### 2.2 Дублирование и пересечения

**Дубль 1: Регистр норм vs hardcoded ссылки.** Главная находка аудита (см. 2.3 и 1.1).

**Дубль 2: `physics.py` vs `physics_advanced.py`.** Оба имеют NPSH-функции (`physics.npsh_available_m_simple` vs `physics_advanced.npsha_with_corrections`), оба считают вязкость и плотность. `physics_advanced` импортирует из `physics`. Нужен единый namespace `physics/` с подмодулями.

**Дубль 3: BOM через два пайплайна.**
- В `matching.py` → `pricing.py` → возвращается `PriceBreakdown` со всеми позициями и `total_low_rub`/`total_high_rub`/`confidence`.
- В Project flow `frontend/src/components/project/ProjectStepResults.tsx:buildBomFromProject` собирает свою BOM с **hardcoded** ценами и **игнорирует `kns.data.selection.results.X.price_breakdown`**.

В backend: `bom/builder.py` (BOMSpecification) — отдельная модель, не пересекается с `pricing.PriceBreakdown`.

**Дубль 4: Расчёт стеклопластикового корпуса.**
- `pricing_glass.py` (Python) — материалоёмкость по слоям, цены сырья.
- `frontend/src/lib/tankFormulas.ts` — независимая JS-реализация для `/tanks` (KnsCorpusForm).
Используются в разных местах, никогда не сравниваются.

**Дубль 5: Маппинг кода → топик энциклопедии.** В `frontend/src/components/project/ProjectStepResults.tsx:12-19` REGULATION_TO_TOPIC через regex; в `encyclopedia/registry.py` `regulations_full` хранится в каждом топике. Третий источник — `regulations.py:category` поле. Нужен один хелпер.

**Дубль 6: `forecast.py` vs `pricing.py` vs `matching.py`.** «Подбор через matching/pricing/forecast» работает не как 3 разных модуля, а как одна цепочка: matching зовёт pricing для каждого результата, потом forecast обогащает диапазонами цен. Граница чёткая, но название `forecast.py` не отражает сути — это «обогащение результата UX-метаданными» (completeness_pct, summary_text, price ranges).

**Псевдо-дубль 7: storm и storm.minimal.** На UI два роута (`/storm/minimal`), форма передаёт `expandPreset(...)` → `/api/storm/calc`. То есть Минимальный фактически = Классический с предзаполненными значениями. Если позже появится `/storm/classical`, нужно убедиться, что бэкенд один.

### 2.3 Регистр нормативов: кто использует, кто нет

**`regulations.py:ALL_REGULATIONS`** содержит 27 записей. Хелпер `ref(reg_key, section, purpose)` помогает создавать `RegulationReference` с авто-резолвом URL.

**Используют `ref()` и/или импортируют из `regulations`:**
- `physics_advanced.py` — 18 вызовов (NPSH, hydroshock, Darcy, parallel pumps).
- `fire_water/scenario.py` — 8 вызовов (СП 8.13130, СП 10.13130, СП 485, ФЗ-123).
- `api.py` — только для `/regulations` и `/regulations/{code}` endpoints.

**НЕ используют (дублируют коды как сырые строки):**
- `climate/frost.py:255-268` — hardcoded `"СП 32.13330.2018"`, `"СП 131.13330.2020"`.
- `structural/seismic.py:156,162` — hardcoded `"СП 14.13330.2018"`, `"СП 14.13330.2018 + ОСР-2015"`.
- `structural/ballast.py:139,145` — `"СП 32.13330.2018"`, `"СП 22.13330.2016"`.
- `structural/ladder.py:71,77` — `"СП 12-104-2002"`, `"СП 28.13330.2017"` (СП 22 и СП 28 вообще нет в `regulations.ALL_REGULATIONS`).
- `los/selection.py:230,236,242` — `"СП 32.13330.2018"`, `"ПП РФ № 728"`, `"Приказ МСХ-552"`.
- `los/aerotank.py:158,164` — `"СП 32.13330.2018"`, `"ИТС 10-2015"` (последний не в реестре).
- `water_supply/demand.py:171,177` — `"СП 30.13330.2020"`, `"СП 31.13330.2021"`.
- `fire_water/sprinklers.py:198,204` — `"СП 485.1311500.2020"` (дважды).
- `fire_water/external.py:117,121` — `table_ref = "СП 8.13130.2020 табл. 1"` как plain string (хотя scenario.py рядом использует `ref()` — несогласованность даже внутри fire_water).
- `electrical/control_panel.py` — references как `list[str]`, без структуры (строки типа `"ПУЭ 7-е изд."`).
- `project/orchestrator.py:137` — каждая подсистема возвращает свой dict со строкой `"СП 32.13330.2018"`.
- `encyclopedia/registry.py:48-...` — `RegulationFull` объекты с дублированными названиями норм.

**Итог:** реестр де-факто — справочник для UI-странички `/regulations`, но **не источник истины** для расчётов. Это противоречит явному design intent, заявленному в `regulations.py:1-23`.

**Дополнительно:** В `regulations.py` отсутствуют:
- СП 22.13330.2016 «Основания» (используется в structural/ballast.py)
- СП 28.13330.2017 «Защита от коррозии» (structural/ladder.py)
- ИТС 10-2015 (los/aerotank.py)
- СП 6.13130.2020 (упоминается в encyclopedia/registry.py:97)
- СП 485 написан и как `SP_5_13130` ключ, и как `SP_485` в кодах — путаница имён.

### 2.4 Рекомендации (backend архитектура)

🔴 **Критично:**
1. Завершить миграцию на `ref()`. Заменить hardcoded строки в 10+ модулях. Заодно добавить недостающие нормы в реестр.
2. Удалить мёртвый `_calc_electrical_subsystem` placeholder из orchestrator или реализовать. Не оставлять чекбокс, который ничего не делает.
3. Чинить hospital-preset (`beds=0`) и АЗС-preset (`wastewater_type` всегда `domestic`).

🟡 **Желательно:**
4. Объединить `physics.py` + `physics_advanced.py` → namespace `physics/{base,npsh,hammer,darcy,parallel}.py`.
5. Удалить дубликат BOM-логики в frontend `buildBomFromProject` — звать `/select` по каждой подсистеме и брать `price_breakdown`.
6. Один источник истины для `RegulationFull` — генерировать `encyclopedia.regulations_full` из `regulations.ALL_REGULATIONS` по `category` или явному списку ключей.

🟢 **Nice-to-have:**
7. Перенести `pricing_glass.py` логику в frontend `tankFormulas.ts` (или наоборот) — они должны давать одинаковые числа.
8. Переименовать `forecast.py` → `result_enrichment.py` или `completeness.py`.

---

## 3. API endpoints

### 3.1 Полный список 30 роутов с описанием

| № | Method | Path | Tag | Используется UI? | Комментарий |
|---|--------|------|-----|------|---|
| 1 | GET  | `/` | meta | нет | redirect-метаинфо |
| 2 | GET  | `/health` | meta | да (через `healthCheck()`) | проверка БД |
| 3 | POST | `/select` | selection | да (`selectPumps()` если L1 не пустой) | основной алгоритм |
| 4 | POST | `/select/quick` | selection | да (`selectPumpsQuick()` если L1 пустой) | дубль шорткат |
| 5 | GET  | `/pumps` | catalog | **нет** | каталог моделей |
| 6 | GET  | `/pumps/{id}` | catalog | **нет** | один насос |
| 7 | GET  | `/producers` | catalog | **нет** | список 8 производителей |
| 8 | GET  | `/coefficients` | catalog | **нет** | таблицы из dataset |
| 9 | POST | `/handoff/questionnaire` | handoff | да (HandoffPanel — но он не подключён!) | PDF опросника |
| 10 | POST | `/handoff/bom` | handoff | да (HandoffPanel) | PDF BOM |
| 11 | POST | `/handoff/questionnaire-docx` | handoff | да (HandoffPanel) | DOCX |
| 12 | POST | `/handoff/empty-questionnaire-docx` | handoff | да (Hero) | пустой DOCX |
| 13 | POST | `/select/from-file` | selection | да (QuizUploader — но он не подключён!) | парсинг DOCX |
| 14 | POST | `/storm/calc` | storm | да (StormMinimalForm) | ливнёвка |
| 15 | GET  | `/storm/cities` | storm | **нет** | автокомплит |
| 16 | GET  | `/storm/presets` | storm | **нет** | заглушка с note |
| 17 | POST | `/fire-water/sprinklers` | fire_water | **нет** | спринклеры |
| 18 | GET  | `/fire-water/sprinkler-groups` | fire_water | **нет** | 8 групп |
| 19 | POST | `/fire-water/calc` | fire_water | **нет (только через `fireWaterApi`, но никто не вызывает)** | пожарка |
| 20 | POST | `/water/demand` | water_supply | **нет** | водоснабжение |
| 21 | GET  | `/water/norms` | water_supply | **нет** | нормы |
| 22 | GET  | `/regulations` | regulations | **нет** | реестр для UI |
| 23 | POST | `/physics/npsh` | physics | **нет** | через `useProject` нет |
| 24 | POST | `/physics/water-hammer` | physics | **нет** | -//- |
| 25 | POST | `/physics/darcy-weisbach` | physics | **нет** | -//- |
| 26 | GET  | `/encyclopedia/topics` | encyclopedia | да (`/teach`) | список топиков |
| 27 | GET  | `/encyclopedia/topic/{key}` | encyclopedia | да (`/teach/[topic]`) | статья |
| 28 | GET  | `/encyclopedia/section/{key}` | encyclopedia | да (drawer) | фрагмент |
| 29 | GET  | `/encyclopedia/examples` | encyclopedia | да | примеры |
| 30 | GET  | `/project/presets` | project | да (wizard) | 13 пресетов |
| 31 | POST | `/project/calculate` | project | да (wizard) | оркестратор |
| 32 | POST | `/climate/burial-depth` | climate | **нет** | через project только |
| 33 | POST | `/climate/loads` | climate | **нет** | через project только |
| 34 | POST | `/structural/ballast` | structural | **нет** | через project только |
| 35 | POST | `/structural/wall-thickness` | structural | **нет** | через project только |
| 36 | POST | `/structural/ladder` | structural | **нет** | через project только |
| 37 | POST | `/los/select` | los | **нет** | через project только |
| 38 | GET  | `/los/catalog` | los | **нет** | каталог ЛОС |
| 39 | POST | `/reports/calculation-pdf` | reports | да (`downloadCalculationPdf`) | PDF |
| 40 | POST | `/complex/summary` | complexes | **нет** | многообъектный комплекс |
| 41 | POST | `/bom/export-csv` | bom | да (`downloadBomCsv`) | CSV |
| 42 | GET  | `/regulations/{code}` | regulations | **нет** | один норматив |

**Итого 42 роута**, не 24+. Из них:
- **15 активных** на frontend (`/health`, `/select*`, `/handoff/empty-*`, `/storm/calc`, `/encyclopedia/*`, `/project/*`, `/reports/*`, `/bom/*`)
- **27 зомби-роутов** — определены в `api.py` и в `lib/api-extended.ts` (через `fireWaterApi`/`waterSupplyApi`/`climateApi`/`structuralApi`/`losApi`/`regulationApi`), но эти объекты **никогда не импортируются в компонентах**.

### 3.2 Дубликаты, забытые, без UI

**Дубликаты:**
- `/select` vs `/select/quick` — оправданы, разные DTO. Мелкий баг: `select_quick` принимает только L0 без L1, что согласуется с тем, что frontend сам выбирает endpoint.
- `/regulations` (list) vs `/regulations/{code}` — норм.
- `/storm/cities` vs `/storm/presets` — оба не используются. Второй буквально `note: "Presets are stored on frontend"`. Удалить.

**Забытые (определены в api.py, но НИЧТО не зовёт в production):**
- `/pumps`, `/pumps/{id}`, `/producers`, `/coefficients` — каталоги для возможной админки, которая не написана.
- `/storm/cities`, `/storm/presets` — для автокомплита и каталога, не подключены.
- `/fire-water/calc`, `/fire-water/sprinklers`, `/fire-water/sprinkler-groups` — отдельные UI-эндпоинты для пожарки, но единственное место использования — через `/project/calculate`. Прямого UI нет.
- `/water/demand`, `/water/norms` — без UI.
- `/physics/npsh`, `/physics/water-hammer`, `/physics/darcy-weisbach` — без UI. `EncyclopediaDrawer` показывает теорию, но не запускает физический калькулятор.
- `/climate/burial-depth`, `/climate/loads` — без UI (только через project).
- `/structural/ballast`, `/structural/wall-thickness`, `/structural/ladder` — без UI (только через project).
- `/los/select`, `/los/catalog` — без UI.
- `/regulations`, `/regulations/{code}` — без UI. Энциклопедия использует свой собственный `regulations_full` на топиках.
- `/complex/summary` — без UI вообще. Класс `Complex` существует, но Phase 29 не подключена к фронту.
- `/handoff/questionnaire`, `/handoff/bom`, `/handoff/questionnaire-docx` — используются `HandoffPanel.tsx`, но сам `HandoffPanel` ни в одном production-роуте не подключён.
- `/select/from-file` — используется `QuizUploader.tsx`, который тоже нигде не используется.

**Без UI, но с реальной ценностью:** `/regulations`, `/los/catalog`, `/storm/cities`, `/fire-water/sprinkler-groups`, `/water/norms` — это эталонные «справочники». Можно сделать страничку `/reference/{topic}` или встроить в EncyclopediaDrawer.

### 3.3 Tags и документация

Все эндпоинты имеют `tags=[...]` ✓. FastAPI auto-docs `/docs` доступен. Описания в большинстве docstring'ов содержательны.

Несогласованности:
- Некоторые эндпоинты возвращают `dict`, некоторые — Pydantic-модели. `/storm/calc` принимает `dict` и парсит в `StormInput` вручную — лучше использовать Pydantic Form/Body.
- `/storm/calc` и `/fire-water/calc` добавляют поле `_signature` с водяным знаком — другие эндпоинты этого не делают. Несогласованно.
- `/fire-water/sprinklers` возвращает поля как ручной dict вместо `result.model_dump()`.

### 3.4 Рекомендации (API)

🔴 **Критично:**
1. Удалить или подключить «зомби-роуты». Минимум — пометить depr-комментарием.

🟡 **Желательно:**
2. Унифицировать ответы — везде `result.model_dump()` плюс единое поле `_meta` с подписью INSERVO и версией.
3. Конкретизировать эндпоинт `/storm/presets` — либо реализовать, либо удалить (текущая заглушка с `note` смотрится дурно).

🟢 **Nice:**
4. Сделать `/admin/pumps` JSON-вьюер на каталог (`/pumps`) — разработчику пригодится.

---

## 4. Frontend целостность

### 4.1 User flow: Hero → ProjectModeCard → Quick / Project

**Главная страница `/`:**
1. `<Hero>` — H1, поле Q, CTA «Рассчитать». При нажатии вызывает `/select/quick` и **скроллит** к секции `#calculator`.
2. `<HowItWorks>` — описание процесса.
3. `<ProjectModeCard>` — карточка-выбор «Проект целиком vs Только насос».
   - «Проект целиком» → ссылка на `/project`.
   - «Только насос» → якорь на `#calculator` (та же страница).
4. `<CalculatorPanel id="calculator">` — расширенная форма (Q + dH + L + тип стоков + corpus, опц. помощник Q).
5. `<ResultsCompare>` — выводит топ-3 насоса в трёх сегментах + ExportActions (PDF + CSV).
6. `<Trust>`, `<Cases>`, `<EngineerCTA>`, `<FAQ>`, `<SiteFooter>`.

**Wizard `/project`:** 4 шага (preset → params → subsystems → results) → `/project/calculate` → `<ProjectStepResults>` с карточками подсистем + кнопками экспорта PDF/CSV.

**Энциклопедия `/teach`:** список 6 топиков + 8 примеров. Клик по топику → `/teach/[topic]` со статьёй.

**Ливнёвка `/storm/minimal`:** 3 поля (тип объекта + площадь + город) → `/api/storm/calc` → результат.

**Резервуары `/tanks`:** 3 вкладки (ПП-ёмкости / Корпус КНС / Стеклопластик). Расчёт **полностью на фронте** через `tankFormulas.ts`. Не использует API.

**Проблемы flow:**
- На `/` Hero сразу делает запрос при клике, потом **второе нажатие** на CalculatorPanel.«Рассчитать» делает второй запрос со своими параметрами. UX неоднозначен: какой результат показывается — из Hero или из CalculatorPanel?
- `<Hero>` имеет также кнопки «Скачать техзадание DOCX» и «Скачать опросный лист DOCX» — оба ведут на одинаковый endpoint и скачивают **тот же файл** с двумя именами. Концептуально честно, но без объяснения два одинаковых файла — путаница.
- `/project` НЕ имеет sticky-навигации к `<SiteNav>`. Только `← На главную` ссылка в углу. Закрытое пространство.
- `/teach` тоже не имеет SiteNav. Если пользователь зашёл на статью, ему нужно ехать назад через `← Все темы` → `← На главную` → найти Hero/Калькулятор.
- `/storm/minimal` и `/tanks` — то же. Sticky SiteNav доступен только на `/`.
- На `/teach/[topic]` нет CTA «Запустить пример» — примеры показаны как карточки с `expected_outcome`, но не открывают сам калькулятор. Visionный «инженерный учебник» обрывается без интерактива.

### 4.2 EncyclopediaDrawer — глобальное мониторирование

**Корректно подключён:** `app/layout.tsx:31` → `<EncyclopediaDrawer />`. Глобальный event-bus `openEncyclopediaDrawer({...})` работает с любой страницы.

**Используется в:**
- `ResultsCompare.tsx` — клики по `pump.P_kW`, `DN`, `impeller`, `Q-H` ведут в drawer ✓
- `ResultsCompare.tsx` BomTable — клики по позициям BOM (Насос/Корпус/Обр.клапан/Поплавки/Шкаф) ✓
- `ProjectStepResults.tsx` — клики по карточкам подсистем + по элементам списка `references_consolidated` ✓
- `ProjectStepResults.DeepCalculationsLinks` — 6 чипов в гидравлике ✓

**НЕ используется:**
- `<Hero>` — параметры в Q-H графике без drawer
- `<CalculatorPanel>` PreviewResult — не открывает drawer для Q/H/мощности
- `<Cases>` — case-cards с числами Q/H без drawer
- `<FAQ>` — не подключён
- `/storm/minimal` SmartDefaultsPreview — не подключён
- `/tanks` HorizontalTankForm/KnsCorpusForm — не подключён

**Проблемы реализации:**
- Поиск секции по подстроке в заголовке `##` или `###` (в `encyclopedia/registry.py:get_topic_section`) — даст false-positives для общих слов («Q-H», «Корпус»).
- При отсутствии секции drawer показывает «Возможно, фрагмент с заголовком "X" отсутствует в энциклопедии. Откройте полную статью →» — это норм, но без логирования какой anchor чаще всего не находится.

### 4.3 Дублирующие компоненты

**Старые компоненты, не используемые в production-роутах:**
- `frontend/src/components/HandoffPanel.tsx` — использовался в Phase 4. Сейчас никем не импортируется (только в тесте).
- `frontend/src/components/QuizUploader.tsx` — тоже Phase 12. Не импортируется.
- `frontend/src/components/WizardL0.tsx` — Phase 6 wizard, заменён `ProjectWizard`. Только тест.
- `frontend/src/components/ResultsCards.tsx`, `PumpCard.tsx`, `QHelper.tsx` — старые версии, заменены `ResultsCompare` и его внутренним `PumpCard`. `QHelper` всё ещё используется внутри `CalculatorPanel`. Остальные — только тесты.
- `frontend/src/components/InservoSignature.tsx` — отдельный signature-блок с тестом, но никем не используется.

**Парные функциональные дубли:**
- `<HandoffPanel>` и `<EngineerCTA>` (premium) делают похожее: показывают баннер «передать инженеру». EngineerCTA активен.
- `<QuizUploader>` дублирует функциональность Hero «Скачать опросный лист DOCX» — плюс upload, который не работает (компонент не подключён).

### 4.4 Технические утечки

- `frontend/src/components/HorizontalTankForm.tsx:195` — на UI отображается `<code>02_dataset/tanks/tank_calculator_models.json</code>`. Пользователь не должен видеть путь к датасету. Заменить на абстракцию (например, «по технологическому паспорту Серво-Юг 2026»).
- `frontend/src/lib/tankFormulas.ts:2` — комментарий `02_dataset/tanks/...` остался в исходнике (не страшно).
- `CalculatorPanel.tsx:320-323` — лейбл «Q расчётный» рядом со значением `result.computed?.H_full_m.toFixed(1)` + ` м³/ч`. Это **баг**: показываются метры напора в графе расхода и наоборот. У пользователя визуально путается Q и H.
- В `ProjectStepResults.tsx:179` поле `inputs_summary` PDF получает `"Подсистем активно": Object.values(result).filter(...)` — это число счётчика, переданное как строка. Не критично, но смотрится грубо.

### 4.5 Висящие концы UI

- В `SiteNav.tsx:42-44` есть пункты `Ливнёвка`, `Резервуары` — корректно. Но при заходе на `/storm/minimal` нет ссылки обратно в Калькулятор (только на главную).
- Footer (`SiteFooter`) есть на всех роутах — ✓.
- `/teach/[topic]` показывает примеры наверху статьи как **карточки с описанием**, но без кнопки «Запустить пример с этими параметрами в калькуляторе» — теряется главная фишка vision (запустимый пример → расчёт).
- `<EngineerCTA result={latest}>` на главной — отображается только когда `result !== null`. Но прочая Trust/Cases — всегда. Логика работает, но без рассчитанного результата плотность контента слишком плоская.

### 4.6 Рекомендации (frontend)

🔴 **Критично:**
1. Починить лейбл `Q расчётный = H_full_m` в `CalculatorPanel.tsx:320`.
2. Убрать утечку `02_dataset/...` из UI на `/tanks`.
3. Удалить или явно отметить как deprecated osиротевшие компоненты `HandoffPanel`, `QuizUploader`, `WizardL0`, `ResultsCards`, `PumpCard.tsx`, `QHelper.tsx` (root) — оставить тесты или удалить и тесты тоже.
4. Добавить SiteNav (или мини-вариант) на `/project`, `/teach`, `/storm/minimal`, `/tanks`. Сейчас они кажутся «отрезанными» — пользователь застревает.

🟡 **Желательно:**
5. На `/teach/[topic]` сделать кнопку «Запустить пример» рядом с каждым `EncyclopediaExample` — открывать `/project` с предзаполненными полями или делать API-вызов и показать результат in-page.
6. Удалить дубль кнопок Hero «Скачать ТЗ / Скачать ОЛ» — оставить одну с явным пояснением что это.
7. Не делать второй запрос при `submit` CalculatorPanel, если уже есть результат от Hero с тем же Q. Хранить Q в URL.

🟢 **Nice:**
8. Перенести логику BOM-table в `ProjectStepResults` через `/select` для каждой подсистемы, а не hardcoded цены.
9. Подключить `regulationApi` в `/teach` (где сейчас три источника `regulations_full`/`Regulation`/раздельные карточки).

---

## 5. Соответствие vision v2

### 5.1 Покрытие 3 режимов

**Минимальный режим** (3-4 поля → результат):
- Для **ливнёвки** — есть `/storm/minimal` ✓.
- Для **КНС/НС** — частично есть (`Hero` с одним полем Q), но возвращает топ-3 насоса с full price_breakdown — это уже не минимальный, это quick-подбор.
- Для **ВНС/ЛОС/пожарка/проект** — отсутствует. Чтобы получить расчёт пожарки или ЛОС, надо идти в полноценный wizard `/project`.

**Классический режим** (60-полевой опросник):
- `Hero` + `CalculatorPanel` суммарно 5 полей: Q, dH, L, wastewater_type, corpus_material.
- `/project` wizard суммарно 11 полей: project_name, project_code, customer, region_city, population, floors, volume_m3, area_m2, soil_type, has_groundwater, is_atex_zone.
- DOCX-опросник (`empty-questionnaire-docx`) содержит ~25 полей.

**60-полевого классического опросника в UI нет.** Поля `liquid_temp_c`, `pipe_material`, `pipe_D_mm`, `n_bends`, `n_valves`, `redundancy`, `Ex_required`, `reliability_category`, `operating_mode`, `inflow_per_hour_m3`, `pumps_total_override` — все они есть в `L1Input` Pydantic, но **нет UI-полей** ни в Hero, ни в CalculatorPanel, ни в ProjectWizard.

**Продвинутый режим** (150+ полей с переопределением коэффициентов):
- В UI **отсутствует**.
- В backend `/coefficients` возвращает все таблицы — теоретическая основа есть, но переопределить из UI нельзя.
- В CalculatorPanel checkbox «Расширенные параметры» открывает только 3 поля.

**Покрытие vs vision: ~25%.** Есть только Hero/Quick (минимальный) и упрощённый wizard (часть классического).

### 5.2 Парный язык «инженерный + бытовой»

Vision: «КНС — канализационная насосная. Q — расход в м³/ч». То есть везде чередовать аббревиатуру и расшифровку.

**Соблюдается:**
- Hero субтитр: `КНС — канализационные насосные станции · ЛОС — локальные очистные сооружения · СПД — станции повышения давления` ✓.
- ProjectModeCard описание: `КНС (канализация), ВНС (водоснабжение)` ✓.
- BetaBanner: «Точность ±15% от паспортного расчёта» — без сложных терминов ✓.
- ProjectStepSubsystems labels: «КНС — канализационная насосная», «ВНС хозпитьевая — повышение давления» ✓.

**Не соблюдается (стиль «инженер для инженера»):**
- `ProjectStepResults` BomTable `section: "ballast"`, `"corpus"`, `"automation"` — английские ключи без расшифровки в UI.
- `ResultsCompare.tsx:325` — labels `P, мощн.`, `DN, патруб.`, `Тип к/к` — слишком сжато.
- В `/teach` статьи markdown — никакого переводчика для ИЖС-владельца. Файлы `02_dataset/_analysis/encyclopedia/*.md` ориентированы на инженера.
- Form labels `pipe_material`, `redundancy`, `Ex_required` — терминология IEC/ISO без расшифровки.
- В Hero subhead: «От ТЗ до спецификации с гидравликой по СП 32.13330» — для ИЖС-владельца «гидравликой» и «СП 32» — пугающе.

### 5.3 Три аудитории — возможность пройти flow

**Аудитория 1: ГИП / инженер-проектировщик ВК.**
- Может: войти в `/project`, выбрать «промпредприятие», получить расчёты КНС/ВНС/пожарка/ЛОС/климат/прочность, скачать PDF + CSV.
- Не может: переопределить коэффициенты, задать pipe_material/n_bends/Ex_required, выбрать редундантность 2+1, увидеть NPSH-расчёт с поправкой на высоту, увидеть отчёт по гидроудару.
- Видит ссылки на нормы ✓.
- **Пройти flow до PDF может, но без точности.**

**Аудитория 2: Менеджер КП Серво-Юг.**
- Может: на `/` ввести Q → получить топ-3 насоса с диапазонами цен → скачать PDF/CSV → отправить КП.
- Не может: одним кликом перенести параметры из Quick в Project (нужно ввести заново).
- **Пройти flow до КП может за 30 секунд** — это хорошо реализовано.

**Аудитория 3: Заказчик-самостроящийся (ИЖС-владелец).**
- Может: ввести Q (если знает) и получить рекомендации.
- Не может: легко определить свой Q (помощник `<QHelper>` есть в CalculatorPanel, но не на Hero).
- Не может понять терминологию `СП 32.13330`, `wastewater_type`, `corpus_material`.
- **Пройти flow в текущем виде сложно.** Нужен «дружественный wizard» (например, «Сколько человек живёт в доме? → 5» → подстановка Q=15 м³/ч).

### 5.4 Рекомендации (vision)

🔴 **Критично:**
1. Реализовать настоящий **Минимальный режим** для проекта: «Тип объекта + город + население» → автогенерация всех расчётов с дефолтами. Это ровно то, что заявлено в vision как «3-4 поля». Сейчас `/project` требует 11 полей и пресет.
2. Сделать **парный язык** обязательным во всех формах через хелпер `<TermLabel rus="..." eng="..."/>`. Убрать `Ex_required` без объяснения.

🟡 **Желательно:**
3. Реализовать **Продвинутый режим** для аудитории ГИП — UI для всех L1-полей + переопределение коэффициентов из `/coefficients`. Это уже не за две недели — большой фронтэнд-проект.
4. На `/teach` каждый пример должен иметь кнопку «Запустить» — и страница должна показать живой результат с тем же layout, что в `/project`.

🟢 **Nice:**
5. Для аудитории ИЖС добавить «Wizard для дома» — отдельный режим с вопросами «сколько человек», «есть ли гараж», «есть ли скважина», без числовых полей.

---

## 6. 3 сквозных кейса (ИЖС, ЖК, АЗС)

Все три кейса проверены **read-only** через анализ кода `ProjectInput → orchestrator.calculate_project → SubsystemResult`. Прогоном тестов не подтверждено.

### 6.1 ИЖС — пройти от Hero до PDF

**Шаги:**
1. Hero. Ввожу Q=2 м³/ч. Кликаю «Рассчитать».
2. Скроллит в `#calculator`. Получаю топ-3 насоса по умолчанию (`dH=5`, `L=50`, `wastewater_type=domestic`).
3. Скачиваю PDF (`Расчётная_записка_…pdf`) или CSV (BOM).
4. Альтернатива: иду на `/project`. Выбираю пресет `ihs`. Параметры: Краснодар, население=4, этажность=1, объём=500. Запускаю.
5. Получаю `result.kns: ok` + `result.los: ok` + `result.climate: ok` + `result.structural: ok`.

**Сложности:**
- В шаге 2 `result.kns` для ИЖС с Q≈2 м³/ч активирует `is_small_kit` в pricing.py → получаем готовый Pedrollo SAR550 + VXm 15/50 (по реестру эталонов это **должен** быть default ответ).
- В шаге 4 orchestrator считает `q_max = 4 × 0.25 / 24 × 2.5 = 0.104 м³/ч`, что округляется до min `1.0 м³/ч`. Это **выглядит** как корректное значение для ИЖС (4 чел = 1 м³/ч на пике), но: фактически для бытовой канализации частного дома типичный Q при пике 1-3 м³/ч — формула выдаёт нижнюю границу.

**Адекватность:**
- Соответствие эталону Pedrollo SAR550 + VXm 15/50 — должно работать (есть в reference_pedrollo_sar550_vxm15_50.md).
- ЛОС: 4 чел × 0.20 = 0.8 м³/сут → `select_los_block` ищет ≥0.8 м³/сут domestic, должна выпадать ПЕГАС-Б 5 (1 м³/сут) или Топас 5 — соответствует эталону `kotedge_los_5_persons` в encyclopedia.
- BOM в `ProjectStepResults` — magic числа: 50000+300000+200000+100000+8500 ≈ 658 000 ₽. Реальная ИЖС стоит 70-200 тыс ₽. **Завышение в 3-9 раз** из-за hardcoded цен.

**Пройдено?** Технически да. Адекватно? Нет — BOM в Project flow искажает экономику кратно.

### 6.2 ЖК 50 квартир — пройти от Hero до PDF

**Шаги:**
1. Иду в `/project`. Пресет `apartment_complex`. Параметры: Москва, население=150, этажность=12, объём=15000, площадь=1500.
2. Subsystems: kns, vns_potable, vns_fire, storm, electrical, climate, structural.
3. Запускаю.

**Что ломается:**
- `_calc_kns_subsystem`: q_max = 150 × 0.25 / 24 × 2.5 = 3.9 м³/ч. **Это слишком мало** для ЖК на 50 квартир (фактически 15-25 м³/ч). Норма 250 л/чел/сут × коэф 1.5-2.5 — для жилого с ваннами и душами это **верхняя граница**, нижний коэффициент почасовой `K_час_max = 1.4` (СП 31 табл.2), а не 2.5.
- `_calc_water_subsystem`: bt = `residential_with_baths`, n_units = 150, norm=250 → Q_avg = 37.5 м³/сут, Q_max_сут = 45, Q_max_час = 2.6 м³/ч, Q_max_сек = 0.73 л/с. Реалистично для 50 квартир.
- `_calc_fire_subsystem`: occupancy=residential, V=15000 → Q_наруж = 15 л/с (по эталону `jk_50_apartments`). ✓
- `_calc_storm_subsystem`: явно пропущен — в `orchestrator.py:382` `# storm — пока пропускаем`. Чекбокс отмечен → `result.storm = None`.
- `_calc_los_subsystem`: not enabled by preset для apartment_complex (`los: False` в PRESET_DEFAULT_SUBSYSTEMS).
- `_calc_electrical_subsystem` — нет такой функции, `result.electrical = None` всегда.

**Адекватность:**
- Q КНС занижен в 4-7 раз. Для ЖК 50 квартир Q реально 18-30 м³/ч.
- Storm не считается несмотря на чекбокс.
- Electrical не считается несмотря на чекбокс.
- BOM hardcoded 50+300+150+120+400+100 = 1.12М ₽ — **в реальности комплекс ЖК 50 квартир (КНС+ВНС+пожарка+резервуар) — 5-8М ₽**. Опять занижение в 5x из-за hardcoded цен в `buildBomFromProject`.

**Пройдено?** Технически частично (3 подсистемы из 7 заявленных работают). Адекватно? Нет.

### 6.3 АЗС — пройти от Hero до PDF

**Шаги:**
1. `/project`, пресет `azs`. Параметры: Краснодар, население=4 (default), этажность=1, объём=500, площадь=2000, грунт=песок_водонасыщенный, УГВ=да, ATEX=да.
2. Subsystems: kns, los, electrical, climate, structural, storm. (По preset `azs`.)
3. Запускаю.

**Что ломается:**
- `_calc_kns_subsystem`: wastewater_type forced **`domestic`**! Для АЗС это **неправильно** — должно быть `drainage` (ливнёвка с мойки) или `industrial` (нефтесодержащие стоки на отдельную систему). Q вычисляется по 0.25 m³/чел/сут — для АЗС это полная бессмыслица: на АЗС нет резидентов.
- `_calc_los_subsystem`: source_type forced **`domestic`** — для АЗС нужен `industrial` или специализированный нефтеуловитель. Q считается как 4 × 0.20 = 0.8 м³/сут.
- `_calc_storm_subsystem`: пропущено комментом.
- `_calc_climate_subsystem`: ✓ Краснодар d_fn=0.8, скорее всего OK.
- `_calc_structural_subsystem`: УГВ=да → пригруз будет посчитан. ✓
- ATEX-флаг `is_atex_zone=True` в orchestrator не передаётся ни в один subsystem (хотя поле есть в `ProjectInput`). Шкаф ATEX, цена +35-45% — не учитывается.

**Адекватность:**
- Концептуально неправильно. АЗС — самый сложный из стандартных пресетов: канализация (фекальная небольшая) + ЛОС с нефтеуловителем + ливнёвка через сепаратор + ATEX электрика. Текущий orchestrator считает АЗС как «маленький жилой дом».
- Для пользователя «менеджер для тендера» это критично: КП на АЗС с Q=0.1 м³/ч и `wastewater_type=domestic` будет тут же отклонён инженером.

**Пройдено?** Формально да. Адекватно? **Нет, ответ грубо неправильный.**

### 6.4 Сводка по кейсам

| Кейс | До PDF? | Точность Q | Точность BOM | Норматив. ссылки |
|------|---------|------------|--------------|------|
| ИЖС | ✓ | OK на нижней границе | завышение ×3-9 | hardcoded в orchestrator |
| ЖК 50 кв. | ✓ частично | занижение ×4-7 | занижение ×5 | + storm/electrical провалены |
| АЗС | ✓ формально | бессмысленно | бессмысленно | wastewater неверный |

Vision-цель «±15% от реального проекта» **не выполняется** ни в одном из 3 эталонных кейсов.

---

## 7. Что улучшить (приоритизированный список)

### 🔴 Критично (блокирует UX и/или грубо ломает результаты)

1. **Заменить hardcoded BOM-цены в `ProjectStepResults.tsx:42-141` на реальные из `kns.data.selection.results.X.price_breakdown`.** Сейчас Project flow выдаёт магические 50/300/120/400/100 тыс ₽.
2. **Починить orchestrator.py `_calc_kns_subsystem` — параметризовать `wastewater_type` от пресета.** АЗС → drainage/industrial, agricultural → drainage, ihs/jk → domestic.
3. **Параметризовать Q-формулу в orchestrator от building_type, не от слепого `0.25`.** Использовать `water_supply.NORMS_LITERS_PER_DAY` (где уже есть 21 тип с правильными нормами и K_hour).
4. **Добавить поле `beds`/`rooms` в `ProjectInput`** или маппить `population` иначе, чтобы hospital-preset не падал с ValueError.
5. **Реализовать `_calc_storm_subsystem` или убрать чекбокс** — сейчас полная путаница для пользователя.
6. **Реализовать `_calc_electrical_subsystem` или убрать чекбокс electrical из ProjectStepSubsystems.**
7. **Подключить ATEX-флаг к расчётам.** `is_atex_zone` собирается в UI, но никуда не идёт.
8. **Починить лейбл `Q расчётный` в CalculatorPanel.tsx:320** (баг: показывает H_full вместо Q).
9. **Убрать утечку `02_dataset/...` в HorizontalTankForm.tsx:195.**
10. **Внедрить `ref()` во все модули.** Заменить hardcoded строки `{"regulation_code": "СП 32..."}` на `ref("SP_32", "...", "...")`. Добавить недостающие нормы (СП 22, СП 28, СП 6.13130, ИТС 10).

### 🟡 Желательно (важно для соответствия vision)

11. **Добавить SiteNav на /project, /teach, /storm/minimal, /tanks.** Пользователь не должен застревать.
12. **Реализовать настоящий Минимальный режим** — единый wizard «Тип объекта + Город + Население» → запуск всех расчётов с дефолтами.
13. **Реализовать Продвинутый режим** — отдельный роут `/project/advanced` с UI для всех L1-полей и переопределения коэффициентов.
14. **На `/teach/[topic]` сделать кнопку «Запустить пример».** Каждый `EncyclopediaExample` должен открывать `/project` с предзаполненными полями или показывать результат in-page.
15. **Объединить три источника regulations:** `regulations.ALL_REGULATIONS` ↔ `encyclopedia.regulations_full` ↔ hardcoded строки. Один источник — `regulations.py`, остальные генерируют из него.
16. **Удалить осиротевшие компоненты:** `HandoffPanel`, `QuizUploader`, `WizardL0`, `ResultsCards`, корневые `PumpCard.tsx`, `QHelper.tsx` — либо удалить, либо подключить.
17. **Добавить парный язык компонент `<TermLabel rus="" eng="">`** и применить ко всем формам.
18. **Унифицировать ответы API.** Везде `model_dump()` + `_meta` с подписью INSERVO. Сейчас storm и fire-water имеют `_signature`, остальные нет.

### 🟢 Nice-to-have

19. Объединить `physics.py` + `physics_advanced.py` в namespace `physics/`.
20. Перенести логику стеклопластикового корпуса из `tankFormulas.ts` в backend через `/tanks/calculate` — чтобы front и back давали одинаковые числа.
21. Удалить мёртвый `api/index.py` или починить vercel.json rewrites (если планируется backend на Vercel — сейчас disagreed с memory-note про 250 MB cap).
22. Сделать `/admin/pumps` JSON-вьюер каталога.
23. Логировать неуспешные anchor-поиски в EncyclopediaDrawer для аналитики «какие термины пользователь запрашивает чаще всего, но статья не находится».

---

## 8. Что убрать (упростить)

### Файлы / endpoint'ы / UI-элементы кандидаты на удаление

- **`api/index.py`** — мёртв из-за отсутствия rewrites. Хранить как «черновик для будущего».
- **`/storm/presets`** — заглушка с note. Удалить.
- **`/storm/cities`** — не используется (autocomplete работает на `RUSSIAN_CITIES` хардкоде в `ProjectStepParams.tsx:12`).
- **Дублирующие zomby-API`s в frontend api-extended.ts** — `fireWaterApi`, `waterSupplyApi`, `climateApi`, `structuralApi`, `losApi`, `regulationApi` — определены, но никто не импортирует. Если нужны — подключить, иначе удалить экспорты.
- **Осиротевшие компоненты**: `HandoffPanel.tsx`, `QuizUploader.tsx`, `WizardL0.tsx`, `ResultsCards.tsx`, `PumpCard.tsx` (корневой, не путать с `ResultsCompare.tsx:PumpCard`), `QHelper.tsx`, `InservoSignature.tsx`. Соответствующие тесты тоже.
- **Дубль кнопок Hero** «Скачать ТЗ DOCX» и «Скачать ОЛ DOCX» — оставить одну с тултипом.
- **`encyclopedia.regulations_full` поле** — генерировать из `regulations.ALL_REGULATIONS` при build-time или загрузке, не дублировать вручную.
- **`forecast.py`** имя — переименовать или вмёрджить в `matching.py` (это часть финального enrichment'а).

### Пути упрощения (не удаление, а merge)

- Слить `physics.py` + `physics_advanced.py` в `physics/__init__.py` с подмодулями (см. 7.19).
- Слить три имплементации regulations.
- Унифицировать BOM: один источник — `pricing.PriceBreakdown` для quick-flow и `bom.BOMSpecification` для project-flow. Сейчас Project flow строит BOM **руками** на frontend — это самое опасное место.

---

## 9. Чек-лист на следующую сессию

Конкретные задачи из категории 🔴 (10 задач, 1-3 часа каждая):

1. `frontend/src/components/premium/CalculatorPanel.tsx:320` — заменить `result.computed?.H_full_m` в графе `Q расчётный` на `result.input.L0.Q_m3h` (или `result.computed.duty_point.Q_m3h`).
2. `frontend/src/components/HorizontalTankForm.tsx:195` — убрать абзац с `<code>02_dataset/...</code>`. Заменить на «По калькулятору стоимости Серво-Юг 2026 (открытая модель)».
3. `backend/pump_calculator/project/orchestrator.py:114-146` — переписать `_calc_kns_subsystem` так, чтобы:
   - брать `wastewater_type` из мапа `preset → wastewater` (azs→drainage, industrial→industrial, agricultural→drainage, ihs/jk/hotel/school/hospital→domestic).
   - брать норму потребления из `water_supply.NORMS_LITERS_PER_DAY[bt]` вместо хардкода 0.25.
   - корректно обрабатывать `inputs.is_atex_zone` через `L1.Ex_required=True`.
4. `backend/pump_calculator/project/orchestrator.py:149-194` — добавить `rooms`/`beds`/`area_m2` поля в `ProjectInput` и передавать в `WaterScenarioInput`. Сначала проверить, что hospital-preset не падает.
5. `backend/pump_calculator/project/orchestrator.py:382` — реализовать `_calc_storm_subsystem` (вызвать `storm.calculate_full_storm` с заполнением `surfaces` по площади + дефолтному типу поверхности из пресета: azs→асфальт 100%, ihs→крыша 30%+газон 50%+отмостка 20%).
6. `backend/pump_calculator/project/orchestrator.py` — добавить `_calc_electrical_subsystem`, который зовёт `electrical.calc_motor_power_required` + `select_cable_section` + `select_control_panel` на базе насосной мощности из KNS-результата. Если КНС не считается — пропускаем.
7. `frontend/src/components/project/ProjectStepResults.tsx:41-141` — переписать `buildBomFromProject` на использование реальных полей из `result.kns.data.selection.results.mid.price_breakdown`. Удалить hardcoded цены 50/300/120/400/100 тыс.
8. Backend модули с hardcoded `regulation_code` — заменить на `ref()` (минимум: `climate/frost.py`, `los/selection.py`, `los/aerotank.py`, `water_supply/demand.py`, `structural/ballast.py`, `structural/seismic.py`, `structural/ladder.py`, `fire_water/sprinklers.py`, `fire_water/external.py`). Добавить недостающие нормы в `regulations.py`.
9. `frontend/src/app/project/page.tsx`, `/teach/page.tsx`, `/storm/minimal/page.tsx`, `/tanks/page.tsx` — добавить `<SiteNav />` сверху. Сейчас только `/` имеет нав-бар.
10. `frontend/src/app/teach/[topic]/page.tsx` — на каждом `EncyclopediaExample` добавить кнопку «Запустить» — POST на `ex.api_endpoint` с `ex.payload`, открыть результат в `<ResultsCompare>` или drawer'е.

После выполнения 10 пунктов:
- результаты по 3 кейсам (ИЖС, ЖК, АЗС) станут адекватными;
- 95% UI и API будут консистентны;
- регистр нормативов станет реальным single-source-of-truth;
- три аудитории получат хотя бы по одному рабочему flow.

Дальнейшая работа (🟡/🟢) — это уже эволюция, не починка.

---

## Приложение A. Карта файлов

**Backend (91 .py):**
- `backend/pump_calculator/api.py` — FastAPI, 42 роута
- `backend/pump_calculator/schemas.py` — L0/L1/SelectionResult Pydantic
- `backend/pump_calculator/regulations.py` — 27 норм, `ref()` хелпер
- `backend/pump_calculator/matching.py` — 7-шаговый алгоритм подбора
- `backend/pump_calculator/hydraulics.py` — Дарси-Альтшуль/Σζ/AOR/POR
- `backend/pump_calculator/physics.py` — 14 функций
- `backend/pump_calculator/physics_advanced.py` — 13 функций (NPSH/гидроудар/Дарси с references)
- `backend/pump_calculator/phase15.py` — формулы §15 (V_min, S/D, Ns, NPSH margin, v_min)
- `backend/pump_calculator/forecast.py` — completeness_pct, summary_text, price ranges
- `backend/pump_calculator/pricing.py` — heuristic-цены + KNS/SPD/Fire kit BOM
- `backend/pump_calculator/pricing_glass.py` — стеклопластиковый корпус
- `backend/pump_calculator/corpus_sizing.py` — геометрия КНС-корпуса
- `backend/pump_calculator/catalog.py` — load JSON
- `backend/pump_calculator/storm/{models,peak_flow,annual,design,regions,surfaces}.py`
- `backend/pump_calculator/fire_water/{models,external,internal,sprinklers,scenario,reservoir,pump_station}.py`
- `backend/pump_calculator/water_supply/{models,demand,alpha_coefficients,station}.py`
- `backend/pump_calculator/electrical/{motor,cable,protection,short_circuit,control_panel}.py` — НЕ ПОДКЛЮЧЕНО к API
- `backend/pump_calculator/climate/{models,frost,loads}.py`
- `backend/pump_calculator/structural/{models,ballast,wall_thickness,ladder,seismic}.py`
- `backend/pump_calculator/los/{models,selection,composition,aerotank}.py`
- `backend/pump_calculator/reports/calculation_report.py` — PDF-генератор
- `backend/pump_calculator/complexes/{models,summary}.py` — Phase 29 (без UI)
- `backend/pump_calculator/bom/{builder,export}.py`
- `backend/pump_calculator/encyclopedia/registry.py` — топики + 8 примеров
- `backend/pump_calculator/project/{models,orchestrator}.py`
- `backend/pump_calculator/handoff/{_pdf_base,bom_pdf,questionnaire_pdf,questionnaire_docx,quiz_extractor}.py`
- `backend/pump_calculator/etl/{cli,curve_fitter,importer,pipeline,review,schemas,pdf/*}.py`
- `backend/tests/*` — 44 тестовых файла

**Frontend:**
- `frontend/src/app/{layout,page,providers}.tsx` + `app/{project,teach/[topic],storm/minimal,tanks}/page.tsx`
- `frontend/src/components/premium/{Hero,HowItWorks,ProjectModeCard,CalculatorPanel,ResultsCompare,Trust,Cases,EngineerCTA,FAQ,SiteNav,SiteFooter,QHCurve}.tsx`
- `frontend/src/components/project/{ProjectWizard,ProjectStepPreset,ProjectStepParams,ProjectStepSubsystems,ProjectStepResults}.tsx`
- `frontend/src/components/teach/{EncyclopediaDrawer,MarkdownView}.tsx`
- `frontend/src/components/storm/minimal/{StormMinimalForm,ObjectTypeSelector,AreaInput,CityAutocomplete,SmartDefaultsPreview,StormMinimalResult}.tsx`
- `frontend/src/components/{BetaBanner,HorizontalTankForm,KnsCorpusForm}.tsx` — активные
- `frontend/src/components/{HandoffPanel,QuizUploader,WizardL0,ResultsCards,PumpCard,QHelper,InservoSignature}.tsx` — **осиротевшие**
- `frontend/src/lib/{api,api-extended,units,tankFormulas}.ts` + `lib/storm/expandPreset.ts`
- `frontend/src/hooks/{usePumpSelection,useProject}.ts`
- `frontend/src/schemas/{input,result}.ts`

**Прочее:**
- `vercel.json` — без rewrites
- `next.config.mjs` — rewrites только в dev
- `api/index.py` — мёртвая попытка serverless backend
- `02_dataset/_analysis/encyclopedia/*.md` — 6 markdown-статей энциклопедии
- `02_dataset/{pumps,corpora,tanks,fittings,pricing,theory}/*.json` — датасет

---

Конец отчёта.
