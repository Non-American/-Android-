import hashlib, hmac, secrets, time

import jwt
from fastapi import Depends, Header, HTTPException

from . import config
from .db import pool


def hash_pw(pw, salt=None):
    salt = salt or secrets.token_bytes(16)
    return salt.hex() + "$" + hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def check_pw(pw, h):
    return hmac.compare_digest(hash_pw(pw, bytes.fromhex(h.split("$")[0])), h)


def make_token(uid, typ="access", ttl=7 * 86400, **extra):
    return jwt.encode({"sub": str(uid), "typ": typ, "exp": int(time.time()) + ttl, **extra},
                      config.JWT_SECRET, "HS256")


def read_token(tok, typ="access"):
    p = jwt.decode(tok, config.JWT_SECRET, ["HS256"])
    if p.get("typ") != typ:
        raise jwt.InvalidTokenError("wrong token type")
    return p


def load_user(uid):
    with pool.connection() as c:
        return c.execute("SELECT id, email, name, email_verified_at, role, banned_at FROM users WHERE id=%s",
                         (uid,)).fetchone()


def current_uid(authorization: str = Header("")) -> int:
    try:
        return int(read_token(authorization.removeprefix("Bearer "))["sub"])
    except Exception:
        raise HTTPException(401, "unauthorized")


def current_user(uid: int = Depends(current_uid)) -> dict:
    u = load_user(uid)
    if not u:
        raise HTTPException(401, "unauthorized")
    if u["banned_at"]:
        raise HTTPException(403, "banned")
    return u


def verified_user(u: dict = Depends(current_user)) -> dict:
    if not u["email_verified_at"]:
        raise HTTPException(403, "email_unverified")
    return u


def admin_user(u: dict = Depends(current_user)) -> dict:
    if u["role"] != "admin":
        raise HTTPException(403, "forbidden")
    return u
