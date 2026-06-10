"""Доступные слоты (раздел 7). Узлы (+загрузка) — routers/checkpoints.py.

Здесь только то, что нужно перевозчику, чтобы забронировать свободный слот.
"""
from __future__ import annotations

from datetime import date as date_cls, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Slot, User
from app.schemas import SlotOut

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/slots", response_model=list[SlotOut])
def list_slots(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    checkpoint_id: int = Query(...),
    date: date_cls | None = Query(default=None),
) -> list[Slot]:
    """Свободные слоты узла. Без даты — все будущие; с датой — за конкретный день (UTC)."""
    stmt = (
        select(Slot)
        .where(Slot.checkpoint_id == checkpoint_id)
        .where(Slot.booked_count < Slot.capacity)
        .order_by(Slot.starts_at)
    )

    if date is not None:
        day_start = datetime.combine(date, time(0), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        stmt = stmt.where(Slot.starts_at >= day_start, Slot.starts_at < day_end)
    else:
        stmt = stmt.where(Slot.starts_at >= datetime.now(timezone.utc))

    return list(db.scalars(stmt))
