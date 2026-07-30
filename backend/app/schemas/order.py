import uuid

from pydantic import BaseModel

from app.models.enums import CancellationStatus, ContactPlatform, OrderStatus, PaymentMethod
from app.schemas.common import Money, UTCDateTime


class CreateOrderRequest(BaseModel):
    rules_accepted: bool = False


class CreateOrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    product_total_amount: Money
    created_at: UTCDateTime


class OrderListItem(BaseModel):
    id: uuid.UUID
    order_number: str
    group_leader_name: str
    activity_name: str
    representative_image_url: str
    item_summary: str
    item_count: int
    product_total_amount: Money
    status: OrderStatus
    rejection_reason: str | None = None
    created_at: UTCDateTime


class OrderItemDetail(BaseModel):
    id: uuid.UUID
    product_name_snapshot: str
    image_url_snapshot: str
    chosen_character_name: str | None = None
    unit_price: Money
    quantity: int
    subtotal: Money


class CancellationRequestSummary(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    reason: str | None
    status: CancellationStatus
    response_note: str | None
    processed_at: UTCDateTime | None
    created_at: UTCDateTime


class MergedSourceOrderSummary(BaseModel):
    """被合併掉的來源訂單摘要。

    這些訂單在畫面上等同已刪除（使用者 2026-07-30 裁決），但拆單申請與團主的
    拆單確認都需要說明「哪幾筆被併進來、各有什麼商品」，所以以摘要形式回傳。
    """

    order_number: str
    status_before: OrderStatus
    item_summary: str
    product_total_amount: Money
    created_at: UTCDateTime


class UnmergeRequestSummary(BaseModel):
    """會員提出的拆單（取消合併）申請。"""

    id: uuid.UUID
    order_id: uuid.UUID
    batch_id: uuid.UUID
    reason: str | None
    status: CancellationStatus
    response_note: str | None
    processed_at: UTCDateTime | None
    created_at: UTCDateTime
    # 這次申請要拆回的來源訂單，讓團主核准前看得到會拆出什麼
    source_orders: list[MergedSourceOrderSummary] = []


class OrderStatusHistoryItem(BaseModel):
    """訂單狀態異動紀錄（圖 08 右側「狀態紀錄」）。"""

    status: OrderStatus
    note: str | None = None
    created_at: UTCDateTime


class OrderDetailResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    rejection_reason: str | None
    product_total_amount: Money
    group_leader_id: uuid.UUID
    group_leader_name: str
    activity_name: str
    payment_method: PaymentMethod
    payment_method_note: str | None
    requires_second_payment: bool
    includes_full_gift: bool
    rules: str
    contact_platform: ContactPlatform
    contact_value: str
    # 收單期限取自開團的即時值（訂單未快照，團主延期時會一併更新）
    deadline_at: UTCDateTime
    # 下單當時保存的會員聯絡方式快照
    member_facebook_contact: str | None = None
    member_discord_contact: str | None = None
    member_line_contact: str | None = None
    items: list[OrderItemDetail]
    status_history: list[OrderStatusHistoryItem] = []
    pending_cancellation_request: CancellationRequestSummary | None
    cancellation_requests: list[CancellationRequestSummary]
    # 這張訂單是由多張合併而來、且目前還能拆回時為 true（圖 10 通知按鈕與訂單詳情共用判斷）
    can_request_unmerge: bool = False
    pending_unmerge_request: UnmergeRequestSummary | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class CreateCancellationRequestRequest(BaseModel):
    reason: str | None = None


class CreateUnmergeRequestRequest(BaseModel):
    """會員提出取消合併（拆單）申請。原因選填。"""

    reason: str | None = None
