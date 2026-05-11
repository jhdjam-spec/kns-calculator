# Frontend (Next.js 14)

React Wizard L0 для kns-calculator. Менеджер вводит 4 поля → видит 3 карточки насосов в ценовых сегментах.

## Стек

- **Next.js 14** (App Router, static export для Yandex Object Storage)
- **TypeScript** strict
- **Tailwind CSS** для стилей
- **Zod** для валидации (зеркалит Pydantic L0Input из backend)
- **React Hook Form** для управления формой
- **TanStack Query** для вызовов backend API
- **Vitest** + **Testing Library** для тестов

## Структура

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx      ← QueryClientProvider, базовый layout
│   │   ├── page.tsx        ← главная: <WizardL0> + <ResultsCards>
│   │   └── globals.css     ← Tailwind directives
│   ├── components/
│   │   ├── WizardL0.tsx    ← форма 4 полей
│   │   ├── ResultsCards.tsx ← 3 карточки (Бюджет/Средний/Премиум)
│   │   └── HandoffPanel.tsx ← кнопка «Передать инженеру» + триггеры
│   ├── hooks/
│   │   └── usePumpSelection.ts ← TanStack Query mutation → POST /api/backend/select/quick
│   ├── schemas/
│   │   └── input.ts        ← Zod схема L0Input (зеркало backend/schemas.py)
│   ├── lib/
│   │   └── api.ts          ← fetch wrapper для backend
│   └── __tests__/
│       ├── input.test.ts
│       └── WizardL0.test.tsx
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs         ← dev: rewrites /api/backend/* → localhost:8000
│                             prod: static export для YC Object Storage
└── vitest.config.ts
```

## Установка и запуск dev-сервера

```bash
cd frontend
npm install
npm run dev
# открыть http://localhost:3000
```

Backend для dev должен крутиться на `http://localhost:8000`:

```bash
cd ../backend
./.venv/Scripts/python.exe -m uvicorn pump_calculator.api:app --reload
```

В dev-режиме `next.config.mjs` проксирует `/api/backend/*` → `http://localhost:8000/*`.

## Тесты

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm test            # vitest run
```

## Деплой — Yandex Cloud Object Storage (static)

Production-сборка — **static export** в `frontend/out/`, заливаемый в YC Object
Storage bucket `kns-calculator-frontend` с включённым website hosting.
Backend живёт отдельно: Yandex Cloud Functions + API Gateway.

### Production URL'ы

| Сервис | URL |
|---|---|
| Frontend (YC Object Storage) | https://kns-calculator-frontend.website.yandexcloud.net |
| Backend (YC API Gateway) | https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net |

### Сборка

`NEXT_PUBLIC_API_BASE` указывает абсолютный URL backend — он попадает в
бандл во время сборки (`process.env.NEXT_PUBLIC_*` инлайнятся).

```bash
cd frontend
NEXT_PUBLIC_API_BASE=https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net \
    npm run build
# артефакт: frontend/out/
```

PowerShell:

```powershell
$env:NEXT_PUBLIC_API_BASE="https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net"
npm run build
```

### Заливка в YC Object Storage

Скрипт `deploy/yandex-cloud/sync_frontend.py` использует boto3 с правильными
forward-slash ключами (на Windows `yc storage cp` иногда ломает пути).

```bash
# Креды читаются из ~/.claude/.secrets/yc-s3.env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# либо берутся напрямую из ENV.
python ../deploy/yandex-cloud/sync_frontend.py
```

Контент-типы (`.html`, `.js`, `.css`, `.woff2`, `.svg`, `.json`) и кэш-заголовки
(`no-cache` для html, `public, max-age=31536000, immutable` для `_next/static`)
выставляются автоматически.

### Что НЕ делает MVP

- Нет L1/L2 полей (опциональные параметры) — только L0
- Нет авторизации
- Нет истории расчётов (это будущая интеграция с CRM)
