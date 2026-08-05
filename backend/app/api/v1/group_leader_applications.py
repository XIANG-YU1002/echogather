from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_member_user, get_db
from app.core.responses import envelope
from app.models.user import AppUser
from app.schemas.group_leader_application import SubmitApplicationRequest
from app.services import group_leader_application_service as service

router = APIRouter(prefix="/group-leader-applications", tags=["group-leader-applications"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_application(
    payload: SubmitApplicationRequest | None = None,
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> dict:
    application = service.submit_application(db, current_user, payload)
    response = service.application_to_response(application)
    return envelope(response.model_dump(mode="json"))


@router.get("/me")
def get_my_application(
    current_user: AppUser = Depends(get_current_member_user), db: Session = Depends(get_db)
) -> dict:
    result = service.get_my_application(db, current_user)
    return envelope(result.model_dump(mode="json") if result is not None else None)
