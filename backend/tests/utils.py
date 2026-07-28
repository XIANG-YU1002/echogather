import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.verification import EmailVerificationCode


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex}@example.com"


def register_payload(**overrides) -> dict:
    payload = {
        "email": unique_email(),
        "password": "Passw0rd1",
        "password_confirmation": "Passw0rd1",
        "nickname": "測試會員",
        "discord_contact": "tester_discord",
        "verification_code": "000000",
    }
    payload.update(overrides)
    return payload


def issue_verification_code(db: Session, email: str, code: str = "000000") -> None:
    """直接寫入一筆可用的驗證碼，讓測試不必真的走寄信流程。

    註冊已改為必須通過 Email 驗證，但測試環境沒有（也不該有）真實信箱；
    這裡跳過 POST /auth/verification-codes 直接建立紀錄，等同測試專用後門。
    """
    db.add(
        EmailVerificationCode(
            email=email.strip().lower(),
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    db.flush()


def register(client: TestClient, db: Session, **overrides) -> dict:
    payload = register_payload(**overrides)
    issue_verification_code(db, payload["email"], payload["verification_code"])
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return {**response.json()["data"], "email": payload["email"], "password": payload["password"]}


def login(client: TestClient, email: str, password: str = "Passw0rd1") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def register_and_login(client: TestClient, db: Session, **overrides) -> tuple[dict, str]:
    user = register(client, db, **overrides)
    token = login(client, user["email"], user["password"])
    return user, token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
