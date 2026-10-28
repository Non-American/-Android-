import io, uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError

from .. import config
from ..cache import hit
from ..db import pool
from ..security import current_user
from ..storage import storage

router = APIRouter(prefix="/api")
Image.MAX_IMAGE_PIXELS = 40_000_000
MAX_SIDE = 1600


def process(data: bytes) -> bytes:
    # re-encoding drops all metadata (incl. GPS)
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in ("JPEG", "PNG", "WEBP", "MPO"):
                raise HTTPException(415, "Поддерживаются JPEG, PNG и WebP")
            im = ImageOps.exif_transpose(im)
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            if im.mode != "RGB":
                bg = Image.new("RGB", im.size, "white")
                rgba = im.convert("RGBA")
                bg.paste(rgba, mask=rgba.getchannel("A"))
                im = bg
            out = io.BytesIO()
            im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
            return out.getvalue()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise HTTPException(415, "Не удалось прочитать изображение")


def _list(c, uid):
    rows = c.execute("SELECT id, key FROM photos WHERE user_id=%s ORDER BY position, id", (uid,)).fetchall()
    return [{"id": r["id"], "url": storage.url(r["key"])} for r in rows]


@router.post("/photos")
async def upload(file: UploadFile = File(...), u: dict = Depends(current_user)):
    uid = u["id"]
    hit("photo", uid, 20, 3600)
    data = await file.read(config.MAX_PHOTO_BYTES + 1)
    if len(data) > config.MAX_PHOTO_BYTES:
        raise HTTPException(413, "Файл больше 8 МБ")
    jpeg = await run_in_threadpool(process, data)
    key = f"{uid}/{uuid.uuid4().hex}.jpg"

    def store():
        with pool.connection() as c:
            c.execute("SELECT 1 FROM users WHERE id=%s FOR UPDATE", (uid,))
            n = c.execute("SELECT count(*) AS n, COALESCE(max(position)+1, 0) AS pos FROM photos "
                          "WHERE user_id=%s", (uid,)).fetchone()
            if n["n"] >= config.MAX_PHOTOS:
                raise HTTPException(409, f"Можно загрузить не больше {config.MAX_PHOTOS} фото")
            storage.save(key, jpeg)
            c.execute("INSERT INTO photos(user_id, key, position) VALUES(%s,%s,%s)", (uid, key, n["pos"]))
            return _list(c, uid)

    return await run_in_threadpool(store)


@router.delete("/photos/{pid}")
def delete(pid: int, u: dict = Depends(current_user)):
    with pool.connection() as c:
        row = c.execute("DELETE FROM photos WHERE id=%s AND user_id=%s RETURNING key", (pid, u["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Фото не найдено")
        photos = _list(c, u["id"])
    storage.delete(row["key"])
    return photos


@router.post("/photos/{pid}/main")
def make_main(pid: int, u: dict = Depends(current_user)):
    with pool.connection() as c:
        if not c.execute("UPDATE photos SET position = -1 WHERE id=%s AND user_id=%s RETURNING id",
                         (pid, u["id"])).fetchone():
            raise HTTPException(404, "Фото не найдено")
        c.execute("UPDATE photos p SET position = o.rn - 1 FROM (SELECT id, row_number() OVER "
                  "(ORDER BY position, id) AS rn FROM photos WHERE user_id=%s) o WHERE p.id = o.id",
                  (u["id"],))
        return _list(c, u["id"])
