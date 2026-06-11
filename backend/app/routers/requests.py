"""Заявки на перевозку (раздел 7): создание, лента, принятие перевозчиком."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import (
    Assignment,
    CargoRequest,
    RequestStatus,
    User,
    UserRole,
)
from app.schemas import AcceptRequestIn, RequestCreate, RequestOut
from app.serializers import request_out

router = APIRouter(prefix="/api/requests", tags=["requests"])

# Жадная загрузка всей цепочки заявки: отправитель + назначение →
# перевозчик и бронь → слот → узел. Без неё — N+1 на каждую строку ленты.
_EAGER = (
    selectinload(CargoRequest.shipper),
    selectinload(CargoRequest.assignment).selectinload(Assignment.carrier),
    selectinload(CargoRequest.assignment)
    .selectinload(Assignment.booking),
)


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.shipper)),
) -> RequestOut:
    req = CargoRequest(
        shipper_id=user.id,
        cargo_type=payload.cargo_type,
        weight_t=payload.weight_t,
        origin=payload.origin,
        destination=payload.destination,
        desired_date=payload.desired_date,
        volume_m3=payload.volume_m3,
        adr_class=payload.adr_class,
        temp_mode=payload.temp_mode,
        ready_at=payload.ready_at,
        urgency=payload.urgency,
        status=RequestStatus.open,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return request_out(req)


@router.get("", response_model=list[RequestOut])
def list_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    mine: int = Query(default=0),
) -> list[RequestOut]:
    """Лента заявок.

    - `?status=open` — открытые заявки (лента перевозчика);
    - `?mine=1` — «мои» с учётом роли: отправитель видит свои заявки,
      перевозчик — те, что принял (для брони слота и QR).
    """
    stmt = select(CargoRequest).options(*_EAGER).order_by(CargoRequest.created_at.desc())

    if mine:
        if user.role is UserRole.shipper:
            stmt = stmt.where(CargoRequest.shipper_id == user.id)
        elif user.role is UserRole.carrier:
            stmt = stmt.join(CargoRequest.assignment).where(
                Assignment.carrier_id == user.id
            )
        # analyst + mine=1 — без доп. фильтра (видит всё)

    if status_filter is not None:
        stmt = stmt.where(CargoRequest.status == status_filter)

    rows = db.scalars(stmt).all()
    return [request_out(r) for r in rows]


@router.post("/{request_id}/accept", response_model=RequestOut)
def accept_request(
    request_id: int,
    payload: AcceptRequestIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.carrier)),
) -> RequestOut:
    """Перевозчик принимает открытую заявку (раздел 5: только carrier).

    Блокируем строку заявки на время транзакции, чтобы двое перевозчиков
    не приняли одну заявку одновременно.
    """
    req = db.scalar(
        select(CargoRequest).where(CargoRequest.id == request_id).with_for_update()
    )
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    if req.status is not RequestStatus.open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Заявку уже приняли или она недоступна",
        )

    asg = Assignment(
        request_id=req.id,
        carrier_id=user.id,
        truck_plate=payload.truck_plate.strip(),
    )
    db.add(asg)
    req.status = RequestStatus.accepted
    db.commit()

    req = db.scalar(
        select(CargoRequest).options(*_EAGER).where(CargoRequest.id == request_id)
    )
    return request_out(req)
