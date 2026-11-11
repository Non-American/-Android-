"""Profile use case: rules, vector creation, persistence, invalidation."""
from app.domain.services.profile import normalize_tags
from app.application.ports.profile import ProfileWriter, TagEmbedder, FeedInvalidator

class ProfileUseCases:
    def __init__(self, repository: ProfileWriter, embeddings: TagEmbedder,
                 feed_cache: FeedInvalidator):
        self.repository = repository
        self.embeddings = embeddings
        self.feed_cache = feed_cache

    def update(self, user_id: int, tags: list[str], bio: str):
        normalized = normalize_tags(tags)
        vector = self.embeddings.embed(normalized)
        self.repository.save_profile(user_id, normalized, bio.strip(), vector)
        self.feed_cache.feed_drop(user_id)
        return {'tags': normalized}
