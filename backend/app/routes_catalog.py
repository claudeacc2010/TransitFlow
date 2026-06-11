"""Каталог маршрутов с альтернативами (§4): рекомендация пути с учётом очередей.

На хакатоне таблицу `Route` не заводим (это потребовало бы миграции БД ради
демо-данных) — держим справочник направлений в Python-словаре. Postgres-требование
кейса покрыто остальными сущностями. Каждая пара «откуда→куда» даёт 1–2 варианта
маршрута; промежуточные точки, совпадающие с реальными узлами, помечены полем
`checkpoint` (по имени) — через них подтягивается ожидание в очереди из §5.

Главный демо-кейс: Актау → Туркменистан. Короткий автопереход «Темир-Баба» стоит
в очереди ~8 ч, а паромно-ж/д путь через Курык+«Болашак» длиннее на дороге, но
узлы свободны — система рекомендует именно его. Так очередь (§5) напрямую влияет
на выбор маршрута, и это видно на демо.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Waypoint:
    name: str
    checkpoint: str | None = None  # имя узла из CHECKPOINTS, если точка — это узел


@dataclass
class RouteVariant:
    name: str
    distance_km: float
    base_hours: float          # «чистое» время в пути без очередей на узлах
    waypoints: list[Waypoint] = field(default_factory=list)


# Ключ — (откуда, куда) в нижнем регистре без лишних пробелов.
# Значение — список альтернативных вариантов.
ROUTE_CATALOG: dict[tuple[str, str], list[RouteVariant]] = {
    ("актау", "туркменистан"): [
        RouteVariant(
            name="Авто через «Темир-Баба»",
            distance_km=480.0,
            base_hours=8.0,
            waypoints=[
                Waypoint("Актау"),
                Waypoint("Погранпереход «Темир-Баба»", "Погранпереход «Темир-Баба»"),
                Waypoint("Туркменистан"),
            ],
        ),
        RouteVariant(
            name="Паром Курык + ж/д «Болашак»",
            distance_km=545.0,
            base_hours=11.0,
            waypoints=[
                Waypoint("Актау"),
                Waypoint("Порт Курык", "Порт Курык"),
                Waypoint("Ж/д переход «Болашак»", "Ж/д переход «Болашак»"),
                Waypoint("Туркменистан"),
            ],
        ),
    ],
    ("актау", "бейнеу"): [
        RouteVariant(
            name="Прямая трасса через узел Бейнеу",
            distance_km=510.0,
            base_hours=8.5,
            waypoints=[
                Waypoint("Актау"),
                Waypoint("Узел Бейнеу (трасса Актау–Бейнеу)", "Узел Бейнеу (трасса Актау–Бейнеу)"),
            ],
        ),
        RouteVariant(
            name="В объезд через Жетыбай и Шетпе",
            distance_km=565.0,
            base_hours=9.5,
            waypoints=[
                Waypoint("Актау"),
                Waypoint("Жетыбай"),
                Waypoint("Шетпе"),
                Waypoint("Бейнеу"),
            ],
        ),
    ],
}


def lookup_routes(origin: str, destination: str) -> list[RouteVariant] | None:
    """Варианты маршрута для пары направлений или None, если пары нет в каталоге."""
    key = (origin.strip().lower(), destination.strip().lower())
    return ROUTE_CATALOG.get(key)
