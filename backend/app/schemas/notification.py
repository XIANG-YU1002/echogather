import uuid

from pydantic import BaseModel

from app.models.enums import NotificationType
from app.schemas.common import UTCDateTime


class NotificationSource(BaseModel):
    type: str
    id: str | None


class NotificationItem(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: UTCDateTime | None
    source: NotificationSource
    target_url: str | None
    # 團主公告的發布者資訊（依圖 10 於列表顯示團主頭像）；系統通知為 None
    actor_name: str | None = None
    actor_avatar_url: str | None = None
    # 「訂單已合併」通知才有值：底下顯示「取消合併訂單」按鈕。
    # can_request_unmerge 在該批次已拆、訂單已出貨或已有待處理申請時為 false，
    # 此時只顯示說明文字而不給按鈕。
    unmerge_batch_id: uuid.UUID | None = None
    can_request_unmerge: bool = False
    created_at: UTCDateTime


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationSummaryResponse(BaseModel):
    """圖 10 右側「通知摘要」：未讀總數與各類型的總筆數。"""

    unread_count: int
    system_count: int
    group_leader_count: int
