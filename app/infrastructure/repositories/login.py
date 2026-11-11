"""Database adapter for the login use case; free of HTTP dependencies."""
from app.db import pool

class PostgresAccountReader:
    def find_for_login(self, email: str):
        with pool.connection() as connection:
            return connection.execute(
                'SELECT id, pw_hash, banned_at FROM users WHERE email=%s',
                (email,)
            ).fetchone()
