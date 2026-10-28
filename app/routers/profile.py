from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..cache import feed_drop
from ..db import pool
from ..embeddings import embed
from ..security import current_user

router = APIRouter(prefix="/api")


class Prof(BaseModel):
    tags: list[str] = Field(min_length=5, max_length=10)
    bio: str = Field("", max_length=500)


@router.put("/profile")
def profile(p: Prof, u: dict = Depends(current_user)):
    tags = sorted({t.strip().lower()[:30] for t in p.tags if t.strip()})
    if len(tags) < 5:
        raise HTTPException(422, "Нужно минимум 5 разных тегов")
    with pool.connection() as c:
        c.execute("UPDATE users SET tags=%s, emb=%s::vector, bio=%s WHERE id=%s",
                  (tags, str(embed(tags)), p.bio.strip(), u["id"]))
    feed_drop(u["id"])
    return {"tags": tags}
