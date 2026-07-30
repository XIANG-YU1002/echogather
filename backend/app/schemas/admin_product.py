import uuid

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import Currency
from app.schemas.common import Money, UTCDateTime


class CharacterSelection(BaseModel):
    id: uuid.UUID | None = None
    new_name: str | None = None

    @field_validator("new_name")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    @model_validator(mode="after")
    def _validate_exactly_one(self) -> "CharacterSelection":
        if bool(self.id) == bool(self.new_name):
            raise ValueError("每筆角色選擇必須只提供 id 或 new_name 其中一項。")
        return self


class CreateProductRequest(BaseModel):
    activity_id: uuid.UUID
    name: str
    official_price: Money | None = Field(default=None, ge=0)
    official_currency: Currency | None = None
    primary_image_url: str
    characters: list[CharacterSelection] = []

    @field_validator("name", "primary_image_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed


class UpdateProductRequest(BaseModel):
    name: str | None = None
    official_price: Money | None = Field(default=None, ge=0)
    official_currency: Currency | None = None
    primary_image_url: str | None = None
    characters: list[CharacterSelection] | None = None

    @field_validator("name", "primary_image_url")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed


class ProductAdminActivityRef(BaseModel):
    id: uuid.UUID
    name: str


class ProductAdminCharacterItem(BaseModel):
    id: uuid.UUID
    name: str


class ProductAdminImageItem(BaseModel):
    id: uuid.UUID
    image_url: str
    sort_order: int


class ProductAdminListItem(BaseModel):
    id: uuid.UUID
    name: str
    primary_image_url: str
    is_active: bool
    activity: ProductAdminActivityRef
    official_price: Money | None
    official_currency: Currency | None
    characters: list[ProductAdminCharacterItem]
    created_at: UTCDateTime


class ProductAdminDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    official_price: Money | None
    official_currency: Currency | None
    # 同活動「其他」商品已在使用的幣別（排除自己）。同一活動幣別必須一致，
    # 前端據此把幣別欄位設為唯讀，而不是讓管理員改到送出才被擋。
    # 排除自己是關鍵：活動內唯一的標價商品若不排除，會被自己的舊值鎖死。
    activity_currency: Currency | None = None
    primary_image_url: str
    is_active: bool
    activity: ProductAdminActivityRef
    images: list[ProductAdminImageItem]
    characters: list[ProductAdminCharacterItem]
    group_buy_count: int
    favorite_count: int
    created_at: UTCDateTime
    updated_at: UTCDateTime


class AddProductImageRequest(BaseModel):
    image_url: str

    @field_validator("image_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("圖片網址不可為空白。")
        return trimmed


class UpdateProductImageRequest(BaseModel):
    image_url: str

    @field_validator("image_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("圖片網址不可為空白。")
        return trimmed


class ReorderProductImagesRequest(BaseModel):
    ordered_image_ids: list[uuid.UUID]
