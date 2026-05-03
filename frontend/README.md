# Frontend (Next.js 14)

React Wizard L0 для kns-calculator. Менеджер вводит 4 поля → видит 3 карточки насосов в ценовых сегментах.

## Стек

- **Next.js 14** (App Router)
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
├── next.config.mjs         ← rewrites /api/backend/* → http://localhost:8000/*
└── vitest.config.ts
```

## Установка и запуск

```bash
cd frontend
npm install
npm run dev
# открыть http://localhost:3000
```

Backend должен крутиться на `http://localhost:8000`:

```bash
cd ../backend
./.venv/Scripts/python.exe -m uvicorn pump_calculator.api:app --reload
```

При запуске на другом хосте — переменная `NEXT_PUBLIC_API_BASE`:

```bash
NEXT_PUBLIC_API_BASE=https://api.example.com npm run dev
```

## Тесты

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm test            # vitest run
```

## Деплой

Целевая платформа — **Vercel** (free tier). Backend деплоится отдельно (Timeweb / Render / Fly.io), `NEXT_PUBLIC_API_BASE` указывает на его домен.

## Что НЕ делает MVP

- Нет L1/L2 полей (опциональные параметры) — только L0
- Нет PDF-экспорта (Phase 4)
- Нет авторизации
- Нет истории расчётов (это будущая интеграция с CRM)
