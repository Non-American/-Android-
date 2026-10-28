"""messages

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE messages(
      id BIGSERIAL PRIMARY KEY,
      a BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      b BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      sender BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 2000),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      read_at TIMESTAMPTZ,
      CHECK (a < b), CHECK (sender IN (a, b))
    );
    CREATE INDEX messages_pair ON messages (a, b, id DESC);
    CREATE INDEX messages_unread ON messages (a, b, sender) WHERE read_at IS NULL;
    """)


def downgrade():
    op.execute("DROP TABLE messages")
