"""Port definitions for profile persistence and side effects."""
from typing import Protocol

class ProfileWriter(Protocol):
    def save_profile(self, user_id: int, tags: list[str], bio: str,
                     embedding: list[float]) -> None: ...

class TagEmbedder(Protocol):
    def embed(self, tags: list[str]) -> list[float]: ...

class FeedInvalidator(Protocol):
    def feed_drop(self, user_id: int) -> None: ...
