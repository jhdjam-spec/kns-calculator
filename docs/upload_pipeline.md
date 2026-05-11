# TZ Upload Pipeline — S3 primary + Yandex.Disk mirror + dataset enrichment

Pipeline для архивации входящих ТЗ от менеджеров Серво-Юг.
Менеджер вставляет произвольный текст ТЗ в `/import`, frontend шлёт
`POST /import/parse`, backend парсит + архивирует + (по confidence)
обогащает dataset эталонов.

## Архитектура

```
                     Frontend (TZImportForm)
                              |
                              | POST /import/parse {text, original_filename}
                              v
              backend.api.import_parse_tz()
                              |
              +---------------+----------------+----------------------+
              v               v                v                      v
        tz_parser.parse_tz   yadisk_uploader  s3_uploader            dataset_enrichment
        (regex)             (mirror)          (primary)              (categorize)
              |               |                |                      |
              | TZParseResult |                |                      |
              | confidence    |                |                      |
              v               v                v                      v
        response.dict     /inservo_tz_      s3://kns-calculator-     etalons_uploaded.jsonl
                         archive/<date>/    tz-archive/...           _queue/<id>.json  
                          (text only)       (text + parsed.json      _rejected/<id>.json
                                            + catalog.jsonl)
```

## Двухуровневый архив

| Цель | S3 primary | Yandex.Disk mirror |
|------|-----------|---------------------|
| Назначение | Backend pipeline, audit, /admin/uploads UI | Менеджеры через привычный Я.Диск |
| Bucket / Path | `kns-calculator-tz-archive/tz_archive/YYYY/MM/DD/` | `/inservo_tz_archive/YYYY-MM-DD/` |
| Файлы на upload | 2 объекта: `*.txt` + `*.parsed.json` + строка в `_metadata/catalog.jsonl` | 1 файл `*.txt` |
| Метаданные | S3 object metadata (upload-id, confidence, Q-m3h, ...) | в имени файла |
| Доступ | Приватный (только backend) | Read доступ у Серво-Юг |
| Зависимость | `boto3` (lazy import) | stdlib `urllib` (zero-deps) |
| Graceful degradation | да (нет креденшалов → no-op) | да (нет токена → no-op) |

## Структура S3

```
kns-calculator-tz-archive/
├── tz_archive/
│   ├── 2026/
│   │   └── 05/
│   │       └── 11/
│   │           ├── 14-30-22_Q88.6_kns_Krasnodar_a1b2c3.txt
│   │           └── 14-30-22_Q88.6_kns_Krasnodar_a1b2c3.parsed.json
│   └── _metadata/
│       └── catalog.jsonl       (append-only лог всех uploads)
```

Имя ключа: `tz_archive/{YYYY}/{MM}/{DD}/{HH-MM-SS}_Q{Q}_{type}_{city}_{hash6}.{ext}`.
Кириллица в `city` транслитерируется в ASCII (`Краснодар → Krasnodar`),
оригинал хранится в S3 object metadata.

## Dataset enrichment правила

| Confidence | Status | Куда пишем |
|-----------|--------|-----------|
| `≥ 0.7` | `auto_accepted` | `02_dataset/etalons/from_uploads/etalons_uploaded.jsonl` (append) |
| `0.5 .. 0.7` | `queued` | `02_dataset/etalons/from_uploads/_queue/<id>.json` (ручной review) |
| `< 0.5` | `archived_only` | только S3, в dataset не попадает |

Confidence = доля 4 ключевых полей (Q, H, city, wastewater_type), которые
удалось извлечь. См. `pump_calculator.etl.tz_parser`.

## API endpoints

### `POST /import/parse` (расширенный response)

```json
{
  "Q_m3h": 88.6,
  "dH_m": 39.0,
  "city": "Краснодар",
  "wastewater_type": "domestic",
  "confidence": 1.0,
  // ... остальные TZParseResult поля

  // Legacy flat keys (sub a4a5e58e, для обратной совместимости):
  "archive_path": "/inservo_tz_archive/2026-05-11/...",
  "archive_error": null,
  "archive_size_bytes": 1234,

  // Nested mirror form:
  "yadisk_archive": {
    "path": "/inservo_tz_archive/2026-05-11/...",
    "error": null,
    "size_bytes": 1234
  },

  // S3 primary archive:
  "s3_archive": {
    "bucket": "kns-calculator-tz-archive",
    "key": "tz_archive/2026/05/11/14-30-22_Q88.6_kns_Krasnodar_a1b2c3.txt",
    "parsed_key": "tz_archive/2026/05/11/...parsed.json",
    "upload_id": "upload-2026-05-11-143022-a1b2c3",
    "size_bytes": 1234,
    "url": "https://storage.yandexcloud.net/kns-calculator-tz-archive/...",
    "configured": true,
    "error": null
  },

  // Dataset enrichment результат:
  "dataset_eligible": true,
  "dataset_enrichment": {
    "status": "auto_accepted",
    "confidence": 1.0,
    "upload_id": "upload-2026-05-11-143022-a1b2c3",
    "record_path": "02_dataset/etalons/from_uploads/etalons_uploaded.jsonl",
    "jsonl_appended": true,
    "error": null
  }
}
```

### `/admin/uploads` (MVP без auth — TODO: JWT перед public)

- `GET /admin/uploads?limit=100&source=jsonl|queue|s3` — список upload'ов
- `GET /admin/uploads/{upload_id}` — детальный просмотр
- `POST /admin/uploads/{upload_id}/approve` — перенести queued → jsonl
- `POST /admin/uploads/{upload_id}/reject` `{reason}` — пометить нерелевантным
- `POST /admin/uploads/merge` — собрать `etalons_uploaded.jsonl` →
  `etalons_from_uploads.json` с дедупликацией против canonical etalons

## ENV конфигурация

### Yandex.Disk (sub a4a5e58e)
- `YANDEX_DISK_TOKEN` — OAuth token Серво-Юг (scope `cloud_api:disk.write`)

### S3 primary
- `KNS_S3_BUCKET_TZ` — bucket name (default `kns-calculator-tz-archive`)
- `KNS_S3_ENDPOINT` — endpoint (default `https://storage.yandexcloud.net`)
- `KNS_S3_PREFIX` — корневой префикс (default `tz_archive/`)
- `KNS_S3_REGION` — регион (default `ru-central1`)
- `AWS_ACCESS_KEY_ID` — static access key для S3-совместимого API YC
- `AWS_SECRET_ACCESS_KEY` — секрет

Креды для local dev хранятся в `~/.claude/.secrets/yc-s3.env` (см.
`deploy/yandex-cloud/sync_frontend.py` — тот же формат).

### Dataset enrichment
- `KNS_DATASET_ROOT` — путь к `02_dataset` (default — относительно файла).
  В YC Functions поставить read-only путь, либо отключить.
- `KNS_DATASET_ENRICHMENT_DISABLED=1` — выключить целиком (для prod
  с read-only FS).

## Создание bucket

Bucket приватный (только backend пишет/читает). Через `yc CLI`:

```bash
yc storage bucket create --name kns-calculator-tz-archive \
    --folder-id b1ge2mgg8tgh92uerm9c \
    --public-read=false \
    --default-storage-class standard
```

Опционально — настроить lifecycle policy (через S3 PutBucketLifecycle):
- raw .txt → standard storage forever (audit-trail)
- catalog.jsonl → standard forever
- старые `*.parsed.json` после 1 года → cold storage (стоит дешевле)

## Privacy / Retention

| Данные | Retention | Privacy |
|--------|-----------|---------|
| `tz_archive/.../*.txt` (оригинал) | forever (audit) | Приватный bucket, ACL=private |
| `tz_archive/.../*.parsed.json` | forever | Same |
| `_metadata/catalog.jsonl` | forever | Same |
| `/inservo_tz_archive/<date>/*.txt` (Я.Диск) | 1 год (manual cleanup) | Доступ менеджерам Серво-Юг |
| `etalons_uploaded.jsonl` (dataset) | forever | Public-открытый dataset, но без `raw_text`/PII |
| `_queue/<id>.json` | до approve/reject | Содержит `raw_text` (приватно) |
| `_rejected/<id>.json` | forever (audit) | Содержит `raw_text` (приватно) |

ВАЖНО: `raw_text` ТЗ может содержать персональные данные заказчика
(имя ГИП, контакты). В `etalons_uploaded.jsonl` `raw_text` НЕ пишется —
только структурированные поля + s3_key как ссылка на оригинал.

## Sample full flow

1. Менеджер вставляет в `/import` текст:
   ```
   ТЗ на КНС жилого комплекса. Q=88.6 м³/ч, H=39 м.
   г. Краснодар, бытовые стоки, шифр 1578-22-НК.
   ```
2. Frontend → `POST /import/parse {"text": "...", "original_filename": "tz.txt"}`
3. Backend:
   - `parse_tz()` → confidence=1.0, Q=88.6, H=39, city=Krasnodar, type=domestic
   - `archive_tz_text()` → `/inservo_tz_archive/2026-05-11/2026-05-11_14-30-22_Q88.6_kns_krasnodar.txt`
   - `archive_tz_to_s3()`:
     - PUT `tz_archive/2026/05/11/14-30-22_Q88.6_kns_Krasnodar_a1b2c3.txt`
     - PUT `tz_archive/2026/05/11/14-30-22_Q88.6_kns_Krasnodar_a1b2c3.parsed.json`
     - APPEND в `tz_archive/_metadata/catalog.jsonl`
   - `enrich_from_parse()`: confidence=1.0 → auto_accepted → APPEND в
     `02_dataset/etalons/from_uploads/etalons_uploaded.jsonl`:
     ```json
     {"id": "upload-2026-05-11-143022-a1b2c3", "Q_m3h": 88.6, "dH_m": 39, ...,
      "source": "user_import", "s3_key": "tz_archive/...", "confidence": 1.0}
     ```
4. Frontend получает `dataset_eligible=true` + `s3_archive.url` — может
   показать «Сохранено в архив, добавлено в эталоны».
5. (Ежедневно) `POST /admin/uploads/merge` → создаёт/обновляет
   `02_dataset/etalons/public/etalons_from_uploads.json` (deduped).

## Тестирование

```bash
cd backend
./.venv/Scripts/python.exe -m pytest tests/test_s3_uploader.py tests/test_dataset_enrichment.py
```

Всего: 8 тестов S3 uploader + 9 тестов dataset enrichment + 21 yadisk = 38
тестов покрытия pipeline'а. Все используют mocks/tmp dirs — реальный S3 / Я.Диск
НЕ требуются для прогона тестов.
