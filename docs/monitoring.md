# KNS Calculator — Monitoring

> Sc.D. Architecture audit 2026-05-13: «Нет YC monitoring + alerts». Этот документ закрывает finding — описывает где смотреть метрики, что мониторить и как реагировать.

## 1. Источники данных

| Источник | Что туда попадает | Retention |
| --- | --- | --- |
| **YC Cloud Logging** (folder `b1ge2mgg8tgh92uerm9c`) | Все `structlog` JSON-логи FastAPI: requests, errors, audit, business events. Поток `default`. | 30 дней (тариф «Стандарт») |
| **Sentry** (`https://sentry.io/organizations/inservo/projects/kns-calculator/`) | Все необработанные исключения с traceback + breadcrumbs + request context. Включён если `SENTRY_DSN` ENV задан. | 90 дней (free tier) |
| **YC Monitoring** | Системные метрики Function (cold-start, memory, duration, invocations). | 30 дней |

## 2. Dashboards

Декларативная спецификация: [`deploy/yandex-cloud/dashboards.yaml`](../deploy/yandex-cloud/dashboards.yaml).

Создание через YC Console: **Cloud Logging → Dashboards → Create dashboard**, widgets — copy/paste запросов из YAML.

### 2.1 `kns-calculator-overview`

Главный dashboard — открывается at-a-glance:

- Requests by status (timeseries)
- P95 latency by endpoint
- Errors 5xx by endpoint
- Rate limit hits 429 by IP
- Sentry-captured exceptions

### 2.2 `kns-calculator-audit`

Compliance + security (152-ФЗ ст.19):

- Все обращения к `/admin/*` (audit log из `structlog.get_logger("audit.admin")`)
- Auth failures по `/admin/*`
- ТЗ-imports / hour
- Daily merge runs (cron success)
- Tenant traffic split (multi-tenancy)

### 2.3 `kns-calculator-business`

Продуктовые метрики:

- Selection requests / hour
- PDF/DOCX генерации
- Tenant breakdown

## 3. Alert rules

См. секцию `alerts:` в [`dashboards.yaml`](../deploy/yandex-cloud/dashboards.yaml). Настраиваются в **YC Monitoring → Alerts**.

| Имя | Условие | Severity | Уведомление |
| --- | --- | --- | --- |
| `high-5xx-rate` | ERROR rate > 1% за 5 минут | critical | Telegram |
| `p95-latency-spike` | P95 latency > 3s за 5 минут | warning | Telegram |
| `5xx-burst` | > 10 5xx за минуту | critical | Telegram + SMS oncall |
| `pumps-dataset-unavailable` | `/health` = 503 | critical | Telegram |
| `daily-merge-failed` | merge-internal вернул non-2xx | warning | Telegram |

Placeholder'ы (`TG_ONCALL_BOT_ID`, `TG_ONCALL_CHAT_ID`, `+7-XXX-...`) заменить на реальные при настройке.

## 4. Sentry

### 4.1 Конфигурация

Включается через ENV в Function-настройках YC:

```bash
SENTRY_DSN=https://<key>@sentry.io/<project_id>
SENTRY_TRACES_SAMPLE_RATE=0.1   # 10% transactions для perf-tracing
ENV=prod                         # тег для фильтрации
APP_VERSION=<git-sha>            # release tag
```

Без `SENTRY_DSN` → graceful no-op (см. [`pump_calculator/error_reporting.py`](../backend/pump_calculator/error_reporting.py)). Тогда исключения остаются только в YC Logging.

### 4.2 Что улетает в Sentry

- Все необработанные exceptions в FastAPI handlers (через `FastApiIntegration`).
- Все вызовы `capture_exception(exc, **context)` из кода. Контекст подсыпается как extra-fields.
- 10% трассировок (для P95-анализа) — управляется `SENTRY_TRACES_SAMPLE_RATE`.

### 4.3 Что **НЕ** попадает в Sentry

- HTTP 4xx — это user errors, не баги.
- `/health`, `/privacy`, `/` — meta endpoints, без бизнес-логики.
- Sensitive PII из ТЗ — Sentry имеет `before_send` фильтр (TODO: добавить когда подключим реального дилера).

## 5. Cron (daily merge)

См. [`deploy/yandex-cloud/triggers.yaml`](../deploy/yandex-cloud/triggers.yaml).

- Триггер: **00:00 UTC = 03:00 МСК** ежедневно.
- Вызывает `POST /admin/uploads/merge-internal` (без HTTP Basic, защищён `X-YC-Internal-Token`).
- Логи trigger'а смотреть: YC Logging → filter `json_payload.path = "/admin/uploads/merge-internal"`.

Ручная активация:

```bash
bash deploy/yandex-cloud/setup_triggers.sh
```

Ручной вызов (debug):

```bash
curl -X POST https://<api-gw>/admin/uploads/merge-internal \
  -H "X-YC-Internal-Token: $YC_INTERNAL_TOKEN"
```

## 6. Runbook

### 6.1 5xx burst

1. YC Logging → `kns-calculator-overview` → «Errors 5xx by endpoint».
2. Если один endpoint — смотреть Sentry trace.
3. Если distributed — проверить health Function в YC Monitoring (memory/duration spike?).
4. Rollback на предыдущий tag через `yc serverless function version create`.

### 6.2 Daily merge failed

1. YC Logging → filter `path = "/admin/uploads/merge-internal"` за последние 24h.
2. Если 401 — проверить `YC_INTERNAL_TOKEN` ENV в Function-настройках.
3. Если 5xx — Sentry trace + проверить write-перм. на `_dataset_root`.
4. Ручной retry: см. секцию 5.

### 6.3 Rate-limit abuse

1. Dashboard `kns-calculator-overview` → «Rate limit hits 429 by IP».
2. Если один IP — добавить в `BLOCKED_IPS` ENV (TODO endpoint).
3. Если distributed (boto) — повысить cost on attacker через captcha (Phase 34+).

## 7. Backlog

- [ ] Sentry `before_send` фильтр для PII (телефоны, email клиентов из ТЗ).
- [ ] OpenTelemetry traces → YC Monitoring (когда выйдет beta для Functions).
- [ ] Per-tenant dashboard split (multi-tenancy roll-out).
- [ ] Synthetic monitoring (Pingdom / YC checks → `/health` каждые 5 минут).
- [ ] Slack-bot для алертов вместо Telegram (когда подключим дилера).
