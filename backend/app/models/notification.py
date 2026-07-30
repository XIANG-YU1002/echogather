import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationType

notification_type_enum = Enum(
    NotificationType,
    name="notification_type",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """儲存會員通知、已讀狀態及相關資料來源。通知只能對應一個來源。"""

    __tablename__ = "notification"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        notification_type_enum, nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_order.id", ondelete="RESTRICT"), nullable=True
    )
    announcement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("announcement.id", ondelete="CASCADE"), nullable=True
    )
    group_leader_application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_leader_application.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # 這則通知對應哪一次訂單合併（order_merge.batch_id）。有值時圖 10 的通知中心
    # 會在該則通知底下顯示「取消合併訂單」按鈕；不是外鍵，因為批次拆掉後紀錄仍留著。
    unmerge_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    read_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_notification_title_not_blank"),
        CheckConstraint("length(trim(message)) > 0", name="ck_notification_message_not_blank"),
        CheckConstraint(
            "num_nonnulls(order_id, announcement_id, group_leader_application_id) = 1",
            name="ck_notification_single_source",
        ),
        CheckConstraint(
            """
            (is_read = false AND read_at IS NULL)
            OR
            (is_read = true AND read_at IS NOT NULL)
            """,
            name="ck_notification_read_state_pair",
        ),
        CheckConstraint(
            "unmerge_batch_id IS NULL OR order_id IS NOT NULL",
            name="ck_notification_unmerge_batch_requires_order",
        ),
    )
