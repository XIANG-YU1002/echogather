import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import favorite_repository, product_repository
from app.schemas.favorite import (
    AddFavoriteResponse,
    FavoriteActivityRef,
    FavoriteItem,
    FavoriteProductSummary,
    FavoriteSort,
)


def list_favorites(
    db: Session,
    user_id: uuid.UUID,
    page: int,
    page_size: int,
    sort: FavoriteSort = FavoriteSort.CREATED_DESC,
) -> tuple[list[FavoriteItem], int]:
    rows, total = favorite_repository.list_by_user(db, user_id, page, page_size, sort)
    items = [
        FavoriteItem(
            favorite_id=favorite.id,
            product=FavoriteProductSummary(
                id=product.id,
                name=product.name,
                primary_image_url=product.primary_image_url,
                is_active=product.is_active,
                official_price=product.official_price,
                official_currency=product.official_currency,
                activity=FavoriteActivityRef.model_validate(activity, from_attributes=True),
            ),
            created_at=favorite.created_at,
        )
        for favorite, product, activity in rows
    ]
    return items, total


def add_favorite(db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> AddFavoriteResponse:
    """依 API Design §16.2：重複收藏為 Idempotent，不建立重複資料。"""
    if product_repository.get_by_id(db, product_id) is None:
        raise AppError(404, "PRODUCT_NOT_FOUND", "找不到指定的商品。")

    if favorite_repository.get(db, user_id, product_id) is None:
        favorite_repository.add(db, user_id, product_id)

    return AddFavoriteResponse(product_id=product_id, is_favorited=True)


def remove_favorite(db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
    """依 API Design §16.3：未收藏時仍可回傳成功（Idempotent）。"""
    favorite_repository.remove(db, user_id, product_id)
