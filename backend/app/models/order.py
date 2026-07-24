import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CancellationStatus, OrderStatus
from app.models.group_buy import contact_platform_enum, payment_method_enum

order_status_enum = Enum(
    OrderStatus,
    name="order_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
cancellation_status_enum = Enum(
    CancellationStatus,
    name="cancellation_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class GroupOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存會員正式送出的跟團訂單及必要歷史快照。`created_at` 亦作為先喊排隊依據。"""

    __tablename__ = "group_order"

    order_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    group_buy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_buy.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        order_status_enum,
        nullable=False,
        server_default=text(f"'{OrderStatus.PENDING_CONFIRMATION.value}'"),
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_total_amount: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    group_leader_name_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    payment_method_snapshot: Mapped[str] = mapped_column(payment_method_enum, nullable=False)
    payment_method_note_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_second_payment_snapshot: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    includes_full_gift_snapshot: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    rules_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    leader_contact_platform_snapshot: Mapped[str] = mapped_column(
        contact_platform_enum, nullable=False
    )
    leader_contact_value_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    member_facebook_contact_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_discord_contact_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_line_contact_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "product_total_amount >= 0", name="ck_group_order_product_total_amount_non_negative"
        ),
        CheckConstraint(
            "length(trim(rules_snapshot)) > 0", name="ck_group_order_rules_snapshot_not_blank"
        ),
        CheckConstraint(
            "length(trim(leader_contact_value_snapshot)) > 0",
            name="ck_group_order_leader_contact_value_snapshot_not_blank",
        ),
        CheckConstraint(
            """
            (
                status = 'rejected'
                AND rejection_reason IS NOT NULL
                AND length(trim(rejection_reason)) > 0
            )
            OR
            (
                status <> 'rejected'
                AND rejection_reason IS NULL
            )
            """,
            name="ck_group_order_rejection_reason_pair",
        ),
        CheckConstraint(
            """
            (
                payment_method_snapshot = 'other'
                AND payment_method_note_snapshot IS NOT NULL
                AND length(trim(payment_method_note_snapshot)) > 0
            )
            OR
            (
                payment_method_snapshot <> 'other'
                AND payment_method_note_snapshot IS NULL
            )
            """,
            name="ck_group_order_payment_method_note_snapshot_pair",
        ),
        CheckConstraint(
            """
            member_facebook_contact_snapshot IS NOT NULL
            OR member_discord_contact_snapshot IS NOT NULL
            OR member_line_contact_snapshot IS NOT NULL
            """,
            name="ck_group_order_member_contact_snapshot_required",
        ),
    )


class OrderItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """儲存訂單商品、單價、數量、小計及商品快照。"""

    __tablename__ = "order_item"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="CASCADE"), nullable=False
    )
    group_buy_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_buy_product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # 所選角色/款式：保留 id 供每角色佔用量計算，名稱另存快照供顯示。無角色商品為 NULL。
    chosen_character_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("character.id", ondelete="RESTRICT"),
        nullable=True,
    )
    chosen_character_name_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    image_url_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    unit_price: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "group_buy_product_id",
            "chosen_character_id",
            name="uq_order_item_order_product_character",
        ),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price_non_negative"),
        CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),
        CheckConstraint("subtotal >= 0", name="ck_order_item_subtotal_non_negative"),
        CheckConstraint("subtotal = unit_price * quantity", name="ck_order_item_subtotal_matches"),
    )


class CancellationRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存會員提出的取消申請及團主處理結果。提出申請不代表訂單立即取消。"""

    __tablename__ = "cancellation_request"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CancellationStatus] = mapped_column(
        cancellation_status_enum,
        nullable=False,
        server_default=text(f"'{CancellationStatus.PENDING.value}'"),
    )
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "reason IS NULL OR length(trim(reason)) > 0", name="ck_cancellation_request_reason_not_blank"
        ),
        CheckConstraint(
            "response_note IS NULL OR length(trim(response_note)) > 0",
            name="ck_cancellation_request_response_note_not_blank",
        ),
        CheckConstraint(
            """
            (status = 'pending' AND response_note IS NULL AND processed_at IS NULL)
            OR
            (status IN ('approved', 'rejected') AND processed_at IS NOT NULL)
            """,
            name="ck_cancellation_request_status_processed_pair",
        ),
    )
