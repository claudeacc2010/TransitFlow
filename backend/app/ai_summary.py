"""AI-сводка для дашборда аналитика (раздел 4 спеки).

Принимает агрегированную статистику и возвращает короткий аналитический текст
на русском — «как акимату прочитать эти цифры».

Провайдер выбирается переменной AI_PROVIDER (gemini|claude). Если ключа нет
или внешний API недоступен/упал — возвращаем детерминированный fallback,
собранный из той же статистики, чтобы дашборд никогда не оставался пустым.
"""
from __future__ import annotations

import sys

import httpx

from app.config import settings

# Жёсткие лимиты, чтобы не подвесить дашборд на медленном/упавшем API.
_TIMEOUT_S = 20.0
_MAX_TOKENS = 512

_SYSTEM = (
    "Ты аналитик логистики для акимата Мангистауской области. "
    "По цифрам трафика грузовых пунктов пропуска дай короткую деловую сводку "
    "на русском: 3–4 предложения, без воды и без markdown. Назови главное: где "
    "загрузка/очереди, эффект слотирования, и один практический вывод."
)


def _stats_to_lines(stats: dict) -> str:
    """Плоское человекочитаемое представление статистики для промпта/fallback."""
    lines = []
    for key, value in stats.items():
        if isinstance(value, float):
            value = f"{value:g}"
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _build_prompt(stats: dict) -> str:
    return f"{_SYSTEM}\n\nДанные за период:\n{_stats_to_lines(stats)}"


def _gemini(prompt: str) -> str:
    """Прямой REST-вызов Gemini generateContent (без SDK)."""
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY не задан")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    resp = httpx.post(
        url,
        params={"key": settings.gemini_api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": _MAX_TOKENS,
                "temperature": 0.4,
                # gemini-2.5-flash «думает» по умолчанию, а скрытые токены
                # размышления тратят maxOutputTokens. Для короткой сводки
                # отключаем — нужен сразу ответ, не цепочка рассуждений.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    data = resp.json()
    # candidates[0].content.parts[*].text
    parts = data["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("Gemini вернул пустой ответ")
    return text


def _claude(prompt: str) -> str:
    """Вызов Claude API (для переключения перед демо)."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    # Импорт локальный: SDK нужен только при AI_PROVIDER=claude.
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text").strip()
    if not text:
        raise RuntimeError("Claude вернул пустой ответ")
    return text


def _fallback(stats: dict) -> str:
    """Детерминированная сводка из той же статистики — без внешнего API."""
    return (
        "AI-сводка временно недоступна, показаны исходные показатели. "
        "Ключевые цифры за период:\n" + _stats_to_lines(stats)
    )


def generate_summary(stats: dict) -> str:
    """Главная точка входа: вернуть текст сводки. Никогда не бросает наружу."""
    prompt = _build_prompt(stats)
    provider = (settings.ai_provider or "gemini").lower()
    try:
        if provider == "claude":
            return _claude(prompt)
        return _gemini(prompt)
    except Exception as exc:  # noqa: BLE001 — любой сбой => fallback, дашборд жив
        print(f"[ai_summary] провайдер={provider} упал, fallback: {exc}", file=sys.stderr)
        return _fallback(stats)
