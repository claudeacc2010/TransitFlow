"""Публичная страница пропуска /pass/{qr_token} (раздел 5, 7).

БЕЗ авторизации: QR ведёт сюда, судья сканирует телефоном и видит пропуск.
Рендерим самодостаточный HTML прямо из FastAPI (фронт-билд для этого не нужен).
"""
from __future__ import annotations

from html import escape
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Booking, BookingStatus, CargoType

router = APIRouter(tags=["pass"])

_CARGO_RU = {
    CargoType.container: "Контейнер",
    CargoType.bulk: "Навалочный",
    CargoType.liquid: "Наливной",
    CargoType.general: "Генеральный",
}
_STATUS_RU = {
    BookingStatus.booked: ("Забронирован", "#F5A623"),
    BookingStatus.arrived: ("Прибыл", "#3FB68B"),
    BookingStatus.passed: ("Проехал", "#3FB68B"),
    BookingStatus.no_show: ("Не явился", "#E2574C"),
}


def _page(booking: Booking) -> str:
    slot = booking.slot
    cp = slot.checkpoint
    asg = booking.assignment
    req = asg.request
    carrier = asg.carrier
    shipper = req.shipper

    status_label, status_color = _STATUS_RU.get(booking.status, (booking.status.value, "#E8ECF1"))
    cargo_label = _CARGO_RU.get(req.cargo_type, req.cargo_type.value)
    window = f'{slot.starts_at:%d.%m.%Y}, {slot.starts_at:%H:%M}–{slot.ends_at:%H:%M} UTC'

    rows = [
        ("Узел", escape(cp.name)),
        ("Окно прохождения", escape(window)),
        ("Гос. номер", escape(asg.truck_plate)),
        ("Перевозчик", escape(f"{carrier.name} · {carrier.company or '—'}")),
        ("Отправитель", escape(f"{shipper.name} · {shipper.company or '—'}")),
        ("Груз", escape(f"{cargo_label}, {float(req.weight_t):g} т")),
        ("Маршрут", escape(f"{req.origin} → {req.destination}")),
    ]
    rows_html = "".join(
        f'<div class="row"><span class="k">{k}</span><span class="v">{v}</span></div>'
        for k, v in rows
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Пропуск · TransitFlow</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #14181F; color: #E8ECF1; padding: 24px;
    font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  }}
  .card {{
    width: 100%; max-width: 460px; background: #1C222B; border-radius: 16px;
    border: 1px solid #2A323F; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,.45);
  }}
  .head {{
    padding: 20px 24px; border-bottom: 1px solid #2A323F;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .brand {{ font-weight: 700; letter-spacing: .5px; color: #F5A623; }}
  .brand small {{ display:block; color:#8A94A6; font-weight:500; letter-spacing:.3px; }}
  .badge {{
    padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 600;
    color: {status_color}; border: 1px solid {status_color}55; background: {status_color}1a;
  }}
  .body {{ padding: 8px 24px 20px; }}
  .row {{ display: flex; justify-content: space-between; gap: 16px; padding: 12px 0;
          border-bottom: 1px solid #232a35; }}
  .row:last-child {{ border-bottom: none; }}
  .k {{ color: #8A94A6; font-size: 14px; }}
  .v {{ text-align: right; font-weight: 600;
        font-family: 'JetBrains Mono','IBM Plex Mono', ui-monospace, monospace; }}
  .foot {{ padding: 14px 24px; border-top: 1px solid #2A323F; color:#5d6675; font-size:12px;
           font-family: 'JetBrains Mono', ui-monospace, monospace; word-break: break-all; }}
</style>
</head>
<body>
  <div class="card">
    <div class="head">
      <div class="brand">TransitFlow<small>Цифровой пропуск</small></div>
      <div class="badge">{escape(status_label)}</div>
    </div>
    <div class="body">{rows_html}</div>
    <div class="foot">QR: {escape(str(booking.qr_token))}</div>
  </div>
</body>
</html>"""


@router.get("/pass/{qr_token}", response_class=HTMLResponse)
def view_pass(qr_token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    try:
        token = UUID(qr_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пропуск не найден")

    booking = db.scalar(select(Booking).where(Booking.qr_token == token))
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пропуск не найден")

    return HTMLResponse(_page(booking))
