import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ContactPlatform, GroupBuyStatus, OrderStatus, PaymentMethod
from app.schemas.common import Money, UTCDateTime
from app.schemas.order import CancellationRequestSummary, OrderItemDetail


class GroupLeaderOrderListItem(BaseModel):
    """圖 25 訂單管理的列表項目。

    商品摘要三欄（representative_image_url／item_summary／item_count）與會員端
    訂單列表同一套組法；total_quantity 是實際件數總和，對應圖上的「共 N 件商品」。
    """

    id: uuid.UUID
    order_number: str
    member_nickname: str
    member_avatar_url: str | None
    group_buy_id: uuid.UUID
    activity_name: str
    # 第 N 團與開團狀態：圖 25 的「開團」欄要顯示「活動名稱｜第 N 團」加狀態標籤
    round_number: int
    group_buy_status: GroupBuyStatus
    representative_image_url: str
    item_summary: str
    item_count: int
    total_quantity: int
    status: OrderStatus
    product_total_amount: Money
    has_pending_cancellation: bool
    created_at: UTCDateTime


class GroupLeaderOrderSummary(BaseModel):
    """圖 25 上方六張統計卡。

    受開團／活動／關鍵字篩選影響，但**不受狀態篩選影響**——狀態卡本身就是切換
    狀態篩選的入口，跟著變動會讓數字自相矛盾。
    """

    pending_confirmation: int
    pending_payment: int
    paid: int
    shipped: int
    completed: int
    cancelled: int
    rejected: int
    pending_cancellation: int


class MemberContactSnapshot(BaseModel):
    facebook: str | None
    discord: str | None
    line: str | None


class GroupLeaderOrderDetailResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    rejection_reason: str | None
    product_total_amount: Money
    # 合併訂單時已收的金額；一般訂單為 0（付款狀態由 status 表達）
    paid_amount: Money
    member_nickname: str
    member_avatar_url: str | None
    member_contacts: MemberContactSnapshot
    activity_name: str
    group_leader_name: str
    # 收單期限取自開團的即時值（訂單未快照，團主延期時會一併更新），同會員端訂單詳情
    deadline_at: UTCDateTime
    payment_method: PaymentMethod
    payment_method_note: str | None
    requires_second_payment: bool
    includes_full_gift: bool
    rules: str
    contact_platform: ContactPlatform
    contact_value: str
    items: list[OrderItemDetail]
    pending_cancellation_request: CancellationRequestSummary | None
    cancellation_requests: list[CancellationRequestSummary]
    available_actions: list[str]
    created_at: UTCDateTime
    updated_at: UTCDateTime


class MergeOrdersRequest(BaseModel):
    """訂單合併。keep 決定保留哪一張的訂單編號與建立時間。

    建立時間會影響先喊先得的排隊順位（Business Rules §24.1），因此由團主選擇
    而非系統代為決定。
    """

    merge_with_order_ids: list[uuid.UUID] = Field(min_length=1)
    keep: Literal["oldest", "newest"] = "oldest"


class RejectOrderRequest(BaseModel):
    reason: str


class ProcessCancellationRequest(BaseModel):
    response_note: str | None = None
