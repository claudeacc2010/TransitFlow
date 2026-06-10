"""Стоп-точка Этапа 2: проверить, что AI-сводка генерится на живом ключе.

Запуск из каталога backend/:  python try_gemini.py
Печатает выбранного провайдера и сгенерированный текст (или fallback).
"""
from __future__ import annotations

from app.ai_summary import generate_summary
from app.config import settings

# Фейковая, но правдоподобная статистика — форму уточним при сборке /analytics.
DEMO_STATS = {
    "период_дней": 90,
    "всего_заявок": 1840,
    "среднее_ожидание_до_слотов_ч": 4.1,
    "среднее_ожидание_сейчас_ч": 1.2,
    "самый_загруженный_узел": "Курык (порт)",
    "пиковый_час": "09:00–10:00",
    "прогноз_на_завтра": "рост загрузки Курыка на ~15%",
}

if __name__ == "__main__":
    print(f"AI_PROVIDER = {settings.ai_provider}")
    print(f"GEMINI_MODEL = {settings.gemini_model}")
    print(f"ключ задан: {bool(settings.gemini_api_key)}")
    print("-" * 60)
    print(generate_summary(DEMO_STATS))
