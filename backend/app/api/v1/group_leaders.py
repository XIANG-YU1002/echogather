import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.core.responses import envelope, paginated_envelope
from app.models.enums import GroupBuyStatus
from app.schemas.group_leader import GroupLeaderSort
from app.services import group_leader_public_service

router = APIRouter(prefix="/group-leaders", tags=["group-leaders"])


@router.get("")
def list_public_profiles(
    keyword: str | None = Query(None),
    sort: GroupLeaderSort = GroupLeaderSort.CREATED_DESC,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    items, total = group_leader_public_service.list_public_profiles(
        db,
        keyword=keyword,
        page=pagination.page,
        page_size=pagination.page_size,
        sort=sort,
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items], pagination.page, pagination.page_size, total
    )


@router.get("/{group_leader_id}")
def get_public_profile(group_leader_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    result = group_leader_public_service.get_public_profile(db, group_leader_id)
    return envelope(result.model_dump(mode="json"))


@router.get("/{group_leader_id}/group-buys")
def get_public_group_buys(
    group_leader_id: uuid.UUID,
    status: GroupBuyStatus | None = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    items, total = group_leader_public_service.get_public_group_buys(
        db, group_leader_id, status, pagination.page, pagination.page_size
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items], pagination.page, pagination.page_size, total
    )


@router.get("/{group_leader_id}/announcements")
def get_public_announcements(group_leader_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    items = group_leader_public_service.get_public_announcements(db, group_leader_id)
    return envelope([i.model_dump(mode="json") for i in items])
