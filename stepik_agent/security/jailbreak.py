import re


BLOCK_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(your\s+)?(rules|instructions|policy)",
    r"you\s+are\s+now\s+(dan|developer\s+mode)",
    r"jailbreak",
    r"system\s+prompt",
    r"reveal\s+(hidden|secret)\s+",
    r"override\s+safety",
]


def is_jailbreak_attempt(text: str) -> bool:
    lowered = text.lower().strip()
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, lowered):
            return True
    return False


def jailbreak_response() -> str:
    return (
        "Запрос не может быть обработан: он нарушает правила безопасности агента. "
        "Опишите цель обучения или уточните параметры курса."
    )
