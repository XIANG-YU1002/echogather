import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FollowList(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存會員尚未正式送出的跟團清單。一名會員同時最多只有一張跟團清單。"""

    __tablename__ = "follow_list"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    group_buy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_buy.id", ondelete="RESTRICT"), nullable=False
    )


class FollowListItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存跟團清單中的商品及預計數量。相同商品再次加入時累加數量，不建立第二筆項目。"""

    __tablename__ = "follow_list_item"

    follow_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("follow_list.id", ondelete="CASCADE"), nullable=False
    )
    group_buy_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_buy_product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # 所選角色/款式：多角色商品必填、單角色自動帶入、無角色商品為 NULL。
    chosen_character_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("character.id", ondelete="RESTRICT"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __table_args__ = (
        UniqueConstraint(
            "follow_list_id",
            "group_buy_product_id",
            "chosen_character_id",
            name="uq_follow_list_item_list_product_character",
        ),
        CheckConstraint("quantity > 0", name="ck_follow_list_item_quantity_positive"),
    )
