from sqlalchemy import func, select

from app.models.enums import UserRole
from app.models.user import AppUser
from tests.factories import create_user
from tests.utils import auth_headers, login, register_and_login


def _admin_headers(client, db_session):
    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


def test_create_platform_announcement_notifies_all_members(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    _, member_token = register_and_login(client)
    member_headers = auth_headers(member_token)

    response = client.post(
        "/api/v1/admin/announcements",
        json={"title": "平台維護通知", "content": "平台將於週日進行維護。"},
        headers=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    # 平台公告發給所有已註冊使用者。測試資料庫與示範資料共用，
    # 因此對照實際使用者數而非寫死數字。
    total_users = db_session.execute(select(func.count()).select_from(AppUser)).scalar_one()
    assert data["recipient_count"] == total_users

    member_notifications = client.get("/api/v1/notifications", headers=member_headers).json()[
        "data"
    ]
    assert len(member_notifications) == 1
    assert member_notifications[0]["notification_type"] == "system"
    assert member_notifications[0]["target_url"] is None


def test_get_and_update_platform_announcement(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    announcement_id = client.post(
        "/api/v1/admin/announcements",
        json={"title": "原標題", "content": "原內容"},
        headers=admin_headers,
    ).json()["data"]["id"]

    detail_response = client.get(
        f"/api/v1/admin/announcements/{announcement_id}", headers=admin_headers
    )
    assert detail_response.status_code == 200

    update_response = client.patch(
        f"/api/v1/admin/announcements/{announcement_id}",
        json={"title": "新標題"},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "新標題"


def test_delete_platform_announcement(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    announcement_id = client.post(
        "/api/v1/admin/announcements",
        json={"title": "標題", "content": "內容"},
        headers=admin_headers,
    ).json()["data"]["id"]

    delete_response = client.delete(
        f"/api/v1/admin/announcements/{announcement_id}", headers=admin_headers
    )
    assert delete_response.status_code == 204

    detail_response = client.get(
        f"/api/v1/admin/announcements/{announcement_id}", headers=admin_headers
    )
    assert detail_response.status_code == 404


def test_non_admin_cannot_create_platform_announcement(client):
    _, token = register_and_login(client)
    response = client.post(
        "/api/v1/admin/announcements",
        json={"title": "標題", "content": "內容"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403
