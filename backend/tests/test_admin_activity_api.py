from app.models.enums import ActivityStatus, UserRole
from tests.factories import create_activity, create_product, create_user
from tests.utils import auth_headers, login, register_and_login


def _admin_headers(client, db_session):
    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


def test_non_admin_cannot_access(client, db_session):
    _, token = register_and_login(client, db_session)
    response = client.get("/api/v1/admin/activities", headers=auth_headers(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_create_and_get_activity(client, db_session):
    headers = _admin_headers(client, db_session)

    create_response = client.post(
        "/api/v1/admin/activities",
        json={
            "name": "3.4 官方周邊",
            "description": "說明",
            "image_url": "/uploads/activity/a.webp",
            "has_full_gift": True,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    data = create_response.json()["data"]
    assert data["status"] == "open"
    assert data["product_count"] == 0

    detail_response = client.get(f"/api/v1/admin/activities/{data['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["name"] == "3.4 官方周邊"


def test_list_activities_filter_by_status_and_keyword(client, db_session):
    headers = _admin_headers(client, db_session)
    create_activity(db_session, name="今汐活動", status=ActivityStatus.OPEN)
    create_activity(db_session, name="長離活動", status=ActivityStatus.ENDED)

    response = client.get(
        "/api/v1/admin/activities", params={"status": "open", "keyword": "今汐"}, headers=headers
    )
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "今汐活動"


def test_update_activity(client, db_session):
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)

    response = client.patch(
        f"/api/v1/admin/activities/{activity.id}",
        json={"name": "新名稱", "has_full_gift": True},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "新名稱"
    assert response.json()["data"]["has_full_gift"] is True


def test_end_and_reopen_activity(client, db_session):
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session, status=ActivityStatus.OPEN)

    end_response = client.post(f"/api/v1/admin/activities/{activity.id}/end", headers=headers)
    assert end_response.status_code == 200
    assert end_response.json()["data"]["status"] == "ended"

    end_again_response = client.post(
        f"/api/v1/admin/activities/{activity.id}/end", headers=headers
    )
    assert end_again_response.status_code == 409
    assert end_again_response.json()["error"]["code"] == "ACTIVITY_ALREADY_ENDED"

    reopen_response = client.post(
        f"/api/v1/admin/activities/{activity.id}/reopen", headers=headers
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["data"]["status"] == "open"

    reopen_again_response = client.post(
        f"/api/v1/admin/activities/{activity.id}/reopen", headers=headers
    )
    assert reopen_again_response.status_code == 409
    assert reopen_again_response.json()["error"]["code"] == "ACTIVITY_ALREADY_OPEN"


def test_activity_detail_counts_products(client, db_session):
    headers = _admin_headers(client, db_session)
    activity = create_activity(db_session)
    create_product(db_session, activity=activity)
    create_product(db_session, activity=activity)

    response = client.get(f"/api/v1/admin/activities/{activity.id}", headers=headers)
    assert response.json()["data"]["product_count"] == 2
