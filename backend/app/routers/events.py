"""Лента событий платформы для дашборда аналитика (раздел 9, шаг 13).

Событий как отдельной таблицы нет — собираем их из таймстампов реальных
действий: создание заявки, принятие перевозчиком, бронь слота (= выдача QR).
Фронт поллит каждые 5 сек; на демо судья проходит поток shipper→carrier, и
эти события всплывают здесь живьём.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_role
from app.db import get_db
from app.models import Assignment, Booking, CargoRequest, ShipmentStatus, User, UserRole
from app.schemas import EventOut

router = APIRouter(prefix="/api", tags=["events"])

_CARGO_RU = {
    "container": "контейнер",
    "bulk": "навалочный",
    "liquid": "наливной",
    "general": "генеральный",
    "food": "продукты",
    "grain": "зерно",
    "oil_products": "нефтепродукты",
    "construction": "стройматериалы",
    "chemicals": "химикаты",
}

# §3: подписи этапов перевозки для ленты (показываем движение, не подтверждение).
_SHIPMENT_RU = {
    ShipmentStatus.awaiting_loading: "ожидает погрузки",
    ShipmentStatus.in_transit: "в пути",
    ShipmentStatus.at_checkpoint: "на пункте пропуска",
    ShipmentStatus.at_port: "в порту",
    ShipmentStatus.delivered: "доставлено",
}


def _fmt_window(starts_at, ends_at) -> str:
    return f"{starts_at:%d.%m} {starts_at:%H:%M}–{ends_at:%H:%M} UTC"


@router.get("/events", response_model=list[EventOut])
def list_events(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(UserRole.analyst)),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[EventOut]:
    events: list[EventOut] = []

    # Новые заявки.
    reqs = db.scalars(
        select(CargoRequest)
        .options(joinedload(CargoRequest.shipper))
        .order_by(CargoRequest.created_at.desc())
        .limit(limit)
    )
    for r in reqs:
        events.append(
            EventOut(
                kind="request",
                ts=r.created_at,
                title="Новая заявка",
                detail=f"{r.shipper.name}: {r.origin} → {r.destination}, "
                f"{_CARGO_RU.get(r.cargo_type.value, r.cargo_type.value)} {float(r.weight_t):g} т",
            )
        )

    # Принятия перевозчиком.
    asgs = db.scalars(
        select(Assignment)
        .options(joinedload(Assignment.carrier), joinedload(Assignment.request))
        .order_by(Assignment.accepted_at.desc())
        .limit(limit)
    )
    for a in asgs:
        events.append(
            EventOut(
                kind="accept",
                ts=a.accepted_at,
                title="Заявка принята",
                detail=f"{a.carrier.name} · {a.truck_plate}: "
                f"{a.request.origin} → {a.request.destination}",
            )
        )

    # §3: переходы статуса перевозки (движение груза по этапам).
    moves = db.scalars(
        select(Assignment)
        .options(joinedload(Assignment.request))
        .where(Assignment.shipment_status.in_(list(_SHIPMENT_RU.keys())))
        .order_by(Assignment.status_updated_at.desc())
        .limit(limit)
    )
    for a in moves:
        events.append(
            EventOut(
                kind="shipment",
                ts=a.status_updated_at,
                title=f"Груз: {_SHIPMENT_RU[a.shipment_status]}",
                detail=f"{a.truck_plate}: {a.request.origin} → {a.request.destination}",
            )
        )

    # Брони слотов (= выдача QR-пропуска).
    bookings = db.scalars(
        select(Booking)
        .options(joinedload(Booking.slot))
        .order_by(Booking.created_at.desc())
        .limit(limit)
    )
    for b in bookings:
        slot = b.slot
        events.append(
            EventOut(
                kind="booking",
                ts=b.created_at,
                title="Слот забронирован",
                detail=f"{slot.checkpoint.name}, {_fmt_window(slot.starts_at, slot.ends_at)} · пропуск выдан",
            )
        )

    events.sort(key=lambda e: e.ts, reverse=True)
    return events[:limit]
