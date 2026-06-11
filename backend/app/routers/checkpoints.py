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


def _queue_estimates(db: Session, capacities: dict[int, int]) -> dict[int, tuple[int, float]]:
    """{checkpoint_id: (машин в очереди сейчас, ожидание в часах)}.

    §5 (главная боль кейса): моделируем очередь как накопление, когда поток
    прибытия за час превышает пропускную способность узла. Берём последние 24
    почасовых среза истории и прогоняем простую модель массового обслуживания:
        q_t = max(0, q_{t-1} + прибыло_t − пропускная_способность_в_час)
    Текущее q — это очередь «сейчас», ожидание = q / пропускная способность.
    """
    th = TrafficHistory
    per_hour = (
        select(th.checkpoint_id, th.ts, func.sum(th.trucks_count).label("arr"))
        .group_by(th.checkpoint_id, th.ts)
        .subquery()
    )
    rows = db.execute(
        select(per_hour.c.checkpoint_id, per_hour.c.ts, per_hour.c.arr)
        .order_by(per_hour.c.checkpoint_id, per_hour.c.ts)
    ).all()

    series: dict[int, list[int]] = {}
    for cp_id, _ts, arr in rows:
        series.setdefault(cp_id, []).append(int(arr))

    result: dict[int, tuple[int, float]] = {}
    for cp_id, arrivals in series.items():
        cap = capacities.get(cp_id) or 1
        q = 0.0
        for arr in arrivals[-24:]:  # последние сутки
            q = max(0.0, q + arr - cap)
        # Потолок: затор сверх суточной ёмкости — это уже «критично»,
        # дальше цифры неинформативны. Ожидание ограничиваем 24 ч.
        waiting = min(int(round(q)), cap * 24)
        est_wait = round(min(q / cap, 24.0), 1)
        result[cp_id] = (waiting, est_wait)
    return result


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
    checkpoints = list(db.scalars(select(Checkpoint).order_by(Checkpoint.name)))
    loads = _last_hour_loads(db)
    capacities = {cp.id: cp.capacity_per_hour for cp in checkpoints}
    queues = _queue_estimates(db, capacities)
    out = []
    for cp in checkpoints:
        trucks = loads.get(cp.id, 0)
        waiting, wait_h = queues.get(cp.id, (0, 0.0))
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
                capacity_per_day=cp.capacity_per_hour * 24,
                waiting_now=waiting,
                est_wait_hours=wait_h,
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
