"""FastAPI transport adapter. Routes and request DTOs; no SQL in this module."""
from app.infrastructure.repositories import auth as adapter
from app.application.use_cases.auth import AuthUseCases
use_cases = AuthUseCases(adapter)
from fastapi import Depends, BackgroundTasks, HTTPException
from app.cache import limit_ip
from app.security import current_user
from app.infrastructure.repositories.auth import Reg, Login
from app.presentation.dependencies import login_use_case
from app.application.use_cases.login import LoginUser
from app.domain.services.auth import InvalidCredentials, BannedAccount
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.post('/register', dependencies=[Depends(limit_ip('register', 20, 3600))])
def register(r: Reg, bg: BackgroundTasks):
    return use_cases.register(r, bg)

@router.post('/login', dependencies=[Depends(limit_ip('login', 20, 300))])
def login(r: Login, use_case: LoginUser = Depends(login_use_case)):
    try:
        return use_case.execute(r.email, r.password)
    except InvalidCredentials as exc:
        raise HTTPException(401, str(exc)) from exc
    except BannedAccount as exc:
        raise HTTPException(403, str(exc)) from exc

@router.get('/verify-email')
def verify_email(token: str):
    return use_cases.verify_email(token)

@router.post('/resend-verification')
def resend(bg: BackgroundTasks, u: dict=Depends(current_user)):
    return use_cases.resend(bg, u)

@router.get('/me')
def me(u: dict=Depends(current_user)):
    return use_cases.me(u)

