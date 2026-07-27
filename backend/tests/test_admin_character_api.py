import uuid

from app.models.enums import UserRole
from tests.factories import create_character, create_product, create_user, link_product_character
from tests.utils import auth_headers, login

# 測試跑在與示範資料共用的 Supabase 上，角色名有不分大小寫的唯一鍵
# （uq_character_name_lower），因此一律使用隨機名稱避免與既有資料撞名。


def _unique_name(prefix: str = "測試角色") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client, db_session):
    admin = create_user(db_session, role=UserRole.ADMIN)
    return auth_headers(login(client, admin.email, "Passw0rd1"))


def test_create_character(client, db_session):
    headers = _admin_headers(client, db_session)
    name = _unique_name()

    response = client.post("/api/v1/admin/characters", json={"name": name}, headers=headers)

    assert response.status_code == 201
    assert response.json()["data"]["name"] == name
    assert response.json()["data"]["related_product_count"] == 0


def test_create_character_duplicate_case_insensitive(client, db_session):
    """唯一鍵為 lower(name)，故以大小寫不同的同名驗證去重（中文無大小寫，改用英文名）。"""
    headers = _admin_headers(client, db_session)
    suffix = uuid.uuid4().hex[:8]
    create_character(db_session, name=f"Jinhsi{suffix}")

    response = client.post(
        "/api/v1/admin/characters", json={"name": f"JINHSI{suffix.upper()}"}, headers=headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CHARACTER_NAME_ALREADY_EXISTS"


def test_get_suggestions(client, db_session):
    headers = _admin_headers(client, db_session)
    # 以隨機片段查詢，確保只會命中本測試建立的角色
    name = _unique_name()
    character = create_character(db_session, name=name)
    product = create_product(db_session)
    link_product_character(db_session, product, character)

    response = client.get(
        "/api/v1/admin/characters/suggestions", params={"q": name}, headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == name
    assert data[0]["related_product_count"] == 1


def test_update_character_name(client, db_session):
    headers = _admin_headers(client, db_session)
    character = create_character(db_session, name="舊名字")

    response = client.patch(
        f"/api/v1/admin/characters/{character.id}", json={"name": "新名字"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "新名字"


def test_delete_character_without_products(client, db_session):
    headers = _admin_headers(client, db_session)
    character = create_character(db_session)

    response = client.delete(f"/api/v1/admin/characters/{character.id}", headers=headers)
    assert response.status_code == 204


def test_delete_character_with_products_blocked(client, db_session):
    headers = _admin_headers(client, db_session)
    character = create_character(db_session)
    product = create_product(db_session)
    link_product_character(db_session, product, character)

    response = client.delete(f"/api/v1/admin/characters/{character.id}", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CHARACTER_HAS_PRODUCT_RELATIONS"
