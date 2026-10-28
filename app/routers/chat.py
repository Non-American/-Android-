import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from .. import cache
from ..db import pool
from ..realtime import hub
from ..security import load_user, read_token, verified_user
from ..storage import storage

router = APIRouter(prefix="/api")

MATCHES_SQL = """
SELECT u.id, u.name, u.age, m.created_at AS matched_at,
  (SELECT p.key FROM photos p WHERE p.user_id = u.id ORDER BY p.position, p.id LIMIT 1) AS photo,
  lm.body AS last_body, lm.sender AS last_sender, lm.created_at AS last_at,
  (SELECT count(*) FROM messages x
    WHERE x.a = m.a AND x.b = m.b AND x.sender <> %(uid)s AND x.read_at IS NULL) AS unread
FROM matches m
JOIN users u ON u.id = CASE WHEN m.a = %(uid)s THEN m.b ELSE m.a END
LEFT JOIN LATERAL (SELECT body, sender, created_at FROM messages x
                   WHERE x.a = m.a AND x.b = m.b ORDER BY x.id DESC LIMIT 1) lm ON true
WHERE (m.a = %(uid)s OR m.b = %(uid)s) AND u.banned_at IS NULL
ORDER BY COALESCE(lm.created_at, m.created_at) DESC
LIMIT 200
"""


@router.get("/matches")
def matches(u: dict = Depends(verified_user)):
    with pool.connection() as c:
        rows = c.execute(MATCHES_SQL, {"uid": u["id"]}).fetchall()
    return [{**r, "photo": r["photo"] and storage.url(r["photo"])} for r in rows]


def _pair(c, uid, other):
    a, b = sorted((uid, other))
    if not c.execute("SELECT 1 FROM matches m JOIN users u ON u.id=%s "
                     "WHERE m.a=%s AND m.b=%s AND u.banned_at IS NULL", (other, a, b)).fetchone():
        raise HTTPException(403, "Переписка доступна только после взаимного лайка")
    return a, b


@router.get("/chats/{other}/messages")
def history(other: int, before: int | None = None, limit: int = Query(50, ge=1, le=100),
            u: dict = Depends(verified_user)):
    uid = u["id"]
    with pool.connection() as c:
        a, b = _pair(c, uid, other)
        rows = c.execute(
            "SELECT id, sender, body, created_at, read_at FROM messages "
            "WHERE a=%s AND b=%s AND (%s::bigint IS NULL OR id < %s) ORDER BY id DESC LIMIT %s",
            (a, b, before, before, limit)).fetchall()
        read = c.execute("UPDATE messages SET read_at=now() WHERE a=%s AND b=%s AND sender=%s "
                         "AND read_at IS NULL RETURNING id", (a, b, other)).fetchall()
    if read:
        cache.publish(other, {"type": "read", "chat": uid, "upto": max(r["id"] for r in read)})
    return rows[::-1]


class Msg(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


@router.post("/chats/{other}/messages")
def send(other: int, m: Msg, u: dict = Depends(verified_user)):
    uid, body = u["id"], m.body.strip()
    if not body:
        raise HTTPException(422, "Пустое сообщение")
    cache.hit("msg", uid, 30, 60)
    with pool.connection() as c:
        a, b = _pair(c, uid, other)
        row = c.execute("INSERT INTO messages(a,b,sender,body) VALUES(%s,%s,%s,%s) "
                        "RETURNING id, sender, body, created_at, read_at", (a, b, uid, body)).fetchone()
    cache.publish(other, {"type": "message", "chat": uid, "message": row})
    cache.publish(uid, {"type": "message", "chat": other, "message": row})
    return row


@router.post("/chats/{other}/read")
def mark_read(other: int, u: dict = Depends(verified_user)):
    with pool.connection() as c:
        a, b = _pair(c, u["id"], other)
        read = c.execute("UPDATE messages SET read_at=now() WHERE a=%s AND b=%s AND sender=%s "
                         "AND read_at IS NULL RETURNING id", (a, b, other)).fetchall()
    if read:
        cache.publish(other, {"type": "read", "chat": u["id"], "upto": max(r["id"] for r in read)})
    return {"read": len(read)}


@router.websocket("/ws")
async def ws(websocket: WebSocket):
    # token comes in the first frame, not in the url
    await websocket.accept()
    try:
        tok = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        uid = int(read_token(tok)["sub"])
        user = await run_in_threadpool(load_user, uid)
    except Exception:
        user = None
    if not user or user["banned_at"]:
        await websocket.close(code=4401)
        return
    await hub.add(uid, websocket)
    try:
        await websocket.send_json({"type": "ready"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.remove(uid, websocket)
