"""allow zero max quantity for per-character group buy limits

Revision ID: 0013_allow_zero_max_quantity
Revises: 0012_notification_unmerge_batch
Create Date: 2026-07-30

依使用者需求：接單上限可以填 0，但**只限多角色商品的每角色上限**。

情境是單商品多角色——團主可依需求拒絕接某個角色的單（缺貨、不代購），
把該角色上限設為 0，而不必把整個商品移出開團。

商品層級（group_buy_product.max_quantity）維持 > 0 不放寬：
使用者裁決「無角色或單一角色的商品若是勾選就不能填 0，必須至少接 1
或是請團主取消勾選」——勾選代表要接單，設 0 應該改成不勾選該商品。

多角色商品「每個角色都填 0」等同整個商品不接單，同樣不允許，
但那是跨列的條件，CHECK 約束無法表達，改由 API 層驗證。

可用量計算本來就是 max(上限 - 已占用, 0)，且可用量 <= 0 會被判為額滿，
因此角色上限 0 會自然呈現為該角色不可選，不需要另外處理。
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0013_allow_zero_max_quantity"
down_revision: Union[str, None] = "0012_notification_unmerge_batch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL 無法直接修改 CHECK 條件，只能先移除再以新條件建立
    op.drop_constraint("ck_gbpc_max_quantity_positive", "group_buy_product_character", type_="check")
    op.create_check_constraint(
        "ck_gbpc_max_quantity_non_negative",
        "group_buy_product_character",
        "max_quantity >= 0",
    )


def downgrade() -> None:
    # 還原成只允許正數前，必須先處理既有的 0，否則加回約束會失敗
    op.execute("UPDATE group_buy_product_character SET max_quantity = 1 WHERE max_quantity = 0")

    op.drop_constraint(
        "ck_gbpc_max_quantity_non_negative", "group_buy_product_character", type_="check"
    )
    op.create_check_constraint(
        "ck_gbpc_max_quantity_positive",
        "group_buy_product_character",
        "max_quantity > 0",
    )
