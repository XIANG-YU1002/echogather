import uuid

from pydantic import BaseModel, field_validator, model_validator

from app.models.enums import AnnouncementAudienceScope
from app.schemas.common import UTCDateTime


class CreateAnnouncementRequest(BaseModel):
    audience_scope: AnnouncementAudienceScope
    group_buy_id: uuid.UUID | None = None
    title: str
    content: str
    is_public: bool = False

    @field_validator("title", "content")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed

    @model_validator(mode="after")
    def _validate_scope_group_buy_pair(self) -> "CreateAnnouncementRequest":
        if self.audience_scope == AnnouncementAudienceScope.LEADER_UNFINISHED and self.group_buy_id is not None:
            raise ValueError("團主整體公告不可指定開團。")
        if self.audience_scope == AnnouncementAudienceScope.GROUP_BUY_UNFINISHED and self.group_buy_id is None:
            raise ValueError("特定開團公告必須指定開團。")
        return self


class UpdateAnnouncementRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    is_public: bool | None = None

    @field_validator("title", "content")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("此欄位不可為空白。")
        return trimmed

    @model_validator(mode="after")
    def _validate_at_least_one_field(self) -> "UpdateAnnouncementRequest":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一個欄位。")
        return self


class AnnouncementOwnerResponse(BaseModel):
    id: uuid.UUID
    audience_scope: AnnouncementAudienceScope
    group_buy_id: uuid.UUID | None
    # 圖 27「目標與對象」欄要顯示指定開團是哪一個活動的第幾團。
    # 不靠前端用開團清單對照——那份清單只載入 50 筆，超出或舊開團就查不到名稱。
    group_buy_activity_name: str | None = None
    group_buy_round_number: int | None = None
    title: str
    content: str
    is_public: bool
    recipient_count: int
    published_at: UTCDateTime
    updated_at: UTCDateTime


class RecipientPreviewResponse(BaseModel):
    """圖 27 表單的「通知對象預覽」：發布前先算出會通知誰、幾個人。

    公告建立後才有 recipient_count（通知筆數），發布前只能即時計算，
    因此沿用建立公告時的同一組收件人查詢，確保預覽與實際發送一致。
    """

    audience_scope: AnnouncementAudienceScope
    group_buy_id: uuid.UUID | None = None
    group_buy_activity_name: str | None = None
    recipient_count: int
    # 給畫面直接顯示的對象描述，例如「3.4 官方周邊未完成訂單會員」
    audience_label: str
