import uuid

from pydantic import BaseModel, field_validator, model_validator

from app.models.enums import ActivityStatus, Currency
from app.schemas.common import UTCDateTime, normalize_optional_text


class CreateActivityRequest(BaseModel):
    name: str
    description: str | None = None
    image_url: str
    has_full_gift: bool = False

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("name", "image_url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed


class UpdateActivityRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    has_full_gift: bool | None = None

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("name", "image_url")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed

    @model_validator(mode="after")
    def _validate_at_least_one_field(self) -> "UpdateActivityRequest":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一個欄位。")
        return self


class ActivityAdminListItem(BaseModel):
    id: uuid.UUID
    name: str
    image_url: str
    status: ActivityStatus
    has_full_gift: bool
    product_count: int
    created_at: UTCDateTime


class ActivityAdminDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    image_url: str
    status: ActivityStatus
    has_full_gift: bool
    product_count: int
    group_buy_count: int
    # 此活動的商品已在使用的官方價幣別；還沒有任何標價商品時為 None。
    # 同一活動的幣別必須一致（使用者 2026-07-30 規則），前端據此把幣別鎖定，
    # 不必等送出被後端擋下來才知道。
    product_currency: Currency | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime
