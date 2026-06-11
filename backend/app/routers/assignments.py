"""Статусы перевозки (§3): перевозчик продвигает груз по этапам.

Цепочка: confirmed → awaiting_loading → in_transit → at_checkpoint → at_port
→ delivered. Двигаться можно только вперёд; при delivered заявка закрывается
(RequestStatus.done). Каждый переход обновляет status_updated_at — это питает
степпер у отправителя и ленту событий у аналитика.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_role
from app.db import get_db
from app.models import (
    Assignment,
    CargoRequest,
    RequestStatus,
    ShipmentStatus,
    SHIPMENT_ORDER,
    User,
    UserRole,
)
from app.schemas import AssignmentOut, ShipmentStatusUpdate
from app.serializers import assignment_out

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.patch("/{assignment_id}/status", response_model=AssignmentOut)
def update_shipment_status(
    assignment_id: int,
    payload: ShipmentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.carrier)),
) -> AssignmentOut:
    asg = db.scalar(
        select(Assignment)
        .options(selectinload(Assignment.carrier), selectinload(Assignment.booking))
        .where(Assignment.id == assignment_id)
    )
    if asg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Назначение не найдено")
    if asg.carrier_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это не ваш рейс")

    cur_idx = SHIPMENT_ORDER.index(asg.shipment_status)
    new_idx = SHIPMENT_ORDER.index(payload.status)
    if new_idx <= cur_idx:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Статус можно двигать только вперёд по цепочке",
        )

    asg.shipment_status = payload.status
    asg.status_updated_at = datetime.now(timezone.utc)
    # Доставлено → заявка завершена.
    if payload.status is ShipmentStatus.delivered:
        req = db.get(CargoRequest, asg.request_id)
        if req is not None:
            req.status = RequestStatus.done
    db.commit()
    db.refresh(asg)
    return assignment_out(asg)
