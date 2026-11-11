"""FastAPI transport adapter. Routes and request DTOs; no SQL in this module."""
from app.infrastructure.repositories import moderation as adapter
from app.application.use_cases.moderation import ModerationUseCases
use_cases = ModerationUseCases(adapter)
from app.infrastructure.repositories.moderation import *  # noqa: F401,F403
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.post('/users/{other}/block')
def block(other: int, u: dict=Depends(current_user)):
    return use_cases.block(other, u)

@router.post('/users/{other}/report')
def report(other: int, r: Report, u: dict=Depends(current_user)):
    return use_cases.report(other, r, u)

@router.get('/admin/reports')
def reports(status: Literal['open', 'dismissed', 'actioned']='open', limit: int=Query(50, le=200), _: dict=Depends(admin_user)):
    return use_cases.reports(status, limit, _)

@router.post('/admin/reports/{rid}')
def resolve(rid: int, body: Resolve, a: dict=Depends(admin_user)):
    return use_cases.resolve(rid, body, a)

@router.post('/admin/users/{uid}/unban')
def unban(uid: int, _: dict=Depends(admin_user)):
    return use_cases.unban(uid, _)

@router.delete('/admin/photos/{pid}')
def delete_photo(pid: int, _: dict=Depends(admin_user)):
    return use_cases.delete_photo(pid, _)

