import json, logging, time

import redis
import redis.asyncio as aioredis
from fastapi import HTTPException, Request

from . import config

log = logging.getLogger(__name__)
r = redis.Redis.from_url(config.REDIS_URL, decode_responses=True,
                         socket_timeout=0.5, socket_connect_timeout=0.5)
_ar = None


def aio():
    global _ar
    if _ar is None:
        _ar = aioredis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    return _ar


def hit(name, key, limit, window):
    if not config.RATE_LIMITS:
        return
    now = int(time.time())
    k = f"rl:{name}:{key}:{now // window}"
    try:
        p = r.pipeline()
        p.incr(k)
        p.expire(k, window)
        n = p.execute()[0]
    except redis.RedisError as e:
        log.warning("rate limit skipped: %s", e)
        return
    if n > limit:
        raise HTTPException(429, "Слишком много запросов, попробуйте позже",
                            headers={"Retry-After": str(window - now % window)})


def client_ip(request: Request):
    if config.TRUST_PROXY and (fwd := request.headers.get("x-forwarded-for")):
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def limit_ip(name, limit, window):
    def dep(request: Request):
        hit(name, client_ip(request), limit, window)
    return dep


# feed:{uid} - cached candidates, swiped:{uid} - swiped after caching, feed:hidden - banned/hidden

def feed_get(uid):
    try:
        raw = r.get(f"feed:{uid}")
        if raw is None:
            return None
        data = json.loads(raw)
        ids = [c["id"] for c in data["items"]]
        if ids:
            p = r.pipeline()
            p.smismember(f"swiped:{uid}", ids)
            p.smismember("feed:hidden", ids)
            swiped, hidden = p.execute()
            data["items"] = [c for c, a, b in zip(data["items"], swiped, hidden) if not a and not b]
        return data
    except redis.RedisError as e:
        log.warning("feed cache unavailable: %s", e)
        return None


def feed_put(uid, items, exhausted):
    try:
        p = r.pipeline()
        p.set(f"feed:{uid}", json.dumps({"items": items, "exhausted": exhausted}, default=str),
              ex=config.FEED_CACHE_TTL)
        p.delete(f"swiped:{uid}")
        p.execute()
    except redis.RedisError as e:
        log.warning("feed cache unavailable: %s", e)


def feed_drop(*uids):
    try:
        r.delete(*[f"feed:{u}" for u in uids])
    except redis.RedisError as e:
        log.warning("feed cache unavailable: %s", e)


def mark_swiped(uid, target):
    try:
        p = r.pipeline()
        p.sadd(f"swiped:{uid}", target)
        p.expire(f"swiped:{uid}", config.FEED_CACHE_TTL * 2)
        p.execute()
    except redis.RedisError as e:
        log.warning("feed cache unavailable: %s", e)


def set_hidden(uid, hidden):
    try:
        (r.sadd if hidden else r.srem)("feed:hidden", uid)
    except redis.RedisError as e:
        log.warning("feed cache unavailable: %s", e)


def publish(uid, event):
    try:
        r.publish(f"user:{uid}", json.dumps(event, default=str))
    except redis.RedisError as e:
        log.warning("publish failed: %s", e)
