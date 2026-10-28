"""baseline

Revision ID: 0001
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS users(
      id BIGSERIAL PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      pw_hash TEXT NOT NULL,
      name TEXT NOT NULL,
      age SMALLINT NOT NULL CHECK (age >= 18),
      bio TEXT NOT NULL DEFAULT '',
      tags TEXT[] NOT NULL DEFAULT '{}',
      emb vector(384),
      lat DOUBLE PRECISION, lon DOUBLE PRECISION
    );
    CREATE INDEX IF NOT EXISTS users_emb_hnsw ON users USING hnsw (emb vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS users_geo ON users (lat, lon);
    CREATE TABLE IF NOT EXISTS swipes(
      swiper BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      target BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      liked BOOLEAN NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (swiper, target)
    );
    CREATE INDEX IF NOT EXISTS swipes_incoming ON swipes (target) WHERE liked;
    CREATE TABLE IF NOT EXISTS matches(
      a BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      b BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (a, b), CHECK (a < b)
    );
    CREATE INDEX IF NOT EXISTS matches_b ON matches (b);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS matches, swipes, users")
