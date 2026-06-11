"""Рекомендованная цена перевозки (§2): «как в Яндекс Такси».

Отправитель видит подсказку цены от А до Б с учётом параметров груза, а затем
ставит свою. Перевозчик выбирает заказы по цене/(тг·км). Здесь — чистые функции
без БД: расстояние по координатам пунктов и формула цены с разложением по
факторам (его и показываем в UI — это «вау» для жюри).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.config import settings
from app.models import CargoType

# Приблизительные координаты пунктов Мангистау/прилегающих (lat, lng).
# Хватает для оценки расстояния; точные дороги — вне рамок MVP.
PLACE_COORDS: dict[str, tuple[float, float]] = {
    "Актау": (43.6500, 51.1600),
    "Бейнеу": (45.3160, 55.1970),
    "Жанаозен": (43.3415, 52.8610),
    "Форт-Шевченко": (44.5090, 50.2640),
    "Курык": (43.1900, 51.6600),
    "Жетыбай": (43.5900, 52.0700),
    "Шетпе": (44.1670, 52.1170),
    "Сай-Утес": (45.0500, 54.0500),
    "Мунайлы": (43.7700, 51.3300),
    "Таучик": (44.0500, 51.3000),
    "Атырау": (47.0945, 51.9238),
    "Бейнеу-Порт": (45.2000, 55.0000),
}

ROAD_FACTOR = 1.3   # извилистость дорог относительно прямой
MIN_DISTANCE_KM = 30.0
DEFAULT_DISTANCE_KM = 250.0  # если пункт неизвестен — типичное плечо по региону


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Расстояние по большой окружности, км."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def route_distance_km(origin: str, destination: str) -> float:
    """Оценка дорожного расстояния между пунктами, км (округлённо)."""
    a = PLACE_COORDS.get(origin.strip())
    b = PLACE_COORDS.get(destination.strip())
    if a is None or b is None:
        return DEFAULT_DISTANCE_KM
    dist = haversine_km(a, b) * ROAD_FACTOR
    return round(max(dist, MIN_DISTANCE_KM), 1)


# Надбавочные коэффициенты к базовой ставке (§2).
_ADR_FACTOR = 1.3      # опасный груз
_TEMP_FACTOR = 1.2     # температурный режим
_URGENT_FACTOR = 1.15  # срочность
_LIQUID_FACTOR = 1.1   # наливной/нефтепродукты — спец. цистерна


@dataclass
class PriceFactor:
    label: str
    multiplier: float


@dataclass
class PriceRecommendation:
    distance_km: float
    weight_t: float
    rate_per_km_t: float   # тг за км·т с учётом надбавок
    recommended: int       # рекомендованная цена, тг (округлённая)
    factors: list[PriceFactor]


def recommend_price(
    *,
    distance_km: float,
    weight_t: float,
    cargo_type: CargoType,
    adr_class: str | None = None,
    temp_mode: str | None = None,
    urgent: bool = False,
) -> PriceRecommendation:
    """Рекомендованная цена = базовая ставка × расстояние × вес × надбавки."""
    base_rate = settings.base_rate_tenge_per_km_t
    factors: list[PriceFactor] = []
    mult = 1.0
    if adr_class:
        factors.append(PriceFactor("Опасный груз (ADR)", _ADR_FACTOR))
        mult *= _ADR_FACTOR
    if temp_mode:
        factors.append(PriceFactor("Температурный режим", _TEMP_FACTOR))
        mult *= _TEMP_FACTOR
    if urgent:
        factors.append(PriceFactor("Срочность", _URGENT_FACTOR))
        mult *= _URGENT_FACTOR
    if cargo_type in (CargoType.liquid, CargoType.oil_products):
        factors.append(PriceFactor("Наливной груз (цистерна)", _LIQUID_FACTOR))
        mult *= _LIQUID_FACTOR

    rate = base_rate * mult
    raw = rate * distance_km * weight_t
    # Округляем до 1000 тг — так цена выглядит «человеческой».
    recommended = int(round(raw / 1000.0) * 1000)
    return PriceRecommendation(
        distance_km=round(distance_km, 1),
        weight_t=round(weight_t, 1),
        rate_per_km_t=round(rate, 2),
        recommended=recommended,
        factors=factors,
    )
