"""hash-partition swipes by swiper

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

PARTS = 16


def upgrade():
    op.execute("ALTER TABLE swipes RENAME TO swipes_old")
    op.execute("ALTER INDEX swipes_incoming RENAME TO swipes_old_incoming")
    op.execute("""
    CREATE TABLE swipes(
      swiper BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      target BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      liked BOOLEAN NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (swiper, target)
    ) PARTITION BY HASH (swiper)""")
    for i in range(PARTS):
        op.execute(f"CREATE TABLE swipes_p{i} PARTITION OF swipes FOR VALUES WITH (MODULUS {PARTS}, REMAINDER {i})")
    op.execute("INSERT INTO swipes SELECT swiper, target, liked, created_at FROM swipes_old")
    op.execute("DROP TABLE swipes_old")
    op.execute("CREATE INDEX swipes_incoming ON swipes (target) WHERE liked")


def downgrade():
    op.execute("ALTER TABLE swipes RENAME TO swipes_part")
    op.execute("ALTER INDEX swipes_incoming RENAME TO swipes_part_incoming")
    op.execute("""
    CREATE TABLE swipes(
      swiper BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      target BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      liked BOOLEAN NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (swiper, target)
    )""")
    op.execute("INSERT INTO swipes SELECT swiper, target, liked, created_at FROM swipes_part")
    op.execute("DROP TABLE swipes_part")
    op.execute("CREATE INDEX swipes_incoming ON swipes (target) WHERE liked")
