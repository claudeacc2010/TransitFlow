"""Pydantic-схемы. Этап 0 — логин; Этап 1 — заявки, слоты, бронь, QR."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
)

from app.models import (
    BookingStatus,
    CargoType,
    CheckpointKind,
    RequestStatus,
    ShipmentStatus,
    Urgency,
    UserRole,
)


class LoginRequest(BaseModel):
    # email — это логин-хендл; демо-аккаунты вида shipper@demo (раздел 4)
    # намеренно не являются валидными RFC-email, поэтому str, а не EmailStr.
    email: str
    password: str


class RegisterRequest(BaseModel):
    # Саморегистрация только для shipper/carrier; analyst — внутренняя роль
    # акимата, выдаётся через сид, не через открытую форму.
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=72)  # bcrypt лимит — 72 байта
    name: str = Field(min_length=1, max_length=255)
    role: Literal[UserRole.shipper, UserRole.carrier]
    company: str | None = Field(default=None, max_length=255)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: UserRole
    company: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Краткое представление пользователя (для вложенных полей заявки)
# ---------------------------------------------------------------------------
class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: str | None = None


# ---------------------------------------------------------------------------
# Узлы (checkpoints)
# ---------------------------------------------------------------------------
class CheckpointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: CheckpointKind
    lat: float
    lng: float
    capacity_per_hour: int


class CheckpointLoadOut(CheckpointOut):
    """Узел + текущая загрузка (последний час истории) — питание карты."""

    trucks_last_hour: int
    load_pct: float  # trucks_last_hour / capacity_per_hour * 100
    # §5: оценка очереди на узле.
    capacity_per_day: int       # capacity_per_hour * 24
    waiting_now: int            # машин в очереди сейчас (симуляция за 24 ч)
    est_wait_hours: float       # ожидаемое время ожидания, ч


class ForecastPoint(BaseModel):
    ts: datetime
    trucks_expected: float


class ForecastOut(BaseModel):
    checkpoint_id: int
    days: int
    points: list[ForecastPoint]


# ---------------------------------------------------------------------------
# Аналитика (Этап 2)
# ---------------------------------------------------------------------------
class AnalyticsOverview(BaseModel):
    """Карточки дашборда (раздел 7)."""

    trucks_today: int
    tons_per_day: float  # средняя тоннажность заявок за 7 дней
    active_requests: int
    avg_load_pct: float  # средняя текущая загрузка узлов


class TimeseriesPoint(BaseModel):
    date: date
    trucks: int


class BreakdownItem(BaseModel):
    key: str
    label: str
    trucks: int


class AISummaryOut(BaseModel):
    summary: str
    provider: str
    generated_at: datetime


class EventOut(BaseModel):
    """Событие ленты дашборда: kind — для цвета (request|accept|booking)."""

    kind: str
    ts: datetime
    title: str
    detail: str


# ---------------------------------------------------------------------------
# Слоты
# ---------------------------------------------------------------------------
class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checkpoint_id: int
    starts_at: datetime
    ends_at: datetime
    capacity: int
    booked_count: int

    @computed_field
    @property
    def available(self) -> int:
        return self.capacity - self.booked_count


# ---------------------------------------------------------------------------
# Бронь / QR
# ---------------------------------------------------------------------------
class BookingBrief(BaseModel):
    """Бронь в контексте заявки: где и когда + QR-токен пропуска."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    qr_token: UUID
    status: BookingStatus
    starts_at: datetime
    ends_at: datetime
    checkpoint_name: str

    @field_serializer("qr_token")
    def _ser_qr(self, v: UUID) -> str:
        return str(v)


class BookingCreate(BaseModel):
    slot_id: int
    assignment_id: int


# ---------------------------------------------------------------------------
# Заявки и назначения
# ---------------------------------------------------------------------------
class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    carrier: UserBrief
    truck_plate: str
    accepted_at: datetime
    shipment_status: ShipmentStatus
    status_updated_at: datetime
    booking: BookingBrief | None = None


class ShipmentStatusUpdate(BaseModel):
    status: ShipmentStatus


class RequestCreate(BaseModel):
    cargo_type: CargoType
    weight_t: float = Field(gt=0, le=100)
    origin: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    desired_date: date
    # Доработка v2 (§1): характеристики груза. Все опциональны, кроме срочности.
    volume_m3: float | None = Field(default=None, gt=0, le=200)
    adr_class: str | None = Field(default=None, max_length=8)
    temp_mode: str | None = Field(default=None, max_length=32)
    ready_at: datetime | None = None
    urgency: Urgency = Urgency.normal
    # §2: цена отправителя за перевозку, тг (опционально — можно создать без цены).
    price_offer: float | None = Field(default=None, gt=0)

    @field_validator("adr_class")
    @classmethod
    def _check_adr(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if v not in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            raise ValueError("Класс ADR должен быть числом 1–9")
        return v


class AcceptRequestIn(BaseModel):
    truck_plate: str = Field(min_length=1, max_length=32)


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipper: UserBrief
    cargo_type: CargoType
    weight_t: float
    origin: str
    destination: str
    desired_date: date
    volume_m3: float | None = None
    adr_class: str | None = None
    temp_mode: str | None = None
    ready_at: datetime | None = None
    urgency: Urgency
    distance_km: float | None = None
    price_offer: float | None = None
    # §6: подсказки логистики (документы и несовместимые грузы).
    required_docs: list[str] = []
    incompatible_with: list[str] = []
    status: RequestStatus
    created_at: datetime
    assignment: AssignmentOut | None = None

    @computed_field
    @property
    def price_per_km(self) -> float | None:
        """Цена за км — для сравнения заказов перевозчиком."""
        if self.price_offer and self.distance_km:
            return round(self.price_offer / self.distance_km, 1)
        return None


# ---------------------------------------------------------------------------
# §2: рекомендация цены и рыночная ставка
# ---------------------------------------------------------------------------
class PriceRecommendIn(BaseModel):
    cargo_type: CargoType
    weight_t: float = Field(gt=0, le=100)
    origin: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    adr_class: str | None = None
    temp_mode: str | None = None
    urgency: Urgency = Urgency.normal


class PriceFactorOut(BaseModel):
    label: str
    multiplier: float


class PriceRecommendOut(BaseModel):
    distance_km: float
    weight_t: float
    rate_per_km_t: float
    recommended: int
    factors: list[PriceFactorOut]


class MarketRateOut(BaseModel):
    """Средняя рыночная ставка тг/км по закрытым заявкам с ценой."""

    avg_price_per_km: float | None
    sample_size: int
