"""Документы и совместимость грузов (§6) — чистые справочные функции.

Системе не нужен документооборот: достаточно подсказать перечень документов и
предупредить о несовместимых грузах. Это дёшево в коде, но показывает знание
настоящей логистики (CMR/ADR/ветеринарный сертификат, запрет смешивать
продукты с химией и опасными грузами).
"""
from __future__ import annotations

from app.models import CargoType

# RU-подписи типов груза — для текста предупреждений о несовместимости.
CARGO_RU: dict[CargoType, str] = {
    CargoType.container: "контейнеры",
    CargoType.bulk: "навалочные",
    CargoType.liquid: "наливные",
    CargoType.general: "генеральные",
    CargoType.food: "продукты питания",
    CargoType.grain: "зерно",
    CargoType.oil_products: "нефтепродукты",
    CargoType.construction: "стройматериалы",
    CargoType.chemicals: "химикаты",
}

# Несовместимые пары (симметрично): нельзя везти вместе в одной машине.
_INCOMPATIBLE: dict[CargoType, set[CargoType]] = {
    CargoType.food: {CargoType.chemicals, CargoType.oil_products},
    CargoType.grain: {CargoType.chemicals, CargoType.oil_products},
    CargoType.chemicals: {CargoType.food, CargoType.grain},
    CargoType.oil_products: {CargoType.food, CargoType.grain},
}


def required_docs(cargo_type: CargoType, adr_class: str | None, temp_mode: str | None) -> list[str]:
    """Перечень документов для перевозки."""
    docs = ["CMR", "Товарная накладная"]
    if adr_class:
        docs.append(f"ADR (класс {adr_class})")
    if cargo_type is CargoType.food:
        docs.append("Ветеринарный/санитарный сертификат")
    if cargo_type is CargoType.grain:
        docs.append("Фитосанитарный сертификат")
    if temp_mode:
        docs.append("Температурный лист")
    return docs


def incompatible_with(cargo_type: CargoType) -> list[str]:
    """RU-подписи грузов, которые нельзя совмещать с данным."""
    return [CARGO_RU[c] for c in sorted(_INCOMPATIBLE.get(cargo_type, set()), key=lambda c: c.value)]
