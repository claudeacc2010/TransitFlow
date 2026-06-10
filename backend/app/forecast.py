"""Прогноз загрузки узла (раздел 4 спеки): бейзлайн, честно НЕ ML.

Для узла берём среднее число машин по каждой паре (день недели × час) за всю
историю traffic_history, сглаживаем суточный профиль соседними часами и
домножаем на тренд (последние 14 дней против всего периода). На питче это
называется «бейзлайн-модель, архитектура готова к замене на ML».
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import TrafficHistory

# Тренд зажимаем, чтобы выброс синтетики не рисовал безумный прогноз.
_TREND_MIN, _TREND_MAX = 0.5, 1.5


def _hourly_totals(db: Session, checkpoint_id: int):
    """Часовые суммы машин по узлу: traffic_history хранит строки в разрезе
    (cargo_type × direction), для профиля нужен общий поток за час."""
    return (
        select(
            TrafficHistory.ts.label("ts"),
            func.sum(TrafficHistory.trucks_count).label("trucks"),
        )
        .where(TrafficHistory.checkpoint_id == checkpoint_id)
        .group_by(TrafficHistory.ts)
        .subquery()
    )


def _profile(db: Session, checkpoint_id: int) -> dict[tuple[int, int], float]:
    """Средние машины/час по (isoweekday 1–7, hour 0–23)."""
    hourly = _hourly_totals(db, checkpoint_id)
    rows = db.execute(
        select(
            func.extract("isodow", hourly.c.ts).label("dow"),
            func.extract("hour", hourly.c.ts).label("hour"),
            func.avg(hourly.c.trucks).label("avg_trucks"),
        ).group_by("dow", "hour")
    ).all()
    return {(int(r.dow), int(r.hour)): float(r.avg_trucks) for r in rows}


def _smooth(profile: dict[tuple[int, int], float]) -> dict[tuple[int, int], float]:
    """Лёгкое сглаживание суточного профиля: час ± сосед с весами 0.25/0.5/0.25."""
    smoothed: dict[tuple[int, int], float] = {}
    for (dow, hour), value in profile.items():
        prev = profile.get((dow, (hour - 1) % 24), value)
        nxt = profile.get((dow, (hour + 1) % 24), value)
        smoothed[(dow, hour)] = 0.25 * prev + 0.5 * value + 0.25 * nxt
    return smoothed


def _trend(db: Session, checkpoint_id: int) -> float:
    """Средний часовой поток за последние 14 дней / за весь период, с зажимом."""
    hourly = _hourly_totals(db, checkpoint_id)
    overall = db.scalar(select(func.avg(hourly.c.trucks)))
    if not overall:
        return 1.0

    since = datetime.now(timezone.utc) - timedelta(days=14)
    recent = db.scalar(select(func.avg(hourly.c.trucks)).where(hourly.c.ts >= since))
    if not recent:
        return 1.0

    return max(_TREND_MIN, min(_TREND_MAX, float(recent) / float(overall)))


def forecast_checkpoint(db: Session, checkpoint_id: int, days: int = 7) -> list[dict]:
    """Почасовой прогноз на `days` дней вперёд от текущего часа (UTC).

    Возвращает [{"ts": datetime, "trucks_expected": float}]; пусто, если по
    узлу нет истории.
    """
    profile = _smooth(_profile(db, checkpoint_id))
    if not profile:
        return []

    trend = _trend(db, checkpoint_id)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    points: list[dict] = []
    for i in range(days * 24):
        ts = start + timedelta(hours=i + 1)
        base = profile.get((ts.isoweekday(), ts.hour), 0.0)
        points.append({"ts": ts, "trucks_expected": round(base * trend, 1)})
    return points
