"""FastAPI transport adapter. Routes and request DTOs; no SQL in this module."""
from app.infrastructure.repositories import chat as adapter
from app.application.use_cases.chat import ChatUseCases
use_cases = ChatUseCases(adapter)
from app.infrastructure.repositories.chat import *  # noqa: F401,F403
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.get('/matches')
def matches(u: dict=Depends(verified_user)):
    return use_cases.matches(u)

@router.get('/chats/{other}/messages')
def history(other: int, before: int | None=None, limit: int=Query(50, ge=1, le=100), u: dict=Depends(verified_user)):
    return use_cases.history(other, before, limit, u)

@router.post('/chats/{other}/messages')
def send(other: int, m: Msg, u: dict=Depends(verified_user)):
    return use_cases.send(other, m, u)

@router.post('/chats/{other}/read')
def mark_read(other: int, u: dict=Depends(verified_user)):
    return use_cases.mark_read(other, u)

@router.websocket('/ws')
async def ws(websocket: WebSocket):
    return await use_cases.ws(websocket)

