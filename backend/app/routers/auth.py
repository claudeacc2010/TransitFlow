"""Роутер аутентификации: login / register (+ верификация email) / me."""
from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.config import settings
from app.db import get_db
from app.emailer import send_verification_email
from app.models import User
from app.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Саморегистрация отправителя/перевозчика.

    Без RESEND_API_KEY — как раньше: сразу токен (авто-логин). С ключом —
    аккаунт создаётся неподтверждённым, на почту уходит ссылка, токен не выдаём.
    Роль ограничена схемой (shipper|carrier); analyst через форму недоступен.
    """
    exists = db.scalar(select(User.id).where(User.email == payload.email))
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже зарегистрирован",
        )

    verification = settings.email_verification_enabled
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
        company=payload.company,
        email_verified=not verification,
        verify_token=secrets.token_urlsafe(32) if verification else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if verification:
        base = (settings.public_base_url or str(request.base_url)).rstrip("/")
        link = f"{base}/api/auth/verify?token={user.verify_token}"
        try:
            send_verification_email(to=user.email, name=user.name, link=link)
        except Exception as exc:
            # Письмо не ушло — откатываем регистрацию, чтобы человек не завис
            # «неподтверждённым» без письма и мог попробовать снова.
            logger.exception("Resend: не удалось отправить письмо на %s", user.email)
            db.delete(user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ошибка отправки письма [{type(exc).__name__}]: {exc}",
            )
        return RegisterResponse(
            verification_required=True,
            user=UserOut.model_validate(user),
        )

    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return RegisterResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/verify", include_in_schema=False)
def verify_email(token: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """Переход по ссылке из письма: подтверждаем и уводим на форму входа."""
    user = db.scalar(select(User).where(User.verify_token == token))
    if user is None:
        # Токен неизвестен или уже использован — на логин с пометкой об ошибке.
        return RedirectResponse(url="/login?verified=0")
    user.email_verified = True
    user.verify_token = None
    db.commit()
    return RedirectResponse(url="/login?verified=1")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email не подтверждён — проверьте почту и перейдите по ссылке из письма.",
        )
    token = create_access_token(user_id=user.id, role=user.role, email=user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Текущий пользователь по токену — удобно для фронта и проверки auth."""
    return UserOut.model_validate(current_user)
