
import psycopg
from alembic import command
from alembic.config import Config

from tests.conftest import ALEMBIC, BASE_URL, recreate_db


def test_upgrade_downgrade_roundtrip(monkeypatch):
    name = "orbita_migr_test"
    recreate_db(name)
    url = BASE_URL.rsplit("/", 1)[0] + "/" + name
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(ALEMBIC.config_file_name)
    cfg.set_main_option("script_location", ALEMBIC.get_main_option("script_location"))
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def test_upgrade_over_legacy_schema_keeps_users(monkeypatch):
    name = "orbita_legacy_test"
    recreate_db(name)
    url = BASE_URL.rsplit("/", 1)[0] + "/" + name
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("""CREATE EXTENSION vector;
          CREATE TABLE users(id BIGSERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL,
            name TEXT NOT NULL, age SMALLINT NOT NULL CHECK (age >= 18), bio TEXT NOT NULL DEFAULT '',
            tags TEXT[] NOT NULL DEFAULT '{}', emb vector(384), lat DOUBLE PRECISION, lon DOUBLE PRECISION);
          INSERT INTO users(email,pw_hash,name,age,lat,lon) VALUES('old@x.dev','h','Old',30,55.7,37.6);""")
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(ALEMBIC.config_file_name)
    cfg.set_main_option("script_location", ALEMBIC.get_main_option("script_location"))
    command.upgrade(cfg, "head")
    with psycopg.connect(url) as c:
        row = c.execute("SELECT email, email_verified_at IS NOT NULL FROM users").fetchone()
    assert row == ("old@x.dev", True)
