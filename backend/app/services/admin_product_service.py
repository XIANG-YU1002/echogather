import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import Currency
from app.models.product import Product
from app.repositories import activity_repository, character_repository, product_repository
from app.schemas.admin_product import (
    CharacterSelection,
    CreateProductRequest,
    ProductAdminActivityRef,
    ProductAdminCharacterItem,
    ProductAdminDetailResponse,
    ProductAdminImageItem,
    ProductAdminListItem,
    UpdateProductRequest,
)


def _load_product_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = product_repository.get_by_id(db, product_id)
    if product is None:
        raise AppError(404, "PRODUCT_NOT_FOUND", "找不到指定的商品。")
    return product


def _resolve_characters(db: Session, selections: list[CharacterSelection]) -> list[uuid.UUID]:
    """依 API Design §28.2：驗證既有角色、正規化新角色並防止大小寫不敏感重複建立。"""
    character_ids: list[uuid.UUID] = []
    for selection in selections:
        if selection.id is not None:
            character = character_repository.get_by_id(db, selection.id)
            if character is None:
                raise AppError(404, "CHARACTER_NOT_FOUND", "找不到指定的角色。")
            character_ids.append(character.id)
        else:
            existing = character_repository.get_by_name_case_insensitive(db, selection.new_name)
            if existing is not None:
                character_ids.append(existing.id)
            else:
                created = character_repository.create(db, selection.new_name)
                character_ids.append(created.id)
    return list(dict.fromkeys(character_ids))


def _to_detail(db: Session, product: Product) -> ProductAdminDetailResponse:
    activity = activity_repository.get_by_id(db, product.activity_id)
    images = product_repository.get_images(db, product.id)
    characters = product_repository.get_characters(db, product.id)

    return ProductAdminDetailResponse(
        id=product.id,
        name=product.name,
        official_price=product.official_price,
        official_currency=product.official_currency,
        # 排除自己：供前端判斷幣別能不能改（同活動必須一致）
        activity_currency=product_repository.get_activity_currency(
            db, product.activity_id, exclude_product_id=product.id
        ),
        primary_image_url=product.primary_image_url,
        is_active=product.is_active,
        activity=ProductAdminActivityRef.model_validate(activity, from_attributes=True),
        images=[ProductAdminImageItem.model_validate(i, from_attributes=True) for i in images],
        characters=[
            ProductAdminCharacterItem.model_validate(c, from_attributes=True) for c in characters
        ],
        group_buy_count=product_repository.get_group_buy_count_for_product(db, product.id),
        favorite_count=product_repository.get_favorite_count(db, product.id),
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _validate_activity_currency(
    db: Session,
    activity_id: uuid.UUID,
    official_currency: Currency | None,
    *,
    exclude_product_id: uuid.UUID | None = None,
) -> None:
    """同一活動的商品幣別必須一致（使用者 2026-07-30 規則）。

    在後端驗證而不只靠前端限制：同一活動的商品可能由不同管理員、不同時間建立，
    只有這裡擋得住「有的台幣有的日圓」的資料。
    """
    if official_currency is None:
        return
    existing = product_repository.get_activity_currency(
        db, activity_id, exclude_product_id=exclude_product_id
    )
    if existing is not None and existing != official_currency:
        raise AppError(
            409,
            "ACTIVITY_CURRENCY_MISMATCH",
            f"此活動的商品幣別為 {existing}，同一活動內必須使用相同幣別。",
            {"activity_currency": existing, "provided_currency": official_currency},
        )


def create_product(db: Session, payload: CreateProductRequest) -> ProductAdminDetailResponse:
    """依 Business Rules §11.2/§11.3：商品必須屬於活動、同活動內名稱不可重複。

    幣別另依使用者 2026-07-30 規則：同一活動內必須一致。
    """
    activity = activity_repository.get_by_id(db, payload.activity_id)
    if activity is None:
        raise AppError(404, "ACTIVITY_NOT_FOUND", "找不到指定的活動。")
    if product_repository.name_exists_in_activity(db, activity.id, payload.name):
        raise AppError(409, "CONFLICT", "此活動內已有相同名稱的商品。")

    official_currency = (
        (payload.official_currency or Currency.TWD) if payload.official_price is not None else None
    )
    _validate_activity_currency(db, activity.id, official_currency)

    product = product_repository.create_product(
        db,
        activity_id=activity.id,
        name=payload.name,
        official_price=payload.official_price,
        official_currency=official_currency,
        primary_image_url=payload.primary_image_url,
        is_active=True,
    )

    character_ids = _resolve_characters(db, payload.characters)
    if character_ids:
        product_repository.link_characters(db, product.id, character_ids)

    db.commit()
    return _to_detail(db, product)


def get_products(
    db: Session,
    *,
    activity_id: uuid.UUID | None,
    is_active: bool | None,
    character_id: uuid.UUID | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> tuple[list[ProductAdminListItem], int]:
    products, total = product_repository.list_products_admin(
        db,
        activity_id=activity_id,
        is_active=is_active,
        character_id=character_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = []
    for product in products:
        activity = activity_repository.get_by_id(db, product.activity_id)
        items.append(
            ProductAdminListItem(
                id=product.id,
                name=product.name,
                primary_image_url=product.primary_image_url,
                is_active=product.is_active,
                activity=ProductAdminActivityRef.model_validate(activity, from_attributes=True),
                official_price=product.official_price,
                official_currency=product.official_currency,
                characters=[
                    ProductAdminCharacterItem.model_validate(c, from_attributes=True)
                    for c in product_repository.get_characters(db, product.id)
                ],
                created_at=product.created_at,
            )
        )
    return items, total


def get_product_detail(db: Session, product_id: uuid.UUID) -> ProductAdminDetailResponse:
    product = _load_product_or_404(db, product_id)
    return _to_detail(db, product)


def update_product(
    db: Session, product_id: uuid.UUID, payload: UpdateProductRequest
) -> ProductAdminDetailResponse:
    product = _load_product_or_404(db, product_id)
    provided = payload.model_fields_set

    if "name" in provided:
        if product_repository.name_exists_in_activity(
            db, product.activity_id, payload.name, exclude_product_id=product.id
        ):
            raise AppError(409, "CONFLICT", "此活動內已有相同名稱的商品。")
        product.name = payload.name

    if "official_price" in provided:
        next_currency = (
            (payload.official_currency or Currency.TWD)
            if payload.official_price is not None
            else None
        )
        # 排除自己：改成與其他商品一致的幣別要放行，不能被自己的舊值擋住
        _validate_activity_currency(
            db, product.activity_id, next_currency, exclude_product_id=product.id
        )
        product.official_price = payload.official_price
        product.official_currency = next_currency

    if "primary_image_url" in provided:
        product.primary_image_url = payload.primary_image_url

    if "characters" in provided:
        product_repository.unlink_all_characters(db, product.id)
        character_ids = _resolve_characters(db, payload.characters)
        if character_ids:
            product_repository.link_characters(db, product.id, character_ids)

    db.commit()
    return _to_detail(db, product)


def deactivate_product(db: Session, product_id: uuid.UUID) -> ProductAdminDetailResponse:
    """依 Business Rules §11.4：下架不刪除收藏、歷史開團、訂單或圖片。"""
    product = _load_product_or_404(db, product_id)
    if not product.is_active:
        raise AppError(409, "PRODUCT_ALREADY_INACTIVE", "商品已經是下架狀態。")
    product.is_active = False
    db.commit()
    return _to_detail(db, product)


def reactivate_product(db: Session, product_id: uuid.UUID) -> ProductAdminDetailResponse:
    product = _load_product_or_404(db, product_id)
    if product.is_active:
        raise AppError(409, "PRODUCT_ALREADY_ACTIVE", "商品已經是上架狀態。")
    product.is_active = True
    db.commit()
    return _to_detail(db, product)


def add_image(db: Session, product_id: uuid.UUID, image_url: str) -> ProductAdminDetailResponse:
    """依 API Design §28.7：新增後預設放在最後。"""
    product = _load_product_or_404(db, product_id)
    next_order = product_repository.get_max_image_sort_order(db, product.id) + 1
    product_repository.create_image(db, product.id, image_url, next_order)
    db.commit()
    return _to_detail(db, product)


def _load_owned_image(db: Session, product: Product, image_id: uuid.UUID):
    image = product_repository.get_image_by_id(db, image_id)
    if image is None or image.product_id != product.id:
        raise AppError(404, "RESOURCE_NOT_FOUND", "找不到指定的圖片。")
    return image


def update_image(
    db: Session, product_id: uuid.UUID, image_id: uuid.UUID, image_url: str
) -> ProductAdminDetailResponse:
    product = _load_product_or_404(db, product_id)
    image = _load_owned_image(db, product, image_id)
    image.image_url = image_url
    db.commit()
    return _to_detail(db, product)


def delete_image(db: Session, product_id: uuid.UUID, image_id: uuid.UUID) -> ProductAdminDetailResponse:
    """依 API Design §28.10：主要圖片不可透過此 Endpoint 刪除（額外圖片與主要圖片為不同欄位/資料表）。"""
    product = _load_product_or_404(db, product_id)
    image = _load_owned_image(db, product, image_id)
    product_repository.delete_image(db, image)
    db.commit()
    return _to_detail(db, product)


def reorder_images(
    db: Session, product_id: uuid.UUID, ordered_image_ids: list[uuid.UUID]
) -> ProductAdminDetailResponse:
    product = _load_product_or_404(db, product_id)
    existing_ids = {image.id for image in product_repository.get_images(db, product.id)}
    if set(ordered_image_ids) != existing_ids:
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "輸入資料格式不正確。",
            {"fields": {"ordered_image_ids": ["必須包含此商品全部額外圖片的完整排列。"]}},
        )
    product_repository.reorder_images(db, product.id, ordered_image_ids)
    db.commit()
    return _to_detail(db, product)
