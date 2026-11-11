"""Message validation without FastAPI."""

class EmptyMessage(ValueError):
    pass

def normalize_message(body: str) -> str:
    text = body.strip()
    if not text:
        raise EmptyMessage("Пустое сообщение")
    return text
