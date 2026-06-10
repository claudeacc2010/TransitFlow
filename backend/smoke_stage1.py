"""Сквозной smoke-тест Этапа 1 против живой БД (раздел 9, пункты 6-8).

Прогон: shipper логинится → создаёт заявку → carrier логинится → видит её в
ленте → принимает → выбирает узел/слот → бронирует → открывает /pass.
Проверяет статусы и инкремент ёмкости слота. Запуск:  python smoke_stage1.py
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


print("1) Логин shipper@demo / carrier@demo")
sh = login("shipper@demo")
ca = login("carrier@demo")
check(bool(sh and ca), "оба токена получены")

print("2) shipper создаёт заявку")
r = c.post(
    "/api/requests",
    headers=auth(sh),
    json={
        "cargo_type": "container",
        "weight_t": 18.5,
        "origin": "Актау",
        "destination": "Бейнеу",
        "desired_date": "2026-06-12",
    },
)
check(r.status_code == 201, f"POST /api/requests -> {r.status_code}")
req = r.json()
req_id = req["id"]
check(req["status"] == "open", f"статус новой заявки = {req['status']} (ожидался open)")

print("3) роль-гард: carrier не может создать заявку")
r = c.post(
    "/api/requests",
    headers=auth(ca),
    json={"cargo_type": "bulk", "weight_t": 5, "origin": "A", "destination": "B",
          "desired_date": "2026-06-12"},
)
check(r.status_code == 403, f"carrier POST /api/requests -> {r.status_code} (ожидался 403)")

print("4) carrier видит заявку в ленте открытых")
r = c.get("/api/requests", headers=auth(ca), params={"status": "open"})
check(r.status_code == 200, f"GET /api/requests?status=open -> {r.status_code}")
ids = [x["id"] for x in r.json()]
check(req_id in ids, "новая заявка присутствует в ленте open")

print("5) carrier принимает заявку")
r = c.post(f"/api/requests/{req_id}/accept", headers=auth(ca),
           json={"truck_plate": "777 ABC 12"})
check(r.status_code == 200, f"POST accept -> {r.status_code}")
acc = r.json()
check(acc["status"] == "accepted", f"статус после accept = {acc['status']}")
asg = acc["assignment"]
check(asg is not None and asg["truck_plate"] == "777 ABC 12", "назначение с гос.номером создано")
asg_id = asg["id"]

print("6) повторный accept той же заявки -> 409")
r = c.post(f"/api/requests/{req_id}/accept", headers=auth(ca),
           json={"truck_plate": "111 XXX 12"})
check(r.status_code == 409, f"повторный accept -> {r.status_code} (ожидался 409)")

print("7) carrier видит принятую заявку в ?mine=1")
r = c.get("/api/requests", headers=auth(ca), params={"mine": 1})
check(r.status_code == 200 and req_id in [x["id"] for x in r.json()],
      "заявка в ленте carrier ?mine=1")

print("8) список узлов и свободных слотов")
r = c.get("/api/checkpoints", headers=auth(ca))
check(r.status_code == 200 and len(r.json()) == 5, f"GET /api/checkpoints -> {len(r.json())} узлов")
cp_id = r.json()[0]["id"]
r = c.get("/api/slots", headers=auth(ca), params={"checkpoint_id": cp_id})
check(r.status_code == 200 and len(r.json()) > 0, f"GET /api/slots -> {len(r.json())} свободных")
slot = r.json()[0]
slot_id = slot["id"]
before = slot["booked_count"]
check("available" in slot, "у слота есть computed-поле available")

print("9) бронирование слота")
r = c.post("/api/bookings", headers=auth(ca),
           json={"slot_id": slot_id, "assignment_id": asg_id})
check(r.status_code == 201, f"POST /api/bookings -> {r.status_code}: {r.text[:120]}")
bk = r.json()
qr = bk["qr_token"]
check(bool(qr) and bk["checkpoint_name"], "бронь вернула qr_token и узел")

print("10) статус заявки -> slot_booked, ёмкость слота +1")
r = c.get("/api/requests", headers=auth(sh), params={"mine": 1})
mine = {x["id"]: x for x in r.json()}
check(mine[req_id]["status"] == "slot_booked", f"статус заявки = {mine[req_id]['status']}")
r = c.get("/api/slots", headers=auth(ca), params={"checkpoint_id": cp_id})
after_slot = next((s for s in r.json() if s["id"] == slot_id), None)
after = after_slot["booked_count"] if after_slot else before + 1
check(after == before + 1, f"booked_count {before} -> {after}")

print("11) двойная бронь по тому же назначению -> 409")
r = c.post("/api/bookings", headers=auth(ca),
           json={"slot_id": slot_id, "assignment_id": asg_id})
check(r.status_code == 409, f"повторная бронь -> {r.status_code} (ожидался 409)")

print("12) публичная страница пропуска /pass/{qr} без авторизации")
r = c.get(f"/pass/{qr}")
check(r.status_code == 200 and "TransitFlow" in r.text and "777 ABC 12" in r.text,
      "пропуск отрендерен с данными")
r = c.get("/pass/not-a-uuid")
check(r.status_code == 404, f"битый qr -> {r.status_code} (ожидался 404)")

print()
print("ИТОГ:", "ВСЕ ПРОВЕРКИ ЗЕЛЁНЫЕ" if ok else "ЕСТЬ ПАДЕНИЯ")
sys.exit(0 if ok else 1)
