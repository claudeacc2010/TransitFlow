"""Аналитика для дашборда акимата (раздел 7, Этап 2). Только роль analyst.

Все окна считаем от max(ts) истории, а не от now(): сид заканчивается «около
сейчас», и дашборд не должен пустеть из-за пары часов рассинхрона.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_summary import generate_summary
from app.auth import require_role
from app.db import get_db
from app.models import (
    CargoRequest,
    CargoType,
    Checkpoint,
    Direction,
    RequestStatus,
    TrafficHistory,
    User,
    UserRole,
)
from app.routers.checkpoints import _last_hour_loads
from app.schemas import AISummaryOut, AnalyticsOverview, BreakdownItem, TimeseriesPoint

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

analyst_only = require_role(UserRole.analyst)

_ACTIVE = (RequestStatus.open, RequestStatus.accepted, RequestStatus.slot_booked)

_CARGO_RU = {
    CargoType.container: "Контейнеры",
    CargoType.bulk: "Навалочные",
    CargoType.liquid: "Наливные",
    CargoType.general: "Генеральные",
}
_DIRECTION_RU = {
    Direction.export: "Экспорт",
    Direction.import_: "Импорт",
    Direction.transit: "Транзит",
}


def _history_end(db: Session) -> datetime:
    """Конец истории (max ts); если истории нет — now()."""
    return db.scalar(select(func.max(TrafficHistory.ts))) or datetime.now(timezone.utc)


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    db: Session = Depends(get_db),
    _user: User = Depends(analyst_only),
) -> AnalyticsOverview:
    end = _history_end(db)

    trucks_today = db.scalar(
        select(func.coalesce(func.sum(TrafficHistory.trucks_count), 0)).where(
            TrafficHistory.ts > end - timedelta(hours=24)
        )
    )

    tons_week = db.scalar(
        select(func.coalesce(func.sum(CargoRequest.weight_t), 0)).where(
            CargoRequest.created_at > end - timedelta(days=7)
        )
    )

    active = db.scalar(
        select(func.count()).select_from(CargoRequest).where(CargoRequest.status.in_(_ACTIVE))
    )

    loads = _last_hour_loads(db)
    cps = list(db.scalars(select(Checkpoint)))
    pcts = [
        loads.get(cp.id, 0) / cp.capacity_per_hour * 100
        for cp in cps
        if cp.capacity_per_hour
    ]
    avg_load = sum(pcts) / len(pcts) if pcts else 0.0

    return AnalyticsOverview(
        trucks_today=int(trucks_today),
        tons_per_day=round(float(tons_week) / 7, 1),
        active_requests=int(active),
        avg_load_pct=round(avg_load, 1),
    )


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def timeseries(
    db: Session = Depends(get_db),
    _user: User = Depends(analyst_only),
    checkpoint_id: int | None = Query(default=None),
    days: int = Query(default=90, ge=1, le=90),
) -> list[TimeseriesPoint]:
    """Машин в сутки за `days` дней — график динамики."""
    end = _history_end(db)
    day = func.date(TrafficHistory.ts).label("date")
    stmt = (
        select(day, func.sum(TrafficHistory.trucks_count).label("trucks"))
        .where(TrafficHistory.ts > end - timedelta(days=days))
        .group_by(day)
        .order_by(day)
    )
    if checkpoint_id is not None:
        stmt = stmt.where(TrafficHistory.checkpoint_id == checkpoint_id)

    return [TimeseriesPoint(date=r.date, trucks=int(r.trucks)) for r in db.execute(stmt)]


@router.get("/breakdown", response_model=list[BreakdownItem])
def breakdown(
    db: Session = Depends(get_db),
    _user: User = Depends(analyst_only),
    by: str = Query(default="cargo_type", pattern="^(cargo_type|direction|checkpoint)$"),
    days: int = Query(default=90, ge=1, le=90),
) -> list[BreakdownItem]:
    """Разбивка потока машин по типу груза / направлению / узлу."""
    end = _history_end(db)
    since = end - timedelta(days=days)

    if by == "checkpoint":
        rows = db.execute(
            select(Checkpoint.name, func.sum(TrafficHistory.trucks_count))
            .join(Checkpoint, Checkpoint.id == TrafficHistory.checkpoint_id)
            .where(TrafficHistory.ts > since)
            .group_by(Checkpoint.name)
            .order_by(func.sum(TrafficHistory.trucks_count).desc())
        ).all()
        return [BreakdownItem(key=name, label=name, trucks=int(t)) for name, t in rows]

    col = TrafficHistory.cargo_type if by == "cargo_type" else TrafficHistory.direction
    labels = _CARGO_RU if by == "cargo_type" else _DIRECTION_RU
    rows = db.execute(
        select(col, func.sum(TrafficHistory.trucks_count))
        .where(TrafficHistory.ts > since)
        .group_by(col)
        .order_by(func.sum(TrafficHistory.trucks_count).desc())
    ).all()
    return [
        BreakdownItem(key=val.value, label=labels.get(val, val.value), trucks=int(t))
        for val, t in rows
    ]


@router.post("/ai-summary", response_model=AISummaryOut)
def ai_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(analyst_only),
) -> AISummaryOut:
    """Собрать реальную статистику из БД и отдать её AI-провайдеру."""
    end = _history_end(db)

    # Карточки (повторяем overview простыми запросами — без хитростей).
    trucks_today = db.scalar(
        select(func.coalesce(func.sum(TrafficHistory.trucks_count), 0)).where(
            TrafficHistory.ts > end - timedelta(hours=24)
        )
    )
    active = db.scalar(
        select(func.count()).select_from(CargoRequest).where(CargoRequest.status.in_(_ACTIVE))
    )

    # Самый загруженный узел за неделю и пиковый час за 90 дней.
    busiest = db.execute(
        select(Checkpoint.name, func.sum(TrafficHistory.trucks_count).label("t"))
        .join(Checkpoint, Checkpoint.id == TrafficHistory.checkpoint_id)
        .where(TrafficHistory.ts > end - timedelta(days=7))
        .group_by(Checkpoint.name)
        .order_by(func.sum(TrafficHistory.trucks_count).desc())
    ).first()

    peak = db.execute(
        select(
            func.extract("hour", TrafficHistory.ts).label("hour"),
            func.avg(TrafficHistory.trucks_count).label("avg_t"),
        )
        .group_by("hour")
        .order_by(func.avg(TrafficHistory.trucks_count).desc())
    ).first()

    stats = {
        "машин_за_последние_сутки": int(trucks_today),
        "активных_заявок": int(active),
        "самый_загруженный_узел_за_неделю": busiest.name if busiest else "н/д",
        "пиковый_час_UTC": f"{int(peak.hour):02d}:00" if peak else "н/д",
        "период_истории_дней": 90,
    }

    text, source = generate_summary(stats)
    return AISummaryOut(summary=text, provider=source, generated_at=datetime.now(timezone.utc))
