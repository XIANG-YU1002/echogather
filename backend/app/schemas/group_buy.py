import uuid
from enum import Enum

from pydantic import BaseModel

from app.models.enums import ActivityStatus, ContactPlatform, GroupBuyStatus, PaymentMethod
from app.schemas.common import Money, UTCDateTime
from app.schemas.group_leader import GroupLeaderSummary


class GroupBuySortOption(str, Enum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    DEADLINE_ASC = "deadline_asc"
    DEADLINE_DESC = "deadline_desc"


class GroupBuyActivitySummary(BaseModel):
    id: uuid.UUID
    name: str
    status: ActivityStatus
    has_full_gift: bool = False


class GroupBuyProductRef(BaseModel):
    id: uuid.UUID
    name: str
    primary_image_url: str


class GroupBuyProductCharacterOption(BaseModel):
    character_id: uuid.UUID
    name: str
    available_quantity: int
    is_available: bool


class GroupBuyProductItem(BaseModel):
    group_buy_product_id: uuid.UUID
    product: GroupBuyProductRef
    unit_price: Money
    available_quantity: int
    is_available: bool
    # 多角色商品的可選角色（含各角色剩餘）；無角色商品為空陣列。
    characters: list[GroupBuyProductCharacterOption] = []


class GroupBuyDetailResponse(BaseModel):
    id: uuid.UUID
    activity: GroupBuyActivitySummary
    group_leader: GroupLeaderSummary
    payment_method: PaymentMethod
    payment_method_note: str | None
    requires_second_payment: bool
    includes_full_gift: bool
    deadline_at: UTCDateTime
    rules: str
    contact_platform: ContactPlatform
    contact_value: str
    status: GroupBuyStatus
    effective_status: str
    is_available: bool
    products: list[GroupBuyProductItem]
    created_at: UTCDateTime


class GroupBuyRulesResponse(BaseModel):
    rules: str
    updated_at: UTCDateTime


class GroupBuyProductAvailabilityResponse(BaseModel):
    group_buy_product_id: uuid.UUID
    is_available: bool
    available_quantity: int
    effective_status: str


class PublicGroupLeaderGroupBuyItem(BaseModel):
    id: uuid.UUID
    activity: GroupBuyActivitySummary
    status: GroupBuyStatus
    effective_status: str
    deadline_at: UTCDateTime
    created_at: UTCDateTime
