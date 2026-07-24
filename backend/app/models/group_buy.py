import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ContactPlatform, GroupBuyStatus, PaymentMethod

payment_method_enum = Enum(
    PaymentMethod,
    name="payment_method",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
contact_platform_enum = Enum(
    ContactPlatform,
    name="contact_platform",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
group_buy_status_enum = Enum(
    GroupBuyStatus,
    name="group_buy_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class GroupBuy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存團主針對單一活動建立的一次開團。"""

    __tablename__ = "group_buy"

    group_leader_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_leader_profile.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity.id", ondelete="RESTRICT"), nullable=False
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(payment_method_enum, nullable=False)
    payment_method_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_second_payment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    includes_full_gift: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    deadline_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    rules: Mapped[str] = mapped_column(Text, nullable=False)
    contact_platform: Mapped[ContactPlatform] = mapped_column(
        contact_platform_enum, nullable=False
    )
    contact_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GroupBuyStatus] = mapped_column(
        group_buy_status_enum, nullable=False, server_default=text(f"'{GroupBuyStatus.OPEN.value}'")
    )
    closed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("deadline_at > created_at", name="ck_group_buy_deadline_after_created"),
        CheckConstraint("length(trim(rules)) > 0", name="ck_group_buy_rules_not_blank"),
        CheckConstraint(
            "length(trim(contact_value)) > 0", name="ck_group_buy_contact_value_not_blank"
        ),
        CheckConstraint(
            """
            (
                payment_method = 'other'
                AND payment_method_note IS NOT NULL
                AND length(trim(payment_method_note)) > 0
            )
            OR
            (
                payment_method <> 'other'
                AND payment_method_note IS NULL
            )
            """,
            name="ck_group_buy_payment_method_note_pair",
        ),
        CheckConstraint(
            """
            (status = 'open' AND closed_at IS NULL)
            OR
            (status = 'closed' AND closed_at IS NOT NULL)
            """,
            name="ck_group_buy_status_closed_at_pair",
        ),
    )


class GroupBuyProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """儲存開團中的商品、售價及接單數量上限。"""

    __tablename__ = "group_buy_product"

    group_buy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_buy.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id", ondelete="RESTRICT"), nullable=False
    )
    unit_price: Mapped[object] = mapped_column(Numeric(12, 2), nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("group_buy_id", "product_id", name="uq_group_buy_product_group_buy_product"),
        CheckConstraint("unit_price >= 0", name="ck_group_buy_product_unit_price_non_negative"),
        CheckConstraint("max_quantity > 0", name="ck_group_buy_product_max_quantity_positive"),
    )


class GroupBuyProductCharacter(Base):
    """開團商品的「每角色接單上限」。

    僅「有關聯角色」的商品才會建立此列（每個角色一列）；無角色商品不建立，
    庫存沿用 `group_buy_product.max_quantity`。單價不分角色（共用 unit_price）。
    """

    __tablename__ = "group_buy_product_character"

    group_buy_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_buy_product.id", ondelete="CASCADE"),
        primary_key=True,
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("character.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("max_quantity > 0", name="ck_gbpc_max_quantity_positive"),
    )
