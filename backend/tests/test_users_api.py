from tests.utils import auth_headers, register_and_login


def test_get_my_profile_requires_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_get_my_profile_success(client, db_session):
    user, token = register_and_login(client, db_session)

    response = client.get("/api/v1/users/me", headers=auth_headers(token))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == user["email"]
    assert data["latest_group_leader_application"] is None
    assert data["group_leader_profile"] is None


def test_update_profile_nickname(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.patch(
        "/api/v1/users/me", json={"nickname": "新暱稱"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["data"]["nickname"] == "新暱稱"


def test_update_profile_requires_at_least_one_field(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.patch("/api/v1/users/me", json={}, headers=auth_headers(token))

    assert response.status_code == 422


def test_update_profile_cannot_change_email(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.patch(
        "/api/v1/users/me",
        json={"nickname": "新暱稱", "email": "hacker@example.com"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["email"] != "hacker@example.com"


def test_update_contacts_requires_at_least_one(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.patch(
        "/api/v1/users/me/contacts",
        json={"facebook_contact": None, "discord_contact": None, "line_contact": None},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONTACT_REQUIRED"


def test_update_contacts_success(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.patch(
        "/api/v1/users/me/contacts",
        json={"facebook_contact": None, "discord_contact": "new_discord", "line_contact": None},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["discord_contact"] == "new_discord"
    assert data["facebook_contact"] is None


def test_update_contacts_blank_string_normalized_to_null(client, db_session):
    _, token = register_and_login(client, db_session)

    response = client.patch(
        "/api/v1/users/me/contacts",
        json={"discord_contact": "kept_discord", "line_contact": "   "},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["line_contact"] is None
