# Шаг 0 — Создать отдельный folder для kns-calculator

## Зачем

Сейчас в cloud `cloud-servoug` (id `b1gafatuvqpp5e9lp7sh`) есть только один folder `default` (id `b1g6culuo3737j3pbupu`), в котором живёт content factory (SA `ai-studio-cfed21`). Чтобы изолировать ресурсы kns-calculator, создадим отдельный folder.

## Что было сделано через MCP (откатить или оставить?)

В рамках первичной настройки 2026-05-09 я создал в **default folder**:

- Service Account `kns-calculator-api` (id `ajeur7e0n1k1n458t79n`)
- Назначены IAM-роли на default folder:
  - `serverless.functions.invoker`
  - `storage.viewer`

**Решение:** перенесём SA в новый folder вручную или удалим и пересоздадим.

## Создание folder через веб-консоль (1 минута)

1. Открыть <https://console.yandex.cloud/cloud/b1gafatuvqpp5e9lp7sh>
2. Кнопка **«Создать каталог»** (Create folder) в правом верхнем углу
3. Параметры:
   - **Имя:** `kns-calculator`
   - **Описание:** `Калькулятор подбора КНС/ВНС/ЛОС для Серво-Юг (production)`
   - **Метки:** `project=kns-calculator`
4. Нажать **«Создать»**
5. Скопировать новый folder ID (формат `b1g...`)

## Альтернатива через CLI (после yc init)

```powershell
yc resource-manager folder create `
    --name kns-calculator `
    --description "Калькулятор подбора КНС/ВНС/ЛОС для Серво-Юг" `
    --labels project=kns-calculator
```

CLI вернёт ID — сохраните его.

## После создания folder — сообщите ID

Пришлите folder ID в чат. Я:

1. Откачу IAM-роли SA `kns-calculator-api` с **default folder** (чистка)
2. Назначу те же роли на новый **kns-calculator folder**
3. Обновлю README/build.sh с новым folder ID
4. Продолжу деплой function в новый folder

## Затем

После этого SA полностью изолирован в `kns-calculator` folder, а content factory остаётся в `default`. Никаких пересечений.

Если потом понадобится S3 bucket для dataset, YDB для метрик — всё это будет в **kns-calculator** folder.
