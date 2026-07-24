import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import ActivityStatus, ContactPlatform, GroupBuyStatus, PaymentMethod
from app.schemas.common import Money, UTCDateTime, normalize_optional_text


class GroupBuyProductCharacterInput(BaseModel):
    character_id: uuid.UUID
    max_quantity: int = Field(gt=0)


class GroupBuyProductInput(BaseModel):
    product_id: uuid.UUID
    unit_price: Money = Field(ge=0)
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
    def _validate_payment_method_note_pair(self) -> "CreateGroupBuyRequest":
        if self.payment_method == PaymentMethod.OTHER and not self.payment_method_note:
            raise ValueError("選擇其他付款方式時必須填寫說明。")
        if self.payment_method != PaymentMethod.OTHER and self.payment_method_note is not None:
            raise ValueError("非其他付款方式不可填寫付款方式說明。")
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
    id: uuid.UUID
    activity: GroupBuyOwnerActivityRef
    status: GroupBuyStatus
    deadline_at: UTCDateTime
    has_orders: bool
    created_at: UTCDateTime


class GroupBuyOwnerDetailResponse(BaseModel):
    id: uuid.UUID
    activity: GroupBuyOwnerActivityRef
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
