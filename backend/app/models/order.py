import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
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
    # 合併訂單時已收的金額（見 migration 0010）。一般訂單為 0——付款狀態由 status 表達，
    # 只有把已付款的訂單併進未付款訂單時，才需要把已收與待收分開。
    paid_amount: Mapped[object] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
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
            "paid_amount >= 0 AND paid_amount <= product_total_amount",
            name="ck_group_order_paid_amount_range",
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
        # 付款方式備註為選填快照；有值時不得為空白字串。
        CheckConstraint(
            "payment_method_note_snapshot IS NULL "
            "OR length(trim(payment_method_note_snapshot)) > 0",
            name="ck_group_order_payment_method_note_snapshot_not_blank",
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


class OrderMerge(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """訂單合併紀錄，一張來源訂單一列（同一次合併的多張共用 batch_id）。

    存在的理由是拆單要能「還原成合併前各自的狀態」（使用者 2026-07-30 裁決）：
    來源訂單的明細在合併時是複製而非搬移，所以明細還在，但狀態與金額會被改動，
    因此把來源與目標在合併前的狀態／金額一併快照下來，拆單時照著寫回。
    目標訂單的三個 target_*_before 在同一批次的每一列都相同（刻意冗餘，換取單表可讀）。
    """

    __tablename__ = "order_merge"

    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="CASCADE"), nullable=False
    )
    source_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="CASCADE"), nullable=False
    )
    source_status_before: Mapped[OrderStatus] = mapped_column(order_status_enum, nullable=False)
    source_paid_amount_before: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    target_status_before: Mapped[OrderStatus] = mapped_column(order_status_enum, nullable=False)
    target_product_total_before: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    target_paid_amount_before: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    # 已拆單的批次留著當歷史，靠這個欄位區分是否仍在合併狀態
    unmerged_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("source_order_id", "batch_id", name="uq_order_merge_source_batch"),
        CheckConstraint(
            "target_order_id <> source_order_id", name="ck_order_merge_target_not_source"
        ),
        CheckConstraint(
            "source_paid_amount_before >= 0 AND target_paid_amount_before >= 0 "
            "AND target_product_total_before >= 0",
            name="ck_order_merge_amounts_non_negative",
        ),
        Index("ix_order_merge_target_unmerged", "target_order_id", "unmerged_at"),
        Index("ix_order_merge_batch", "batch_id"),
    )


class OrderUnmergeRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """會員提出的拆單（取消合併）申請，團主可核准或附原因拒絕。

    流程與 CancellationRequest 相同（使用者 2026-07-30 裁決），因此沿用
    CancellationStatus；order_id 指的是合併後保留的那張訂單，batch_id 指定要拆的批次。
    """

    __tablename__ = "order_unmerge_request"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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
            "reason IS NULL OR length(trim(reason)) > 0",
            name="ck_order_unmerge_request_reason_not_blank",
        ),
        CheckConstraint(
            "response_note IS NULL OR length(trim(response_note)) > 0",
            name="ck_order_unmerge_request_response_note_not_blank",
        ),
        CheckConstraint(
            """
            (status = 'pending' AND response_note IS NULL AND processed_at IS NULL)
            OR
            (status IN ('approved', 'rejected') AND processed_at IS NOT NULL)
            """,
            name="ck_order_unmerge_request_status_processed_pair",
        ),
        Index("ix_order_unmerge_request_order_status", "order_id", "status"),
    )


class OrderStatusHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """訂單狀態異動歷史。

    依圖 08 右側「狀態紀錄」需求新增：訂單每次狀態變更（含建立）寫入一筆，
    供訂單詳情頁顯示各狀態的實際發生時間。
    """

    __tablename__ = "order_status_history"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(order_status_enum, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "note IS NULL OR length(trim(note)) > 0",
            name="ck_order_status_history_note_not_blank",
        ),
        Index("ix_order_status_history_order_created", "order_id", "created_at"),
    )


class OrderNumberCounter(Base):
    """訂單編號的每日流水號計數器。

    依使用者決議，訂單編號格式為 WG{YYMMDD}-{6 位流水}，流水號每日重新從 1 開始。
    以 `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` 單一原子語句取號，
    避免併發下單時搶到相同號碼。
    """

    __tablename__ = "order_number_counter"

    date_key: Mapped[str] = mapped_column(String(6), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("last_value > 0", name="ck_order_number_counter_last_value_positive"),
    )
