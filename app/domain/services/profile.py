"""Profile invariants (no infrastructure or HTTP dependencies)."""

class InvalidTags(ValueError):
    pass

def normalize_tags(tags: list[str]) -> list[str]:
    normalized = sorted({t.strip().lower()[:30] for t in tags if t.strip()})
    if len(normalized) < 5:
        raise InvalidTags("Нужно минимум 5 разных тегов")
    return normalized
