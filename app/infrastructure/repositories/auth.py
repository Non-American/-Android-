"""Persistence and integration adapter (migration stage)."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field
from app.cache import hit, limit_ip
from app.db import pool
from app.mailer import send_verification
from app.security import check_pw, current_user, hash_pw, make_token, read_token
from app.storage import storage
router = APIRouter(prefix='/api')

class Login(BaseModel):
    email: str = Field(pattern='^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$', max_length=200)
    password: str = Field(min_length=8, max_length=200)

class Reg(Login):
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=18, le=99)

def register(r: Reg, bg: BackgroundTasks):
    email, name = (r.email.lower(), r.name.strip())
    if not name:
        raise HTTPException(422, 'Укажите имя')
    with pool.connection() as c:
        try:
            row = c.execute('INSERT INTO users(email,pw_hash,name,age) VALUES(%s,%s,%s,%s) RETURNING id', (email, hash_pw(r.password), name, r.age)).fetchone()
        except UniqueViolation:
            raise HTTPException(409, 'Этот email уже зарегистрирован')
    bg.add_task(send_verification, row['id'], email, name)
    return {'token': make_token(row['id'])}

def verify_email(token: str):
    try:
        p = read_token(token, 'verify')
    except Exception:
        return RedirectResponse('/#verify-failed', 303)
    with pool.connection() as c:
        c.execute('UPDATE users SET email_verified_at = COALESCE(email_verified_at, now()) WHERE id=%s AND email=%s', (int(p['sub']), p['email']))
    return RedirectResponse('/#verified', 303)

def resend(bg: BackgroundTasks, u: dict=Depends(current_user)):
    if u['email_verified_at']:
        return {'sent': False}
    hit('resend', u['id'], 3, 3600)
    bg.add_task(send_verification, u['id'], u['email'], u['name'])
    return {'sent': True}

def me(u: dict=Depends(current_user)):
    with pool.connection() as c:
        p = c.execute('SELECT name, age, bio, tags, emb IS NOT NULL AS has_profile FROM users WHERE id=%s', (u['id'],)).fetchone()
        photos = c.execute('SELECT id, key FROM photos WHERE user_id=%s ORDER BY position, id', (u['id'],)).fetchall()
    return {'id': u['id'], 'email': u['email'], 'role': u['role'], 'email_verified': u['email_verified_at'] is not None, **p, 'photos': [{'id': f['id'], 'url': storage.url(f['key'])} for f in photos]}
