"""Smoke ленты событий (Этап 2, шаг 13) против живой БД.

Проверяет: лента непуста, поля на месте, kind из набора, сортировка по
времени убыв., limit работает, роль-гард (shipper -> 403).
Запуск:  python smoke_events.py
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
ok = True


def check(cond: bool, msg: str) -> None:
    global ok
    mark = "OK  " if cond else "FAIL"
    print(f"  [{mark}] {msg}")
    if not cond:
        ok = False


def login(email: str) -> str:
    r = c.post("/api/auth/login", json={"email": email, "password": "demo123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


an = login("analyst@demo")
sh = login("shipper@demo")
auth = lambda t: {"Authorization": f"Bearer {t}"}

print("1) Роль-гард: shipper не видит ленту")
r = c.get("/api/events", headers=auth(sh))
check(r.status_code == 403, f"shipper -> {r.status_code} (ожидался 403)")

print("2) Лента аналитика непуста и валидна")
r = c.get("/api/events", headers=auth(an))
check(r.status_code == 200, f"GET /api/events -> {r.status_code}")
ev = r.json()
check(len(ev) > 0, f"событий: {len(ev)}")
kinds = {"request", "accept", "booking"}
check(all(e["kind"] in kinds for e in ev), "все kind из набора request/accept/booking")
check(all(e["title"] and e["detail"] for e in ev), "у всех есть title и detail")

print("3) Сортировка по времени убыв.")
ts = [e["ts"] for e in ev]
check(ts == sorted(ts, reverse=True), "события отсортированы от новых к старым")

print("4) limit работает")
r = c.get("/api/events", headers=auth(an), params={"limit": 5})
check(len(r.json()) <= 5, f"limit=5 -> {len(r.json())} событий")

print(f"       пример: [{ev[0]['kind']}] {ev[0]['title']} — {ev[0]['detail'][:60]}")

print()
print("ИТОГ:", "ВСЁ ЗЕЛЁНОЕ" if ok else "ЕСТЬ ПАДЕНИЯ")
sys.exit(0 if ok else 1)
