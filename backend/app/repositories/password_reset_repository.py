import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_reset import PasswordResetToken


def create(
    db: Session,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    created_at: datetime,
) -> PasswordResetToken:
    """明確帶入 created_at，與驗證碼同樣避免混用資料庫與應用端兩個時鐘。"""
    record = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=created_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest_by_user(db: Session, user_id: uuid.UUID) -> PasswordResetToken | None:
    stmt = (
        select(PasswordResetToken)
        .where(PasswordResetToken.user_id == user_id)
        .order_by(PasswordResetToken.created_at.desc(), PasswordResetToken.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_usable_by_hash(
    db: Session, token_hash: str, now: datetime
) -> PasswordResetToken | None:
    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.consumed_at.is_(None),
        PasswordResetToken.expires_at > now,
    )
    return db.execute(stmt).scalar_one_or_none()


def invalidate_unconsumed(db: Session, user_id: uuid.UUID, now: datetime) -> None:
    """讓該會員先前未使用的重設連結立刻失效，避免同時存在多條可用連結。"""
    records = (
        db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.consumed_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    for record in records:
        record.expires_at = now - timedelta(seconds=1)
    db.flush()


def mark_consumed(db: Session, record: PasswordResetToken, now: datetime) -> None:
    record.consumed_at = now
    db.flush()
