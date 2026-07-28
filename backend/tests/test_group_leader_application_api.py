from tests.utils import auth_headers, register_and_login


def test_get_my_application_none_when_never_applied(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.get("/api/v1/group-leader-applications/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["data"] is None


def test_submit_application_success(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.post("/api/v1/group-leader-applications", headers=auth_headers(token))

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["reviewed_at"] is None


def test_submit_application_twice_conflicts_while_pending(client, db_session):
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    first = client.post("/api/v1/group-leader-applications", headers=headers)
    assert first.status_code == 201

    second = client.post("/api/v1/group-leader-applications", headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "GROUP_LEADER_APPLICATION_PENDING"


def test_get_my_application_after_submit_can_reapply_is_false_while_pending(client, db_session):
    _, token = register_and_login(client, db_session)
    headers = auth_headers(token)

    client.post("/api/v1/group-leader-applications", headers=headers)
    response = client.get("/api/v1/group-leader-applications/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["can_reapply"] is False


def test_submit_application_requires_authentication(client):
    response = client.post("/api/v1/group-leader-applications")
    assert response.status_code == 401
