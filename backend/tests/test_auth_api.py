import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.verification import EmailVerificationCode
from tests.utils import (
    auth_headers,
    issue_verification_code,
    login,
    register,
    register_payload,
    unique_email,
)


def _register_with_code(client, db_session, **overrides):
    """建立可用的驗證碼後送出註冊請求。"""
    payload = register_payload(**overrides)
    issue_verification_code(db_session, payload["email"], payload["verification_code"])
    return payload, client.post("/api/v1/auth/register", json=payload)


def test_register_success(client, db_session):
    payload, response = _register_with_code(client, db_session)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == payload["email"]
    assert data["nickname"] == payload["nickname"]
    assert data["avatar_url"] is None


def test_register_duplicate_email_returns_conflict(client, db_session):
    payload, first = _register_with_code(client, db_session)
    assert first.status_code == 201

    issue_verification_code(db_session, payload["email"], payload["verification_code"])
    second = client.post("/api/v1/auth/register", json={**payload, "nickname": "另一個暱稱"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_email_is_case_insensitive_unique(client, db_session):
    payload, first = _register_with_code(client, db_session)
    assert first.status_code == 201

    # 驗證碼以正規化後的小寫 Email 建立，大寫請求仍應命中同一組
    upper_email_payload = register_payload(email=payload["email"].upper())
    issue_verification_code(
        db_session, upper_email_payload["email"], upper_email_payload["verification_code"]
    )
    second = client.post("/api/v1/auth/register", json=upper_email_payload)
    assert second.status_code == 409


def test_register_password_confirmation_mismatch(client, db_session):
    _, response = _register_with_code(client, db_session, password_confirmation="Different123")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_requires_at_least_one_contact(client, db_session):
    _, response = _register_with_code(client, db_session, discord_contact=None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_blank_contact_is_normalized_to_none(client, db_session):
    _, response = _register_with_code(
        client, db_session, discord_contact="   ", line_contact="tester_line"
    )

    assert response.status_code == 201


def test_register_requires_verification_code(client, db_session):
    """未帶驗證碼欄位一律 422。"""
    payload = register_payload()
    payload.pop("verification_code")
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_wrong_verification_code(client, db_session):
    payload = register_payload()
    issue_verification_code(db_session, payload["email"], "000000")

    response = client.post("/api/v1/auth/register", json={**payload, "verification_code": "999999"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VERIFICATION_CODE_INVALID"


def test_register_rejects_expired_verification_code(client, db_session):
    payload = register_payload()
    db_session.add(
        EmailVerificationCode(
            email=payload["email"],
            code_hash=hashlib.sha256(b"000000").hexdigest(),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    db_session.flush()

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VERIFICATION_CODE_INVALID"


def test_verification_code_is_single_use(client, db_session):
    """同一組驗證碼註冊成功後不能再用於第二個帳號。"""
    payload, first = _register_with_code(client, db_session)
    assert first.status_code == 201

    second_payload = register_payload(
        email=payload["email"], verification_code=payload["verification_code"]
    )
    # 不重新發碼，直接沿用剛才那組（已被消耗）
    response = client.post("/api/v1/auth/register", json=second_payload)
    assert response.status_code in (400, 409)


def test_send_verification_code_success(client, db_session):
    email = unique_email()

    response = client.post("/api/v1/auth/verification-codes", json={"email": email})

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["email"] == email
    assert data["expires_in_seconds"] > 0

    stored = db_session.execute(
        select(EmailVerificationCode).where(EmailVerificationCode.email == email)
    ).scalar_one()
    # 只存雜湊，不留明碼
    assert len(stored.code_hash) == 64
    assert stored.consumed_at is None


def test_send_verification_code_rejects_registered_email(client, db_session):
    payload, created = _register_with_code(client, db_session)
    assert created.status_code == 201

    response = client.post("/api/v1/auth/verification-codes", json={"email": payload["email"]})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_send_verification_code_rate_limited(client, db_session):
    email = unique_email()

    first = client.post("/api/v1/auth/verification-codes", json={"email": email})
    assert first.status_code == 201

    second = client.post("/api/v1/auth/verification-codes", json={"email": email})
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "VERIFICATION_CODE_TOO_FREQUENT"


def test_send_verification_code_rejects_invalid_email(client, db_session):
    response = client.post("/api/v1/auth/verification-codes", json={"email": "not-an-email"})

    assert response.status_code == 422


def test_login_success(client, db_session):
    user = register(client, db_session)
    response = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 8 * 60 * 60
    assert data["access_token"]


def test_login_invalid_password(client, db_session):
    user = register(client, db_session)
    response = client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": "WrongPass1"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_login_unknown_email_does_not_leak_existence(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "WrongPass1"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_get_current_session_requires_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_MISSING"


def test_get_current_session_rejects_invalid_token(client):
    response = client.get("/api/v1/auth/me", headers=auth_headers("not-a-real-token"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_INVALID"


def test_get_current_session_success(client, db_session):
    user = register(client, db_session)
    token = login(client, user["email"], user["password"])

    response = client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == user["id"]
    assert data["email"] == user["email"]
    assert data["role"] == "member"
    assert data["group_leader"] is None
    assert data["permissions"] == {
        "is_admin": False,
        "has_group_leader_profile": False,
        "can_manage_group_buys": False,
    }
