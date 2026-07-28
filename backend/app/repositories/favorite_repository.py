import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.favorite import ProductFavorite
from app.models.product import Product
from app.schemas.favorite import FavoriteSort


def get(db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> ProductFavorite | None:
    stmt = select(ProductFavorite).where(
        ProductFavorite.user_id == user_id, ProductFavorite.product_id == product_id
    )
    return db.execute(stmt).scalar_one_or_none()


def add(db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> ProductFavorite:
    favorite = ProductFavorite(user_id=user_id, product_id=product_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def remove(db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
    favorite = get(db, user_id, product_id)
    if favorite is not None:
        db.delete(favorite)
        db.commit()


def _order_by(sort: FavoriteSort) -> list:
    """排序條件；未定價商品（official_price 為 NULL）在價格排序時一律排最後。"""
    if sort is FavoriteSort.CREATED_ASC:
        return [ProductFavorite.created_at.asc()]
    if sort is FavoriteSort.NAME_ASC:
        return [Product.name.asc()]
    if sort is FavoriteSort.PRICE_DESC:
        return [Product.official_price.desc().nullslast(), ProductFavorite.created_at.desc()]
    if sort is FavoriteSort.PRICE_ASC:
        return [Product.official_price.asc().nullslast(), ProductFavorite.created_at.desc()]
    return [ProductFavorite.created_at.desc()]


def list_by_user(
    db: Session,
    user_id: uuid.UUID,
    page: int,
    page_size: int,
    sort: FavoriteSort = FavoriteSort.CREATED_DESC,
) -> tuple[list[tuple[ProductFavorite, Product, Activity]], int]:
    stmt = (
        select(ProductFavorite, Product, Activity)
        .join(Product, Product.id == ProductFavorite.product_id)
        .join(Activity, Activity.id == Product.activity_id)
        .where(ProductFavorite.user_id == user_id)
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        # 加上 id 為次要排序鍵，避免同分項目在跨頁時順序飄移造成重複／遺漏
        stmt.order_by(*_order_by(sort), ProductFavorite.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(row[0], row[1], row[2]) for row in rows], total
