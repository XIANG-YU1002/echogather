import enum
import uuid

from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class GroupLeaderSort(str, enum.Enum):
    """公開團主列表排序方式（依圖 12 的排序下拉）。"""

    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    GROUP_BUY_DESC = "group_buy_desc"
    COMPLETED_ORDER_DESC = "completed_order_desc"


class GroupLeaderSummary(BaseModel):
    id: uuid.UUID
    display_name: str


class PublicContacts(BaseModel):
    facebook: str | None
    discord: str | None
    line: str | None


class GroupLeaderStatistics(BaseModel):
    group_buy_count: int
    completed_order_count: int


class PublicGroupLeaderProfileResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    avatar_url: str | None
    introduction: str | None
    public_contacts: PublicContacts
    created_at: UTCDateTime
    statistics: GroupLeaderStatistics
    default_rules: str | None
