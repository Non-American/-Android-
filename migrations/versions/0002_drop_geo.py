"""drop geo columns

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP INDEX IF EXISTS users_geo")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS lat, DROP COLUMN IF EXISTS lon")


def downgrade():
    op.execute("ALTER TABLE users ADD COLUMN lat DOUBLE PRECISION, ADD COLUMN lon DOUBLE PRECISION")
    op.execute("CREATE INDEX users_geo ON users (lat, lon)")
