import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import AppUser


def get_by_email(db: Session, email: str) -> AppUser | None:
    """取一般用戶（非管理員）帳號。

    管理員與一般用戶是分開的兩套身分（使用者 2026-07-31 裁決），同一個 Email
    可以同時存在一個管理員帳號與一個一般用戶帳號，因此「這個 Email 能不能註冊」
    只看一般用戶那一側。要連管理員一起找請用 list_by_email。
    """
    stmt = (
        select(AppUser)
        .where(func.lower(AppUser.email) == func.lower(email))
        .where(AppUser.role != UserRole.ADMIN)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_by_email(db: Session, email: str) -> list[AppUser]:
    """同一個 Email 底下的所有帳號（可能是一般用戶與管理員各一）。

    管理員排在前面：登入時逐一比對密碼，兩邊密碼剛好相同時以管理員身分登入，
    這樣既有管理員帳號的登入行為不會因為別人用同 Email 註冊而改變。
    """
    stmt = (
        select(AppUser)
        .where(func.lower(AppUser.email) == func.lower(email))
        .order_by((AppUser.role != UserRole.ADMIN).asc())
    )
    return list(db.execute(stmt).scalars())


def get_by_id(db: Session, user_id: uuid.UUID) -> AppUser | None:
    return db.get(AppUser, user_id)


def get_all_user_ids(db: Session) -> list[uuid.UUID]:
    return [row[0] for row in db.execute(select(AppUser.id)).all()]
