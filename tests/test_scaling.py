import json

from app import embeddings
from app.cache import r
from app.db import pool


def test_tag_vectors_are_cached(monkeypatch):
    calls = []
    real = embeddings._compute
    monkeypatch.setattr(embeddings, "_compute", lambda tags: calls.append(list(tags)) or real(tags))
    embeddings.embed(["бег", "кофе"])
    embeddings.embed(["кофе", "джаз"])
    assert calls == [["бег", "кофе"], ["джаз"]]
    assert len(json.loads(r.get("emb:hash:кофе"))) == embeddings.DIM


def test_swipes_table_is_partitioned():
    with pool.connection() as c:
        n = c.execute("SELECT count(*) AS n FROM pg_inherits WHERE inhparent = 'swipes'::regclass").fetchone()["n"]
    assert n == 16
