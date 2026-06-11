"""Полный сброс схемы БД (без Alembic, раздел 9).

Нужен, когда на проде остался устаревший Postgres-тип ENUM или столбец:
`create_all` создаёт только недостающие таблицы и НИКОГДА не меняет уже
существующие типы/колонки. Поэтому после добавления новых значений в enum
(например, новые виды груза в cargo_type) старый прод-тип их не знает и INSERT
падает. Здесь — разовый сброс: дропаем таблицы и enum-типы, дальше `init_db()`
пересоздаёт всё по актуальным моделям, а seed наполняет заново.

Запускается из seed.py только при переменной окружения RESET_DB=1 — чтобы
случайно не стереть прод. Все данные синтетические (сид), потеря не страшна.
"""
from __future__ import annotations

from sqlalchemy import text

from app.db import Base, engine

# Имена Postgres-типов ENUM (совпадают с name= в models._enum).
_ENUM_TYPES = [
    "user_role",
    "checkpoint_kind",
    "cargo_type",
    "urgency",
    "request_status",
    "shipment_status",
    "booking_status",
    "direction",
]


def reset_database() -> None:
    """Дропает все таблицы и enum-типы. Вызывать ДО init_db()."""
    from app import models  # noqa: F401 — регистрация таблиц в Base.metadata

    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        for type_name in _ENUM_TYPES:
            conn.execute(text(f'DROP TYPE IF EXISTS "{type_name}" CASCADE'))
