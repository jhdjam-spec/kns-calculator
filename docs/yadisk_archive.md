# Архив ТЗ на Яндекс.Диск (Серво-Юг)

После того как менеджер парсит ТЗ через `POST /import/parse`, оригинал
текста автоматически копируется в архив Серво-Юг на Яндекс.Диск.
Это даёт полный audit-trail входящих заявок, возможность вернуться к
исходнику если парсер пропустил что-то, и удобный share с инженером.

## Структура архива

```
/inservo_tz_archive/
├── 2026-05-11/
│   ├── 2026-05-11_14-30-22_Q88.6_кнс_Краснодар.txt
│   └── техзадание_крокус.pdf       # при file-upload — оригинальное имя
├── 2026-05-12/
│   └── ...
```

Имя файла собирается из:
- даты/времени UTC,
- расхода Q (если распознан),
- типа объекта (КНС/ЛОС/ВНС/...),
- города.

Если в `POST /import/parse` передан `original_filename` — используется как есть.

## Получение OAuth-токена Яндекс.Диска

Для API нужен **OAuth token с правом записи на Диск** (scope `cloud_api:disk.write`).

### Шаг 1. Создать приложение в Яндекс OAuth

1. Зайти на https://oauth.yandex.ru/client/new под аккаунтом Серво-Юг.
2. Указать имя приложения (например, `kns-calculator-archive`).
3. Платформа: **Web-сервис**, redirect URL: `https://oauth.yandex.ru/verification_code`
   (для устройств без коллбэка).
4. Запросить права:
   - `cloud_api:disk.read` — Чтение всего Диска.
   - `cloud_api:disk.write` — Запись в любом месте Диска.
   - `cloud_api:disk.app_folder` — (опц.) Доступ к папке приложения.
5. Создать. Скопировать `Client ID`.

### Шаг 2. Получить токен по device-flow

В браузере открыть:

```
https://oauth.yandex.ru/authorize?response_type=token&client_id=<CLIENT_ID>
```

Авторизоваться → скопировать `access_token` из URL после редиректа
(параметр после `#access_token=`).

Токен бессрочный, но **может быть отозван** в личном кабинете
https://id.yandex.ru/security/applications.

### Шаг 3. Положить токен в YC Functions environment

```bash
yc serverless function version create \
    --function-name kns-calculator-api \
    --runtime python311 \
    --entrypoint handler.handler \
    --memory 512m \
    --execution-timeout 30s \
    --source-path ./deploy/yandex-cloud/kns-calculator.zip \
    --environment YANDEX_DISK_TOKEN=<paste_token_here>
```

Или через UI YC: Cloud Functions → `kns-calculator-api` → Edit version
→ Environment variables → add `YANDEX_DISK_TOKEN`.

### Проверка

После деплоя, отправить тестовый запрос:

```bash
curl -X POST https://d5dnu7r53036cq815mes.apigw.yandexcloud.net/import/parse \
    -H "Content-Type: application/json" \
    -d '{"text": "Q=88.6 м³/ч, напор 39 м, г. Краснодар"}'
```

В ответе должно быть:

```json
{
  ...,
  "archive_path": "/inservo_tz_archive/2026-05-11/2026-05-11_14-30-22_Q88.6_Краснодар.txt",
  "archive_error": null,
  "archive_size_bytes": 42
}
```

Если `archive_error` содержит `YANDEX_DISK_TOKEN not configured` — токен
не подхватился; перепроверить ENV.

Если `archive_error: "Unauthorized — token invalid or expired"` — токен
протух или отозван; получить новый.

## Privacy / Что хранится

В архив попадает **только текст ТЗ**, который менеджер вставляет в форму.

Это **не** содержит personal data (email менеджера, контакты клиента и т.п.)
если только сам менеджер не вставил их в ТЗ. В таком случае хранение
оправдано — тексты ТЗ это рабочий business-материал Серво-Юг.

Архив **не публичный** — лежит на корпоративном Яндекс.Диске Серво-Юг,
доступ только у владельцев аккаунта.

## Graceful degradation

Если `YANDEX_DISK_TOKEN` **не задан** или валидный:
- `/import/parse` **не падает** — парсинг продолжает работать.
- В ответе: `archive_path=null, archive_error="..."`.
- Фронт показывает **жёлтый warning** в правой колонке, не блокируя UX.

## Лимиты Я.Диск API

- 40 запросов / секунду (rate limit).
- Файлы до 50 GB (но для нашего use-case это plain-text 1-100 KB).
- Бесплатный тариф: 10 GB. Этого хватит на годы архива ТЗ.
- Платный business-аккаунт Серво-Юг (если есть): 100 GB / 1 TB / 3 TB.

## Source

- `backend/pump_calculator/etl/yadisk_uploader.py` — клиент REST API.
- `backend/pump_calculator/api.py` (`/import/parse`) — вызывает `archive_tz_text`.
- `backend/tests/test_yadisk_uploader.py` — 21 unit-тест с mock opener.

## Reference

- Я.Диск REST API: https://yandex.ru/dev/disk/api/reference/all-files.html
- OAuth Яндекс: https://yandex.ru/dev/id/doc/dg/oauth/concepts/about.html
- Получение токена: https://yandex.ru/dev/id/doc/dg/oauth/reference/web-client.html
