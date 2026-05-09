#!/usr/bin/env bash
# Сборка zip-пакета для Yandex Cloud Functions
#
# Использование:
#   cd deploy/yandex-cloud && bash build.sh
#
# Выход: kns-calculator.zip готов для yc serverless function version create

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/_build"
OUT_ZIP="$SCRIPT_DIR/kns-calculator.zip"

echo "[*] Очистка предыдущей сборки"
rm -rf "$BUILD_DIR" "$OUT_ZIP"
mkdir -p "$BUILD_DIR"

echo "[*] Копирую handler.py + requirements.txt"
cp "$SCRIPT_DIR/handler.py" "$BUILD_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$BUILD_DIR/"

echo "[*] Копирую pump_calculator/ (без __pycache__ и .ruff_cache)"
rsync -a --exclude='__pycache__' --exclude='.ruff_cache' \
    --exclude='*.pyc' --exclude='*.pyo' \
    "$REPO_ROOT/backend/pump_calculator/" "$BUILD_DIR/pump_calculator/"

echo "[*] Копирую 02_dataset/ (только публичные файлы)"
mkdir -p "$BUILD_DIR/02_dataset"
# Копируем только нужные подпапки, без _inbox, _analysis, etalons/downloads_*
for sub in pumps fittings theory etl_seed; do
    if [ -d "$REPO_ROOT/02_dataset/$sub" ]; then
        rsync -a "$REPO_ROOT/02_dataset/$sub/" "$BUILD_DIR/02_dataset/$sub/"
    fi
done

# Публичные эталоны (обезличенные)
if [ -d "$REPO_ROOT/02_dataset/etalons/public" ]; then
    mkdir -p "$BUILD_DIR/02_dataset/etalons/public"
    rsync -a "$REPO_ROOT/02_dataset/etalons/public/" "$BUILD_DIR/02_dataset/etalons/public/"
fi

echo "[*] Установка зависимостей в _build/ (для bundling)"
pip install -r "$SCRIPT_DIR/requirements.txt" --target "$BUILD_DIR" --upgrade --quiet

echo "[*] Создаю zip-архив"
cd "$BUILD_DIR"
zip -rq "$OUT_ZIP" . -x "*.pyc" -x "*/__pycache__/*"

SIZE_MB=$(du -m "$OUT_ZIP" | cut -f1)
echo "[+] Готово: $OUT_ZIP ($SIZE_MB МБ)"
echo ""
echo "Следующий шаг (PowerShell):"
echo ""
echo "  # Создать функцию (один раз)"
echo "  yc serverless function create --name kns-calculator-api"
echo ""
echo "  # Загрузить версию"
echo "  yc serverless function version create \`"
echo "      --function-name kns-calculator-api \`"
echo "      --runtime python311 \`"
echo "      --entrypoint handler.handler \`"
echo "      --memory 512m \`"
echo "      --execution-timeout 30s \`"
echo "      --service-account-id ajeur7e0n1k1n458t79n \`"
echo "      --source-path $OUT_ZIP \`"
echo "      --environment KNS_DATASET_ROOT=./02_dataset"
echo ""
echo "  # Сделать публично доступной"
echo "  yc serverless function allow-unauthenticated-invoke kns-calculator-api"
