import json
import re
from collections import Counter


def recognize_text(source_payload: str) -> tuple[str, str]:
    normalized_text = " ".join(source_payload.split())
    words = re.findall(r"[A-Za-zА-Яа-я0-9-]+", normalized_text.lower())
    top_words = [word for word, _count in Counter(words).most_common(5)]
    features = {
        "char_count": len(normalized_text),
        "word_count": len(words),
        "top_words": top_words,
    }
    return normalized_text, json.dumps(features, ensure_ascii=False, indent=2)


def classify_document(recognized_text: str) -> tuple[str, str, float]:
    text = recognized_text.lower()
    rules = (
        ("invoice", ("invoice", "счет", "оплата", "payment", "total")),
        ("contract", ("contract", "agreement", "договор", "сторона", "условия")),
        ("identity", ("passport", "id", "identity", "паспорт", "дата рождения")),
        ("letter", ("letter", "уважаемый", "dear", "подпись", "сообщаем")),
    )
    for label, keywords in rules:
        matches = [keyword for keyword in keywords if keyword in text]
        if matches:
            reason = f"Matched keywords: {', '.join(matches[:3])}"
            confidence = min(0.95, 0.55 + len(matches) * 0.1)
            return label, reason, round(confidence, 2)
    return "unknown", "No classification keywords matched", 0.25
