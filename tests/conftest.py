"""Integration tests against real postgres + redis: docker compose run --rm api pytest -q"""
import os, re, tempfile, uuid
from dataclasses import dataclass

import psycopg
import pytest

BASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:orbita@db:5432/orbita")
TEST_DB = "orbita_test"
os.environ.update(
    DATABASE_URL=BASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB,
    DATABASE_READ_URL="",
    PGBOUNCER="false",
    REDIS_URL=os.environ.get("TEST_REDIS_URL", "redis://redis:6379/15"),
    JWT_SECRET="test-secret",
    EMBEDDINGS="hash",
    SMTP_HOST="",
    TRUST_PROXY="false",
    MEDIA_DIR=tempfile.mkdtemp(prefix="orbita-media-"),
    PUBLIC_URL="http://testserver",
)


def recreate_db(name):
    with psycopg.connect(BASE_URL, autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        c.execute(f"CREATE DATABASE {name}")


recreate_db(TEST_DB)
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

ALEMBIC = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
ALEMBIC.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
command.upgrade(ALEMBIC, "head")

from fastapi.testclient import TestClient  # noqa: E402

from app import mailer  # noqa: E402
from app.cache import r as redis_client  # noqa: E402
from app.db import pool  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean(client):
    with pool.connection() as c:
        c.execute("TRUNCATE users, swipes, matches, photos, messages, blocks, reports RESTART IDENTITY CASCADE")
    redis_client.flushdb()
    mailer.outbox.clear()


@dataclass
class U:
    id: int
    token: str
    email: str
    name: str

    @property
    def h(self):
        return {"Authorization": f"Bearer {self.token}"}


def verify_link_for(email):
    msg = next(m for m in reversed(mailer.outbox) if m["To"] == email)
    text = msg.get_body(("plain",)).get_content()
    return re.search(r"http://testserver(/api/verify-email\?token=\S+)", text).group(1)


@pytest.fixture
def make_user(client):
    def make(name="Анна", tags=None, verify=True, age=27, role=None, bio=""):
        email = f"{uuid.uuid4().hex[:10]}@test.dev"
        r = client.post("/api/register", json={"email": email, "password": "password123", "name": name, "age": age})
        assert r.status_code == 200, r.text
        tok = r.json()["token"]
        uid = client.get("/api/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]
        u = U(uid, tok, email, name)
        if verify:
            assert client.get(verify_link_for(email), follow_redirects=False).status_code == 303
        if tags:
            assert client.put("/api/profile", json={"tags": tags, "bio": bio}, headers=u.h).status_code == 200
        if role:
            with pool.connection() as c:
                c.execute("UPDATE users SET role=%s WHERE id=%s", (role, uid))
        return u
    return make


TAGS_A = ["бег", "кофе", "джаз", "фотография", "путешествия"]
TAGS_B = ["бег", "кофе", "джаз", "фотография", "книги"]
TAGS_C = ["вязание", "садоводство", "астрономия", "шахматы", "керамика"]


@pytest.fixture
def pair(client, make_user):
    a, b = make_user("Анна", TAGS_A), make_user("Максим", TAGS_B)
    client.post("/api/swipe", json={"target": b.id, "liked": True}, headers=a.h)
    assert client.post("/api/swipe", json={"target": a.id, "liked": True}, headers=b.h).json() == {"match": True}
    return a, b
