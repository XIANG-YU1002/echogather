import uuid

from pydantic import BaseModel

from app.models.enums import ActivityStatus, Currency
from app.schemas.common import Money, UTCDateTime
from app.schemas.product import CharacterSummary


class ActivityListItem(BaseModel):
    id: uuid.UUID
    name: str
    image_url: str
    status: ActivityStatus
    has_full_gift: bool
    created_at: UTCDateTime


class ActivityDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    image_url: str
    status: ActivityStatus
    has_full_gift: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ActivityProductCard(BaseModel):
    """活動底下的商品卡。

    官方價與角色清單供圖 24 建立開團頁使用：商品卡要顯示官方定價作為訂價參考，
    多角色商品則需逐角色設定接單上限。
    """

    id: uuid.UUID
    name: str
    primary_image_url: str
    official_price: Money | None
    official_currency: Currency | None
    # 無角色商品為空陣列
    characters: list[CharacterSummary]
