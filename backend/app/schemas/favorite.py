import enum
import uuid

from pydantic import BaseModel

from app.models.enums import Currency
from app.schemas.common import Money, UTCDateTime


class FavoriteSort(str, enum.Enum):
    """收藏清單排序方式（依圖 11 的「排序方式」下拉）。"""

    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    NAME_ASC = "name_asc"
    PRICE_DESC = "price_desc"
    PRICE_ASC = "price_asc"


class FavoriteActivityRef(BaseModel):
    id: uuid.UUID
    name: str


class FavoriteProductSummary(BaseModel):
    id: uuid.UUID
    name: str
    primary_image_url: str
    is_active: bool
    official_price: Money | None
    official_currency: Currency | None
    activity: FavoriteActivityRef


class FavoriteItem(BaseModel):
    favorite_id: uuid.UUID
    product: FavoriteProductSummary
    created_at: UTCDateTime


class AddFavoriteResponse(BaseModel):
    product_id: uuid.UUID
    is_favorited: bool
