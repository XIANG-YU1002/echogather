import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core import supabase_storage
from app.core.config import settings
from app.core.errors import AppError
from app.models.enums import UserRole
from app.models.user import AppUser

ALLOWED_CATEGORIES = {"avatar", "activity", "product"}

_ADMIN_ONLY_CATEGORIES = {"activity", "product"}

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}


def _check_permission(current_user: AppUser, category: str) -> None:
    """依 Business Rules §13.6：Avatar 為已登入會員；Activity／Product 僅限管理員。"""
    if category in _ADMIN_ONLY_CATEGORIES and current_user.role != UserRole.ADMIN:
        raise AppError(403, "UPLOAD_PERMISSION_DENIED", "沒有上傳此類圖片的權限。")


def _validate_declared_type(content_type: str | None, filename: str | None) -> None:
    if content_type is None or content_type.lower() not in _ALLOWED_CONTENT_TYPES:
        raise AppError(415, "UPLOAD_FILE_TYPE_NOT_SUPPORTED", "不支援的圖片格式。")

    extension = Path(filename or "").suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise AppError(415, "UPLOAD_FILE_TYPE_NOT_SUPPORTED", "不支援的圖片格式。")


def _load_and_verify_image(raw: bytes) -> Image.Image:
    """依 Business Rules §13.1／§31.4：驗證實際檔案內容，不只信任副檔名與 Content-Type。"""
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AppError(422, "UPLOAD_FILE_INVALID", "圖片檔案無法辨識或已損壞。") from exc

    image = Image.open(io.BytesIO(raw))
    if image.format not in _ALLOWED_PIL_FORMATS:
        raise AppError(415, "UPLOAD_FILE_TYPE_NOT_SUPPORTED", "不支援的圖片格式。")
    return image


def save_image(
    current_user: AppUser,
    category: str,
    *,
    raw: bytes,
    content_type: str | None,
    filename: str | None,
) -> dict:
    if category not in ALLOWED_CATEGORIES:
        raise AppError(422, "UPLOAD_CATEGORY_INVALID", "不支援的圖片分類。")

    _check_permission(current_user, category)

    if len(raw) > settings.max_upload_file_size_bytes:
        raise AppError(413, "UPLOAD_FILE_TOO_LARGE", "圖片檔案過大。")

    _validate_declared_type(content_type, filename)
    image = _load_and_verify_image(raw)

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="WEBP")
    webp_bytes = buffer.getvalue()

    now = datetime.now(timezone.utc)
    stored_filename = f"{uuid.uuid4().hex}.webp"
    object_path = f"{category}/{now.year:04d}/{now.month:02d}/{stored_filename}"

    public_url = supabase_storage.upload_bytes(object_path, webp_bytes, content_type="image/webp")

    return {
        "url": public_url,
        "category": category,
        "content_type": "image/webp",
        "size": len(webp_bytes),
    }
