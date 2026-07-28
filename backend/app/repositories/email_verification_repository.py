from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.verification import EmailVerificationCode


def create(
    db: Session, email: str, code_hash: str, expires_at: datetime, created_at: datetime
) -> EmailVerificationCode:
    """明確帶入 created_at，不使用 server default。

    server default 是 PostgreSQL 的 now()，與應用端 datetime.now() 是不同時鐘；
    兩者混用會讓「距離上次寄送幾秒」算錯（實測本機與資料庫相差約 36 秒）。
    """
    record = EmailVerificationCode(
        email=email, code_hash=code_hash, expires_at=expires_at, created_at=created_at
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest(db: Session, email: str) -> EmailVerificationCode | None:
    stmt = (
        select(EmailVerificationCode)
        .where(EmailVerificationCode.email == email)
        .order_by(EmailVerificationCode.created_at.desc(), EmailVerificationCode.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_usable(db: Session, email: str, now: datetime) -> EmailVerificationCode | None:
    """最新一筆尚未使用且未過期的驗證碼。"""
    stmt = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == email,
            EmailVerificationCode.consumed_at.is_(None),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc(), EmailVerificationCode.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def count_since(db: Session, email: str, since: datetime) -> int:
    stmt = (
        select(func.count())
        .select_from(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == email,
            EmailVerificationCode.created_at >= since,
        )
    )
    return db.execute(stmt).scalar_one()


def invalidate_unconsumed(db: Session, email: str, now: datetime) -> None:
    """讓該 Email 先前未使用的驗證碼立刻失效，避免同時存在多組可用驗證碼。"""
    records = (
        db.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.consumed_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    for record in records:
        record.expires_at = now - timedelta(seconds=1)
    db.flush()


def mark_attempt(db: Session, record: EmailVerificationCode) -> None:
    record.attempt_count += 1
    db.commit()


def mark_consumed(db: Session, record: EmailVerificationCode) -> None:
    record.consumed_at = datetime.now(timezone.utc)
    db.flush()
