import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_member_user, get_db
from app.core.responses import envelope
from app.models.user import AppUser
from app.schemas.follow_list import (
    AddFollowListItemRequest,
    UpdateFollowListItemQuantityRequest,
)
from app.services import follow_list_service

router = APIRouter(prefix="/follow-list", tags=["follow-list"])


@router.get("")
def get_follow_list(
    current_user: AppUser = Depends(get_current_member_user), db: Session = Depends(get_db)
) -> dict:
    result = follow_list_service.get_follow_list(db, current_user.id)
    return envelope(result.model_dump(mode="json") if result is not None else None)


@router.post("/items", status_code=status.HTTP_201_CREATED)
def add_follow_list_item(
    payload: AddFollowListItemRequest,
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> dict:
    result = follow_list_service.add_item(db, current_user.id, payload)
    return envelope(result.model_dump(mode="json"))


@router.patch("/items/{item_id}")
def update_follow_list_item_quantity(
    item_id: uuid.UUID,
    payload: UpdateFollowListItemQuantityRequest,
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> dict:
    result = follow_list_service.update_item_quantity(
        db, current_user.id, item_id, payload.quantity
    )
    return envelope(result.model_dump(mode="json"))


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_follow_list_item(
    item_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> None:
    follow_list_service.remove_item(db, current_user.id, item_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_follow_list(
    current_user: AppUser = Depends(get_current_member_user), db: Session = Depends(get_db)
) -> None:
    follow_list_service.clear_follow_list(db, current_user.id)
