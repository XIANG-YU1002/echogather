"""Stage 1 結構測試：驗證 SQLAlchemy Model 定義是否符合 Database Design v2.1。

這些測試只讀取 `Base.metadata`（純 Python 物件），不需要連線到真正的 PostgreSQL，
因此可以在尚未設定資料庫的環境下執行。
"""

from app.models import Base

EXPECTED_TABLES = {
    "app_user",
    "group_leader_application",
    "group_leader_profile",
    "activity",
    "product",
    "product_image",
    "character",
    "product_character",
    "group_buy",
    "group_buy_product",
    # migration 0003_per_character_stock 新增：分角色庫存
    "group_buy_product_character",
    "follow_list",
    "follow_list_item",
    "group_order",
    "order_item",
    # migration 0005_order_status_history 新增：訂單狀態異動歷史
    "order_status_history",
    # migration 0006_order_number_serial 新增：訂單編號每日流水計數器
    "order_number_counter",
    "cancellation_request",
    "product_favorite",
    "announcement",
    "notification",
}


def test_all_tables_registered():
    """規格 18 張表，加上 0003 的 group_buy_product_character、0005 的
    order_status_history 與 0006 的 order_number_counter，共 21 張。"""
    assert set(Base.metadata.tables.keys()) == EXPECTED_TABLES
    assert len(EXPECTED_TABLES) == 21


def test_app_user_contact_columns_nullable_and_required_by_check_constraint():
    table = Base.metadata.tables["app_user"]
    for column_name in ("facebook_contact", "discord_contact", "line_contact"):
        assert table.columns[column_name].nullable is True

    check_names = {
        constraint.name
        for constraint in table.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_app_user_contact_required" in check_names


def test_product_official_price_and_currency_extension_columns_exist():
    table = Base.metadata.tables["product"]
    assert "official_price" in table.columns
    assert "official_currency" in table.columns
    assert table.columns["official_price"].nullable is True
    assert table.columns["official_currency"].nullable is True


def test_group_order_has_required_snapshot_columns():
    table = Base.metadata.tables["group_order"]
    snapshot_columns = {
        "group_leader_name_snapshot",
        "activity_name_snapshot",
        "payment_method_snapshot",
        "rules_snapshot",
        "leader_contact_platform_snapshot",
        "leader_contact_value_snapshot",
        "member_facebook_contact_snapshot",
        "member_discord_contact_snapshot",
        "member_line_contact_snapshot",
    }
    assert snapshot_columns.issubset(set(table.columns.keys()))


def test_unique_constraints_exist_for_pending_style_business_rules():
    order_item_table = Base.metadata.tables["order_item"]
    unique_names = {
        constraint.name
        for constraint in order_item_table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    # migration 0003_per_character_stock 起，唯一鍵納入所選角色
    assert "uq_order_item_order_product_character" in unique_names

    favorite_table = Base.metadata.tables["product_favorite"]
    unique_names = {
        constraint.name
        for constraint in favorite_table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert "uq_product_favorite_user_product" in unique_names
