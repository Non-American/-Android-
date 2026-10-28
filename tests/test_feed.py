import redis

from app import cache
from app.db import pool
from tests.conftest import TAGS_A, TAGS_B, TAGS_C


def test_profile_needs_five_tags_and_no_location(client, make_user):
    u = make_user()
    assert client.put("/api/profile", json={"tags": ["a", "b", "c", "d"]}, headers=u.h).status_code == 422
    assert client.put("/api/profile", json={"tags": ["a", "A", "a ", "b", "c"]}, headers=u.h).status_code == 422
    r = client.put("/api/profile", json={"tags": TAGS_A, "bio": "привет"}, headers=u.h)
    assert r.status_code == 200 and r.json()["tags"] == sorted(TAGS_A)


def test_feed_requires_profile(client, make_user):
    u = make_user()
    assert client.get("/api/feed", headers=u.h).status_code == 409


def test_feed_sorted_by_similarity_with_common_tags(client, make_user):
    me = make_user("Я", TAGS_A)
    close, far = make_user("Близкий", TAGS_B), make_user("Далёкий", TAGS_C)
    make_user("Неподтверждённый", TAGS_A, verify=False)
    feed = client.get("/api/feed", headers=me.h).json()
    assert [c["id"] for c in feed] == [close.id, far.id]
    assert feed[0]["sim"] > feed[1]["sim"]
    assert feed[0]["common"] == sorted(set(TAGS_A) & set(TAGS_B))
    assert "km" not in feed[0] and feed[0]["photos"] == []


def test_swipe_hides_card_and_mutual_like_matches(client, make_user):
    a, b = make_user("A", TAGS_A), make_user("B", TAGS_B)
    client.get("/api/feed", headers=a.h)
    assert client.post("/api/swipe", json={"target": b.id, "liked": True}, headers=a.h).json() == {"match": False}
    assert client.get("/api/feed", headers=a.h).json() == []
    assert client.post("/api/swipe", json={"target": a.id, "liked": True}, headers=b.h).json() == {"match": True}
    assert [m["id"] for m in client.get("/api/matches", headers=a.h).json()] == [b.id]


def test_swipe_errors(client, make_user):
    a = make_user("A", TAGS_A)
    assert client.post("/api/swipe", json={"target": a.id, "liked": True}, headers=a.h).status_code == 400
    assert client.post("/api/swipe", json={"target": 999999, "liked": True}, headers=a.h).status_code == 404


def test_feed_cache_served_until_invalidated(client, make_user):
    a = make_user("A", TAGS_A)
    make_user("B", TAGS_B)
    assert len(client.get("/api/feed", headers=a.h).json()) == 1
    assert cache.r.exists(f"feed:{a.id}")
    late = make_user("Поздний", TAGS_B)
    # served from cache until invalidated
    assert late.id not in [c["id"] for c in client.get("/api/feed", headers=a.h).json()]
    client.put("/api/profile", json={"tags": TAGS_A}, headers=a.h)
    assert late.id in [c["id"] for c in client.get("/api/feed", headers=a.h).json()]


def test_feed_rebuilds_when_cache_runs_low(client, make_user):
    a = make_user("A", TAGS_A)
    others = [make_user(f"U{i}", TAGS_B) for i in range(3)]
    feed = client.get("/api/feed?limit=2", headers=a.h).json()
    assert len(feed) == 2
    for c in feed:
        client.post("/api/swipe", json={"target": c["id"], "liked": False}, headers=a.h)
    rest = client.get("/api/feed?limit=2", headers=a.h).json()
    assert [c["id"] for c in rest] == [u.id for u in others if u.id not in {c["id"] for c in feed}]


def test_redis_down_fails_open(client, make_user, monkeypatch):
    a = make_user("A", TAGS_A)
    make_user("B", TAGS_B)
    monkeypatch.setattr(cache, "r", redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1))
    assert client.post("/api/login", json={"email": a.email, "password": "password123"}).status_code == 200
    assert len(client.get("/api/feed", headers=a.h).json()) == 1


def test_banned_and_hidden_users_not_in_feed(client, make_user):
    a, b, c = make_user("A", TAGS_A), make_user("B", TAGS_B), make_user("C", TAGS_C)
    with pool.connection() as conn:
        conn.execute("UPDATE users SET banned_at=now() WHERE id=%s", (b.id,))
        conn.execute("UPDATE users SET hidden_at=now() WHERE id=%s", (c.id,))
    assert client.get("/api/feed", headers=a.h).json() == []
