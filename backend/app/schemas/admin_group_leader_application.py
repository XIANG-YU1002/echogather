import uuid

from pydantic import BaseModel

from app.models.enums import GroupLeaderApplicationStatus
from app.schemas.common import UTCDateTime


class ApplicationUserRef(BaseModel):
    id: uuid.UUID
    email: str
    nickname: str
    avatar_url: str | None = None
    facebook_contact: str | None = None
    discord_contact: str | None = None
    line_contact: str | None = None


class ApplicationAdminListItem(BaseModel):
    id: uuid.UUID
    user: ApplicationUserRef
    status: GroupLeaderApplicationStatus
    reason: str | None
    reviewed_at: UTCDateTime | None
    created_at: UTCDateTime


class ApplicationAdminDetailResponse(BaseModel):
    id: uuid.UUID
    user: ApplicationUserRef
    status: GroupLeaderApplicationStatus
    reason: str | None
    reviewed_by: uuid.UUID | None
    reviewed_at: UTCDateTime | None
    created_at: UTCDateTime


class ReviewedApplicationSummary(BaseModel):
    id: uuid.UUID
    status: GroupLeaderApplicationStatus
    reviewed_at: UTCDateTime | None


class ReviewedGroupLeaderProfileSummary(BaseModel):
    id: uuid.UUID
    display_name: str | None
    is_profile_complete: bool


class ApproveApplicationResponse(BaseModel):
    application: ReviewedApplicationSummary
    group_leader_profile: ReviewedGroupLeaderProfileSummary


class RejectApplicationResponse(BaseModel):
    application: ReviewedApplicationSummary
