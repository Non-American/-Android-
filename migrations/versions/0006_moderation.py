"""blocks and reports

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE blocks(
      blocker BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      blocked BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (blocker, blocked)
    );
    CREATE INDEX blocks_blocked ON blocks (blocked);
    CREATE TABLE reports(
      id BIGSERIAL PRIMARY KEY,
      reporter BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      target BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      reason TEXT NOT NULL CHECK (reason IN ('spam','fake','abuse','inappropriate_photo','underage','other')),
      comment TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','dismissed','actioned')),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      resolved_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
      resolved_at TIMESTAMPTZ
    );
    CREATE UNIQUE INDEX reports_open_once ON reports (reporter, target) WHERE status = 'open';
    CREATE INDEX reports_target_open ON reports (target) WHERE status = 'open';
    CREATE INDEX reports_status ON reports (status, id DESC);
    """)


def downgrade():
    op.execute("DROP TABLE reports, blocks")
