"""Отправка письма подтверждения email через SMTP (STARTTLS).

Синхронно и просто: для MVP достаточно. Если SMTP не настроен
(settings.email_verification_enabled == False), модуль не используется.

Подключаемся принудительно по IPv4: в контейнерах Railway нет IPv6-маршрута,
а getaddrinfo нередко отдаёт AAAA-адрес Gmail первым → [Errno 101] Network is
unreachable. Резолвим A-запись сами, но при STARTTLS подставляем настоящее имя
хоста, чтобы проверка сертификата проходила.
"""
from __future__ import annotations

import smtplib
import socket
import ssl
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


def _resolve_ipv4(host: str, port: int) -> str:
    """Первый IPv4-адрес хоста (обходим IPv6 без маршрута на Railway)."""
    infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    return infos[0][4][0]


def send_verification_email(*, to: str, name: str, link: str) -> None:
    """Шлёт письмо со ссылкой подтверждения. Бросает исключение при сбое SMTP."""
    msg = EmailMessage()
    msg["Subject"] = _SUBJECT
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(_BODY.format(name=name, link=link))

    host = settings.smtp_host
    port = settings.smtp_port
    ipv4 = _resolve_ipv4(host, port)

    smtp = smtplib.SMTP(timeout=20)
    try:
        smtp.connect(ipv4, port)
        # Возвращаем настоящее имя хоста, чтобы STARTTLS проверил сертификат
        # по нему, а не по IP-адресу.
        smtp._host = host
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    finally:
        try:
            smtp.quit()
        except Exception:
            pass
