"""FastAPI transport adapter. Routes and request DTOs; no SQL in this module."""
from app.infrastructure.repositories import feed as adapter
from app.application.use_cases.feed import FeedUseCases
use_cases = FeedUseCases(adapter)
from app.infrastructure.repositories.feed import *  # noqa: F401,F403
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.get('/feed')
def feed(limit: int=Query(20, ge=1, le=50), u: dict=Depends(verified_user)):
    return use_cases.feed(limit, u)

@router.post('/swipe')
def swipe(s: Swipe, u: dict=Depends(verified_user)):
    return use_cases.swipe(s, u)

