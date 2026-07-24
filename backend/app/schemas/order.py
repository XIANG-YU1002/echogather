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
    product_total_amount: Money
    status: OrderStatus
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


class OrderDetailResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    rejection_reason: str | None
    product_total_amount: Money
    group_leader_name: str
    activity_name: str
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
    created_at: UTCDateTime
    updated_at: UTCDateTime


class CreateCancellationRequestRequest(BaseModel):
    reason: str | None = None
