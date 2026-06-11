"""Сборка вложенных API-ответов из ORM-объектов.

Заявка тянет за собой назначение → бронь → слот → узел. `from_attributes`
сам по себе не достанет starts_at/checkpoint_name из связанных таблиц, поэтому
вложенные части собираем здесь явно. Роутеры заявок и броней используют это
вместе, чтобы не дублировать логику.
"""
from __future__ import annotations

from app.models import Assignment, Booking, CargoRequest
from app.schemas import (
    AssignmentOut,
    BookingBrief,
    RequestOut,
    UserBrief,
)


def booking_brief(booking: Booking) -> BookingBrief:
    slot = booking.slot
    return BookingBrief(
        id=booking.id,
        slot_id=booking.slot_id,
        qr_token=booking.qr_token,
        status=booking.status,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        checkpoint_name=slot.checkpoint.name,
    )


def assignment_out(asg: Assignment) -> AssignmentOut:
    return AssignmentOut(
        id=asg.id,
        carrier=UserBrief.model_validate(asg.carrier),
        truck_plate=asg.truck_plate,
        accepted_at=asg.accepted_at,
        booking=booking_brief(asg.booking) if asg.booking else None,
    )


def request_out(req: CargoRequest) -> RequestOut:
    return RequestOut(
        id=req.id,
        shipper=UserBrief.model_validate(req.shipper),
        cargo_type=req.cargo_type,
        weight_t=float(req.weight_t),
        origin=req.origin,
        destination=req.destination,
        desired_date=req.desired_date,
        volume_m3=float(req.volume_m3) if req.volume_m3 is not None else None,
        adr_class=req.adr_class,
        temp_mode=req.temp_mode,
        ready_at=req.ready_at,
        urgency=req.urgency,
        distance_km=float(req.distance_km) if req.distance_km is not None else None,
        price_offer=float(req.price_offer) if req.price_offer is not None else None,
        status=req.status,
        created_at=req.created_at,
        assignment=assignment_out(req.assignment) if req.assignment else None,
    )
