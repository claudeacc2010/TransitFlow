"""Точка входа FastAPI. Этап 1: auth + поток заявок; Этап 2: аналитика."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import analytics as analytics_router
from app.routers import auth as auth_router
from app.routers import bookings as bookings_router
from app.routers import checkpoints as checkpoints_router
from app.routers import passes as passes_router
from app.routers import requests as requests_router
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
app.include_router(checkpoints_router.router)
app.include_router(slots_router.router)
app.include_router(bookings_router.router)
app.include_router(passes_router.router)
app.include_router(analytics_router.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "transitflow"}
