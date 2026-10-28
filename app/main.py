import logging, os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .db import close_pools, open_pools
from .routers import auth, chat, feed, moderation, photos, profile

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    open_pools()
    yield
    close_pools()


app = FastAPI(title="Orbita", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


for r in (auth, profile, feed, chat, photos, moderation):
    app.include_router(r.router)

# in production nginx serves these directly
os.makedirs(config.MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static"), html=True),
          name="static")
