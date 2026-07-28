import uuid

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GroupLeaderApplicationStatus

group_leader_application_status_enum = Enum(
    GroupLeaderApplicationStatus,
    name="group_leader_application_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class GroupLeaderApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存會員申請成為團主的狀態及管理員審核結果。

    註：`uq_group_leader_application_pending_user`（同一會員同時最多一筆待審核申請）
    由 Alembic Migration 以原生 partial unique index 建立，詳見 Database Design §9.2。
    """

    __tablename__ = "group_leader_application"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[GroupLeaderApplicationStatus] = mapped_column(
        group_leader_application_status_enum,
        nullable=False,
        server_default=text(f"'{GroupLeaderApplicationStatus.PENDING.value}'"),
    )
    # 申請原因為選填（依使用者需求新增），供管理員審核時參考
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            """
            (
                status = 'pending'
                AND reviewed_by_user_id IS NULL
                AND reviewed_at IS NULL
            )
            OR
            (
                status IN ('approved', 'rejected')
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
            )
            """,
            name="ck_group_leader_application_review_state",
        ),
    )


class GroupLeaderProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存已通過審核會員的團主公開資料。一名使用者最多只有一筆團主資料。

    註：`uq_group_leader_display_name_lower`（LOWER(display_name) 唯一索引，
    display_name IS NOT NULL 時適用）由 Alembic Migration 以原生 SQL 建立，
    詳見 Database Design §9.3。
    """

    __tablename__ = "group_leader_profile"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    introduction: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    discord_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
