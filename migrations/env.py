import os

from alembic import context
from sqlalchemy import create_engine, pool


def url():
    u = os.environ["DATABASE_URL"]
    return u.replace("postgresql://", "postgresql+psycopg://", 1) if u.startswith("postgresql://") else u


if context.is_offline_mode():
    context.configure(url=url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url(), poolclass=pool.NullPool).connect() as conn:
        context.configure(connection=conn, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
