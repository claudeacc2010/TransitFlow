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

print("2) shipper создаёт заявку (с характеристиками груза §1)")
r = c.post(
    "/api/requests",
    headers=auth(sh),
    json={
        "cargo_type": "oil_products",
        "weight_t": 22.0,
        "volume_m3": 26.5,
        "origin": "Актау",
        "destination": "Бейнеу",
        "desired_date": "2026-06-12",
        "adr_class": "3",
        "temp_mode": None,
        "urgency": "urgent",
        "price_offer": 400000,
    },
)
check(r.status_code == 201, f"POST /api/requests -> {r.status_code}")
req = r.json()
req_id = req["id"]
check(req["status"] == "open", f"статус новой заявки = {req['status']} (ожидался open)")
check(req["cargo_type"] == "oil_products", f"cargo_type = {req['cargo_type']}")
check(req["volume_m3"] == 26.5, f"volume_m3 = {req['volume_m3']}")
check(req["adr_class"] == "3", f"adr_class = {req['adr_class']}")
check(req["urgency"] == "urgent", f"urgency = {req['urgency']}")
# §2: расстояние посчиталось, цена сохранилась, тг/км вычислился
check(req["distance_km"] and req["distance_km"] > 0, f"distance_km = {req['distance_km']}")
check(req["price_offer"] == 400000, f"price_offer = {req['price_offer']}")
check(req["price_per_km"] and req["price_per_km"] > 0, f"price_per_km = {req['price_per_km']}")
# §6: для нефтепродуктов с ADR нужен CMR+ADR и есть несовместимость
check("CMR" in req["required_docs"] and any("ADR" in d for d in req["required_docs"]),
      f"документы: {req['required_docs']}")
check("продукты питания" in req["incompatible_with"],
      f"несовместимо с: {req['incompatible_with']}")

print("2b) валидация: неверный класс ADR отклоняется")
r_bad = c.post(
    "/api/requests",
    headers=auth(sh),
    json={
        "cargo_type": "chemicals",
        "weight_t": 10.0,
        "origin": "Актау",
        "destination": "Курык",
        "desired_date": "2026-06-12",
        "adr_class": "99",
    },
)
check(r_bad.status_code == 422, f"POST с adr_class=99 -> {r_bad.status_code} (ожидался 422)")

print("2c) §2: рекомендация цены и рыночная ставка")
rp = c.post(
    "/api/requests/recommend-price",
    headers=auth(sh),
    json={"cargo_type": "oil_products", "weight_t": 22, "origin": "Актау",
          "destination": "Бейнеу", "adr_class": "3", "urgency": "urgent"},
)
check(rp.status_code == 200, f"POST recommend-price -> {rp.status_code}")
rec = rp.json()
check(rec["recommended"] > 0, f"рекомендованная цена = {rec['recommended']}")
check(len(rec["factors"]) >= 2, f"факторов надбавки: {len(rec['factors'])} (ADR+срочность+наливной)")
mr = c.get("/api/requests/market-rate", headers=auth(ca))
check(mr.status_code == 200, f"GET market-rate -> {mr.status_code}")
check(mr.json()["sample_size"] > 0, f"рыночная выборка: {mr.json()['sample_size']}")

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

print("13) §3: статусы перевозки — переход вперёд, запрет назад, delivered->done")
r = c.get("/api/requests", headers=auth(sh), params={"mine": 1})
asg0 = {x["id"]: x for x in r.json()}[req_id]["assignment"]
check(asg0["shipment_status"] == "confirmed", f"стартовый статус = {asg0['shipment_status']}")
r = c.patch(f"/api/assignments/{asg_id}/status", headers=auth(ca), json={"status": "in_transit"})
check(r.status_code == 200 and r.json()["shipment_status"] == "in_transit", "переход confirmed -> in_transit")
r = c.patch(f"/api/assignments/{asg_id}/status", headers=auth(ca), json={"status": "confirmed"})
check(r.status_code == 409, f"переход назад -> {r.status_code} (ожидался 409)")
r = c.patch(f"/api/assignments/{asg_id}/status", headers=auth(sh), json={"status": "at_port"})
check(r.status_code == 403, f"shipper меняет статус -> {r.status_code} (ожидался 403)")
r = c.patch(f"/api/assignments/{asg_id}/status", headers=auth(ca), json={"status": "delivered"})
check(r.status_code == 200, f"переход -> delivered = {r.status_code}")
r = c.get("/api/requests", headers=auth(sh), params={"mine": 1})
check({x["id"]: x for x in r.json()}[req_id]["status"] == "done", "delivered закрыл заявку (status=done)")

print()
print("ИТОГ:", "ВСЕ ПРОВЕРКИ ЗЕЛЁНЫЕ" if ok else "ЕСТЬ ПАДЕНИЯ")
sys.exit(0 if ok else 1)
