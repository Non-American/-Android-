from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import cache, config
from ..db import pool
from ..security import admin_user, current_user
from ..storage import storage

router = APIRouter(prefix="/api")

Reason = Literal["spam", "fake", "abuse", "inappropriate_photo", "underage", "other"]


def _block(c, uid, other):
    if uid == other:
        raise HTTPException(400, "self")
    if not c.execute("SELECT 1 FROM users WHERE id=%s", (other,)).fetchone():
        raise HTTPException(404, "no such user")
    c.execute("INSERT INTO blocks(blocker, blocked) VALUES(%s,%s) ON CONFLICT DO NOTHING", (uid, other))
    a, b = sorted((uid, other))
    return c.execute("DELETE FROM matches WHERE a=%s AND b=%s RETURNING a", (a, b)).fetchone() is not None


def _after_block(uid, other, unmatched):
    cache.feed_drop(uid, other)
    if unmatched:
        cache.publish(other, {"type": "unmatch", "chat": uid})
        cache.publish(uid, {"type": "unmatch", "chat": other})


@router.post("/users/{other}/block")
def block(other: int, u: dict = Depends(current_user)):
    with pool.connection() as c:
        unmatched = _block(c, u["id"], other)
    _after_block(u["id"], other, unmatched)
    return {"blocked": True}


class Report(BaseModel):
    reason: Reason
    comment: str = Field("", max_length=1000)


@router.post("/users/{other}/report")
def report(other: int, r: Report, u: dict = Depends(current_user)):
    uid = u["id"]
    cache.hit("report", uid, 20, 86400)
    with pool.connection() as c:
        unmatched = _block(c, uid, other)
        c.execute("INSERT INTO reports(reporter, target, reason, comment) VALUES(%s,%s,%s,%s) "
                  "ON CONFLICT (reporter, target) WHERE status = 'open' DO NOTHING",
                  (uid, other, r.reason, r.comment.strip()))
        n = c.execute("SELECT count(DISTINCT reporter) AS n FROM reports WHERE target=%s AND status='open'",
                      (other,)).fetchone()["n"]
        hidden = n >= config.REPORTS_TO_HIDE and c.execute(
            "UPDATE users SET hidden_at=now() WHERE id=%s AND hidden_at IS NULL RETURNING id", (other,)
        ).fetchone() is not None
    _after_block(uid, other, unmatched)
    if hidden:
        cache.set_hidden(other, True)
    return {"reported": True}


# admin
@router.get("/admin/reports")
def reports(status: Literal["open", "dismissed", "actioned"] = "open", limit: int = Query(50, le=200),
            _: dict = Depends(admin_user)):
    with pool.connection() as c:
        rows = c.execute("""
            SELECT r.id, r.reason, r.comment, r.status, r.created_at,
                   r.reporter, ru.name AS reporter_name,
                   t.id AS target, t.name AS target_name, t.age AS target_age, t.bio AS target_bio,
                   t.tags AS target_tags, t.banned_at, t.hidden_at,
                   (SELECT count(*) FROM reports x WHERE x.target = t.id AND x.status = 'open') AS open_reports,
                   ARRAY(SELECT json_build_object('id', p.id, 'key', p.key) FROM photos p
                         WHERE p.user_id = t.id ORDER BY p.position, p.id) AS photos,
                   ARRAY(SELECT json_build_object('body', m.body, 'created_at', m.created_at) FROM messages m
                         WHERE m.a = LEAST(r.reporter, t.id) AND m.b = GREATEST(r.reporter, t.id)
                           AND m.sender = t.id ORDER BY m.id DESC LIMIT 20) AS messages
            FROM reports r JOIN users t ON t.id = r.target JOIN users ru ON ru.id = r.reporter
            WHERE r.status = %s ORDER BY r.id DESC LIMIT %s""", (status, limit)).fetchall()
    for r in rows:
        r["photos"] = [{"id": p["id"], "url": storage.url(p["key"])} for p in r["photos"]]
    return rows


class Resolve(BaseModel):
    action: Literal["dismiss", "ban"]


@router.post("/admin/reports/{rid}")
def resolve(rid: int, body: Resolve, a: dict = Depends(admin_user)):
    with pool.connection() as c:
        rep = c.execute("SELECT target FROM reports WHERE id=%s", (rid,)).fetchone()
        if not rep:
            raise HTTPException(404, "Жалоба не найдена")
        target = rep["target"]
        if body.action == "ban":
            c.execute("UPDATE users SET banned_at=now() WHERE id=%s", (target,))
            c.execute("UPDATE reports SET status='actioned', resolved_by=%s, resolved_at=now() "
                      "WHERE target=%s AND status='open'", (a["id"], target))
        else:
            c.execute("UPDATE reports SET status='dismissed', resolved_by=%s, resolved_at=now() "
                      "WHERE id=%s AND status='open'", (a["id"], rid))
            left = c.execute("SELECT count(DISTINCT reporter) AS n FROM reports WHERE target=%s "
                             "AND status='open'", (target,)).fetchone()["n"]
            if left < config.REPORTS_TO_HIDE:
                c.execute("UPDATE users SET hidden_at=NULL WHERE id=%s", (target,))
        st = c.execute("SELECT banned_at, hidden_at FROM users WHERE id=%s", (target,)).fetchone()
    cache.set_hidden(target, bool(st["banned_at"] or st["hidden_at"]))
    return {"ok": True}


@router.post("/admin/users/{uid}/unban")
def unban(uid: int, _: dict = Depends(admin_user)):
    with pool.connection() as c:
        if not c.execute("UPDATE users SET banned_at=NULL, hidden_at=NULL WHERE id=%s RETURNING id",
                         (uid,)).fetchone():
            raise HTTPException(404, "no such user")
    cache.set_hidden(uid, False)
    return {"ok": True}


@router.delete("/admin/photos/{pid}")
def delete_photo(pid: int, _: dict = Depends(admin_user)):
    with pool.connection() as c:
        row = c.execute("DELETE FROM photos WHERE id=%s RETURNING key", (pid,)).fetchone()
    if not row:
        raise HTTPException(404, "Фото не найдено")
    storage.delete(row["key"])
    return {"ok": True}
