from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewResult:
    prompt: str
    word_count: int
    strengths: list[str]
    risks: list[str]
    recommendations: list[str]


def analyze_prompt(prompt: str) -> ReviewResult:
    normalized_prompt = " ".join(prompt.split())
    lowered_prompt = normalized_prompt.lower()
    word_count = len(normalized_prompt.split())

    strengths: list[str] = []
    risks: list[str] = []
    recommendations: list[str] = []

    if any(marker in lowered_prompt for marker in ("must", "should", "нужно", "должен")):
        strengths.append("Есть явные требования или ограничения.")
    else:
        risks.append("Требования сформулированы неявно.")
        recommendations.append("Добавить явные ограничения и критерий результата.")

    if any(marker in lowered_prompt for marker in ("format", "output", "ответ", "формат")):
        strengths.append("Указан ожидаемый формат ответа.")
    else:
        risks.append("Не указан формат итогового ответа.")
        recommendations.append("Уточнить форму результата: список, текст, JSON или шаблон.")

    if word_count > 180:
        risks.append("Промпт длинный и может размывать приоритеты.")
        recommendations.append("Сократить второстепенные детали и оставить только обязательные правила.")
    elif word_count < 12:
        risks.append("Промпт слишком короткий для надежной интерпретации.")
        recommendations.append("Добавить цель, ограничения и ожидаемый результат.")
    else:
        strengths.append("Объем промпта подходит для быстрой ручной проверки.")

    if not any(marker in lowered_prompt for marker in ("example", "например", "пример")):
        recommendations.append("При необходимости добавить короткий пример ожидаемого результата.")

    if not strengths:
        strengths.append("Промпт передан явно, модуль может проверить его вручную.")

    if not risks:
        risks.append("Явных структурных проблем по базовой эвристике не найдено.")

    return ReviewResult(
        prompt=normalized_prompt,
        word_count=word_count,
        strengths=strengths,
        risks=risks,
        recommendations=recommendations,
    )


def format_review(review: ReviewResult) -> str:
    sections = [
        "prompt_reviewer",
        "",
        "Mode: manual review only",
        f"Words: {review.word_count}",
        "",
        "Strengths:",
        *[f"- {item}" for item in review.strengths],
        "",
        "Risks:",
        *[f"- {item}" for item in review.risks],
        "",
        "Recommendations:",
        *[f"- {item}" for item in review.recommendations],
    ]
    return "\n".join(sections)
