from app.models.enums import UserRole
from tests.factories import create_user
from tests.utils import auth_headers, login, register_and_login


def _admin_headers(client, db_session):
    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


def test_get_applications_and_detail(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    created_id = client.post(
        "/api/v1/group-leader-applications",
        json={"reason": "測試申請原因"},
        headers=member_headers,
    ).json()["data"]["id"]

    # 測試跑在與示範資料共用的資料庫上，可能已存在其他待審申請；
    # 只確認本測試建立的那筆出現在列表中，不斷言絕對筆數。
    list_response = client.get(
        "/api/v1/admin/group-leader-applications",
        params={"status": "pending", "page_size": 100},
        headers=admin_headers,
    )
    assert list_response.status_code == 200
    items = list_response.json()["data"]
    matched = [item for item in items if item["id"] == created_id]
    assert len(matched) == 1
    assert matched[0]["reason"] == "測試申請原因"

    detail_response = client.get(
        f"/api/v1/admin/group-leader-applications/{created_id}", headers=admin_headers
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["status"] == "pending"
    assert detail["reason"] == "測試申請原因"


def test_application_reason_is_optional(client, db_session):
    """申請原因選填：不帶欄位與帶空白都應存成 null。"""
    admin_headers = _admin_headers(client, db_session)
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)

    created_id = client.post(
        "/api/v1/group-leader-applications", json={"reason": "   "}, headers=member_headers
    ).json()["data"]["id"]

    detail = client.get(
        f"/api/v1/admin/group-leader-applications/{created_id}", headers=admin_headers
    ).json()["data"]
    assert detail["reason"] is None


def test_approve_application_creates_profile_and_notification(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    application_id = client.post(
        "/api/v1/group-leader-applications", headers=member_headers
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/admin/group-leader-applications/{application_id}/approve", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["application"]["status"] == "approved"
    assert data["group_leader_profile"]["is_profile_complete"] is False

    profile_response = client.get("/api/v1/group-leader/profile", headers=member_headers)
    assert profile_response.status_code == 200

    notifications = client.get("/api/v1/notifications", headers=member_headers).json()["data"]
    assert len(notifications) == 1
    assert notifications[0]["source"]["type"] == "group_leader_application"


def test_approve_application_twice_conflicts(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    application_id = client.post(
        "/api/v1/group-leader-applications", headers=member_headers
    ).json()["data"]["id"]

    client.post(
        f"/api/v1/admin/group-leader-applications/{application_id}/approve", headers=admin_headers
    )
    second_response = client.post(
        f"/api/v1/admin/group-leader-applications/{application_id}/approve", headers=admin_headers
    )
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "APPLICATION_ALREADY_REVIEWED"


def test_reject_application_allows_reapply(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    _, member_token = register_and_login(client, db_session)
    member_headers = auth_headers(member_token)
    application_id = client.post(
        "/api/v1/group-leader-applications", headers=member_headers
    ).json()["data"]["id"]

    reject_response = client.post(
        f"/api/v1/admin/group-leader-applications/{application_id}/reject", headers=admin_headers
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["application"]["status"] == "rejected"

    my_application = client.get(
        "/api/v1/group-leader-applications/me", headers=member_headers
    ).json()["data"]
    assert my_application["can_reapply"] is True

    reapply_response = client.post("/api/v1/group-leader-applications", headers=member_headers)
    assert reapply_response.status_code == 201


def test_non_admin_cannot_review(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.get(
        "/api/v1/admin/group-leader-applications", headers=auth_headers(token)
    )
    assert response.status_code == 403
