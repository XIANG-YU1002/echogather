from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import TokenExpiredError, TokenInvalidError, decode_access_token
from app.models.enums import UserRole
from app.models.group_leader import GroupLeaderProfile
from app.models.user import AppUser
from app.repositories import group_leader_repository
from app.services.group_leader_service import is_profile_complete

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "get_current_member_user",
    "get_current_group_leader_profile",
    "get_current_active_group_leader_profile",
    "get_current_admin_user",
    "PaginationParams",
]

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser:
    """依 Business Rules §31.1 / API Design §4.5：驗證 Token 簽章、到期時間及使用者存在。"""
    if credentials is None:
        raise AppError(401, "AUTH_TOKEN_MISSING", "請先登入。")

    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise AppError(401, "AUTH_TOKEN_EXPIRED", "登入已過期，請重新登入。") from exc
    except TokenInvalidError as exc:
        raise AppError(401, "AUTH_TOKEN_INVALID", "登入資訊無效，請重新登入。") from exc

    user = db.get(AppUser, user_id)
    if user is None:
        raise AppError(401, "AUTH_TOKEN_INVALID", "登入資訊無效，請重新登入。")
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser | None:
    """公開 API 可選擇性辨識目前使用者（例如商品詳情的 is_favorited），Token 缺漏或無效時視為訪客。"""
    if credentials is None:
        return None
    try:
        user_id = decode_access_token(credentials.credentials)
    except (TokenExpiredError, TokenInvalidError):
        return None
    return db.get(AppUser, user_id)


def get_current_member_user(
    current_user: AppUser = Depends(get_current_user),
) -> AppUser:
    """依 CD §2.2/§3.1/§13.1（D-06）：Admin 是獨立管理用途帳號，不得使用收藏、
    購物車、訂單、團主申請與團主後台；會員專屬 API 一律掛本 Dependency。"""
    if current_user.role == UserRole.ADMIN:
        raise AppError(
            403, "ADMIN_MEMBER_ACCESS_FORBIDDEN", "管理員帳號不可使用會員或團主功能。"
        )
    return current_user


def get_current_group_leader_profile(
    current_user: AppUser = Depends(get_current_member_user),
    db: Session = Depends(get_db),
) -> GroupLeaderProfile:
    """依 API Design §4.6：需已擁有 group_leader_profile（資料不須已完成）。
    掛在 get_current_member_user 之下，Admin 會先收到 403 角色拒絕（D-06，FR-006），
    而不是 404 GROUP_LEADER_PROFILE_NOT_FOUND。"""
    profile = group_leader_repository.get_profile_by_user_id(db, current_user.id)
    if profile is None:
        raise AppError(404, "GROUP_LEADER_PROFILE_NOT_FOUND", "找不到團主資料。")
    return profile


def get_current_active_group_leader_profile(
    profile: GroupLeaderProfile = Depends(get_current_group_leader_profile),
) -> GroupLeaderProfile:
    """依 API Design §4.6：管理開團、訂單及公告等操作，還需團主公開資料已完成。"""
    if not is_profile_complete(profile):
        raise AppError(403, "GROUP_LEADER_PROFILE_INCOMPLETE", "團主公開資料尚未完成。")
    return profile


def get_current_admin_user(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    """依 API Design §4.7：所有 /admin/* API 需 app_user.role = admin。"""
    if current_user.role != UserRole.ADMIN:
        raise AppError(403, "PERMISSION_DENIED", "沒有管理員權限。")
    return current_user


class PaginationParams:
    """統一分頁參數，依 API Design §7.1/§7.2：預設 page=1、page_size=20，上限 100。"""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
