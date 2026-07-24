"""per-character stock and chosen character on follow list / order items

Revision ID: 0003_per_character_stock
Revises: 0002_add_currency_values
Create Date: 2026-07-24

依使用者決議新增「款式／角色」可選變體功能：
- 角色變體共用單價、但庫存分角色（新增 group_buy_product_character 表）。
- follow_list_item / order_item 記錄所選角色，唯一鍵一併納入角色。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003_per_character_stock"
down_revision: Union[str, None] = "0002_add_currency_values"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 每角色接單上限表（僅多角色商品建立資料列）
    op.create_table(
        "group_buy_product_character",
        sa.Column("group_buy_product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", UUID(as_uuid=True), nullable=False),
        sa.Column("max_quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_buy_product_id"], ["group_buy_product.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["character_id"], ["character.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("group_buy_product_id", "character_id"),
        sa.CheckConstraint("max_quantity > 0", name="ck_gbpc_max_quantity_positive"),
    )

    # 2. follow_list_item 新增所選角色，唯一鍵改為（清單, 商品, 角色）
    op.add_column(
        "follow_list_item",
        sa.Column("chosen_character_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_follow_list_item_chosen_character",
        "follow_list_item",
        "character",
        ["chosen_character_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "uq_follow_list_item_list_product", "follow_list_item", type_="unique"
    )
    op.create_unique_constraint(
        "uq_follow_list_item_list_product_character",
        "follow_list_item",
        ["follow_list_id", "group_buy_product_id", "chosen_character_id"],
    )

    # 3. order_item 新增所選角色 id 與名稱快照，唯一鍵改為（訂單, 商品, 角色）
    op.add_column(
        "order_item",
        sa.Column("chosen_character_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "order_item",
        sa.Column("chosen_character_name_snapshot", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_item_chosen_character",
        "order_item",
        "character",
        ["chosen_character_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_order_item_order_product", "order_item", type_="unique")
    op.create_unique_constraint(
        "uq_order_item_order_product_character",
        "order_item",
        ["order_id", "group_buy_product_id", "chosen_character_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_order_item_order_product_character", "order_item", type_="unique"
    )
    op.create_unique_constraint(
        "uq_order_item_order_product", "order_item", ["order_id", "group_buy_product_id"]
    )
    op.drop_constraint("fk_order_item_chosen_character", "order_item", type_="foreignkey")
    op.drop_column("order_item", "chosen_character_name_snapshot")
    op.drop_column("order_item", "chosen_character_id")

    op.drop_constraint(
        "uq_follow_list_item_list_product_character", "follow_list_item", type_="unique"
    )
    op.create_unique_constraint(
        "uq_follow_list_item_list_product",
        "follow_list_item",
        ["follow_list_id", "group_buy_product_id"],
    )
    op.drop_constraint(
        "fk_follow_list_item_chosen_character", "follow_list_item", type_="foreignkey"
    )
    op.drop_column("follow_list_item", "chosen_character_id")

    op.drop_table("group_buy_product_character")
