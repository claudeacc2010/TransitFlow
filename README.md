# TransitFlow Mangystau

Веб-платформа координации автотранзита Мангистауской области. Одна база — три роли — один деплой:

- **Грузоотправитель** создаёт заявку на перевозку и видит загруженность узлов в реальном времени.
- **Перевозчик** берёт заявку, бронирует тайм-слот прохождения узла (порт / погранпереход) и получает QR-пропуск.
- **Аналитик акимата** видит сводный дашборд транзита: карта области, графики динамики, прогноз загрузки, AI-сводка аномалий и PDF-отчёт.

Координационный слой «последней мили» для авто-транзита: не заменяет госсистемы (АСТАНА-1, КТЖ, портовые ИС), а закрывает нижний слой — региональных автоперевозчиков и малый бизнес, и готов к интеграции с госсистемами через API.

> Подробная спецификация продукта и решений — в [`SPEC_TransitFlow.md`](SPEC_TransitFlow.md).
> Инструкция по деплою — в [`DEPLOY.md`](DEPLOY.md).

## Данные: что реальное, что синтетика

Узлы и маршруты — **реальные** (реальные координаты объектов Мангистау на карте). Трафик — **синтетический**, сгенерирован с реалистичными паттернами (недельная сезонность, суточные пики, 3–4 аномальных дня) и откалиброван на публичную статистику (12+ млн т/год через порт Актау). 90 дней почасовой истории — основа аналитики и прогноза.

## Стек

- **Backend:** FastAPI, SQLAlchemy 2.x, PostgreSQL (psycopg 3), JWT (python-jose), reportlab (PDF).
- **Frontend:** React + Vite, react-leaflet (OpenStreetMap), Recharts, qrcode.react.
- **AI-сводка:** Gemini или Claude API (по конфигу), с graceful-fallback на кешированную сводку без ключа.
- **Деплой:** один URL — FastAPI раздаёт собранный фронт как статику (ноль CORS-боли в проде). Railway + управляемый Postgres.

## Демо-аккаунты

| Роль | Логин | Пароль |
|---|---|---|
| Грузоотправитель | `shipper@demo` | `demo123` |
| Перевозчик | `carrier@demo` | `demo123` |
| Аналитик акимата | `analyst@demo` | `demo123` |
| Аналитик (питч) | `akimat@123` | `123456` |

На странице логина есть кнопки быстрого входа.

## Локальный запуск

Нужны: Python 3.12+, Node 18+, Docker (для Postgres).

### 1. Postgres

```bash
docker compose up -d db
```

Поднимет Postgres на `localhost:5432` (БД/пользователь/пароль — `transitflow`).

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # при необходимости отредактируй

python seed.py              # наполнить БД: 90 дней истории, узлы, демо-юзеры, заявки, слоты
uvicorn app.main:app --reload --port 8000
```

API поднимется на http://localhost:8000 (Swagger — `/docs`, health — `/api/health`).

Переменные окружения (`backend/.env`, см. `.env.example`):

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | строка подключения Postgres (схема `postgresql+psycopg://`) |
| `JWT_SECRET` | секрет подписи JWT (в проде — длинная случайная строка) |
| `AI_PROVIDER` | `gemini` (по умолчанию) или `claude` |
| `GEMINI_API_KEY` | ключ Google AI Studio (опционально) |
| `ANTHROPIC_API_KEY` | ключ Claude API (опционально, при `AI_PROVIDER=claude`) |

Без AI-ключа сводка работает в fallback-режиме — демо не падает.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev          # Vite на http://localhost:5173, ходит в API на :8000
```

Для прода фронт собирается (`npm run build`) и кладётся в `backend/app/static` — тогда бэкенд раздаёт его с того же домена. Подробности — в [`DEPLOY.md`](DEPLOY.md).

## Smoke-чеклист демо-сценария

1. Войти как `shipper@demo` → создать заявку (тип груза, тоннаж, маршрут, дата).
2. Войти как `carrier@demo` → увидеть заявку в ленте → принять → забронировать слот на узле → получить QR-пропуск.
3. Открыть публичную страницу пропуска `/pass/{qr_token}` (без авторизации — судья сканирует QR со сцены).
4. Войти как `analyst@demo` → карта узлов с цветом загрузки, графики динамики (90 дней) и разбивок, прогноз, AI-сводка, лента событий, PDF-отчёт.
5. Проверить, что действия из шагов 1–2 отразились в ленте событий аналитика.

## Архитектура

```
TransitFlow/
├── SPEC_TransitFlow.md      ← спецификация продукта (источник правды)
├── DEPLOY.md                ← инструкция деплоя (Railway)
├── docker-compose.yml       ← локальный Postgres
├── backend/                 ← FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── main.py          ← FastAPI app, раздаёт API и статику фронта
│   │   ├── models.py        ← SQLAlchemy модели
│   │   ├── schemas.py       ← Pydantic схемы
│   │   ├── auth.py          ← JWT, роли
│   │   ├── routers/         ← auth, requests, slots, bookings, analytics, …
│   │   ├── forecast.py      ← прогноз: среднее по (день недели × час) + тренд
│   │   ├── ai_summary.py    ← AI-сводка (Gemini/Claude) + fallback
│   │   └── reports.py       ← PDF-отчёт для акимата
│   ├── seed.py              ← идемпотентный генератор синтетики + демо-юзеры
│   └── requirements.txt
└── frontend/                ← React + Vite + Leaflet + Recharts
```
