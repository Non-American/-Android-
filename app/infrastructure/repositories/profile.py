"""PostgreSQL profile repository. No HTTP transport or validation here."""
from app.db import pool

class PostgresProfileWriter:
    def save_profile(self, user_id: int, tags: list[str], bio: str,
                     embedding: list[float]) -> None:
        with pool.connection() as connection:
            connection.execute(
                'UPDATE users SET tags=%s, emb=%s::vector, bio=%s WHERE id=%s',
                (tags, str(embedding), bio, user_id),
            )
