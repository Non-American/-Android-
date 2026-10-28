from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.errors import ForeignKeyViolation
from pydantic import BaseModel

from .. import cache
from ..db import pool, read_pool
from ..security import verified_user
from ..storage import storage

router = APIRouter(prefix="/api")
FEED_BATCH = 100

FEED_SQL = """
SELECT u.id, u.name, u.age, u.bio, u.tags,
  1 - (u.emb <=> %(e)s::vector) AS sim,
  ARRAY(SELECT p.key FROM photos p WHERE p.user_id = u.id ORDER BY p.position, p.id) AS photos
FROM users u
WHERE u.id <> %(uid)s AND u.emb IS NOT NULL
  AND u.email_verified_at IS NOT NULL AND u.banned_at IS NULL AND u.hidden_at IS NULL AND u.role = 'user'
  AND NOT EXISTS (SELECT 1 FROM swipes s WHERE s.swiper = %(uid)s AND s.target = u.id)
  AND NOT EXISTS (SELECT 1 FROM blocks b WHERE (b.blocker = %(uid)s AND b.blocked = u.id)
                                          OR (b.blocker = u.id AND b.blocked = %(uid)s))
ORDER BY u.emb <=> %(e)s::vector
LIMIT %(n)s
"""


def build_feed(uid):
    with read_pool.connection() as c:
        u = c.execute("SELECT emb, tags FROM users WHERE id=%s", (uid,)).fetchone()
        if not u or u["emb"] is None:
            raise HTTPException(409, "profile")
        c.execute("SET LOCAL statement_timeout = '3s'")
        c.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
        c.execute("SET LOCAL hnsw.ef_search = 200")
        rows = c.execute(FEED_SQL, {"e": u["emb"], "uid": uid, "n": FEED_BATCH}).fetchall()
    mine = set(u["tags"])
    items = [{**r, "sim": round(float(r["sim"]), 4), "common": sorted(mine & set(r["tags"])),
              "photos": [storage.url(k) for k in r["photos"]]} for r in rows]
    return items, len(rows) < FEED_BATCH


@router.get("/feed")
def feed(limit: int = Query(20, ge=1, le=50), u: dict = Depends(verified_user)):
    uid = u["id"]
    data = cache.feed_get(uid)
    if data is None or (len(data["items"]) < limit and not data["exhausted"]):
        items, exhausted = build_feed(uid)
        cache.feed_put(uid, items, exhausted)
        data = {"items": items}
    return data["items"][:limit]


class Swipe(BaseModel):
    target: int
    liked: bool


@router.post("/swipe")
def swipe(s: Swipe, u: dict = Depends(verified_user)):
    uid = u["id"]
    if s.target == uid:
        raise HTTPException(400, "self")
    cache.hit("swipe", uid, 300, 60)
    with pool.connection() as c:
        try:
            c.execute("INSERT INTO swipes(swiper,target,liked) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                      (uid, s.target, s.liked))
        except ForeignKeyViolation:
            raise HTTPException(404, "no such user")
        match = None
        if s.liked and c.execute(
                "SELECT 1 FROM swipes s JOIN users t ON t.id = s.swiper "
                "WHERE s.swiper=%s AND s.target=%s AND s.liked AND t.banned_at IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM blocks b WHERE (b.blocker=%s AND b.blocked=%s) "
                "                                       OR (b.blocker=%s AND b.blocked=%s))",
                (s.target, uid, uid, s.target, s.target, uid)).fetchone():
            a, b = sorted((uid, s.target))
            match = c.execute("INSERT INTO matches(a,b) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING a",
                              (a, b)).fetchone()
            people = {r["id"]: r for r in c.execute(
                "SELECT u.id, u.name, u.age, (SELECT p.key FROM photos p WHERE p.user_id=u.id "
                "ORDER BY p.position, p.id LIMIT 1) AS photo FROM users u WHERE u.id IN (%s,%s)",
                (uid, s.target)).fetchall()}
    cache.mark_swiped(uid, s.target)
    if match:
        for me_, other in ((uid, s.target), (s.target, uid)):
            o = people[other]
            cache.publish(me_, {"type": "match", "user": {
                "id": o["id"], "name": o["name"], "age": o["age"],
                "photo": o["photo"] and storage.url(o["photo"])}})
    return {"match": bool(match)}
