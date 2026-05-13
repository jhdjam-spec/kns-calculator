#!/usr/bin/env bash
# Создание YC Trigger'ов для kns-calculator.
#
# Требует:
#   - yc CLI (https://cloud.yandex.ru/docs/cli/quickstart)
#   - предварительно `yc init` с активным профилем для folder kns-calc
#   - service-account ajeur7e0n1k1n458t79n с ролью functions.functionInvoker
#   - ENV YC_INTERNAL_TOKEN в Function-настройках (не в этом скрипте!)
#
# Запуск:
#   bash deploy/yandex-cloud/setup_triggers.sh
#
# Идемпотентность: если trigger с таким именем уже есть — `yc create` упадёт
# с ошибкой «already exists», что безопасно. Для re-create — сначала `yc delete`.

set -euo pipefail

FOLDER_ID="b1ge2mgg8tgh92uerm9c"
FUNCTION_ID="d4echfb1ckrlkv68vog5"
SA_ID="ajeur7e0n1k1n458t79n"

echo "→ Создаём trigger 'daily-merge-uploads' (00:00 UTC = 03:00 МСК)..."

yc serverless trigger timer create \
    --name daily-merge-uploads \
    --description "Daily merge of etalons_uploaded.jsonl → canonical etalons JSON" \
    --folder-id "${FOLDER_ID}" \
    --cron-expression "0 0 * * ? *" \
    --invoke-function-id "${FUNCTION_ID}" \
    --invoke-function-service-account-id "${SA_ID}" \
    --invoke-function-tag '$latest' \
    --retry-attempts 1 \
    --retry-interval 60s

echo "✔ Trigger создан. Проверить:"
echo "    yc serverless trigger list --folder-id ${FOLDER_ID}"
echo "    yc serverless trigger get --name daily-merge-uploads"
echo ""
echo "⚠ ВАЖНО: убедись что в Function kns-calculator-api заданы ENV:"
echo "    YC_INTERNAL_TOKEN=<random-32-bytes>   # для /admin/uploads/merge-internal"
echo "    ADMIN_PASS=<...>                       # для остальных /admin/*"
echo ""
echo "Сгенерировать новый токен:"
echo "    openssl rand -hex 32"
