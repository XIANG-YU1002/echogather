from datetime import datetime, timedelta, timezone

from app.models.enums import UserRole
from tests.factories import (
    create_activity,
    create_group_buy,
    create_group_buy_product,
    create_group_leader_profile,
    create_product,
    create_user,
)
from tests.utils import auth_headers, login, register_and_login


def _admin_headers(client, db_session):
    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


def test_dashboard_counts(client, db_session):
    """儀表板各卡片統計全資料庫，測試又與示範資料共用資料庫，
    因此比對「新增資料前後的增量」而非絕對數字 —— 也順便驗證每張卡確實只對
    應到該類型的資料。"""
    admin_headers = _admin_headers(client, db_session)

    def read_cards():
        response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert response.status_code == 200
        return {c["key"]: c["count"] for c in response.json()["data"]["cards"]}

    before = read_cards()

    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    create_group_buy_product(db_session, group_buy, product)

    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    client.post("/api/v1/group-leader-applications", headers=member_headers)

    after = read_cards()
    for key in (
        "pending_group_leader_applications",
        "open_activities",
        "active_products",
        "current_group_buys",
    ):
        assert after[key] == before[key] + 1, key


def test_current_group_buys_list(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)
    product = create_product(db_session, activity=activity)
    leader_profile = create_group_leader_profile(db_session)
    # 同一團主對同一活動只能有一個進行中的開團，因此第二團改用另一個活動。
    other_activity = create_activity(db_session)
    create_group_buy(db_session, group_leader_profile=leader_profile, activity=other_activity)
    group_buy = create_group_buy(db_session, group_leader_profile=leader_profile, activity=activity)
    create_group_buy_product(db_session, group_buy, product)

    response = client.get("/api/v1/admin/dashboard/current-group-buys", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1


def test_dashboard_requires_admin(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.get("/api/v1/admin/dashboard", headers=auth_headers(token))
    assert response.status_code == 403
