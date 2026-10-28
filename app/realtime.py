import asyncio, contextlib, logging
from collections import defaultdict

import redis

from .cache import aio

log = logging.getLogger(__name__)
SEND_TIMEOUT = 5


class Hub:
    # one pubsub connection per worker for all its sockets

    def __init__(self):
        self.sockets = defaultdict(set)
        self.waiting = {}
        self.ps = None
        self.task = None
        self.lock = asyncio.Lock()

    async def _ensure(self):
        if self.task is None or self.task.done():
            self.ps = aio().pubsub()
            await self.ps.subscribe("hub:keepalive")
            for uid in self.sockets:
                await self.ps.subscribe(f"user:{uid}")
            self.task = asyncio.create_task(self._run())

    async def add(self, uid, ws):
        async with self.lock:
            await self._ensure()
            first = not self.sockets[uid]
            self.sockets[uid].add(ws)
            if first:
                ev = self.waiting[f"user:{uid}"] = asyncio.Event()
                await self.ps.subscribe(f"user:{uid}")
        if first:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(ev.wait(), 2)

    async def remove(self, uid, ws):
        async with self.lock:
            s = self.sockets.get(uid)
            if s is None:
                return
            s.discard(ws)
            if not s:
                del self.sockets[uid]
                with contextlib.suppress(Exception):
                    await self.ps.unsubscribe(f"user:{uid}")

    async def _send(self, ws, data):
        try:
            await asyncio.wait_for(ws.send_text(data), SEND_TIMEOUT)
        except Exception:
            with contextlib.suppress(Exception):
                await ws.close()

    async def _run(self):
        while True:
            try:
                async for m in self.ps.listen():
                    ch = m["channel"]
                    if m["type"] == "subscribe" and ch in self.waiting:
                        self.waiting.pop(ch).set()
                    elif m["type"] == "message" and ch.startswith("user:"):
                        targets = list(self.sockets.get(int(ch[5:]), ()))
                        if targets:
                            await asyncio.gather(*(self._send(ws, m["data"]) for ws in targets))
            except asyncio.CancelledError:
                raise
            except (redis.RedisError, OSError) as e:
                log.warning("pubsub connection lost: %s", e)
                await asyncio.sleep(1)
                async with self.lock:
                    with contextlib.suppress(Exception):
                        await self.ps.aclose()
                    self.ps = aio().pubsub()
                    await self.ps.subscribe("hub:keepalive", *[f"user:{u}" for u in self.sockets])


hub = Hub()
