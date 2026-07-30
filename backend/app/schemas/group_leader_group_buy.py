import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import (
    ActivityStatus,
    ContactPlatform,
    GroupBuyStatus,
    OrderStatus,
    PaymentMethod,
)
from app.schemas.common import Money, UTCDateTime, normalize_optional_text


class GroupBuyProductCharacterInput(BaseModel):
    character_id: uuid.UUID
    # 0＝不接這個角色的單。單商品多角色時，團主可只接部分角色（缺貨或不代購的設 0）。
    # 「單一角色商品不可為 0」「多角色不可全部為 0」是跨列條件，由 service 驗證。
    max_quantity: int = Field(ge=0)


class GroupBuyProductInput(BaseModel):
    product_id: uuid.UUID
    unit_price: Money = Field(ge=0)
    # 商品層級上限維持至少 1：勾選商品就代表要接單，完全不接應該取消勾選而不是填 0。
    max_quantity: int = Field(gt=0)
    # 多角色商品的每角色接單上限；未提供時後端以 max_quantity 作為每角色 fallback。
    character_quantities: list[GroupBuyProductCharacterInput] = []


class CreateGroupBuyRequest(BaseModel):
    activity_id: uuid.UUID
    products: list[GroupBuyProductInput] = Field(min_length=1)
    payment_method: PaymentMethod
    payment_method_note: str | None = None
    requires_second_payment: bool = False
    includes_full_gift: bool = False
    deadline_at: datetime
    rules: str
    contact_platform: ContactPlatform
    contact_value: str

    @field_validator("payment_method_note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("rules", "contact_value")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed

    @model_validator(mode="after")
    def _normalize_payment_method_note(self) -> "CreateGroupBuyRequest":
        """付款方式備註為選填；空白字串一律正規化成 None。"""
        if self.payment_method_note is not None:
            trimmed = self.payment_method_note.strip()
            self.payment_method_note = trimmed or None
        return self

    @model_validator(mode="after")
    def _validate_no_duplicate_products(self) -> "CreateGroupBuyRequest":
        product_ids = [item.product_id for item in self.products]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("商品不得重複。")
        return self


class UpdateGroupBuySettingsRequest(BaseModel):
    payment_method: PaymentMethod | None = None
    payment_method_note: str | None = None
    requires_second_payment: bool | None = None
    includes_full_gift: bool | None = None
    deadline_at: datetime | None = None
    rules: str | None = None
    contact_platform: ContactPlatform | None = None
    contact_value: str | None = None

    @field_validator("payment_method_note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("rules", "contact_value")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed


class AddGroupBuyProductRequest(BaseModel):
    product_id: uuid.UUID
    unit_price: Money = Field(ge=0)
    max_quantity: int = Field(gt=0)
    character_quantities: list[GroupBuyProductCharacterInput] = []


class UpdateGroupBuyProductRequest(BaseModel):
    unit_price: Money | None = Field(default=None, ge=0)
    max_quantity: int | None = Field(default=None, gt=0)
    character_quantities: list[GroupBuyProductCharacterInput] | None = None


class GroupBuyOwnerActivityRef(BaseModel):
    id: uuid.UUID
    name: str
    status: ActivityStatus


class GroupBuyOwnerActivityCard(BaseModel):
    """圖 20／21 列表用的活動資訊，比 GroupBuyOwnerActivityRef 多帶圖片。

    參考圖另有「活動期間」，但 activity 沒有起訖日期欄位，依使用者 2026-07-29
    裁決不做這一行（同圖 07 出貨單號、圖 20 較昨日增減的處理方式）。
    """

    id: uuid.UUID
    name: str
    image_url: str
    status: ActivityStatus


class GroupBuyOwnerProductRef(BaseModel):
    id: uuid.UUID
    name: str
    primary_image_url: str


class GroupBuyOwnerCharacterStock(BaseModel):
    character_id: uuid.UUID
    name: str
    max_quantity: int
    occupied_quantity: int
    available_quantity: int


class GroupBuyOwnerProductItem(BaseModel):
    id: uuid.UUID
    product: GroupBuyOwnerProductRef
    unit_price: Money
    max_quantity: int
    occupied_quantity: int
    available_quantity: int
    # 多角色商品的每角色庫存明細；無角色商品為空陣列。
    character_stock: list[GroupBuyOwnerCharacterStock] = []


class GroupBuyOwnerListItem(BaseModel):
    """圖 20／21 的開團列表項目。

    round_number 是「第 N 團」，由後端在同團主同活動範圍內依建立時間算出
    （資料庫沒有開團名稱欄位，使用者裁決不新增）。
    order_count／ordered_quantity 排除已取消與已拒絕；has_orders 則是
    Business Rules §16.1 的欄位凍結判斷，含所有紀錄，兩者基準刻意不同。
    pending_order_count 為「待處理」＝待確認＋待付款，與儀表板統計卡同一定義。
    """

    id: uuid.UUID
    activity: GroupBuyOwnerActivityCard
    round_number: int
    status: GroupBuyStatus
    payment_method: PaymentMethod
    deadline_at: UTCDateTime
    is_upcoming_deadline: bool
    order_count: int
    ordered_quantity: int
    pending_order_count: int
    has_orders: bool
    created_at: UTCDateTime


class GroupBuyOwnerListSummary(BaseModel):
    """圖 21 上方三張統計卡。與分頁結果同一次回應送出。"""

    total: int
    open: int
    closed: int


class ProductOrderMemberItem(BaseModel):
    """圖 22 商品明細表的一列（成員／數量／訂單狀態／提交時間）。

    同一會員在同一商品可有多筆（不同訂單、或同訂單不同角色），因此不做合併。
    """

    order_id: uuid.UUID
    order_number: str
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None
    chosen_character_name: str | None
    quantity: int
    order_status: OrderStatus
    submitted_at: UTCDateTime


class ProductOrderGroup(BaseModel):
    group_buy_product_id: uuid.UUID
    product: GroupBuyOwnerProductRef
    unit_price: Money
    max_quantity: int
    total_quantity: int
    # 訂購成員數以不重複會員計算；同一人訂多筆只算一人。
    member_count: int
    items: list[ProductOrderMemberItem]


class GroupBuyProductOrdersResponse(BaseModel):
    """圖 22 商品訂購總覽：一次回傳頁首統計與每個商品的訂購明細。

    未被訂購的商品也會出現（total_quantity 為 0、items 為空），
    讓團主看得出「這個商品還沒有人訂」而不是以為漏資料。
    """

    group_buy_id: uuid.UUID
    activity: GroupBuyOwnerActivityCard
    round_number: int
    status: GroupBuyStatus
    deadline_at: UTCDateTime
    total_order_count: int
    total_ordered_quantity: int
    products: list[ProductOrderGroup]


class GroupBuyOwnerDetailResponse(BaseModel):
    id: uuid.UUID
    activity: GroupBuyOwnerActivityRef
    # 第 N 團。圖 23 的「開團名稱」以「活動名稱 - 第 N 團」組成，麵包屑也需要。
    round_number: int
    payment_method: PaymentMethod
    payment_method_note: str | None
    requires_second_payment: bool
    includes_full_gift: bool
    deadline_at: UTCDateTime
    rules: str
    contact_platform: ContactPlatform
    contact_value: str
    status: GroupBuyStatus
    closed_at: UTCDateTime | None
    products: list[GroupBuyOwnerProductItem]
    has_orders: bool
    editable_fields: list[str]
    created_at: UTCDateTime
    updated_at: UTCDateTime
