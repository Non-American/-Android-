"""Tests for framework-independent domain rules."""
from app.domain.services.profile import InvalidTags, normalize_tags
from app.domain.services.chat import EmptyMessage, normalize_message
import pytest


def test_tags_normalize_and_deduplicate():
    result = normalize_tags(["  Jazz  ", "jazz", "Coding", "Art", "Travel", "Tea", "Music"])
    assert result == ["art", "coding", "jazz", "music", "tea", "travel"]


def test_five_distinct_tags_required():
    with pytest.raises(InvalidTags):
        normalize_tags(["same"] * 5)


def test_message_trim_and_reject_whitespace():
    assert normalize_message("  hello  ") == "hello"
    with pytest.raises(EmptyMessage):
        normalize_message("  ")
