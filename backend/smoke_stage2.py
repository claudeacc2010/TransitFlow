"""Smoke-тест Этапа 2 (бэкенд аналитики) против живой БД (раздел 9, шаг 10).

Прогон: analyst логинится → узлы с загрузкой → прогноз → overview →
timeseries → breakdown×3 → ai-summary. Плюс роль-гард: shipper в аналитику
не допущен. Запуск:  python smoke_stage2.py
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


def login(email: str, password: str = "demo123") -> str:
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


print("1) Логин analyst@demo + роль-гард")
an = login("analyst@demo")
sh = login("shipper@demo")
check(bool(an), "токен аналитика получен")
r = c.get("/api/analytics/overview", headers=auth(sh))
check(r.status_code == 403, f"shipper в /analytics/overview -> {r.status_code} (ожидался 403)")

print("2) Узлы с текущей загрузкой")
r = c.get("/api/checkpoints", headers=auth(an))
check(r.status_code == 200, f"GET /api/checkpoints -> {r.status_code}")
cps = r.json()
check(len(cps) >= 3, f"узлов: {len(cps)}")
check(all("trucks_last_hour" in cp and "load_pct" in cp for cp in cps), "у всех узлов есть загрузка")
check(any(cp["trucks_last_hour"] > 0 for cp in cps), "хотя бы на одном узле трафик > 0")
# §5: очереди
check(all({"waiting_now", "est_wait_hours", "capacity_per_day"} <= cp.keys() for cp in cps),
      "у всех узлов есть оценка очереди (waiting_now/est_wait_hours/capacity_per_day)")
check(any(cp["est_wait_hours"] > 0 for cp in cps), "хотя бы на одном узле есть очередь")
check(any(cp["est_wait_hours"] == 0 for cp in cps), "хотя бы один узел свободен (контраст)")

print("3) Прогноз по самому загруженному узлу")
busiest = max(cps, key=lambda cp: cp["load_pct"])
r = c.get(f"/api/checkpoints/{busiest['id']}/forecast", headers=auth(an), params={"days": 7})
check(r.status_code == 200, f"GET forecast -> {r.status_code}")
fc = r.json()
check(len(fc["points"]) == 7 * 24, f"точек прогноза: {len(fc['points'])} (ожидалось 168)")
check(all(p["trucks_expected"] >= 0 for p in fc["points"]), "прогноз неотрицательный")
check(sum(p["trucks_expected"] for p in fc["points"]) > 0, "прогноз не нулевой")
r404 = c.get("/api/checkpoints/99999/forecast", headers=auth(an))
check(r404.status_code == 404, f"forecast несуществующего узла -> {r404.status_code} (ожидался 404)")

print("4) Overview")
r = c.get("/api/analytics/overview", headers=auth(an))
check(r.status_code == 200, f"GET overview -> {r.status_code}")
ov = r.json()
print(f"       {ov}")
check(ov["trucks_today"] > 0, f"машин за сутки: {ov['trucks_today']}")
check(ov["active_requests"] >= 0, f"активных заявок: {ov['active_requests']}")
check(0 <= ov["avg_load_pct"] <= 200, f"средняя загрузка: {ov['avg_load_pct']}%")

print("5) Timeseries 90 дней")
r = c.get("/api/analytics/timeseries", headers=auth(an), params={"days": 90})
check(r.status_code == 200, f"GET timeseries -> {r.status_code}")
ts = r.json()
check(85 <= len(ts) <= 91, f"точек: {len(ts)} (ожидалось ~90)")
check(all(p["trucks"] > 0 for p in ts), "во всех днях трафик > 0")
r = c.get("/api/analytics/timeseries", headers=auth(an), params={"days": 90, "checkpoint_id": busiest["id"]})
ts_one = r.json()
total_all = sum(p["trucks"] for p in ts)
total_one = sum(p["trucks"] for p in ts_one)
check(0 < total_one < total_all, f"фильтр по узлу сужает: {total_one} < {total_all}")

print("6) Breakdown по трём разрезам")
sums = {}
for by in ("cargo_type", "direction", "checkpoint"):
    r = c.get("/api/analytics/breakdown", headers=auth(an), params={"by": by, "days": 90})
    check(r.status_code == 200, f"breakdown by={by} -> {r.status_code}")
    items = r.json()
    check(len(items) >= 2, f"  by={by}: категорий {len(items)}")
    sums[by] = sum(i["trucks"] for i in items)
check(
    sums["cargo_type"] == sums["direction"] == sums["checkpoint"],
    f"суммы разрезов сходятся: {sums}",
)
r = c.get("/api/analytics/breakdown", headers=auth(an), params={"by": "hacker"})
check(r.status_code == 422, f"breakdown by=hacker -> {r.status_code} (ожидался 422)")

print("6b) §4: рекомендация маршрута с учётом очередей")
r = c.get("/api/routes/recommend", headers=auth(an),
          params={"origin": "Актау", "destination": "Туркменистан"})
check(r.status_code == 200, f"GET routes/recommend -> {r.status_code}")
rr = r.json()
check(len(rr["options"]) == 2, f"вариантов маршрута: {len(rr['options'])}")
rec = [o for o in rr["options"] if o["recommended"]]
check(len(rec) == 1, "ровно один вариант помечен рекомендованным")
check(rec[0]["reason"], f"у рекомендованного есть причина: {rec[0].get('reason')}")
# рекомендованный должен иметь минимальный total_hours
check(rec[0]["total_hours"] == min(o["total_hours"] for o in rr["options"]),
      "рекомендован вариант с минимальным total_hours (с учётом очередей)")
# у каждого варианта total = base + queue
check(all(abs(o["total_hours"] - (o["base_hours"] + o["queue_hours"])) < 0.05 for o in rr["options"]),
      "total_hours = base_hours + queue_hours для всех вариантов")
# незнакомая пара -> один прямой вариант
r2 = c.get("/api/routes/recommend", headers=auth(an),
           params={"origin": "Прага", "destination": "Лиссабон"})
check(r2.status_code == 200 and len(r2.json()["options"]) == 1,
      "незнакомая пара -> один прямой вариант (fallback)")

print("7) AI-сводка (живой вызов провайдера)")
r = c.post("/api/analytics/ai-summary", headers=auth(an))
check(r.status_code == 200, f"POST ai-summary -> {r.status_code}")
summ = r.json()
check(len(summ["summary"]) > 50, f"текст сводки {len(summ['summary'])} симв.")
check(summ["provider"] in ("gemini", "claude", "cache", "fallback"), f"источник: {summ['provider']}")
if summ["provider"] in ("cache", "fallback"):
    print("       ВНИМАНИЕ: сводка не от живого API — проверь ключ/сеть")
print(f"       [{summ['provider']}] {summ['summary'][:160]}...")

print()
print("ИТОГ:", "ВСЁ ЗЕЛЁНОЕ" if ok else "ЕСТЬ ПАДЕНИЯ")
sys.exit(0 if ok else 1)
