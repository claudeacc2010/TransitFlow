"""Живой smoke верификации email (Resend). Запускать при работающем сервере :8000.

Сценарий A (ключа нет — текущее состояние): регистрация сразу выдаёт токен.
Сценарий B (фейковый ключ): письмо не уходит → 502, пользователь откатился.
Сценарий C: ручная проверка /verify — создаём пользователя с токеном напрямую
в БД, дёргаем ссылку, убеждаемся в редиректе и снятии блокировки логина.
"""
from __future__ import annotations

import secrets
import sys
import uuid

import httpx

from app.auth import hash_password
from app.db import SessionLocal
from app.models import User, UserRole

BASE = "http://127.0.0.1:8000"
ok = True


def check(label: str, cond: bool, extra: str = "") -> None:
    global ok
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {label}" + (f" — {extra}" if extra else ""))
    if not cond:
        ok = False


def cleanup(email: str) -> None:
    with SessionLocal() as db:
        u = db.query(User).filter_by(email=email).first()
        if u:
            db.delete(u)
            db.commit()


# --- A: верификация выключена (RESEND_API_KEY не задан) ---
email_a = f"smoke-{uuid.uuid4().hex[:8]}@test.local"
r = httpx.post(f"{BASE}/api/auth/register", json={
    "role": "shipper", "name": "Smoke A", "company": None,
    "email": email_a, "password": "demo123",
})
check("A: регистрация без ключа -> 201", r.status_code == 201, f"got {r.status_code}")
data = r.json() if r.status_code == 201 else {}
check("A: токен выдан сразу", bool(data.get("access_token")))
check("A: verification_required=false", data.get("verification_required") is False)
r = httpx.post(f"{BASE}/api/auth/login", json={"email": email_a, "password": "demo123"})
check("A: логин сразу работает -> 200", r.status_code == 200, f"got {r.status_code}")
cleanup(email_a)

# --- C: /verify подтверждает и пускает в логин ---
email_c = f"smoke-{uuid.uuid4().hex[:8]}@test.local"
token_c = secrets.token_urlsafe(32)
with SessionLocal() as db:
    db.add(User(
        email=email_c, password_hash=hash_password("demo123"), name="Smoke C",
        role=UserRole.shipper, company=None,
        email_verified=False, verify_token=token_c,
    ))
    db.commit()

r = httpx.post(f"{BASE}/api/auth/login", json={"email": email_c, "password": "demo123"})
check("C: логин до подтверждения -> 403", r.status_code == 403, f"got {r.status_code}")

r = httpx.get(f"{BASE}/api/auth/verify", params={"token": token_c}, follow_redirects=False)
check("C: /verify -> редирект на /login?verified=1",
      r.status_code in (302, 307) and r.headers.get("location") == "/login?verified=1",
      f"got {r.status_code} -> {r.headers.get('location')}")

r = httpx.post(f"{BASE}/api/auth/login", json={"email": email_c, "password": "demo123"})
check("C: логин после подтверждения -> 200", r.status_code == 200, f"got {r.status_code}")

r = httpx.get(f"{BASE}/api/auth/verify", params={"token": token_c}, follow_redirects=False)
check("C: повторный /verify -> verified=0",
      r.headers.get("location") == "/login?verified=0",
      f"got {r.headers.get('location')}")
cleanup(email_c)

print()
sys.exit(0 if ok else 1)
