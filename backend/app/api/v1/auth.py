from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.responses import envelope
from app.models.user import AppUser
from app.schemas.user import (
    CurrentSessionResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
)
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verification-codes", status_code=status.HTTP_201_CREATED)
def send_verification_code(
    payload: SendVerificationCodeRequest, db: Session = Depends(get_db)
) -> dict:
    result = auth_service.send_verification_code(db, payload)
    return envelope(result.model_dump(mode="json"))


@router.post("/password-reset-requests", status_code=status.HTTP_201_CREATED)
def request_password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict:
    result = auth_service.request_password_reset(db, payload)
    return envelope(result.model_dump(mode="json"))


@router.get("/password-reset-tokens/{token}")
def verify_password_reset_token(token: str, db: Session = Depends(get_db)) -> dict:
    """前端在顯示重設表單前先確認連結有效，避免使用者填完才被拒。"""
    return envelope({"is_valid": auth_service.verify_password_reset_token(db, token)})


@router.post("/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.reset_password(db, payload)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    user = auth_service.register(db, payload)
    response = RegisterResponse.model_validate(user, from_attributes=True)
    return envelope(response.model_dump(mode="json"))


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    access_token, expires_in = auth_service.login(db, payload)
    response = LoginResponse(access_token=access_token, expires_in=expires_in)
    return envelope(response.model_dump(mode="json"))


@router.get("/me")
def get_current_session(
    current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    response: CurrentSessionResponse = user_service.build_current_session(db, current_user)
    return envelope(response.model_dump(mode="json"))
