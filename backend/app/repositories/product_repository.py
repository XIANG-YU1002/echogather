import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.favorite import ProductFavorite
from app.models.group_buy import GroupBuyProduct
from app.models.product import Character, Product, ProductCharacter, ProductImage


def get_by_id(db: Session, product_id: uuid.UUID) -> Product | None:
    return db.get(Product, product_id)


def count_active_products(db: Session) -> int:
    stmt = select(func.count()).select_from(Product).where(Product.is_active.is_(True))
    return db.execute(stmt).scalar_one()


def get_images(db: Session, product_id: uuid.UUID) -> list[ProductImage]:
    stmt = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc())
    )
    return db.execute(stmt).scalars().all()


def get_characters_for_products(
    db: Session, product_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[Character]]:
    """一次取回多個商品的角色，避免商品列表逐筆再查一次（Supabase 在 ap-south-1，往返成本高）。

    無角色的商品不會出現在回傳的 dict 中，呼叫端以空清單處理。
    """
    if not product_ids:
        return {}
    stmt = (
        select(ProductCharacter.product_id, Character)
        .join(Character, Character.id == ProductCharacter.character_id)
        .where(ProductCharacter.product_id.in_(product_ids))
        .order_by(Character.name.asc())
    )
    grouped: dict[uuid.UUID, list[Character]] = {}
    for product_id, character in db.execute(stmt).all():
        grouped.setdefault(product_id, []).append(character)
    return grouped


def get_characters(db: Session, product_id: uuid.UUID) -> list[Character]:
    stmt = (
        select(Character)
        .join(ProductCharacter, ProductCharacter.character_id == Character.id)
        .where(ProductCharacter.product_id == product_id)
        .order_by(Character.name.asc())
    )
    return db.execute(stmt).scalars().all()


def is_favorited(db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
    stmt = select(ProductFavorite).where(
        ProductFavorite.user_id == user_id, ProductFavorite.product_id == product_id
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def search_active_products(
    db: Session,
    *,
    q: str | None,
    character_id: uuid.UUID | None,
    page: int,
    page_size: int,
) -> tuple[list[Product], int]:
    """依 Business Rules §14.5：公開搜尋只回傳上架商品。"""
    stmt = select(Product).where(Product.is_active.is_(True))
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    if character_id is not None:
        stmt = stmt.join(ProductCharacter, ProductCharacter.product_id == Product.id).where(
            ProductCharacter.character_id == character_id
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total


def list_products_admin(
    db: Session,
    *,
    activity_id: uuid.UUID | None,
    is_active: bool | None,
    character_id: uuid.UUID | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Product], int]:
    stmt = select(Product)
    if activity_id is not None:
        stmt = stmt.where(Product.activity_id == activity_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active.is_(is_active))
    if keyword:
        stmt = stmt.where(Product.name.ilike(f"%{keyword}%"))
    if character_id is not None:
        stmt = stmt.join(ProductCharacter, ProductCharacter.product_id == Product.id).where(
            ProductCharacter.character_id == character_id
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = (
        db.execute(
            stmt.order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return items, total


def name_exists_in_activity(
    db: Session, activity_id: uuid.UUID, name: str, exclude_product_id: uuid.UUID | None = None
) -> bool:
    stmt = select(Product.id).where(Product.activity_id == activity_id, Product.name == name)
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def get_activity_currency(
    db: Session, activity_id: uuid.UUID, exclude_product_id: uuid.UUID | None = None
) -> str | None:
    """同一活動已在使用的官方價幣別；還沒有任何標價商品時回 None。

    依使用者 2026-07-30 規則：同一活動的商品幣別必須一致，不能有的台幣有的日圓。
    只看有標價的商品——沒填官方價的商品 official_currency 為 NULL，不構成限制。
    """
    stmt = select(Product.official_currency).where(
        Product.activity_id == activity_id,
        Product.official_currency.is_not(None),
    )
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none()


def create_product(db: Session, **fields) -> Product:
    product = Product(**fields)
    db.add(product)
    db.flush()
    return product


def get_favorite_count(db: Session, product_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(ProductFavorite).where(
        ProductFavorite.product_id == product_id
    )
    return db.execute(stmt).scalar_one()


def get_group_buy_count_for_product(db: Session, product_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(GroupBuyProduct).where(
        GroupBuyProduct.product_id == product_id
    )
    return db.execute(stmt).scalar_one()


def link_characters(db: Session, product_id: uuid.UUID, character_ids: list[uuid.UUID]) -> None:
    for character_id in character_ids:
        db.add(ProductCharacter(product_id=product_id, character_id=character_id))


def unlink_all_characters(db: Session, product_id: uuid.UUID) -> None:
    stmt = select(ProductCharacter).where(ProductCharacter.product_id == product_id)
    for link in db.execute(stmt).scalars().all():
        db.delete(link)


def get_image_by_id(db: Session, image_id: uuid.UUID) -> ProductImage | None:
    return db.get(ProductImage, image_id)


def get_max_image_sort_order(db: Session, product_id: uuid.UUID) -> int:
    stmt = select(func.coalesce(func.max(ProductImage.sort_order), -1)).where(
        ProductImage.product_id == product_id
    )
    return db.execute(stmt).scalar_one()


def create_image(db: Session, product_id: uuid.UUID, image_url: str, sort_order: int) -> ProductImage:
    image = ProductImage(product_id=product_id, image_url=image_url, sort_order=sort_order)
    db.add(image)
    db.flush()
    return image


def delete_image(db: Session, image: ProductImage) -> None:
    db.delete(image)


def reorder_images(db: Session, product_id: uuid.UUID, ordered_image_ids: list[uuid.UUID]) -> None:
    """先移到不會衝突的暫用區間再寫入最終順序，避免違反 (product_id, sort_order) 唯一限制。"""
    images_by_id = {image.id: image for image in get_images(db, product_id)}
    temporary_offset = len(images_by_id) + 1000

    for index, image_id in enumerate(ordered_image_ids):
        images_by_id[image_id].sort_order = temporary_offset + index
    db.flush()

    for index, image_id in enumerate(ordered_image_ids):
        images_by_id[image_id].sort_order = index
    db.flush()
