"""Подключение к Postgres, сессии и Base. create_all без Alembic (раздел 9, этап 0)."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: сессия на запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создаёт таблицы по метаданным моделей. Вызывается на старте приложения и в сиде."""
    # Импорт моделей обязателен, чтобы они зарегистрировались в Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Мини-миграция (без Alembic): create_all не добавляет колонки в уже
    # существующие таблицы. DEFAULT true — существующие пользователи (сид,
    # ранняя саморегистрация) считаются подтверждёнными, не запираем их.
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "email_verified BOOLEAN NOT NULL DEFAULT true"
        ))
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
            "verify_token VARCHAR(64)"
        ))
