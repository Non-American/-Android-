"""FastAPI transport adapter. Routes and request DTOs; no SQL in this module."""
from app.infrastructure.repositories import photos as adapter
from app.application.use_cases.photos import PhotosUseCases
use_cases = PhotosUseCases(adapter)
from app.infrastructure.repositories.photos import *  # noqa: F401,F403
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.post('/photos')
async def upload(file: UploadFile=File(...), u: dict=Depends(current_user)):
    return await use_cases.upload(file, u)

@router.delete('/photos/{pid}')
def delete(pid: int, u: dict=Depends(current_user)):
    return use_cases.delete(pid, u)

@router.post('/photos/{pid}/main')
def make_main(pid: int, u: dict=Depends(current_user)):
    return use_cases.make_main(pid, u)

