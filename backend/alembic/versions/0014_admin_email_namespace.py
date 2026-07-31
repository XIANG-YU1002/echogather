"""separate admin and normal-user email namespaces

Revision ID: 0014_admin_email_namespace
Revises: 0013_allow_zero_max_quantity
Create Date: 2026-07-31

（revision id 要短：alembic_version.version_num 是 varchar(32)，太長會在
更新版本號時噴 StringDataRightTruncation。）

使用者 2026-07-31 裁決：管理員與一般用戶是分開的兩套身分，所以管理員用的
Email 必須還能拿去註冊一般用戶，不該回報「此 Email 已被註冊」。

原本 uq_app_user_email_lower 是 LOWER(email) 全域唯一，一個 Email 只能有一個
帳號。改成兩個「部分唯一索引」，把命名空間切開：
  - 一般用戶側（role <> 'admin'）：同一 Email 最多一個帳號
  - 管理員側（role = 'admin'）：同一 Email 最多一個帳號
於是同一個 Email 最多存在「一般用戶 1 個 ＋ 管理員 1 個」，各自唯一，
不會退化成完全沒有唯一性。

帳號的識別本來就是 app_user.id（UUID 主鍵，僅供系統內部使用、不對外顯示），
不依賴 Email，因此這項調整不影響主鍵或任何外鍵關聯。

登入改為以密碼決定登入哪一個帳號（見 auth_service.login）。
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0014_admin_email_namespace"
down_revision: Union[str, None] = "0013_allow_zero_max_quantity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_app_user_email_lower")
    op.execute(
        "CREATE UNIQUE INDEX uq_app_user_email_lower_member "
        "ON app_user (LOWER(email)) WHERE role <> 'admin'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_app_user_email_lower_admin "
        "ON app_user (LOWER(email)) WHERE role = 'admin'"
    )


def downgrade() -> None:
    # 還原成全域唯一之前，必須先確認沒有同 Email 的管理員／一般用戶並存，
    # 否則建立索引會失敗；這裡不自動刪帳號，讓它明確報錯由人工處理。
    op.execute("DROP INDEX IF EXISTS uq_app_user_email_lower_member")
    op.execute("DROP INDEX IF EXISTS uq_app_user_email_lower_admin")
    op.execute("CREATE UNIQUE INDEX uq_app_user_email_lower ON app_user (LOWER(email))")
