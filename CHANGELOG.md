# Changelog

Все значимые изменения проекта. Формат основан на [Keep a Changelog](https://keepachangelog.com/), версионирование по календарным датам.

## [2026-05-10] — Hardening + Phase 28 PDF (sessions 01:19→11:00)

### Database
- **+174 насоса** через multi-agent research:
  - ИСТРАТЕХ Групп (Agent A): 59 моделей серии BM (CR-style многоступенчатые) + ВО + HC-FS, цены 65-520 тыс ₽, артикулы S74xxx подтверждены, ПП-1875
  - ГМС Ливгидромаш / ЯНЗ / СЗПН (Agent B): 77 типоразмеров ЦНС в 8 сериях (Q=13/38/60/105/180/300/500/850), закрывает дыру H=150-600 м для пожарки-СПД и ППД
  - CNP (Agent C): 38 моделей WQ-серии с подтверждёнными RU розничными ценами 2026
- **24 ценовых калибровки** через subagent (16 Pedrollo + 8 KSB):
  - 16 high-conf повышены `_engineer_flag` `needs_review → ok`
  - Цены из e-nasos.ru, pd-shop.ru, baymart.ru, ksb.nt-rt.ru
- **151 насос** помечен `_engineer_flag="request_quote"` (75 Antarus + 76 KSB):
  - Antarus НК — B2B-only через search.antarus.su
  - KSB DN65/100/150/200+ — KSB ушёл из РФ-розницы

**Итого: 471 насос в БД** (было 297). 230/471 (49%) с подтверждёнными ценами.

### Schema
- `_version` 0.1 → 0.2
- `brand` enum: 10 → 24 (+ИСТРАТЕХ, ГМС, CNP, Fancy, MAS DAF, и др.)
- `type` enum: 7 → 9 (+`fire_protection`, `vertical_dry_well`)
- `voltage_v` enum: 2 → 6 (+230, 400, 460, 6000)
- `wastewater_compat` enum: 4 → 6 (+`fire_water`, `fire_protection`)
- `available_ru.status` enum: 4 → 12 (+`available`, `build_to_order`, `domestic_manufacturer`, `imported_*`, и др.)
- `_engineer_flag` enum: 4 → 6 (+`calibration_pending`, `request_quote`)
- `impeller` enum нормализован: 18 → 7 канонических значений
- `price_segment`: добавлен `standard` (затем мигрирован → `mid`)

### Backend hardening (PRR audit driven)
- **`logger.exception`** в 26 except-блоках `api.py` + 8 в `orchestrator.py` — stack trace теперь попадает в YC Function logs
- **`catalog.load_pumps`**: try/except + safe-empty вместо 500-краша при повреждённом JSON
- **`/health`**: 503 если pumps_in_db=0 (было 500)
- **CORS** читает `CORS_ALLOWED_ORIGINS` из ENV (было захардкожено `["*"]`)
- **`composite_score` штрафы**: `needs_review ×0.7`, `request_quote ×0.5`
- **`PumpResult.notes`**: автоматические UI-warnings для request_quote/needs_review

### Backend features
- **`nu_water_at_t(T_celsius)`** в `hydraulics.py` — кинематическая вязкость воды через интерполяцию IAPWS-IF97 (0..100°C)
- **`compute_hydraulics`** использует `L1.liquid_temp_c` через `nu_water_at_t` (для T=40°C H_тр меньше на ~7%)
- **L1Input.altitude_m** добавлен (-500..4500 м) для будущей коррекции NPSHa в горных регионах

### Phase 28 PDF РПЗ
- **`reports/qh_chart.py`** — `render_qh_chart_png(pump, duty_Q, duty_H)`:
  - Парабольная аппроксимация Q-H через 3 точки envelope
  - Зоны AOR (±15%) / POR (±10%) по HI 9.6.1-2024
  - BEP маркер + рабочая точка + matplotlib lazy-import
- **`CalculationReportInput`** расширен 4 полями (`pump_for_chart`, `duty_Q_m3h`, `duty_H_m`, `encyclopedia_citations`)
- **`generate_calculation_report_pdf`**:
  - Кликабельные ссылки на нормативы через `<a href>` (использует `references[].url` или `url_official`)
  - Секция "Обоснование расчётных подходов" с цитатами из энциклопедии
  - Секция 3.8 Q-H характеристика рабочего насоса
- **`encyclopedia/registry.build_pdf_citation`** — helper для извлечения 1-2 параграфов из секции, очистка markdown для reportlab

### Refactors / cruft cleanup
- `phase15.py` → `pump_station_geometry.py` (имя=смысл)
- `forecast.py` → `result_enrichment.py` (имя=смысл, никаких прогнозов)
- `regulations.SP_5_13130` → `SP_485` (СП 5 отменён в 2020)
- `regulations.SP_12_04` → `SP_49` (СП 12-104 отменён в 2017)
- `regulations.SANPIN_2_1_4` → `SANPIN_2_1_3684` (СанПиН 2.1.4 заменён в 2021)
- Все старые имена сохранены как deprecated alias для backward compat

### Frontend
- **BetaBanner overlap fix**: `SiteNav.tsx` `top-9 md:top-10 z-40` (было `top-0 z-50` — перекрывал BetaBanner на mobile)

### YC Functions deploy
- `registry.py` encyclopedia path-resolver (3 кандидата: env, walk-up, cwd) — `/teach` теперь работает в YC Functions runtime
- `build.py` копирует encyclopedia md-файлы в deploy zip

### Tests
- **544 passed, 2 skipped, 2 deselected** (pytest backend)
- 62/62 passed (vitest frontend)
- +13 новых тестов: 4 qh_chart, 5 hot_stocks, 3 build_pdf_citation, 1 phase28 PDF integration
- 1 калибровочный тест обновлён (KNS1 premium P_kW допуск 80→150 кВт после изменения логики штрафа)

### Multi-agent аудиты (memory)

3 параллельных subagent'а провели:
1. **PRR Audit** — top-5 рисков продакшна (4 P0/P1 закрыты в этой сессии)
2. **Теория-практика** — топ-10 практик-дыр + Phase 28 рекомендация
3. **Frontend smoke** — БЛОКЕРЫ Vercel proxy 404 + YC backend deploy

### Известные блокеры (требуют ручного действия)

🚨 Vercel `/api/backend/*` возвращает 404 (кэш 31ч) — `BUILD_TARGET=yc-static` ИЛИ `NEXT_PUBLIC_API_BASE` env fix
🚨 YC backend `pumps_in_db=297` — нужен `cd deploy/yandex-cloud && python build.py && yc serverless function version create ...` (yc CLI не установлен)
🟡 YC static frontend устарел — rebuild + upload в Object Storage

---

## [До 2026-05-10]

См. `git log --oneline` и `PROJECT_STATUS.md`.

Phase 1-21 + 31-32 реализованы (физика, гидравлика, пожарка, водоснабжение, климатика, прочность, ЛОС, энциклопедия, мульти-объектные комплексы).
