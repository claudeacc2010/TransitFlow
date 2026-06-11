"""Точка входа FastAPI. Этап 1: auth + поток заявок; Этап 2: аналитика."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import analytics as analytics_router
from app.routers import assignments as assignments_router
from app.routers import auth as auth_router
from app.routers import bookings as bookings_router
from app.routers import checkpoints as checkpoints_router
from app.routers import events as events_router
from app.routers import passes as passes_router
from app.routers import requests as requests_router
from app.routers import routes as routes_router
from app.routers import slots as slots_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all на старте (без Alembic, раздел 9). Идемпотентно.
    init_db()
    yield


app = FastAPI(
    title="TransitFlow Mangystau API",
    version="0.1.0",
    lifespan=lifespan,
)

# Vite-дев крутится на 5173, бэкенд на 8000 — для локальной разработки
# разрешаем фронту ходить в API. На Railway фронт раздаётся статикой с того же
# домена, так что прод это не ослабляет.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(requests_router.router)
app.include_router(routes_router.router)
app.include_router(assignments_router.router)
app.include_router(checkpoints_router.router)
app.include_router(slots_router.router)
app.include_router(bookings_router.router)
app.include_router(passes_router.router)
app.include_router(analytics_router.router)
app.include_router(events_router.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "transitflow"}


# --- Раздача собранного фронтенда (Vite) с того же домена ---------------------
# На Railway корень сборки — backend/, поэтому фронт собирается локально и
# кладётся в backend/app/static (коммитится в репозиторий). Локально без сборки
# каталога просто нет — API работает как раньше, фронт крутится на Vite :5173.
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        # Маршруты API и /pass зарегистрированы выше и перехватываются раньше;
        # на всякий случай не отдаём им index.html, а честно возвращаем 404.
        if full_path.startswith(("api/", "pass/")):
            raise HTTPException(status_code=404)
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # Любой клиентский маршрут React Router → отдаём SPA-оболочку.
        return FileResponse(STATIC_DIR / "index.html")
