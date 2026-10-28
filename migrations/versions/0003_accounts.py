"""email verification, roles, bans

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE users
      ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      ADD COLUMN email_verified_at TIMESTAMPTZ,
      ADD COLUMN role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
      ADD COLUMN banned_at TIMESTAMPTZ,
      ADD COLUMN hidden_at TIMESTAMPTZ;
    UPDATE users SET email_verified_at = now();
    """)


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN created_at, DROP COLUMN email_verified_at, DROP COLUMN role, "
               "DROP COLUMN banned_at, DROP COLUMN hidden_at")
