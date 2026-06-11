"""Отправка письма подтверждения email через Resend HTTP API.

SMTP на Railway недоступен (исходящие порты 25/465/587 заблокированы), поэтому
письма шлём по HTTPS через Resend (https://resend.com). Если верификация не
настроена (settings.email_verification_enabled == False), модуль не вызывается.
"""
from __future__ import annotations

import httpx

from app.config import settings

_RESEND_URL = "https://api.resend.com/emails"
_SUBJECT = "TransitFlow — подтвердите ваш email"

_BODY = """Здравствуйте, {name}!

Вы зарегистрировались на платформе TransitFlow (координация транзита,
Мангистауская область). Чтобы активировать аккаунт, подтвердите email —
перейдите по ссылке:

{link}

Если вы не регистрировались — просто проигнорируйте это письмо.

— TransitFlow
"""


def send_verification_email(*, to: str, name: str, link: str) -> None:
    """Шлёт письмо со ссылкой подтверждения через Resend. Бросает исключение при сбое."""
    payload = {
        "from": settings.resend_from,
        "to": [to],
        "subject": _SUBJECT,
        "text": _BODY.format(name=name, link=link),
    }
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    resp = httpx.post(_RESEND_URL, json=payload, headers=headers, timeout=20)
    # Resend возвращает 200 с {"id": ...} при успехе. Иначе — поднимаем с телом.
    if resp.status_code >= 400:
        raise RuntimeError(f"Resend {resp.status_code}: {resp.text}")
