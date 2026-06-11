"""Отправка письма подтверждения email через SMTP (STARTTLS).

Синхронно и просто: для MVP достаточно. Если SMTP не настроен
(settings.email_verification_enabled == False), модуль не используется.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings

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
    """Шлёт письмо со ссылкой подтверждения. Бросает исключение при сбое SMTP."""
    msg = EmailMessage()
    msg["Subject"] = _SUBJECT
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(_BODY.format(name=name, link=link))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
