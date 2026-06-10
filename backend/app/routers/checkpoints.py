"""Узлы с текущей загрузкой + прогноз (раздел 7, Этап 2).

GET /api/checkpoints переехал сюда из slots.py и обогащён загрузкой за
последний час истории — этим питается карта Leaflet (узлы-индикаторы).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.forecast import forecast_checkpoint
from app.models import Checkpoint, TrafficHistory, User
from app.schemas import CheckpointLoadOut, ForecastOut

router = APIRouter(prefix="/api", tags=["catalog"])


def _last_hour_loads(db: Session) -> dict[int, int]:
    """{checkpoint_id: машин за последний час истории узла}.

    «Последний час» — max(ts) по узлу, а не now()-1h: сид мог закончиться
    чуть в прошлом, а карта должна показывать загрузку всегда.
    """
    th = TrafficHistory
    last_ts = (
        select(th.checkpoint_id, func.max(th.ts).label("ts"))
        .group_by(th.checkpoint_id)
        .subquery()
    )
    rows = db.execute(
        select(th.checkpoint_id, func.sum(th.trucks_count))
        .join(last_ts, (th.checkpoint_id == last_ts.c.checkpoint_id) & (th.ts == last_ts.c.ts))
        .group_by(th.checkpoint_id)
    ).all()
    return {cp_id: int(trucks) for cp_id, trucks in rows}


@router.get("/checkpoints", response_model=list[CheckpointLoadOut])
def list_checkpoints(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[CheckpointLoadOut]:
    loads = _last_hour_loads(db)
    out = []
    for cp in db.scalars(select(Checkpoint).order_by(Checkpoint.name)):
        trucks = loads.get(cp.id, 0)
        out.append(
            CheckpointLoadOut(
                id=cp.id,
                name=cp.name,
                kind=cp.kind,
                lat=float(cp.lat),
                lng=float(cp.lng),
                capacity_per_hour=cp.capacity_per_hour,
                trucks_last_hour=trucks,
                load_pct=round(trucks / cp.capacity_per_hour * 100, 1) if cp.capacity_per_hour else 0.0,
            )
        )
    return out


@router.get("/checkpoints/{checkpoint_id}/forecast", response_model=ForecastOut)
def checkpoint_forecast(
    checkpoint_id: int,
    days: int = Query(default=7, ge=1, le=14),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ForecastOut:
    cp = db.get(Checkpoint, checkpoint_id)
    if cp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Узел не найден")

    return ForecastOut(
        checkpoint_id=checkpoint_id,
        days=days,
        points=forecast_checkpoint(db, checkpoint_id, days),
    )
