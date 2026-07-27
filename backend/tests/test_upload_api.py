import io
import re

import pytest
from PIL import Image

from app.core import supabase_storage
from app.core.config import settings
from app.models.enums import UserRole
from tests.factories import create_user
from tests.utils import auth_headers, login, register_and_login


@pytest.fixture(autouse=True)
def uploaded_objects(monkeypatch):
    """圖片改存 Supabase Storage 後，測試不真的呼叫外部 Storage：
    以與正式相同的公開網址格式回傳，並記錄 (object_path, 位元組數) 供斷言。"""
    recorded: list[tuple[str, int]] = []

    def _fake_upload_bytes(object_path: str, data: bytes, content_type: str = "image/webp") -> str:
        recorded.append((object_path, len(data)))
        return f"{_public_url_base()}/{object_path}"

    monkeypatch.setattr(supabase_storage, "upload_bytes", _fake_upload_bytes)
    return recorded


def _public_url_base() -> str:
    base = (settings.supabase_url or "https://test.supabase.co").rstrip("/")
    return f"{base}/storage/v1/object/public/{settings.supabase_storage_bucket}"


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_requires_authentication(client):
    files = {"file": ("avatar.png", _png_bytes(), "image/png")}
    response = client.post("/api/v1/uploads/images", files=files, data={"category": "avatar"})
    assert response.status_code == 401


def test_upload_avatar_success(client, uploaded_objects):
    _, token = register_and_login(client)
    files = {"file": ("avatar.png", _png_bytes(), "image/png")}

    response = client.post(
        "/api/v1/uploads/images",
        files=files,
        data={"category": "avatar"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["category"] == "avatar"
    assert data["content_type"] == "image/webp"
    assert data["url"] == f"{_public_url_base()}/{uploaded_objects[0][0]}"
    assert data["size"] > 0

    # 存放路徑格式：<分類>/<西元年>/<月>/<uuid>.webp
    object_path, size = uploaded_objects[0]
    assert re.fullmatch(r"avatar/\d{4}/\d{2}/[0-9a-f]{32}\.webp", object_path)
    assert size == data["size"]


def test_upload_activity_requires_admin(client):
    _, token = register_and_login(client)
    files = {"file": ("activity.png", _png_bytes(), "image/png")}

    response = client.post(
        "/api/v1/uploads/images",
        files=files,
        data={"category": "activity"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "UPLOAD_PERMISSION_DENIED"


def test_upload_activity_success_for_admin(client, db_session, uploaded_objects):
    admin = create_user(db_session, role=UserRole.ADMIN)
    token = login(client, admin.email, "Passw0rd1")
    files = {"file": ("activity.png", _png_bytes(), "image/png")}

    response = client.post(
        "/api/v1/uploads/images",
        files=files,
        data={"category": "activity"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["data"]["url"].startswith(f"{_public_url_base()}/activity/")
    assert re.fullmatch(r"activity/\d{4}/\d{2}/[0-9a-f]{32}\.webp", uploaded_objects[0][0])


def test_upload_invalid_category(client):
    _, token = register_and_login(client)
    files = {"file": ("banner.png", _png_bytes(), "image/png")}

    response = client.post(
        "/api/v1/uploads/images",
        files=files,
        data={"category": "banner"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UPLOAD_CATEGORY_INVALID"


def test_upload_unsupported_content_type(client):
    _, token = register_and_login(client)
    files = {"file": ("notes.txt", b"just some text", "text/plain")}

    response = client.post(
        "/api/v1/uploads/images",
        files=files,
        data={"category": "avatar"},
        headers=auth_headers(token),
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UPLOAD_FILE_TYPE_NOT_SUPPORTED"


def test_upload_corrupt_image_rejected(client):
    _, token = register_and_login(client)
    files = {"file": ("avatar.png", b"not-really-a-png-file", "image/png")}

    response = client.post(
        "/api/v1/uploads/images",
        files=files,
        data={"category": "avatar"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UPLOAD_FILE_INVALID"
