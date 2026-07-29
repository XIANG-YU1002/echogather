import uuid

from pydantic import BaseModel

from app.schemas.common import UTCDateTime
from app.schemas.group_leader_profile import DashboardCard

__all__ = ["DashboardCard", "DashboardResponse", "CurrentGroupBuyItem"]


class DashboardResponse(BaseModel):
    """管理員儀表板：只有統計卡。

    原本直接沿用團主端的 DashboardResponse，但團主端依圖 20 加入了「目前開團」
    清單後兩者結構分歧，因此改為各自定義。管理員的「目前開團」是獨立的分頁端點
    GET /admin/dashboard/current-group-buys，不併進這個回應。
    卡片結構兩邊相同，仍共用 DashboardCard。
    """

    cards: list[DashboardCard]


class CurrentGroupBuyItem(BaseModel):
    id: uuid.UUID
    activity_name: str
    group_leader_name: str
    deadline_at: UTCDateTime
    order_count: int
    created_at: UTCDateTime
