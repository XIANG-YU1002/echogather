import uuid

from pydantic import BaseModel, Field, field_validator

from app.models.enums import GroupLeaderApplicationStatus
from app.schemas.common import UTCDateTime, normalize_optional_text


class SubmitApplicationRequest(BaseModel):
    """申請原因為選填（依使用者需求新增）。"""

    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    status: GroupLeaderApplicationStatus
    reason: str | None
    reviewed_at: UTCDateTime | None
    created_at: UTCDateTime


class MyApplicationResponse(ApplicationResponse):
    can_reapply: bool
