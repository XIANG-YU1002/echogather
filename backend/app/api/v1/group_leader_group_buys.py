import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_active_group_leader_profile, get_db
from app.core.responses import envelope, paginated_envelope
from app.models.enums import GroupBuyListSort, GroupBuyStatus
from app.models.group_leader import GroupLeaderProfile
from app.schemas.group_leader_group_buy import (
    AddGroupBuyProductRequest,
    CreateGroupBuyRequest,
    UpdateGroupBuyProductRequest,
    UpdateGroupBuySettingsRequest,
)
from app.services import group_leader_group_buy_service as service

router = APIRouter(prefix="/group-leader/group-buys", tags=["group-leader-group-buys"])


@router.get("")
def get_my_group_buys(
    status_filter: GroupBuyStatus | None = Query(None, alias="status"),
    keyword: str | None = Query(None, description="比對活動名稱（不分大小寫部分比對）"),
    sort: GroupBuyListSort = Query(
        GroupBuyListSort.CREATED_DESC, description="依開團建立時間排序"
    ),
    pagination: PaginationParams = Depends(),
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    items, total, summary = service.get_my_group_buys(
        db,
        profile,
        status_filter,
        pagination.page,
        pagination.page_size,
        keyword=keyword,
        sort=sort,
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items],
        pagination.page,
        pagination.page_size,
        total,
        summary=summary.model_dump(mode="json"),
    )


@router.get("/open")
def get_my_open_group_buys(
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    """圖 20 儀表板「目前開團」：只列進行中、不分頁。"""
    items = service.get_my_open_group_buys(db, profile)
    return envelope([i.model_dump(mode="json") for i in items])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group_buy(
    payload: CreateGroupBuyRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.create_group_buy(db, profile, payload)
    return envelope(result.model_dump(mode="json"))


@router.get("/{group_buy_id}")
def get_my_group_buy_detail(
    group_buy_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.get_my_group_buy_detail(db, profile, group_buy_id)
    return envelope(result.model_dump(mode="json"))


@router.get("/{group_buy_id}/product-orders")
def get_group_buy_product_orders(
    group_buy_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    """圖 22 商品訂購總覽：該開團每個商品的訂購總量、成員數與明細。"""
    result = service.get_product_orders(db, profile, group_buy_id)
    return envelope(result.model_dump(mode="json"))


@router.patch("/{group_buy_id}")
def update_group_buy_settings(
    group_buy_id: uuid.UUID,
    payload: UpdateGroupBuySettingsRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.update_group_buy_settings(db, profile, group_buy_id, payload)
    return envelope(result.model_dump(mode="json"))


@router.post("/{group_buy_id}/products", status_code=status.HTTP_201_CREATED)
def add_group_buy_product(
    group_buy_id: uuid.UUID,
    payload: AddGroupBuyProductRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.add_group_buy_product(db, profile, group_buy_id, payload)
    return envelope(result.model_dump(mode="json"))


@router.patch("/{group_buy_id}/products/{group_buy_product_id}")
def update_group_buy_product(
    group_buy_id: uuid.UUID,
    group_buy_product_id: uuid.UUID,
    payload: UpdateGroupBuyProductRequest,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.update_group_buy_product(
        db, profile, group_buy_id, group_buy_product_id, payload
    )
    return envelope(result.model_dump(mode="json"))


@router.delete("/{group_buy_id}/products/{group_buy_product_id}")
def remove_group_buy_product(
    group_buy_id: uuid.UUID,
    group_buy_product_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.remove_group_buy_product(db, profile, group_buy_id, group_buy_product_id)
    return envelope(result.model_dump(mode="json"))


@router.post("/{group_buy_id}/close")
def close_group_buy(
    group_buy_id: uuid.UUID,
    profile: GroupLeaderProfile = Depends(get_current_active_group_leader_profile),
    db: Session = Depends(get_db),
) -> dict:
    result = service.close_group_buy(db, profile, group_buy_id)
    return envelope(result.model_dump(mode="json"))
