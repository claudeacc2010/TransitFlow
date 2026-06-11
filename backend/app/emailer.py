"""Отправка письма подтверждения email через Brevo HTTP API.

SMTP на Railway недоступен (исходящие порты 25/465/587 заблокированы), поэтому
письма шлём по HTTPS через Brevo (https://api.brevo.com). Если верификация не
настроена (settings.email_verification_enabled == False), модуль не вызывается.
"""
from __future__ import annotations

import httpx

from app.config import settings

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
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
    """Шлёт письмо со ссылкой подтверждения через Brevo. Бросает исключение при сбое."""
    payload = {
        "sender": {
            "name": settings.brevo_sender_name,
            "email": settings.brevo_sender_email,
        },
        "to": [{"email": to, "name": name}],
        "subject": _SUBJECT,
        "textContent": _BODY.format(name=name, link=link),
    }
    headers = {
        "api-key": settings.brevo_api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }
    resp = httpx.post(_BREVO_URL, json=payload, headers=headers, timeout=20)
    # Brevo возвращает 201 при успехе. Иначе — поднимаем с телом ответа.
    if resp.status_code >= 400:
        raise RuntimeError(f"Brevo {resp.status_code}: {resp.text}")
