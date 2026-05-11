# kns-calculator — Public Project Status

**Заказчик:** Серво-Юг (Краснодар), партнёр INSERVO
**Лицензия:** MIT
**Период разработки:** 2026-05-03 → продолжается
**Production:** Yandex Cloud (backend + frontend), LIVE
- Frontend: https://kns-calculator-frontend.website.yandexcloud.net (YC Object Storage)
- Backend: https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net (YC Functions + API Gateway)

## Roadmap

- ✅ **Priority 1** — БД пожарных насосов, ANTARUS MLV/MST, НДС 22%, dealer-флаг
- ✅ **Priority 2** — Wizard L1 (+8 полей), ref() helper, alternatives (множественные бренды)
- 🚧 **Priority 4 (PRE-PROD)** — Design UX/UI, генерация TS-типов из Pydantic, упрощение главной
- ✅ **Priority 5 (PROD)** — переезд на Yandex Cloud Functions + Object Storage (LIVE)

---

## Архитектура

### Backend (Python 3.13 / FastAPI)

22 модуля, ~16.5K строк, **536 тестов passed**, ruff чистый.

```
backend/pump_calculator/
├── api.py / matching.py / schemas.py    — REST + ядро подбора (3 ценовых сегмента)
├── regulations.py                        — 27 нормативов с RegulationFull
├── hydraulics.py / physics.py / physics_advanced.py
├── corpus_sizing.py                      — размеры корпуса от Q
├── pricing.py / pricing_glass.py         — БД цен + price_breakdown
├── catalog.py                            — БД 284 насоса
├── fire_water/                           — пожаротушение СП 8.13130, СП 485
├── water_supply/                         — α-метод СП 30, спринклеры
├── electrical/                           — мощность, КЗ ПУЭ
├── climate/                              — СП 131 (200+ городов)
├── structural/                           — стенки, лестницы, ballast (anti-buoyancy), сейсмика СП 14
├── los/                                  — локальные очистные
├── storm/                                — ливневая канализация СП 32 §6
├── complexes/ bom/ reports/ encyclopedia/ handoff/ etl/
└── project/                              — оркестратор Проект-визарда
```

### Frontend (Next.js 14 / React / TypeScript / Tailwind)

31 компонент, ~8.5K строк, **62 теста passed**, typecheck/lint/build чистые.

```
frontend/src/app/
├── /                  — Premium-главная (Hero/CalculatorPanel/ResultsCompare/Cases/FAQ)
├── /project           — Единый Проект-визард (4 шага: Preset → Subsystems → Params → Results)
├── /storm/minimal     — Калькулятор ливневых стоков
├── /tanks             — Корпуса и горизонтальные ёмкости
└── /teach[topic]      — Энциклопедия инженера ВК (7 тем + 16 примеров)
```

---

## Покрытие нормативами (27)

| Группа | Документы |
|---|---|
| Канализация / водоснабжение | СП 32.13330.2018, СП 30.13330.2020, СП 31.13330.2021 |
| Пожарная защита | СП 8.13130.2020, СП 10.13130, СП 485.1311500.2020 (8 групп спринклеров) |
| Сейсмика и грунты | СП 14.13330.2018, СП 20, СП 22, СП 25, СП 45 |
| Климат | СП 131.13330.2018 |
| Электрика | ПУЭ, СП 12-104 |
| ТР ТС | 004 (низковольтное), 012 (взрывозащита), 020 (ЭМС) |
| ГОСТ / ИСО | 6134, 21.110-2013 (BOM), Р 21.101-2020 (РПЗ), Р 70628.2 (трубы), 9906 (ISO) |
| ФЗ / СанПиН / ПП | ФЗ-123, ФЗ-384, ПП-728, ПП-644, СанПиН 42-128-4690-88 |

---

## БД насосов (284 модели)

| Сегмент | Производители |
|---|---|
| Premium | KSB Amarex, Wilo Helix, Grundfos SP/SL/UNILIFT, Pedrollo VX/F, Lowara |
| Mid | ANTARUS НК/MLV/MST/MS, ИСТРАТЕХ ИЛТ, ЦНС, FloTenk, BloPlast |
| Budget | KAIQUAN, CNP, LEO, Fancy, ГНОМ, СМЗ, Иртыш Ex, ФГПУ |

## Корпуса

Стеклопластик (Plastek/Rainpark/Промбэйс/ANTARUS/ГЕОН/НеоДрейн/БиоПроект/КИТ/АЛИВА), полиэтилен (Серво-Юг), бетон/ж/б (ТП 901/902).

---

## Эталонная база

**Публичная (обезличенная):** `02_dataset/etalons/public/etalons_public_2026-05-09.json` — 47 объектов:

- Спорткомплексы, ЖК, рекреационные комплексы, промбазы, АЗС, нефтегаз
- ВЭС с маслосборником, ЛОС-комплексы, КС газотранспорт
- Регионы: Краснодарский край, Крым, Ростов, Москва, Сочи, Севастополь, Казахстан

---

## Метрики проекта

| Параметр | Значение |
|---|---|
| Коммитов | 73 |
| Строк кода | 25 033 |
| Тестов passed | 598 |
| Эталонов проектов (публичных) | 47 |
| Полей опросных листов в схеме | 109 |
| Позиций в pricelist | 97 |
| Тем энциклопедии | 7 |

---

## Главные UI-страницы

- **Главная** `/` — быстрый подбор по Q/H, 3 ценовых сегмента, сравнение
- **Проект** `/project` — единый визард для типов объектов (ИЖС/ЖК/гостиница/ТРЦ/АЗС/промпредприятие/больница и др.)
- **Ливневка** `/storm/minimal` — расчёт пиковых дождевых стоков
- **Корпуса** `/tanks` — параметры подземных и горизонтальных ёмкостей
- **Энциклопедия** `/teach` — 7 справочных разделов с интерактивными примерами

---

## Подсистемы калькулятора

При выборе типа объекта оркестратор автоматически прогоняет нужные подсистемы:

- **КНС** (хозбытовая, дренажная, промышленная)
- **ВНС** хозпит. + пожарная
- **Ливневая канализация** с расчётом водосборных площадей
- **ЛОС** (локальные очистные сооружения)
- **Электрика** (мощность, КЗ, категория надёжности)
- **Климат** (по 200+ городам, обогрев, утепление)
- **Прочность** (стенки корпуса, anti-buoyancy при УГВ, сейсмика, лестницы)
- **Pricing** (3 сегмента + полная BOM + диапазон цены)

---

## Deploy

**Frontend:** YC Object Storage (static) — https://kns-calculator-frontend.website.yandexcloud.net — LIVE

**Backend:** YC Functions через API Gateway — https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net — LIVE

Подробности — в [`deploy/yandex-cloud/README.md`](deploy/yandex-cloud/README.md).

---

## Контакты

INSERVO — Студия интеграции умных решений Константина Морозова
https://inservo.ru · zakaz@inservo.ru · 8 (800) 222-44-57
