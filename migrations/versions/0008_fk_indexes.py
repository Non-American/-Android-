"""indexes for foreign keys used by cascading deletes

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP INDEX IF EXISTS swipes_incoming")
    op.execute("CREATE INDEX swipes_target ON swipes (target) INCLUDE (liked)")
    op.execute("CREATE INDEX messages_b ON messages (b)")
    op.execute("CREATE INDEX messages_sender ON messages (sender)")
    op.execute("CREATE INDEX reports_reporter ON reports (reporter)")
    op.execute("CREATE INDEX reports_target ON reports (target)")
    op.execute("CREATE INDEX reports_resolved_by ON reports (resolved_by) WHERE resolved_by IS NOT NULL")


def downgrade():
    for ix in ("reports_resolved_by", "reports_target", "reports_reporter", "messages_sender", "messages_b",
               "swipes_target"):
        op.execute(f"DROP INDEX {ix}")
    op.execute("CREATE INDEX swipes_incoming ON swipes (target) WHERE liked")
