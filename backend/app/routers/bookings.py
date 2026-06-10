"""Бронирование слотов (раздел 7) с транзакционной проверкой ёмкости.

Бизнес-правила (раздел 5):
  - бронь уменьшает свободную ёмкость слота; при booked_count == capacity
    слот недоступен — проверка под блокировкой строки;
  - слот бронируется только для принятой заявки и только её перевозчиком.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db import get_db
from app.models import (
    Assignment,
    Booking,
    RequestStatus,
    Slot,
    User,
    UserRole,
)
from app.schemas import BookingBrief, BookingCreate
from app.serializers import booking_brief

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingBrief, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.carrier)),
) -> BookingBrief:
    asg = db.scalar(select(Assignment).where(Assignment.id == payload.assignment_id))
    if asg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Назначение не найдено")
    if asg.carrier_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Это назначение принадлежит другому перевозчику",
        )

    req = asg.request
    if req.status is not RequestStatus.accepted:
        # Уже забронировано (slot_booked) либо заявка закрыта/отменена.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Слот можно бронировать только для принятой заявки",
        )

    # Защита от двойной брони на одно назначение.
    existing = db.scalar(select(Booking).where(Booking.assignment_id == asg.id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="По этому назначению уже есть бронь",
        )

    # Блокируем слот: одновременные брони не превысят ёмкость.
    slot = db.scalar(select(Slot).where(Slot.id == payload.slot_id).with_for_update())
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Слот не найден")
    if slot.booked_count >= slot.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Слот заполнен, выберите другое время",
        )

    booking = Booking(slot_id=slot.id, assignment_id=asg.id)  # qr_token = uuid4 по умолчанию
    slot.booked_count += 1
    req.status = RequestStatus.slot_booked
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking_brief(booking)
