import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_member_user, get_db
from app.core.responses import envelope, paginated_envelope
from app.models.user import AppUser
from app.schemas.favorite import FavoriteSort
from app.services import favorite_service

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/products")
def get_favorite_products(
    sort: FavoriteSort = FavoriteSort.CREATED_DESC,
    pagination: PaginationParams = Depends(),
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = favorite_service.list_favorites(
        db, current_user.id, pagination.page, pagination.page_size, sort
    )
    return paginated_envelope(
        [i.model_dump(mode="json") for i in items], pagination.page, pagination.page_size, total
    )


@router.post("/products/{product_id}", status_code=status.HTTP_201_CREATED)
def add_favorite_product(
    product_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> dict:
    result = favorite_service.add_favorite(db, current_user.id, product_id)
    return envelope(result.model_dump(mode="json"))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_product(
    product_id: uuid.UUID,
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> None:
    favorite_service.remove_favorite(db, current_user.id, product_id)
