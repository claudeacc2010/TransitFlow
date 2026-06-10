"""Smoke регистрации (off-spec доп. к Этапу 2) против живой БД.

Проверяет: новый пользователь регистрируется и сразу залогинен (токен валиден
на /auth/me), дубль email -> 409, роль analyst через форму -> 422, короткий
пароль -> 422. Email уникальный по времени запуска, чтобы прогон был идемпотентным.
Запуск:  python smoke_register.py
"""
from __future__ import annotations

import sys
import time

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
ok = True
uniq = int(time.time())
email = f"carrier_{uniq}@test.kz"


def check(cond: bool, msg: str) -> None:
    global ok
    mark = "OK  " if cond else "FAIL"
    print(f"  [{mark}] {msg}")
    if not cond:
        ok = False


print(f"1) Регистрация нового перевозчика ({email})")
r = c.post(
    "/api/auth/register",
    json={
        "role": "carrier",
        "name": "Тест Перевозчиков",
        "company": "ТОО Тест",
        "email": email,
        "password": "secret123",
    },
)
check(r.status_code == 201, f"POST /api/auth/register -> {r.status_code} (ожидался 201)")
data = r.json()
token = data.get("access_token", "")
check(bool(token), "вернулся access_token (авто-логин)")
check(data["user"]["role"] == "carrier", f"роль пользователя = {data['user']['role']}")

print("2) Токен валиден на /auth/me")
r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
check(r.status_code == 200 and r.json()["email"] == email, "токен после регистрации рабочий")

print("3) Дубль email -> 409")
r = c.post(
    "/api/auth/register",
    json={"role": "shipper", "name": "Дубль", "email": email, "password": "secret123"},
)
check(r.status_code == 409, f"повторный email -> {r.status_code} (ожидался 409)")

print("4) Роль analyst через форму запрещена -> 422")
r = c.post(
    "/api/auth/register",
    json={"role": "analyst", "name": "Шпион", "email": f"a_{uniq}@test.kz", "password": "secret123"},
)
check(r.status_code == 422, f"role=analyst -> {r.status_code} (ожидался 422)")

print("5) Короткий пароль -> 422")
r = c.post(
    "/api/auth/register",
    json={"role": "shipper", "name": "Слабый", "email": f"w_{uniq}@test.kz", "password": "123"},
)
check(r.status_code == 422, f"password='123' -> {r.status_code} (ожидался 422)")

print("6) Новый аккаунт логинится штатно через /auth/login")
r = c.post("/api/auth/login", json={"email": email, "password": "secret123"})
check(r.status_code == 200, f"login новым аккаунтом -> {r.status_code}")

print()
print("ИТОГ:", "ВСЁ ЗЕЛЁНОЕ" if ok else "ЕСТЬ ПАДЕНИЯ")
sys.exit(0 if ok else 1)
