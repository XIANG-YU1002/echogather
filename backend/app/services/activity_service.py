import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import ActivityStatus
from app.repositories import activity_repository, product_repository
from app.schemas.activity import ActivityDetailResponse, ActivityListItem, ActivityProductCard
from app.schemas.product import CharacterSummary


def list_activities(
    db: Session, status: ActivityStatus | None, page: int, page_size: int
) -> tuple[list[ActivityListItem], int]:
    activities, total = activity_repository.list_activities(db, status, page, page_size)
    items = [ActivityListItem.model_validate(a, from_attributes=True) for a in activities]
    return items, total


def get_activity_detail(db: Session, activity_id: uuid.UUID) -> ActivityDetailResponse:
    activity = activity_repository.get_by_id(db, activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "找不到指定的活動。")
    return ActivityDetailResponse.model_validate(activity, from_attributes=True)


def get_activity_products(db: Session, activity_id: uuid.UUID) -> list[ActivityProductCard]:
    activity = activity_repository.get_by_id(db, activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "找不到指定的活動。")

    products = activity_repository.list_active_products_by_activity(db, activity_id)
    # 角色一次查完再組裝，避免每項商品各打一次 DB
    characters_by_product = product_repository.get_characters_for_products(
        db, [product.id for product in products]
    )
    return [
        ActivityProductCard(
            id=product.id,
            name=product.name,
            primary_image_url=product.primary_image_url,
            official_price=product.official_price,
            official_currency=product.official_currency,
            characters=[
                CharacterSummary(id=character.id, name=character.name)
                for character in characters_by_product.get(product.id, [])
            ],
        )
        for product in products
    ]
