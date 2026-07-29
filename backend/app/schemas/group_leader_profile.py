import uuid

from pydantic import BaseModel, field_validator

from app.models.enums import ActivityStatus
from app.schemas.common import (
    FACEBOOK_URL_ERROR,
    UTCDateTime,
    is_facebook_url,
    normalize_optional_text,
)
from app.schemas.group_leader_group_buy import GroupBuyOwnerListItem


class GroupLeaderProfileOwnerResponse(BaseModel):
    id: uuid.UUID
    display_name: str | None
    introduction: str | None
    default_rules: str | None
    facebook_url: str | None
    discord_contact: str | None
    line_contact: str | None
    is_profile_complete: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime


class UpdateGroupLeaderProfileRequest(BaseModel):
    display_name: str | None = None
    introduction: str | None = None
    facebook_url: str | None = None
    discord_contact: str | None = None
    line_contact: str | None = None

    @field_validator("introduction", "facebook_url", "discord_contact", "line_contact", mode="before")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("團主名稱不可為空白。")
        return trimmed

    @field_validator("facebook_url")
    @classmethod
    def _validate_facebook_url(cls, value: str | None) -> str | None:
        """公開聯絡方式的 Facebook 也必須是連結，與會員聯絡欄位同一套規則。"""
        if value is None:
            return None
        if not is_facebook_url(value):
            raise ValueError(FACEBOOK_URL_ERROR)
        return value


class UpdateDefaultRulesRequest(BaseModel):
    default_rules: str | None = None

    @field_validator("default_rules", mode="before")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


class DashboardCard(BaseModel):
    key: str
    label: str
    count: int
    target_url: str


class DashboardActivityGroup(BaseModel):
    """圖 20「目前開團」依活動分組。

    同一活動可有多輪（第一團、追加團…），因此開團是活動底下的一層。
    參考圖另有「活動期間」，但 activity 沒有起訖日期欄位，依使用者
    2026-07-29 裁決不做該行。
    """

    activity_id: uuid.UUID
    activity_name: str
    activity_image_url: str
    activity_status: ActivityStatus
    group_buys: list[GroupBuyOwnerListItem]


class DashboardResponse(BaseModel):
    cards: list[DashboardCard]
    # 只含進行中的開團、不分頁（依使用者裁決）；完整紀錄請看「我的開團」。
    current_group_buys: list[DashboardActivityGroup]
