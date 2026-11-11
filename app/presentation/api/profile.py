"""Transport layer for profile updates."""
from fastapi import APIRouter, Depends, HTTPException
from app.domain.services.profile import InvalidTags
from app.presentation.schemas.profile import Prof
from app.presentation.dependencies import update_profile_use_case
from app.application.use_cases.profile import ProfileUseCases
from app.security import current_user

router = APIRouter(prefix='/api')

@router.put('/profile')
def profile(p: Prof, u: dict = Depends(current_user),
            use_case: ProfileUseCases = Depends(update_profile_use_case)):
    try:
        return use_case.update(u['id'], p.tags, p.bio)
    except InvalidTags as exc:
        raise HTTPException(422, str(exc)) from exc
