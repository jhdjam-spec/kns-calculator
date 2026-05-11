# Yandex Cloud Functions deployment

Деплой backend kns-calculator на Yandex Cloud Functions (Python 3.11 runtime).
Это **единственная** production-платформа проекта — фронт и бэк живут в YC.

## Зачем YC

- YC Functions: 512MB code+layers, 4GB RAM, 10мин timeout, ~500мс cold start
- РФ-юрисдикция (152-ФЗ персональные данные), оплата в рублях
- Free tier: 1 млн вызовов в месяц
- Yandex Cloud MCP уже подключён в Claude Code (`mcp__yandex-cloud__*`)
- Frontend (static export) рядом в Object Storage с website hosting

## Структура

```text
deploy/yandex-cloud/
├── handler.py            — entry point с Mangum-адаптером
├── requirements.txt      — fastapi+pydantic+mangum+reportlab+python-docx
├── README.md             — этот файл
├── build.sh              — скрипт сборки zip-пакета
└── pump_calculator/      — символическая копия из backend/pump_calculator (через build.sh)
```

## Подготовка к деплою

### 0. Существующая инфраструктура (созданная через MCP 2026-05-09)

```text
Organization ID  : bpft7o1pahp23rlhkliq
Cloud            : cloud-servoug      (id: b1gafatuvqpp5e9lp7sh)
Folder kns       : kns-calculator     (id: b1ge2mgg8tgh92uerm9c)  ← ИЗОЛИРОВАН
Folder default   : default            (id: b1g6culuo3737j3pbupu)  ← content factory
Service Account  : kns-calculator-api (id: ajeur7e0n1k1n458t79n)
                   роли в kns-calculator folder:
                     - serverless.functions.invoker
                     - serverless.functions.admin
                     - storage.viewer
```

**Изоляция проектов:** kns-calculator и content factory в разных folder одного cloud.
Общий billing, но изолированные ресурсы и IAM.

### 1. Yandex Cloud CLI

```powershell
# Установить YC CLI (Windows PowerShell)
iex (New-Object System.Net.WebClient).DownloadString('https://storage.yandexcloud.net/yandexcloud-yc/install.ps1')

# Авторизоваться (откроет браузер с OAuth-flow)
yc init
# При запросе:
#   cloud:  cloud-servoug (b1gafatuvqpp5e9lp7sh)
#   folder: default (b1g6culuo3737j3pbupu)

# Проверка
yc config list
```

### 3. Сборка пакета

```bash
cd deploy/yandex-cloud
bash build.sh   # создаёт kns-calculator.zip
```

### 4. Создание функции

```powershell
yc serverless function create --name kns-calculator-api
yc serverless function version create `
    --function-name kns-calculator-api `
    --runtime python311 `
    --entrypoint handler.handler `
    --memory 512m `
    --execution-timeout 30s `
    --service-account-id ajeur7e0n1k1n458t79n `
    --source-path kns-calculator.zip `
    --environment KNS_DATASET_ROOT=./02_dataset `
    --environment CORS_ALLOWED_ORIGINS=https://kns-calculator-frontend.website.yandexcloud.net
```

### 5. Публичный URL

Включить Functions Public access:

```bash
yc serverless function allow-unauthenticated-invoke kns-calculator-api
```

URL: `https://functions.yandexcloud.net/<function_id>`

### 6. Frontend build env var

При сборке фронта (`frontend/`) задайте `NEXT_PUBLIC_API_BASE` — он
инлайнится в статический бандл во время `next build`:

```bash
cd frontend
NEXT_PUBLIC_API_BASE=https://<api-gateway>.apigw.yandexcloud.net npm run build
python ../deploy/yandex-cloud/sync_frontend.py
```

После повторной заливки в Object Storage фронт начнёт ходить в YC backend.

## Smoke tests

После деплоя проверить:

```bash
# Health check
curl https://functions.yandexcloud.net/<id>/

# Расчёт КНС
curl -X POST https://functions.yandexcloud.net/<id>/select/quick \
    -H "Content-Type: application/json" \
    -d '{"L0": {"Q_m3h": 16.08, "wastewater_type": "domestic"}}' | jq

# Расчёт пожарной (Бондаревская ВЭС)
curl -X POST https://functions.yandexcloud.net/<id>/select/quick \
    -H "Content-Type: application/json" \
    -d '{"L0": {"Q_m3h": 133.2, "dH_m": 30, "wastewater_type": "fire_protection"}}' | jq
```

Должны вернуться: 4 кандидата (mid + premium + 2 alternatives) для Бондаревской.

## Calibration smoke

После деплоя прогнать:

```bash
python backend/_scripts/calibrate_etalons_2026_05_09.py \
    --api https://functions.yandexcloud.net/<id>
```

Ожидаемый результат: pass=3, warn=2, error=0 (как локально).

## DNS (опционально)

Если есть свой домен:

```text
CNAME kns-api.servoyug.ru → functions.yandexcloud.net
```

Сертификат Let's Encrypt — через YC Certificate Manager.

## Стоимость (оценка)

При 10K вызовов/месяц:

- 1М вызовов free → нагрузка 10K: бесплатно
- Compute time ~2 GB-сек на вызов = 20K GB-сек
  - Free 10 GB-сек/мес → платно 10K GB-сек × ₽0.0000035 = **₽35/мес**
- Egress traffic: ~100 МБ → ₽0
- Object Storage (если dataset в S3): 50 МБ × ₽1/ГБ/мес = ₽0.05

**Итого:** ~₽35-50/мес для текущей нагрузки. Расширяемо до 1М вызовов без линейного роста.

## Альтернативы

Если упрёмся в лимиты YC Functions:

- **Compute VM** (`s2.micro` 2vCPU+2GB) — ₽300-400/мес, тёплый, без cold start
- **Serverless Containers** — для тяжёлых deps (libreoffice для DOCX→PDF)

См. `memory/project_kns_yandex_cloud_plan.md` для подробностей.
