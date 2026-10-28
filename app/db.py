from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

# no server-side prepares behind pgbouncer (transaction mode)
_kwargs = {"row_factory": dict_row}
if config.PGBOUNCER:
    _kwargs["prepare_threshold"] = None

pool = ConnectionPool(config.DATABASE_URL, min_size=2, max_size=config.DB_POOL_MAX,
                      kwargs=_kwargs, open=False, timeout=10)

if config.DATABASE_READ_URL != config.DATABASE_URL:
    read_pool = ConnectionPool(config.DATABASE_READ_URL, min_size=2, max_size=config.DB_POOL_MAX,
                               kwargs=_kwargs, open=False, timeout=10)
else:
    read_pool = pool


def open_pools():
    pool.open(wait=True)
    if read_pool is not pool:
        read_pool.open(wait=True)


def close_pools():
    if read_pool is not pool:
        read_pool.close()
    pool.close()
